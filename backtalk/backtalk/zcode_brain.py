# backtalk: talk to your agent out loud.
# Zero-brain: a persistent conversation via the ZCode app-server.
#
# Same interface contract as brain.WarmBrain (main.py cannot tell them
# apart): start / ask_stream / interrupt / reset_turn / stop / command /
# set_permission_mode / context_usage / session / model. The substrate
# is the ZCode CLI's "app-server" — a stdio JSON protocol (wire format:
# {"id","method","params"} requests, {"id","result"} responses,
# {"id","method","params"} server->client requests which MUST be
# answered, and notifications) — discovered empirically on 2026-09-07:
#
#   session/create  {workspace:{workspaceKey, workspacePath}} -> result.session.sessionId
#   session/send    {sessionId, content, inputId} -> {accepted}
#   session/messages{sessionId} -> {messages:[{info,parts:[{type:"text",text}]}]}
#   turn lifecycle arrives as computer-use/operation-event notifications
#   with params.kind "turn-started" / "turn-completed"
#   session/stop interrupts; session/compact compacts; session/setModel
#   switches models mid-session
#
# One process lives for the whole voice session: no per-turn spawn, no
# per-turn bootstrap. The session cwd is agent_dir, so the AGENTS.md
# that lives there defines who is speaking. Streaming comes from
# polling session/messages (~3x/sec, local stdio) and diffing the
# newest assistant text: sentences reach the mouth while the rest of
# the thought is still forming. backtalk adds only the spoken-delivery
# discipline (config.DISCIPLINE) on the FIRST prompt of a session.
"""The Zero brain — persistent session over the ZCode app-server."""
import asyncio
import json
import os
import re
import shutil

from backtalk.config import CFG, DISCIPLINE
from backtalk.vlog import log

SESSION_FILE = os.path.join(CFG["signals_dir"], ".backtalk_session")

_SENTENCE_END = re.compile(r"(?<=[.!?])\s")
_POLL_S = 0.3
_TURN_TIMEOUT_S = 300


def _zcode_command() -> list[str] | None:
    """[node, zcode.cjs] — the CLI bundled with the ZCode desktop app,
    or a standalone zcode on PATH. Config key zcode_cli overrides."""
    cli = str(CFG.get("zcode_cli") or "").strip()
    if cli:
        cli = os.path.expanduser(cli)
        if os.path.exists(cli):
            return [shutil.which("node") or "node", cli]
        log(f"[zbrain] zcode_cli path does not exist: {cli}")
    exe = shutil.which("zcode")
    if exe:
        return [exe]
    for cand in (
            os.path.expandvars(
                r"%LOCALAPPDATA%\Programs\ZCode\resources\glm\zcode.cjs"),
            os.path.expanduser(
                "~/.local/share/zcode/resources/glm/zcode.cjs")):
        if os.path.exists(cand):
            return [shutil.which("node") or "node", cand]
    return None


class _ProcDead(Exception):
    pass


