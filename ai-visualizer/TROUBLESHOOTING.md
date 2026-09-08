# Troubleshooting: ai-visualizer

## The server won't start

- `Address already in use`: Another process owns port 8790. Change `"port"` in `ai-visualizer.json` or run `python server.py --port 8791`.
- `python: command not found`: Ensure Python 3.11+ is installed and on your system PATH.

## The face stays at idle while Zero is speaking

1. Test mock mode: `python server.py --mock speaking`. If the face animates, browser rendering is working and the issue is signal bus pathing.
2. Check `bus_dir` in `ai-visualizer.json`: ensure it points to the `backtalk` directory (default: `"../backtalk"`).
3. Verify signal files: While Zero speaks, check that `.voice_state` and `.voice_waveform` are being created in `backtalk/`.

## No audio from thinking sound

- Browsers require user interaction before playing audio. Click anywhere inside the HUD window once.
- Check the SND toggle at bottom left and ensure it is ON.
- To disable thinking sound permanently, set `"thinking_sound": false` in `ai-visualizer.json`.

## Performance & Framerate

- Zero Core (`faces/zero/`) and Circuit Board (`faces/board/`) are optimized for hardware-accelerated WebGL. Ensure hardware acceleration is enabled in your browser settings.
- The standalone app launcher (`start-zero.bat` / `start-zero.sh`) launches Chrome or Edge in dedicated app mode, preventing background tab throttling.
- Press `F` to toggle fullscreen.

## OBS Studio Integration

Add a Browser Source in OBS pointing to `http://127.0.0.1:8790/faces/zero/index.html` at your canvas resolution. Enable "Control audio via OBS" if you wish to route thinking sounds through your stream audio mixer.
