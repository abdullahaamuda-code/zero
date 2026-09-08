# backtalk // Zero Voice Engine

The real-time voice line for **Zero**: ultra-fast speech-to-text, streaming LLM integration, pipelined neural text-to-speech, and spoken tool narration.

---

## Key Capabilities

- **Ultra-Fast STT (~300ms):** Powered by Groq Whisper LPU cloud transcription (`small.en`) or offline local `faster-whisper`.
- **Zero Dead-Air Neural TTS:** Streams speech sentence-by-sentence via Microsoft Edge-TTS (`en-US-ChristopherNeural`), local Kokoro, or ElevenLabs.
- **Pipelined Pre-Fetching:** Sentence $N+1$ pre-renders in the background while sentence $N$ plays, eliminating awkward pauses.
- **Adaptive Breath-Phrased Tokenizer:** Prevents fragments, orphan words, or unnatural mid-phrase pauses.
- **Contextual Tool Narration:** Zero verbally narrates actions aloud as it executes tools (e.g. file writing, CLI execution, web searches) instead of remaining silent.
- **Push-to-Talk & Hands-Free:** Toggle anytime between hardware push-to-talk (`shift`, `home`, `right_alt`) and voice-activated open mic.
- **Automated Session Summarizer (`vault_logger.py`):** Compiles spoken turns, executed commands, and files modified directly into your memory vault's daily log on exit.

---

## Architecture

```
Push-to-Talk / Open Mic
         │
         ▼
[ ears.py ] ──► Groq Whisper / Faster-Whisper (~300ms)
         │
         ▼
[ zcode_brain.py ] ──► Streaming Autonomous Brain / LLM Gateway
         │
         ▼
[ mouth.py ] ──► Edge-TTS / Kokoro Pipelined Audio Prefetch
         │
         ▼
Speakers + Signal Bus (.voice_state, .voice_waveform) ──► ai-visualizer HUD
```

---

## Installation & Running

Dependencies are managed via `uv`:

```bash
cd backtalk
uv sync
uv run python -m backtalk.main
```

Or launch everything (voice + HUD) via the root launcher:
- **Windows:** `start-zero.bat`
- **macOS / Linux:** `./start-zero.sh`

---

## Configuration (`backtalk.json`)

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

Set `"model"` and `"deep_model"` to your chosen model routes (e.g., `"google/gemini-2.5-flash"`, `"deepseek/deepseek-r1"`, `"openai/gpt-4o"`, or your [Cupbearer](https://github.com/cupbearer-gateway/cupbearer) gateway route; see [Cupbearer Docs](https://cupbearer-gateway.github.io/cupbearer/)).

### Voice Console Commands

Speak these phrases during a session to control the voice engine:

| Phrase | Action |
| :--- | :--- |
| **"Go hands free"** | Switch to continuous open-mic listening |
| **"Push to talk mode"** | Switch back to push-to-talk (Shift) |
| **"Switch to Gemini"** | Switch active model to fast interactive Gemini |
| **"Switch to the deep model"** | Switch to deep reasoning model (Opus) |
| **"Back to the fast model"** | Return to primary speed-tier model |
| **"Stop asking for permission"** | Enable autonomous YOLO execution |
| **"Start asking again"** | Require spoken verbal confirmation before modifying files |
| **"Clear the session"** | Reset conversation context |
| **"Compact the session"** | Trigger context window compaction |
| **"Goodbye Zero"** | Hang up and persist session summary to vault |
