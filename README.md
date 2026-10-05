# Grok bot on your computer (not a VM)

This repository now includes a **local Grok chatbot**. It runs with Python on the same computer you are sitting at. Cursor Cloud Agents cannot jump onto your PC — they always run in a remote virtual machine — so this app is the live Grok chat you actually use locally.

It talks to the official [xAI Grok API](https://docs.x.ai/) from `127.0.0.1` (localhost only).

## Windows

1. Install [Python 3](https://www.python.org/downloads/) if you do not have it. During setup, check **Add python.exe to PATH**.
2. Download this repo and unzip it, or clone it.
3. Double-click `start.bat`.
4. A browser window opens at `http://127.0.0.1:8787`.
5. Create an API key at [console.x.ai](https://console.x.ai/), paste it into the page, and chat.

Optional terminal chat after the first run: double-click `start-cli.bat`.

## macOS or Linux

```bash
chmod +x start.sh start-cli.sh
./start.sh
```

Then paste your xAI key in the browser.

## Manual commands

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m grok_bot serve    # browser
python -m grok_bot chat     # terminal
```

## Settings

Copy `.env.example` to `.env` if you prefer to edit the key in a file:

```
XAI_API_KEY=xai-your-key-here
GROK_MODEL=grok-4-fast
```

`GROK_MODEL` can be `grok-4-fast` (default, cheaper) or `grok-4.6` (flagship).

The key is stored only in `.env` on your computer. The server refuses connections that are not from localhost.

## Tests

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```
