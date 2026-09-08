# ai-visualizer // Holographic HUD & Reactive Face for Zero

The visual system for **Zero**: a lightweight, zero-dependency browser HUD driven by real-time audio waveforms and agent state.

The visualizer runs purely on Python standard library and vanilla HTML5 / WebGL — no npm packages or heavy browser frameworks required.

---

## Faces

- **Zero Core (`faces/zero/`):** Dedicated holographic cyber interface with 3D perspective neon grid (#06070d, cyan #00f0ff, violet #8b5cf6), audio-reactive particle core, targeting reticles, and 64-band radial equalizer.
- **Circuit Board (`faces/board/`):** Living procedural PCB layout with data pulses and cinematic flythroughs.
- **Neural Core (`faces/neural/`):** Color constellation neural brain showing real-time agent cognitive states.
- **Radial (`faces/radial/`):** 80-bar audio starburst with rotating particle orb and sonar sweeps.
- **Rain (`faces/rain/`):** Reactive matrix code rain that shifts with speech amplitude.

The root URL (`http://127.0.0.1:8790/`) serves a gallery to view and test all faces.

---

## How It Works: The Signal Bus

The visualizer polls three lightweight local files written by `backtalk`:

```
.voice_state        idle | listening | thinking | speaking
.voice_waveform     JSON {ts, samples: [64 floats]} while speaking
.voice_loading_pid  Active process indicator during reasoning
```

When Zero speaks, real-time PCM waveforms are captured and broadcast to the visualizer at ~15 FPS, dynamically powering the on-screen equalizers and particle cores.

---

## Standalone Usage

Run the server directly:

```bash
python server.py
```

### Options

- **Dedicated App Mode (Windows):** Launches Microsoft Edge or Google Chrome in frameless window mode (`--app=http://127.0.0.1:8790/faces/zero/`) so the HUD never sleeps or lags in background tabs.
- **Mock Demo Mode:** Test visualizer animations without running the voice line:
  ```bash
  python server.py --mock speaking
  python server.py --mock listening
  python server.py --mock thinking
  ```
- **Custom Port:**
  ```bash
  python server.py --port 9000
  ```
- **Headless (No Browser Popup):**
  ```bash
  python server.py --no-open
  ```

---

## Configuration (`ai-visualizer.json`)

```json
{
  "name": "ZERO",
  "badge": "",
  "face": "zero",
  "port": 8790,
  "bus_dir": "../backtalk",
  "thinking_sound": true
}
```

- `"face"`: Default face loaded at root (`"zero"`, `"board"`, `"neural"`, `"radial"`, `"rain"`).
- `"bus_dir"`: Path to `backtalk` folder containing `.voice_*` signal files. Relative paths resolve automatically.
- `"thinking_sound"`: Play subtle audio sweep while thinking (`assets/thinking.wav`).
