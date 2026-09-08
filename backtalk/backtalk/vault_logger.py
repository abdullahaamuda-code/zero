# backtalk: talk to your agent out loud.
# ZeroVault Session Logger: auto-summarize and persist voice sessions to the vault.
"""Automatic session summarizer and vault logger for Zero.

Upon voice session hang-up, exit, or disconnect, this module compiles
the session transcript, tools run, files modified, and topics discussed,
and automatically updates today's Daily Note in ZeroVault
(01 - Daily Notes/<YYYY-MM-DD>.md) following the exact vault format rules.
"""

from datetime import datetime
import os
from pathlib import Path
import re
import tempfile
import time

from backtalk.config import CFG
from backtalk.vlog import log

_LOGGED = False  # Ensure single write per voice session run


def get_vault_path() -> Path:
    """Locate the memory vault root directory."""
    for d in CFG.get("extra_dirs", []):
        if "vault" in str(d).lower():
            p = Path(os.path.expanduser(str(d)))
            if not p.is_absolute():
                p = (Path(CFG.get("agent_dir", ".")).resolve() / p).resolve()
            if p.exists():
                return p
    env_vault = os.environ.get("ZERO_VAULT")
    if env_vault:
        p = Path(os.path.expanduser(env_vault))
        if p.exists():
            return p
    agent_vault = Path(CFG.get("agent_dir", ".")).resolve() / "vault"
    if agent_vault.exists():
        return agent_vault
    for cand in ("~/ZeroVault", "~/vault"):
        p = Path(os.path.expanduser(cand))
        if p.exists():
            return p
    return agent_vault


def get_daily_note_path(vault_dir: Path, today: datetime | None = None) -> Path:
    """Find or determine today's daily note path."""
    today = today or datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    notes_dir = vault_dir / "01 - Daily Notes"
    
    # 1. Check direct file: 01 - Daily Notes/YYYY-MM-DD.md
    direct = notes_dir / f"{date_str}.md"
    if direct.exists():
        return direct
        
    # 2. Check month subfolder: 01 - Daily Notes/NN - Month YYYY/YYYY-MM-DD.md
    month_folder = notes_dir / f"{today.strftime('%m - %B %Y')}"
    if month_folder.exists():
        sub = month_folder / f"{date_str}.md"
        if sub.exists():
            return sub
        return sub
        
    return direct


def create_daily_note_if_missing(daily_note_path: Path, vault_dir: Path, today: datetime | None = None) -> None:
    """Create today's daily note from the template if it does not yet exist."""
    if daily_note_path.exists():
        return
        
    today = today or datetime.now()
    daily_note_path.parent.mkdir(parents=True, exist_ok=True)
    template_path = vault_dir / "01 - Daily Notes" / "Daily Note Template.md"
    
    if template_path.exists():
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Fill placeholders
            content = content.replace("{{date}}", today.strftime("%Y-%m-%d"))
            content = content.replace("{{Day of week}}", today.strftime("%A"))
            content = content.replace("{{Month}}", today.strftime("%B"))
            content = content.replace("{{Day}}", str(today.day))
            content = content.replace("{{Year}}", today.strftime("%Y"))
            content = content.replace("{{time}}", today.strftime("%H:%M"))
            content = content.replace("{{topic}}", "Startup")
            with open(daily_note_path, "w", encoding="utf-8") as f:
                f.write(content)
            log(f"[vault] Created daily note from template: {daily_note_path.name}")
            return
        except Exception as e:
            log(f"[vault] Error creating daily note from template: {e}")

    # Fallback standard daily note structure
    fallback = f"""---
status: active
project: meta
type: log
created: {today.strftime("%Y-%m-%d")}
---

# {today.strftime("%A, %B %d, %Y")}

## Index

"""
    with open(daily_note_path, "w", encoding="utf-8") as f:
        f.write(fallback)
    log(f"[vault] Created standard daily note: {daily_note_path.name}")


