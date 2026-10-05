# Grok bot

A terminal chat bot for Grok (xAI) that runs on your own computer.

## Run it on your computer

1. Install Python 3.9+ from https://www.python.org/downloads/ (on Windows, tick **Add python.exe to PATH**).
2. Download this repo: `git clone https://github.com/yaaa2005/yaaa2005` (or **Code > Download ZIP** on GitHub and unzip it).
3. Get an API key at https://console.x.ai.
4. Start it:
   - **Windows:** double-click `run.bat`.
   - **Mac / Linux:** open a terminal in the folder and run `chmod +x run.sh && ./run.sh`.

   The first run creates a `.env` file. Put your key in it (`XAI_API_KEY=xai-...`), save it, then start the bot again.

Type a message and press Enter. `/reset` clears the conversation and `/exit` quits.

## Settings (`.env`)

| Variable | Default |
| --- | --- |
| `XAI_API_KEY` | required |
| `GROK_MODEL` | `grok-4` |
| `GROK_SYSTEM_PROMPT` | `You are Grok, a helpful assistant.` |

`.env` is git-ignored, so your key stays on your machine.
