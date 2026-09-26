# Zero // Autonomous AI Operator & Build Partner

Real-time voice line, reactive holographic HUD face, persistent memory vault, full autonomous hands.

---

## Overview

**Zero** is an autonomous AI build partner and system operator designed to work alongside you. Unlike passive chatbots that merely give advice, Zero has real hands on your operating system, speaks out loud in real time, visualizes its mental state via a holographic 3D HUD, and retains permanent cross-session memory in a plain markdown vault.

Zero operates under two equal mandates:
1. **Own the work:** Dispatches tasks, writes files, executes commands, fixes breaks, and reports finished outcomes — never handing back "you could try...".
2. **Strategic partner:** Challenges assumptions when an idea doesn't add up, brings better angles, and moves at high velocity without sycophancy or fluff.

---

## Core Systems

```
┌─────────────────────────────────────────────────────────────────────────┐
│                               ZERO RIG                                  │
├───────────────────┬───────────────────┬─────────────────────────────────┤
│    THE VOICE      │     THE FACE      │           THE MEMORY            │
│    (backtalk/)    │ (ai-visualizer/)  │            (vault/)             │
│                   │                   │                                 │
│  • Groq Whisper   │  • 3D Cyber Grid  │  • Markdown Vault (Obsidian)    │
│    (~300ms STT)   │  • 64-Band Audio  │  • Daily Session Auto-Logger    │
│  • Edge-TTS       │    Equalizer      │  • Active Priorities Queue      │
│    Streaming      │  • Standalone App │  • Cross-Session Retention      │
│  • Zero Dead-Air  │    Window (Edge/  │  • Frontmatter Indexing         │
│    Prefetching    │    Chrome)        │                                 │
└─────────┬─────────┴─────────┬─────────┴────────────────┬────────────────┘
          │                   │                          │
          └───────────────────┼──────────────────────────┘
                              ▼
                 ┌─────────────────────────┐
                 │     BRAIN & HANDS       │
                 │   (zcode / Gateways)    │
                 │                         │
                 │  • Multi-Model Routing  │
                 │    (Gemini, Opus, etc.) │
                 │  • Spoken Tool Narration│
                 │  • Direct CLI Execution │
                 │  • Local File System Ops│
                 └─────────────────────────┘
```

### 1. The Voice (`backtalk/`)
- **Ultra-low latency STT:** Sub-300ms cloud transcription via Groq Whisper LPU or offline local transcription with `faster-whisper`.
- **Zero dead-air neural speech:** Streams speech sentence-by-sentence via Microsoft Edge-TTS neural voices (default: `en-US-ChristopherNeural`), local Kokoro TTS, or ElevenLabs.
- **Pipelined pre-fetching:** While sentence $N$ plays through your speakers, sentence $N+1$ pre-renders in the background for zero inter-sentence pauses.
- **Adaptive breath-phrased chunking:** Natural speech flow that avoids word orphaning or comma hesitation.
- **Contextual tool narration:** Zero narrates actions aloud as it works (e.g., *"Building holographic interface now..."*, *"Syncing packages, one sec..."*, *"Checking git status..."*) instead of leaving dead air.