def clean_utterance(text: str) -> str:
    """Clean speech-to-text filler prefixes and artifacts."""
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r'^(okay\s+so\s+|so\s+yh\s+|okay\s+|hey\s+zero\s+|zero\s+|well\s+man\s+)+', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def summarize_session(turns: list[dict], actions: list[dict] | None = None) -> dict:
    """Compile structured session data from turns and tool executions."""
    actions = actions or []
    files_touched = set()
    commands_run = []

    for a in actions:
        args = a.get("args") or {}
        tool = str(a.get("tool") or "")
        f = args.get("path") or args.get("file_path") or args.get("TargetFile") or args.get("file")
        if f:
            files_touched.add(str(f).replace("/", "\\"))
        cmd = args.get("command") or args.get("CommandLine")
        if cmd:
            commands_run.append(str(cmd)[:80])

    what_got_done = []
    topics = []

    for turn in turns:
        u = turn.get("user") or ""
        u_clean = clean_utterance(u)
        if not u_clean:
            continue
        snippet = u_clean[:140].rsplit(" ", 1)[0] + "..." if len(u_clean) > 140 else u_clean

        low = u_clean.lower()
        if any(k in low for k in ("who you are", "about yourself", "what you can do", "capabilities")):
            topics.append("Operator Capabilities")
        elif any(k in low for k in ("linkedin", "post", "video")):
            topics.append("LinkedIn Showcase Post")
        elif any(k in low for k in ("sessions", "session history", "mix ideas")):
            topics.append("Session Architecture & Isolation")
        elif any(k in low for k in ("voice", "mic", "ptt", "hands free")):
            topics.append("Voice & Mic Controls")

        user_name = CFG.get("user_name", "Operator")
        what_got_done.append(f"- **{user_name}:** \"{snippet}\"")
        reply = (turn.get("reply") or "").strip()
        if reply:
            reply_snip = reply[:140].rsplit(" ", 1)[0] + "..." if len(reply) > 140 else reply
            what_got_done.append(f"  - **Zero:** {reply_snip}")

    # Add tool action summary
    for f in sorted(files_touched):
        base = os.path.basename(f)
        what_got_done.append(f"- Wrote/modified `{base}` at `{f}`.")
    for cmd in commands_run:
        what_got_done.append(f"- Executed `{cmd}`.")

    # Deduplicate topics
    unique_topics = []
    for t in topics:
        if t not in unique_topics:
            unique_topics.append(t)

    if unique_topics:
        topic_title = " & ".join(unique_topics[:2])
    elif files_touched:
        topic_title = "Work on " + ", ".join([os.path.basename(f) for f in list(files_touched)[:2]])
    elif turns:
        first_clean = clean_utterance(turns[0].get("user", ""))
        topic_title = (first_clean[:36] + "...") if len(first_clean) > 36 else first_clean
    else:
        topic_title = "Voice Dialogue & Tool Execution"

    index_summary = f"{len(turns)} turns spoken"
    if files_touched:
        index_summary += f", touched {len(files_touched)} files"

    return {
        "title": topic_title,
        "index_summary": index_summary,
        "what_got_done": what_got_done,
        "notes_touched": sorted(list(files_touched)),
    }


def update_daily_note_content(content: str, summary_data: dict, session_time: str | None = None) -> str:
    """Format and insert the new session into the daily note markdown."""
    session_time = session_time or datetime.now().strftime("%H:%M")

    # 1. Find max session number
    session_nums = [int(m.group(1)) for m in re.finditer(r"^##\s+Session\s+(\d+)", content, re.MULTILINE)]
    next_num = max(session_nums) + 1 if session_nums else 1

    # 2. Prepare Session Block
    title = summary_data["title"]
    index_line = f"- **Voice Session {next_num}: {title}** — {summary_data['index_summary']}."

    block_lines = [
        f"## Session {next_num} — {session_time}: Voice Session: {title}",
        "",
        "### What Got Done",
    ]
    block_lines.extend(summary_data["what_got_done"])
    block_lines.extend([
        "",
        "### What's Still In Progress",
        "- None / Completed live in session.",
        "",
        "### Decisions Made",
        "- Spoken turns recorded and auto-summarized to vault.",
        "",
        "### Notes Touched",
    ])
    if summary_data["notes_touched"]:
        for n in summary_data["notes_touched"]:
            block_lines.append(f"- {n}")
    else:
        block_lines.append("- None")

    block_lines.append("")
    new_session_block = "\n".join(block_lines)

    # 3. Insert into ## Index
    index_match = re.search(r"(##\s+Index\s*\n\n)([\s\S]*?)(?=\n##\s+Session|\n---\n|$)", content)
    if index_match:
        existing_index = index_match.group(2).rstrip()
        updated_index = existing_index + "\n" + index_line if existing_index else index_line
        new_content = content[:index_match.start(2)] + updated_index + "\n\n" + content[index_match.end(2):].lstrip("\n")
    else:
        new_content = content + "\n\n" + index_line

    # 4. Append the new session block
    new_content = new_content.rstrip() + "\n\n" + new_session_block + "\n"
    return new_content


def log_session_to_vault(turns: list[dict], actions: list[dict] | None = None,
                         model: str | None = None, start_time: datetime | None = None) -> bool:
    """Commit session summary directly to today's daily note in ZeroVault."""
    global _LOGGED
    if _LOGGED:
        return False
    if not turns and not actions:
        log("[vault] No turns or actions in session; skipping vault log.")
        return False

    now = datetime.now()
    vault_dir = get_vault_path()
    daily_note = get_daily_note_path(vault_dir, now)

    create_daily_note_if_missing(daily_note, vault_dir, now)

    try:
        with open(daily_note, "r", encoding="utf-8") as f:
            content = f.read()

        summary_data = summarize_session(turns, actions)
        updated_content = update_daily_note_content(content, summary_data, now.strftime("%H:%M"))

        # Atomic write
        tmp_dir = daily_note.parent
        fd, tmp_path = tempfile.mkstemp(prefix="daily_note_", suffix=".tmp", dir=str(tmp_dir))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(updated_content)

        os.replace(tmp_path, str(daily_note))
        _LOGGED = True
        log(f"[vault] Voice session automatically logged to {daily_note.name} ({summary_data['title']})")
        return True
    except Exception as e:
        log(f"[vault] Failed to log session to vault: {e}")
        return False