class AdaptiveVoiceTokenizer:
    """Natural breath-phrased tokenizer.
    Ensures:
    1. First chunk emits on a complete first sentence, or at a natural clause only if 6+ words.
    2. Never splits into 1-2 word orphan fragments (e.g., never leaves short names alone).
    3. Subsequent chunks are full sentences or natural conversational thoughts.
    """
    SENTENCE_RE = re.compile(r'^(.*?[.!?](\s+|$))(.*)$', re.DOTALL)
    CLAUSE_RE = re.compile(r'^(.*?([,;:—\n]|\s[-–]\s))(.*)$', re.DOTALL)

    def __init__(self, min_first_words: int = 6, min_chunk_words: int = 3):
        self.buffer = ""
        self.is_first = True
        self.min_first_words = min_first_words
        self.min_chunk_words = min_chunk_words

    def feed(self, delta: str):
        self.buffer += delta
        out = []
        while self.buffer:
            words = self.buffer.strip().split()
            if not words:
                break

            if self.is_first:
                # Check for full sentence first
                m_sent = self.SENTENCE_RE.match(self.buffer)
                if m_sent:
                    chunk = m_sent.group(1).strip()
                    # If sentence is tiny (< 3 words) and more text is buffered, wait or merge
                    if len(chunk.split()) < self.min_chunk_words and len(words) < self.min_first_words:
                        break
                    self.buffer = m_sent.group(3)
                    self.is_first = False
                    if chunk:
                        out.append(chunk)
                    continue

                # If no sentence boundary yet, but buffer is long enough (>= min_first_words)
                if len(words) >= self.min_first_words:
                    m_clause = self.CLAUSE_RE.match(self.buffer)
                    if m_clause and len(m_clause.group(1).split()) >= 4:
                        chunk = m_clause.group(1).strip()
                        self.buffer = m_clause.group(3)
                        self.is_first = False
                        if chunk:
                            out.append(chunk)
                        continue
                    elif len(words) >= 10:
                        split_idx = self.buffer.find(words[7]) + len(words[7])
                        chunk = self.buffer[:split_idx].strip()
                        self.buffer = self.buffer[split_idx:].lstrip()
                        self.is_first = False
                        if chunk:
                            out.append(chunk)
                        continue
                break
            else:
                m_sent = self.SENTENCE_RE.match(self.buffer)
                if m_sent:
                    chunk = m_sent.group(1).strip()
                    # If chunk is too tiny (e.g. short greeting) and there's more after it, combine
                    rem_words = m_sent.group(3).strip().split()
                    if len(chunk.split()) < self.min_chunk_words and rem_words:
                        m_next = self.SENTENCE_RE.match(m_sent.group(3))
                        if m_next:
                            merged = chunk + " " + m_next.group(1).strip()
                            self.buffer = m_next.group(3)
                            out.append(merged)
                            continue
                        else:
                            break
                    self.buffer = m_sent.group(3)
                    if chunk:
                        out.append(chunk)
                else:
                    break
        return out

    def flush(self):
        tail = self.buffer.strip()
        self.buffer = ""
        self.is_first = True
        return [tail] if tail else []


def clean_speech_text(text: str) -> str:
    """Strip all markdown formatting, headers, asterisks, bullet dashes,
    code blocks, and artifacts so speech sounds 100% clean and natural."""
    if not text:
        return ""
    # Strip code blocks ```...```
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Strip inline code `code` -> code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Strip markdown links [label](url) -> label
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Strip markdown image tags ![alt](url) -> ''
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    # Strip markdown headers (e.g. ### Heading -> Heading)
    text = re.sub(r'^\s*#{1,6}\s*', '', text, flags=re.MULTILINE)
    # Strip bold/italics
    text = re.sub(r'\*\*([^*]+)\*\*', r' \1 ', text)
    text = re.sub(r'\*([^*]+)\*', r' \1 ', text)
    text = re.sub(r'__([^_]+)__', r' \1 ', text)
    text = re.sub(r'_([^_]+)_', r' \1 ', text)
    # Strip bullet markers at start of lines: - , * , + , •
    text = re.sub(r'^\s*[-*+•]\s+', '', text, flags=re.MULTILINE)
    # Strip any remaining lone asterisks or hashes
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+', '', text)
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _narrate_tool(tool_name: str, args: dict | None = None) -> str:
    """Intelligent, contextual spoken narration when the agent executes actions,
    describing the specific file or command instead of robotic repetition."""
    args = args or {}
    t = str(tool_name or "").lower()

    # Write / Edit / Create file
    if any(k in t for k in ("write", "create", "save", "edit", "patch")):
        f = str(args.get("path") or args.get("file_path") or args.get("TargetFile") or args.get("file") or "").replace("\\", "/")
        base = f.rsplit("/", 1)[-1] if "/" in f else f
        ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
        if "hud" in base.lower() or "html" in ext:
            return f"Building the holographic interface in {base} now..."
        if "script" in base.lower() or "showcase" in base.lower():
            return f"Writing the showcase script into {base}..."
        if ext in ("py", "js", "ts", "cjs"):
            return f"Writing the code into {base}..."
        if ext in ("bat", "ps1", "sh"):
            return "Writing the launcher script..."
        if base:
            return f"Writing {base} now..."
        return "Writing that file now..."

    # Bash / Terminal execution
    if any(k in t for k in ("bash", "exec", "run", "command")):
        cmd = str(args.get("command") or args.get("CommandLine") or "").strip()
        if not cmd:
            return ""
        # Silent for internal workspace checks and find/grep loops
        if any(c in cmd for c in ("find", "ls", "date", "grep", "dir")):
            return ""
        if "start" in cmd and (".html" in cmd or "http" in cmd):
            return "Popping that open on your display..."
        if "git" in cmd:
            return "Checking git status..."
        if any(p in cmd for p in ("npm", "uv", "pip", "sync", "install")):
            return "Syncing packages, one sec..."
        if "test" in cmd or "pytest" in cmd:
            return "Running tests now..."
        return "Executing that command, give me a sec..."

    # Read / View
    if any(k in t for k in ("read", "view", "cat")):
        f = str(args.get("file_path") or args.get("AbsolutePath") or args.get("path") or "").replace("\\", "/")
        base = f.rsplit("/", 1)[-1] if "/" in f else f
        base_low = base.lower()
        # Silent for internal memory/index/daily note reads
        if (not base or "vault-index" in base_low or "active priorities" in base_low
                or "agents.md" in base_low or re.match(r"^\d{4}-\d{2}-\d{2}\.md$", base_low)):
            return ""
        return f"Checking {base}..."

    # Search / Grep
    if any(k in t for k in ("search", "grep", "find")):
        # Silent for internal greps
        return ""

    # Subagent / Agent
    if any(k in t for k in ("subagent", "delegate", "invoke_subagent", "agent")):
        prompt = str(args.get("prompt") or args.get("description") or "").lower()
        if any(w in prompt for w in ("search", "web", "map", "google", "find")):
            return "Searching the web for that now..."
        return "Spawning a subagent for this..."

    return ""


