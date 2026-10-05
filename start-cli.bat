@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  echo Run start.bat once first so Python packages are installed.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m grok_bot chat
pause
