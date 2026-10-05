@echo off
REM Start the Grok bot on this machine. Pass --web for the browser UI.
cd /d "%~dp0"

where py >nul 2>nul && (
  py -3 -m grokbot %*
  exit /b %errorlevel%
)
where python >nul 2>nul && (
  python -m grokbot %*
  exit /b %errorlevel%
)

echo Python 3 was not found. Install it from https://www.python.org/downloads/ and try again.
exit /b 1
