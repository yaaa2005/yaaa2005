@echo off
cd /d "%~dp0"
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo Python not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
        pause
        exit /b 1
    )
)
call venv\Scripts\activate.bat
pip install -q -r requirements.txt
if not exist .env (
    copy .env.example .env >nul
    echo Put your xAI key in .env, save it, then double-click run.bat again.
    notepad .env
    exit /b 0
)
python grok_bot.py
pause
