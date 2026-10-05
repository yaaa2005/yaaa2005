# Grok bot

A Grok chat bot that runs on your own computer. No virtual machine, no Docker, no
`pip install` — just Python 3.9 or newer and your xAI API key.

It talks to the [xAI API](https://console.x.ai/) over HTTPS, so the only thing
running on your machine is this folder of Python files. Your key stays on your
machine in a local `.env` file.

## Run it in three steps

1. **Get a key.** Sign in at [console.x.ai](https://console.x.ai/), create an API
   key, and copy it.

2. **Save the key next to the bot.** Copy `.env.example` to `.env` and put your
   key in it:

```bash
cp .env.example .env
# then edit .env so the first line reads XAI_API_KEY=xai-...
```

3. **Start chatting.**

```bash
./run.sh            # macOS / Linux
run.cmd             # Windows
```

You should see:

```
Grok bot ready - model grok-4. Type /help for commands, /exit to quit.

you > hello
grok > Hi! What can I help you with?
```

If `./run.sh` says "Permission denied", run `chmod +x run.sh` once.

## Chat in your browser instead

```bash
./run.sh --web
```

This starts a small server on `http://127.0.0.1:8777` and opens it in your
browser. The page is served from your own machine and the server only listens on
`127.0.0.1`, so nothing is exposed to your network. Press Ctrl-C in the terminal
to stop it.

Use `--port 9000` for a different port, and `--no-browser` to skip opening a
browser window.

## Other ways to call it

```bash
./run.sh "summarise the plot of Dune in two sentences"   # ask one question and exit
echo "fix this error: $(cat error.txt)" | ./run.sh       # pipe text in
./run.sh --list-models                                   # see which models your key allows
./run.sh -m grok-3 -s "Reply only in Arabic"             # pick a model and system prompt
```

Without `run.sh` the bot is just a Python module, so `python3 -m grokbot` works
the same way from this folder.

## Commands inside a chat

| Command | What it does |
| --- | --- |
| `/help` | list the commands |
| `/reset` | forget the conversation so far |
| `/system <text>` | replace the system prompt and start over |
| `/model [name]` | show or switch the model |
| `/save <file>` | write the conversation to a text file |
| `/exit` | quit (Ctrl-C and Ctrl-D also work) |

While Grok is answering, Ctrl-C stops that answer without quitting the chat.

## Settings

Set these in `.env` or in your shell. Command-line flags win over both.

| Variable | Default | Meaning |
| --- | --- | --- |
| `XAI_API_KEY` | *(required)* | your xAI key, also accepted as `GROK_API_KEY` |
| `GROK_MODEL` | `grok-4` | model name |
| `GROK_SYSTEM_PROMPT` | a short helpful-assistant prompt | how the bot should behave |
| `GROK_TIMEOUT` | `120` | seconds to wait for a reply |
| `XAI_BASE_URL` | `https://api.x.ai/v1` | point the bot at another OpenAI-compatible API |

## If something goes wrong

- **"No API key found"** — `.env` is missing, is not in the folder you ran the
  bot from, or the line is not exactly `XAI_API_KEY=your-key`.
- **"The API rejected your key"** — the key is wrong, revoked, or belongs to a
  different xAI account.
- **"Model or endpoint not found"** — your key has no access to that model. Run
  `./run.sh --list-models` and pass one of the names it prints with `-m`.
- **"Rate limited by the API"** — you are sending requests faster than your plan
  allows, or you are out of credit.
- **"Could not reach ..."** — no internet connection, or a proxy or firewall is
  blocking `api.x.ai`.
- **`python3: command not found`** — install Python from
  [python.org/downloads](https://www.python.org/downloads/), then try again.

## Tests

The tests run the bot against a fake API on localhost, so they need no key and
no network:

```bash
python3 -m unittest discover -s tests -t .
```
