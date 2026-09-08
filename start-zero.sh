#!/usr/bin/env bash
# Zero: start the voice line and holographic HUD face (macOS & Linux)
# Usage:
#   ./start-zero.sh       Start voice loop + visualizer HUD
#   ./start-zero.sh chat  Start interactive session

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# 1. Check uv
if ! command -v uv >/dev/null 2>&1; then
  echo "[Error] 'uv' was not found on your PATH."
  echo "Install it via: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

# 2. Chat mode
if [ "$1" = "chat" ]; then
  if command -v zcode >/dev/null 2>&1; then
    exec zcode
  else
    echo "[Zero] Starting shell..."
    exec bash
  fi
fi

# 3. Sync dependencies in backtalk
if [ -d "backtalk" ]; then
  echo "  [1/3] Syncing packages..."
  (cd "$DIR/backtalk" && uv sync --inexact)
fi

# 4. Launch visualizer HUD in background
if [ -d "ai-visualizer" ]; then
  echo "  [2/3] Launching HUD face..."
  python3 "$DIR/ai-visualizer/server.py" >/dev/null 2>&1 &
fi

# 5. Start real-time voice line
if [ -d "backtalk" ]; then
  echo "  [3/3] Voice line starting. Press Ctrl+C to exit."
  cd "$DIR/backtalk"
  exec uv run python -m backtalk.main
fi
