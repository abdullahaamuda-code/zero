# Troubleshooting: backtalk

Diagnostics and fixes for Zero's voice engine. Log details are written to `logs/backtalk.log`.

---

## Quick Fixes

### 1. `ModuleNotFoundError` on launch
Run package sync inside the `backtalk` directory:
```bash
uv sync
```
If `uv sync` errors, verify your Python version is 3.11 or 3.12.

### 2. The greeting speaks, then nothing happens / brain hangs
Zero connected to audio and spoken greeting played, but the autonomous brain backend did not respond:
- Check that your LLM CLI or gateway server is running.
- Verify your API keys in `.env` (e.g. `GROQ_API_KEY`, `GEMINI_API_KEY`).
- Inspect `logs/backtalk.log` for the exact connection failure trace.

### 3. Push-to-Talk key is not detected
- **Windows:** Push-to-Talk defaults to the `Shift` key and uses native Win32 hardware checks (`GetAsyncKeyState`). Run the terminal with standard user permissions.
- **macOS:** Grant **Input Monitoring** permission: *System Settings → Privacy & Security → Input Monitoring* for your terminal application.

### 4. Microphone selection
If audio records from the wrong microphone or headset:
1. List available devices:
   ```bash
   python -m sounddevice
   ```
2. Set `"mic_device"` in `backtalk.json` to the exact name of your preferred microphone (e.g. `"Microphone (Realtek Audio)"`).

### 5. High STT Latency
- If using local `faster-whisper`, set `"stt_device": "auto"` to use CUDA if available, or reduce model size in `backtalk.json` (`"stt_model": "tiny.en"` or `"base.en"`).
- For sub-300ms ultra-fast transcription, set `"stt_engine": "groq"` and set `GROQ_API_KEY` in `.env`.

### 6. Edge-TTS playback stutter
- Verify an active internet connection.
- If running offline, switch to local Kokoro: set `"tts_engine": "kokoro"` in `backtalk.json`.

---

## Voice Loop Data Flow

```
Hold Key (Shift) ──► ears.py (sounddevice, 16kHz PCM)
                  ──► ears.py (Groq Whisper LPU or Faster-Whisper)
                  ──► zcode_brain.py (Autonomous Session)
                  ──► AdaptiveVoiceTokenizer (Breath-phrased chunker)
                  ──► mouth.py (Edge-TTS / Kokoro prefetch pipeline)
                  ──► Speakers + Signal Bus (.voice_state, .voice_waveform)
```