class ZcodeBrain:
    def __init__(self, model: str | None = None, can_use_tool=None,
                 resume_id: str | None = None):
        self.model = model or CFG["model"]
        self._can_use_tool = can_use_tool      # accepted, never consulted
        self.session = {"turns": 0, "out_tokens": 0, "in_tokens": 0,
                        "cost": 0.0}
        self._resume_id = resume_id
        self.session_id: str | None = None
        self._proc: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._pending: dict[object, asyncio.Future] = {}
        self._turn_done: asyncio.Event | None = None
        self._next_id = 100
        self._alive = False
        self._tallied = {}          # assistant msg id -> last (in, out, cache)
        self._narrated_calls: set[str] = set()
        self.session_actions: list[dict] = []

    # ---- wire ----

    def _env(self) -> dict:
        env = dict(os.environ)
        home = str(CFG.get("zcode_home") or "").strip()
        if home:
            # An isolated config home: no desktop MCP servers (their
            # npx spawns cost ~10s per launch), no plugin pile, and a
            # session store the voice line owns. The provider/model
            # config lives in <zcode_home>/.zcode/cli/config.json.
            env["USERPROFILE"] = os.path.expanduser(home)
        return env

    async def _send_wire(self, method: str, params: dict, with_id=True):
        msg = {"method": method, "params": params}
        if with_id:
            self._next_id += 1
            msg["id"] = self._next_id
        if self._proc and self._proc.stdin:
            self._proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
            try:
                await self._proc.stdin.drain()
            except Exception:
                pass
        return msg.get("id")

    async def _request(self, method: str, params: dict, timeout: float = 60):
        wid = await self._send_wire(method, params)
        fut = asyncio.get_running_loop().create_future()
        self._pending[wid] = fut
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            self._pending.pop(wid, None)

    async def _reader(self):
        proc = self._proc
        while True:
            try:
                raw = await proc.stdout.readline()
            except Exception as e:
                log(f"[zbrain] stdout read error: {e}")
                raw = b""
            line = raw.decode("utf-8", "replace") if raw else ""
            if not line:
                self._alive = False
                rc = proc.returncode if proc else None
                log(f"[zbrain] app-server stdout reached EOF (returncode={rc})")
                for f in self._pending.values():
                    if not f.done():
                        f.set_exception(_ProcDead())
                self._pending.clear()
                if self._turn_done:
                    self._turn_done.set()
                return
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            method = msg.get("method") or ""
            if method:
                if "id" in msg:       # server->client request: MUST answer
                    if method == "interaction/requestPermission":
                        result = {"decision": "allow"}
                    elif method == "interaction/requestUserInput":
                        result = {"action": "accept"}
                    elif method == "session/requestRuntimePreferences":
                        result = {"nativeSearchEnhancementsEnabled": False}
                    else:
                        result = msg.get("params") or {}
                    reply = {"id": msg["id"], "result": result}
                    try:
                        proc.stdin.write(
                            (json.dumps(reply) + "\n").encode("utf-8"))
                        await proc.stdin.drain()
                    except Exception:
                        pass
                    if (method == "computer-use/operation-event"
                            and (msg.get("params") or {}).get("kind")
                            == "turn-completed" and self._turn_done):
                        self._turn_done.set()
                    continue
                # one-way notification carrying the turn lifecycle
                if (method == "computer-use/operation-event"
                        and (msg.get("params") or {}).get("kind")
                        == "turn-completed" and self._turn_done):
                    self._turn_done.set()
                continue
            wid = msg.get("id")
            if wid in self._pending:
                fut = self._pending.pop(wid)
                if not fut.done():
                    if "error" in msg:
                        fut.set_exception(RuntimeError(
                            json.dumps(msg["error"])[:400]))
                    else:
                        fut.set_result(msg.get("result"))

    # ---- lifecycle ----

    async def _stderr_logger(self):
        proc = self._proc
        if not (proc and proc.stderr):
            return
        while True:
            try:
                line = await proc.stderr.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", "replace").strip()
                if decoded:
                    log(f"[zcode-stderr] {decoded}")
            except Exception:
                break

    async def _ensure_alive(self):
        if not (self._proc and self._alive and self._proc.returncode is None):
            log("[zbrain] process not active, restarting app-server...")
            await self.stop()
            await self.start()

    async def start(self):
        argv = _zcode_command()
        if argv is None:
            raise RuntimeError(
                "The ZCode CLI was not found. Install the ZCode desktop "
                "app, or point zcode_cli in backtalk.json at zcode.cjs.")
        self._proc = await asyncio.create_subprocess_exec(
            *argv, "--mode", "yolo", "app-server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=16 * 1024 * 1024,
            env=self._env(), cwd=CFG["agent_dir"])
        self._alive = True
        self._reader_task = asyncio.get_running_loop().create_task(
            self._reader())
        self._stderr_task = asyncio.get_running_loop().create_task(
            self._stderr_logger())
        try:
            await self._create_session()
        except Exception:
            await self.stop()
            raise
        log(f"[zbrain] app-server up, session {self.session_id[:20]}")

    async def _create_session(self):
        ws = {"workspaceKey": "zero-voice",
              "workspacePath": CFG["agent_dir"].replace("\\", "/")}
        if self._resume_id:
            try:
                r = await self._request("session/resume",
                                        {"sessionId": self._resume_id,
                                         "workspace": ws}, 30)
                self.session_id = self._sid_from(r) or self._resume_id
                self._resume_id = None
                log(f"[zbrain] resumed {self.session_id[:20]}")
            except Exception as e:
                log(f"[zbrain] resume failed ({str(e)[:120]}), fresh")
                self._resume_id = None
        if not self.session_id:
            r = await self._request("session/create", {"workspace": ws, "mode": "yolo"}, 60)
            self.session_id = self._sid_from(r)
            if not self.session_id:
                raise RuntimeError("session/create returned no session id")
        try:
            await self._request("session/setMode", {"sessionId": self.session_id, "mode": "yolo"}, 10)
        except Exception:
            pass

    @staticmethod
    def _sid_from(result) -> str | None:
        r = result or {}
        return (r.get("sessionId")
                or (r.get("session") or {}).get("sessionId")
                or (r.get("projection") or {}).get("sessionId"))

    async def stop(self):
        if self._proc and self._alive:
            try:
                if self.session_id:
                    await self._request("session/close",
                                        {"sessionId": self.session_id}, 5)
            except Exception:
                pass
        self._alive = False
        self.session_id = None
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self._stderr_task:
            self._stderr_task.cancel()
            self._stderr_task = None
        if self._proc:
            proc, self._proc = self._proc, None
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            try:
                await proc.wait()
            except Exception:
                pass

    async def interrupt(self):
        """Interrupt the in-flight turn ("session/stop"), conversation
        intact — the same contract as the SDK brain's interrupt."""
        if not (self._proc and self._alive and self.session_id):
            return
        try:
            await self._request("session/stop",
                                {"sessionId": self.session_id}, 10)
        except Exception as e:
            log(f"[zbrain] stop request failed: {str(e)[:120]}")

    async def reset_turn(self, timeout: float = 8.0):
        if self._proc and self._alive and self.session_id:
            try:
                await self._request("session/stop",
                                    {"sessionId": self.session_id}, 5)
            except Exception:
                pass
        self._turn_done = None      # nothing buffered between turns

    async def set_permission_mode(self, backtalk_mode: str):
        target = "yolo" if backtalk_mode in ("bypassPermissions", "yolo") else "build"
        if self._proc and self._alive and self.session_id:
            try:
                await self._request("session/setMode", {"sessionId": self.session_id, "mode": target}, 10)
                log(f"[zbrain] permission mode switched to {target}")
            except Exception as e:
                log(f"[zbrain] setMode failed: {e}")

    async def context_usage(self):
        return None               # main.py's usage report skips it cleanly

    # ---- model switching (deep / fast console verbs) ----

    async def _switch_model(self, target: str) -> str:
        provider, _, model_id = target.partition("/")
        try:
            r = await self._request("session/setModel",
                                    {"sessionId": self.session_id,
                                     "model": {"providerId": provider,
                                               "modelId": model_id}}, 15)
            self.model = target
            self._discipline_sent = False   # new model, re-state the medium
            log(f"[zbrain] model switched to {target}")
            return ""
        except Exception as e:
            return (f"error: switching models failed: {str(e)[:200]}")

    # ---- the turn ----

    async def _messages(self):
        r = await self._request("session/messages",
                                {"sessionId": self.session_id}, 20)
        return (r or {}).get("messages") or []

    async def ask_stream(self, utterance: str):
        """Yield complete sentences and spoken tool narrations as they stream out of the model."""
        await self._ensure_alive()
        known = set()
        narrated_tools = set()
        try:
            for m in await self._messages():
                known.add(((m.get("info") or {}).get("id")) or id(m))
        except Exception as e:
            log(f"[zbrain] pre-turn read failed ({e}), creating fresh session...")
            self.session_id = None
            try:
                await self._create_session()
                for m in await self._messages():
                    known.add(((m.get("info") or {}).get("id")) or id(m))
            except Exception as e_rec:
                log(f"[zbrain] session recreation failed ({e_rec}), restarting app-server...")
                await self.stop()
                await self.start()
                try:
                    for m in await self._messages():
                        known.add(((m.get("info") or {}).get("id")) or id(m))
                except Exception:
                    pass

        if not getattr(self, "_discipline_sent", False):
            # The discipline rides the FIRST prompt of a session: how
            # to write for the ear. The character is AGENTS.md's job.
            prompt = (DISCIPLINE + "\n\n(The line above is how you must "
                      "write your spoken replies this session. Now, the "
                      "actual message.) " + utterance)
            self._discipline_sent = True
        else:
            uname = CFG.get("user_name", "Operator")
            prompt = (f"[Voice Mode: Spoken turn via TTS. Speak directly to {uname} in "
                      "natural conversational English with NO markdown. Skip startup "
                      "scans and answer directly unless explicitly asked for "
                      "file or code actions.]\n\n" + utterance)

        self._turn_done = asyncio.Event()
        try:
            await self._request("session/send",
                                {"sessionId": self.session_id,
                                 "content": prompt, "inputId": "voice"},
                                30)
        except Exception as e:
            self._turn_done = None
            log(f"[zbrain] send failed ({e}), refreshing session and retrying...")
            self.session_id = None
            try:
                await self._create_session()
                self._turn_done = asyncio.Event()
                await self._request("session/send",
                                    {"sessionId": self.session_id,
                                     "content": prompt, "inputId": "voice"},
                                    30)
            except Exception as e2:
                log(f"[zbrain] fast retry failed ({e2}), full app-server restart...")
                await self.stop()
                try:
                    await self.start()
                    self._turn_done = asyncio.Event()
                    await self._request("session/send",
                                        {"sessionId": self.session_id,
                                         "content": prompt, "inputId": "voice"},
                                        30)
                except Exception as e3:
                    yield ("I hit an error reaching my brain: " + str(e3)[:180]
                           + ". Check the voice window for details.")
                    return

        yielded_by_mid: dict[str, int] = {}
        tokenizer = AdaptiveVoiceTokenizer()
        deadline = asyncio.get_running_loop().time() + _TURN_TIMEOUT_S
        while True:
            loop = asyncio.get_running_loop()
            try:
                await asyncio.wait_for(self._turn_done.wait(), _POLL_S)
                finished = True
            except asyncio.TimeoutError:
                finished = False
            if loop.time() > deadline:
                log("[zbrain] turn timeout — giving up on this turn")
                break
            try:
                msgs = await self._messages()
            except Exception as e:
                if not self._alive:
                    log(f"[zbrain] process disconnected ({e}), attempting auto-heal restart...")
                    try:
                        await self.stop()
                        await self.start()
                        msgs = await self._messages()
                    except Exception as e2:
                        yield ("My brain process hit an error: " + str(e2)[:120] + ". Check the voice window.")
                        return
                else:
                    log(f"[zbrain] poll failed: {str(e)[:120]}")
                    await asyncio.sleep(1.0)
                    continue

            for m in msgs:
                info = m.get("info") or {}
                mid = info.get("id") or ""
                if info.get("role") != "assistant":
                    continue
                self._tally_delta(mid, info)

                # Skip messages that already existed before this turn!
                if mid in known:
                    continue

                # Live tool narration: ONLY narrate new tool calls initiated in THIS turn!
                for p in (m.get("parts") or []):
                    ptype = str(p.get("type") or "").lower()
                    if ptype in ("tool-call", "tool_call", "tool_use") or "tool" in p:
                        call_id = str(p.get("callId") or p.get("id") or (mid + ":" + str(p.get("tool") or p.get("name"))))
                        if call_id not in self._narrated_calls:
                            self._narrated_calls.add(call_id)
                            tool_name = p.get("tool") or p.get("name") or "tool"
                            tool_args = p.get("input") or p.get("args") or {}
                            self.session_actions.append({
                                "tool": tool_name,
                                "args": tool_args,
                                "time": loop.time(),
                            })
                            narration = _narrate_tool(tool_name, tool_args)
                            if narration:
                                # Flush any buffered pre-tool speech before narrating
                                for tail in tokenizer.flush():
                                    c = clean_speech_text(tail)
                                    if c:
                                        yield c
                                log(f"[zbrain] narrating action: {narration}")
                                yield narration

                # Stream assistant text for this message across all messages in turn
                parts = [p.get("text", "") for p in (m.get("parts") or [])
                         if p.get("type") == "text"]
                msg_text = " ".join(parts).strip()
                prev_len = yielded_by_mid.get(mid, 0)
                if len(msg_text) > prev_len:
                    delta = msg_text[prev_len:]
                    yielded_by_mid[mid] = len(msg_text)
                    for chunk in tokenizer.feed(delta):
                        c = clean_speech_text(chunk)
                        if c:
                            yield c

            if finished:
                break

        for tail in tokenizer.flush():
            c = clean_speech_text(tail)
            if c:
                yield c

        self.session["turns"] += 1
        self._turn_done = None

    def _tally_delta(self, mid, info):
        """Count each message's tokens exactly once, at their FINAL
        values: poll-diff of (in, out) per message id."""
        try:
            t = info.get("tokens") or {}
            if not t:
                return
            inp = int(t.get("input") or 0)
            out = int(t.get("output") or 0)
            cache = int((t.get("cache") or {}).get("read") or 0)
            last = self._tallied.get(mid, (0, 0, 0))
            cur = (inp, out, cache)
            if cur == last:
                return
            self.session["in_tokens"] += max(0, inp - last[0])
            self.session["out_tokens"] += max(0, out - last[1])
            self.session["in_tokens"] += max(0, cache - last[2])
            self.session["turns"] += 0      # turns counted per ask_stream
            self._tallied[mid] = cur
        except Exception:
            pass

    async def command(self, cmd: str) -> str:
        """Console slash verbs over the protocol: /clear opens a fresh
        session, /model switches live, /compact compacts."""
        c = (cmd or "").strip().lower()
        if c == "/clear":
            try:
                await self._request("session/close",
                                    {"sessionId": self.session_id}, 10)
            except Exception:
                pass
            self.session_id = None
            self.session.update(turns=0, out_tokens=0, in_tokens=0,
                                cost=0.0)
            self._discipline_sent = False
            try:
                await self._create_session()
                log(f"[zbrain] fresh session {self.session_id[:20]}")
                return ""
            except Exception as e:
                raise RuntimeError(f"reopening the session failed: {e}")
        if c.startswith("/model"):
            target = cmd.split(None, 1)[1].strip() if len(
                cmd.split(None, 1)) > 1 else ""
            if not target:
                return "error: no model name given"
            if "/" not in target and CFG.get("model_prefix"):
                target = f"{CFG['model_prefix']}/{target}"
            return await self._switch_model(target)
        if c.startswith("/compact"):
            try:
                await self._request("session/compact",
                                    {"sessionId": self.session_id}, 120)
                return ""
            except Exception as e:
                return f"error: compact failed: {str(e)[:200]}"
        if c.startswith("/effort"):
            return ("error: effort control is not wired into the ZCode "
                    "voice line yet")
        return ""


if __name__ == "__main__":
    import time

    async def demo():
        b = ZcodeBrain()
        await b.start()
        for prompt in ("Voice check: greet me in one sentence.",
                       "And what's two plus two, spoken like yourself?"):
            t0 = time.time()
            async for s in b.ask_stream(prompt):
                print(f"  ({time.time()-t0:4.1f}s) {s}", flush=True)
        await b.stop()

    asyncio.run(demo())
