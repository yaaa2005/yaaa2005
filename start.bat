@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo Python 3 is required. Install it from https://www.python.org/downloads/ then run start.bat again.
    pause
    exit /b 1
  )
)

if not exist .venv (
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
echo.
echo Starting Grok on this computer (http://127.0.0.1:8787)
echo Not a virtual machine — this is your local Python app.
echo.
python -m grok_bot serve
pause
