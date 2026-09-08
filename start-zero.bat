@echo off
rem Zero: start the voice line and holographic HUD face.
rem   start-zero.bat        start voice loop + visualizer HUD
rem   start-zero.bat chat   typed terminal session
rem Close the voice window (or press Ctrl-C) to hang up.

setlocal enabledelayedexpansion
cd /d "%~dp0"

rem 1. Locate uv
set "UVCMD="
where uv >nul 2>&1
if not errorlevel 1 (
  set "UVCMD=uv"
) else (
  if exist "%APPDATA%\Python\Python314\Scripts\uv.exe" set "UVCMD=%APPDATA%\Python\Python314\Scripts\uv.exe"
  if exist "%LOCALAPPDATA%\Programs\uv\uv.exe" set "UVCMD=%LOCALAPPDATA%\Programs\uv\uv.exe"
  if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UVCMD=%USERPROFILE%\.cargo\bin\uv.exe"
)

if "%UVCMD%"=="" (
  echo.
  echo [Error] 'uv' was not found on your system.
  echo Please install uv via: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  echo or visit https://docs.astral.sh/uv/getting-started/installation/
  echo.
  pause
  exit /b 1
)

rem Ensure uv directory is on PATH for spaCy / model fetching
for %%I in ("%UVCMD%") do set "UV_DIR=%%~dpI"
set "PATH=%UV_DIR%;%PATH%"

rem 2. Chat mode shortcut
if "%~1"=="chat" (
  where zcode >nul 2>&1
  if not errorlevel 1 (
    start "" zcode
    exit /b
  )
  if exist "%LOCALAPPDATA%\Programs\ZCode\ZCode.exe" (
    start "" "%LOCALAPPDATA%\Programs\ZCode\ZCode.exe"
    exit /b
  )
  echo [Zero] Starting typed session...
  cmd /k
  exit /b
)

rem 3. Sync dependencies first (creates .venv cleanly on first run)
if exist "backtalk\" (
  echo   [1/3] Syncing packages...
  cd /d "%~dp0backtalk"
  %UVCMD% sync --inexact
  if errorlevel 1 (
    echo.
    echo   [Error] The voice line packages could not be installed.
    echo   Please check the terminal output above.
    echo.
    pause
    exit /b 1
  )
)

rem 4. Launch reactive face HUD in background
cd /d "%~dp0"
if exist "ai-visualizer\" (
  echo   [2/3] Launching holographic HUD...
  if exist "%~dp0backtalk\.venv\Scripts\pythonw.exe" (
    start "" "%~dp0backtalk\.venv\Scripts\pythonw.exe" "%~dp0ai-visualizer\server.py"
  ) else (
    start "" pythonw "%~dp0ai-visualizer\server.py"
  )
)

rem 5. Start the real-time voice line
if exist "backtalk\" (
  echo   [3/3] Voice line starting. Close this window or press Ctrl+C to hang up.
  echo.
  cd /d "%~dp0backtalk"
  %UVCMD% run python -m backtalk.main
  if errorlevel 1 (
    echo.
    echo   The voice line stopped with an error. Check backtalk\logs\backtalk.log
    pause
  )
)