### 2. The Face (`ai-visualizer/`)
- **Holographic neon grid HUD:** Built in HTML5 canvas and WebGL with 3D perspective grids, particle fields, glowing core reticle, and targeting brackets (#06070d obsidian, cyan #00f0ff, and violet #8b5cf6).
- **Audio-reactive 64-band radial equalizer:** Directly driven by real-time waveform packets published over the local signal bus.
- **Standalone dedicated HUD window:** Launches in native frameless app mode (`--app=...`) on Windows/macOS/Linux so it never goes to sleep in background tabs.

### 3. The Memory (`vault/`)
- **Obsidian-compatible plain markdown:** Infinite external memory living in human-readable markdown notes.
- **Automatic daily session logger (`vault_logger.py`):** On disconnect or hang-up, Zero automatically compiles spoken turns, tools run, files touched, and topics covered into today's Daily Note (`vault/01 - Daily Notes/YYYY-MM-DD.md`).
- **Startup sequence:** Automatically reads `vault/VAULT-INDEX.md` and `vault/Active Priorities.md` on boot to restore full state.

---

## Quickstart

### Prerequisites

- **OS:** Windows 10/11, macOS 12+, or Linux.
- **Python:** 3.11 or 3.12 installed.
- **uv:** Fast Python package manager ([install uv](https://docs.astral.sh/uv/getting-started/installation/)):
  - **Windows (PowerShell):** `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
  - **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Node.js:** (Recommended for LLM CLI runtime).

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/abdullahaamuda-code/zero.git
cd zero
```

### Step 2: Environment Setup

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Groq API key for ultra-fast ~300ms speech-to-text
GROQ_API_KEY=gsk_your_groq_api_key_here

# Direct AI Provider Keys (if using cloud LLMs directly)
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
```

> **Get a free Groq key:** [Groq Cloud Console](https://console.groq.com/keys) (Groq provides free-tier Whisper transcription).

### Step 3: Configure Voice & Identity

Review `backtalk/backtalk.json`:

```json
{
  "brain": "zcode",
  "agent_dir": "..",
  "name": "Zero",
  "user_name": "Operator",
  "model": "your-provider/your-fast-model",
  "deep_model": "your-provider/your-deep-model",
  "permission_mode": "bypassPermissions",
  "ptt_key": "shift",
  "tts_engine": "edge-tts",
  "edge_voice": "en-US-ChristopherNeural",
  "stt_engine": "groq",
  "stt_model": "small.en",
  "extra_dirs": [
    "../vault"
  ],
  "mic_mode": "ptt"
}
```

- **Set your models:** Replace `"your-provider/your-fast-model"` and `"your-provider/your-deep-model"` with your specific target models (e.g., `"google/gemini-2.5-flash"`, `"deepseek/deepseek-r1"`, `"openai/gpt-4o"`, or your [Cupbearer](https://github.com/abdullahaamuda-code/cupbearer) model routes).
- Change `"user_name"` to your preferred name or callsign (e.g. `"Operator"`).
- Set `"ptt_key"` to your desired Push-to-Talk hotkey (default: `"shift"`, or `"home"`, `"right_alt"`, `"f13"`).

### Step 4: Launch Zero

**Windows:**
```cmd
start-zero.bat
```

**macOS / Linux:**
```bash
chmod +x start-zero.sh
./start-zero.sh
```

On first run, `uv` will automatically install all Python dependencies in seconds. The HUD will pop open on your screen and Zero will speak its greeting:
> *"Zero online. Hold Shift and tell me what we're building."*

---

## AI Brain & Gateway Setup

Zero connects to LLMs via persistent app-server sessions or API gateways.

### Option A: Cupbearer / Custom Gateway
If you run [Cupbearer](https://github.com/abdullahaamuda-code/cupbearer) (docs in its `docs/` folder), LiteLLM, or an OpenAI-compatible proxy:
1. Configure your gateway endpoint and API keys in `.env` or your gateway secrets config (`~/.config/cupbearer/secrets.json`).
2. In `backtalk/backtalk.json`, set your model strings to route through your gateway (e.g., `"model": "cupbearer/your-fast-model"`, `"deep_model": "cupbearer/your-deep-model"`).

### Option B: Direct Providers (Gemini, DeepSeek, OpenAI)
Set the model directly in `backtalk/backtalk.json`:
- `"model": "google/gemini-2.5-flash"`
- `"deep_model": "deepseek/deepseek-r1"` (or `"openai/o3-mini"`)

---

## Customizing Your Operator Persona

Identity is configured in **`AGENTS.md`** at the workspace root:

- **Tone:** Sharp, competent, direct, no fluff.
- **Custom Rules:** Add your project-specific rules, coding conventions, or personal working style under the `## Make it yours` section.
- **Welcome Line:** `"Zero online. What are we building?"`

Zero reads `AGENTS.md` at the start of every session to align itself with your rules.

---

## Spoken Voice Commands

While in voice mode, speak any of these natural commands:

| Command | Action |
| :--- | :--- |
| **"Go hands free"** | Switch microphone to open voice-activation mode |
| **"Turn on push to talk"** | Switch microphone back to push-to-talk (Shift) |
| **"Switch to Gemini"** | Switch active model to fast interactive Gemini |
| **"Switch to the deep model"** | Switch to deep reasoning model (e.g. Opus) for complex tasks |
| **"Back to the fast model"** | Return to the primary speed-tier model |
| **"Stop asking for permission"** | Enable direct local CLI and file system execution |
| **"Start asking again"** | Require spoken verbal confirmation before modifying files / CLI |
| **"Compact the session"** | Compact context window to reduce token usage |
| **"Clear the session"** | Start a completely fresh active session |
| **"Goodbye" / "Hang up"** | Close voice line, compile summary, and log to vault |

---

## Voice Choices

Zero supports three TTS backends out of the box:

### 1. Edge-TTS (Default, Free, Cloud Neural Streaming)
Set `"tts_engine": "edge-tts"` in `backtalk/backtalk.json`:
- `en-US-ChristopherNeural` (Calm, crisp, authoritative male)
- `en-US-GuyNeural` (Casual, energetic male)
- `en-GB-RyanNeural` (British modern male)
- `en-US-AriaNeural` (Natural female)

### 2. Kokoro (Local, 100% Offline, Apache-2.0)
Set `"tts_engine": "kokoro"`:
- `bm_lewis` (British male butler register)
- `am_michael` (American natural male)
- `af_heart` (American female)

### 3. ElevenLabs (Optional Premium Cloud TTS)
Set `"tts_engine": "elevenlabs"` and provide `ELEVENLABS_API_KEY` in `.env` along with your `"voice_id"` in `backtalk.json`.

---

## Project Structure

```
zero/
├── AGENTS.md                   # Zero core boot configuration & identity
├── README.md                   # Project documentation
├── CONTRIBUTING.md             # Contribution guidelines
├── LICENSE                     # MIT open-source license
├── start-zero.bat              # One-click Windows launcher
├── start-zero.sh               # macOS / Linux launcher
├── zero.ico                    # Desktop icon
├── .env.example                # Sample environment variables
│
├── backtalk/                   # Real-time voice line
│   ├── pyproject.toml          # Package dependencies
│   ├── backtalk.json           # Active voice & brain configuration
│   ├── backtalk.json.example   # Documented sample configuration
│   └── backtalk/
│       ├── main.py             # Voice loop orchestration & command routing
│       ├── ears.py             # Audio capture & Groq/Whisper STT
│       ├── mouth.py            # Edge-TTS/Kokoro pipelined audio synthesis
│       ├── zcode_brain.py      # App-server session management & streaming
│       ├── brain.py            # Persistent session seam (WarmBrain / resume)
│       ├── signals.py          # Signal bus: state, waveform, directions
│       ├── ducking.py          # Spotify auto-duck while speaking (macOS)
│       ├── vlog.py             # Session log to logs/backtalk.log (UTF-8 safe)
│       ├── vault_logger.py     # Automatic session summarizer & daily note writer
│       ├── ptt.py              # Native OS push-to-talk key listeners
│       └── config.py           # Configuration parser & delivery discipline
│
├── ai-visualizer/              # Holographic face HUD
│   ├── server.py               # Standalone HTTP server & signal bus reader
│   ├── index.html              # Face gallery selector
│   ├── core.js                 # Signal bus engine & audio visualizer bridge
│   ├── ai-visualizer.json      # Visualizer configuration & port settings
│   └── faces/
│       ├── zero/               # 3D cyber perspective grid HUD & reticle (Default)
│       ├── board/              # Living circuit PCB with flythrough
│       ├── radial/             # 80-bar dynamic starburst visualizer
│       ├── rain/               # Matrix digital rain screensaver
│       └── neural/             # Constellation neural core
│
├── vault/                      # Persistent Markdown Memory
│   ├── VAULT-INDEX.md          # Profile and vault structure map
│   ├── Active Priorities.md    # Active task queue
│   ├── 00 - Inbox/             # Quick notes & captures
│   ├── 01 - Daily Notes/       # Chronological session logs & templates
│   ├── 02 - Agent Rig/         # Zero stack documentation & architecture
│   ├── 09 - Archive/           # Archived notes and historical logs
│   └── 10 - Resources/         # Reference materials & guides
```

---

## Troubleshooting

- **Microphone not picking up audio:** Check your default audio recording device in OS settings, or set `"mic_device"` in `backtalk.json` to the exact name of your microphone.
- **Push-to-talk key issues on Windows:** Ensure the voice terminal window has standard permissions. Shift is supported with native Win32 hardware checks (`GetAsyncKeyState`).
- **Edge-TTS audio playback stutter:** Verify you have an active internet connection. If working offline, switch to `"tts_engine": "kokoro"`.
- **Brain connection timeout:** Verify your LLM CLI or gateway server is accessible, and check `backtalk/logs/backtalk.log` for details.

---

## License & Technology

- Speech recognition powered by [Groq](https://groq.com/) and [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
- Text-to-speech powered by [Edge-TTS](https://github.com/rany2/edge-tts) and [Kokoro](https://github.com/hexgrad/kokoro).

## Why

Assistants answer questions; operators finish tasks. Zero holds voice, face, memory,
and hands in one local process so you can hand it a build — not a prompt — and get an
outcome.

## License

[MIT](LICENSE) — free to use, modify, and ship.
