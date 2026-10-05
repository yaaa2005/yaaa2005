"""A tiny local web UI for the Grok bot, served from the standard library."""

from __future__ import annotations

import itertools
import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .client import GrokClient, GrokError
from .config import Settings

MAX_BODY_BYTES = 1_000_000
ALLOWED_ROLES = ("user", "assistant")
# Browsers send cross-origin POSTs without a preflight only for simple headers, so
# requiring a custom header keeps other pages from spending the user's API key.
GUARD_HEADER = "X-Grok-Bot"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Grok bot</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; height: 100vh; display: flex; flex-direction: column;
    background: #0f1115; color: #e7e9ee;
    font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  header {
    display: flex; align-items: center; gap: 12px; padding: 14px 20px;
    border-bottom: 1px solid #22262f; background: #13161c;
  }
  header h1 { font-size: 15px; font-weight: 600; margin: 0; }
  header .model { font-size: 13px; color: #8b93a3; margin-right: auto; }
  button {
    background: #22262f; color: #e7e9ee; border: 1px solid #2f3540;
    border-radius: 8px; padding: 7px 14px; font-size: 13px; cursor: pointer;
  }
  button:hover:not(:disabled) { background: #2b313b; }
  button:disabled { opacity: .5; cursor: default; }
  #log { flex: 1; overflow-y: auto; padding: 24px 20px; }
  .wrap { max-width: 760px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
  .msg { display: flex; flex-direction: column; gap: 6px; }
  .who { font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: #8b93a3; }
  .text { white-space: pre-wrap; word-wrap: break-word; }
  .msg.user .text {
    background: #1b2330; border: 1px solid #27313f; border-radius: 12px; padding: 10px 14px;
  }
  .msg.error .text { color: #ff9c9c; }
  .empty { color: #8b93a3; text-align: center; margin-top: 15vh; }
  footer { border-top: 1px solid #22262f; background: #13161c; padding: 14px 20px; }
  form { max-width: 760px; margin: 0 auto; display: flex; gap: 10px; align-items: flex-end; }
  textarea {
    flex: 1; resize: none; min-height: 46px; max-height: 200px; padding: 12px 14px;
    border-radius: 10px; border: 1px solid #2f3540; background: #0f1115; color: inherit;
    font: inherit;
  }
  textarea:focus { outline: none; border-color: #4b5565; }
  form button { background: #3b6ef5; border-color: #3b6ef5; padding: 12px 20px; }
  form button:hover:not(:disabled) { background: #4f7df7; }
</style>
</head>
<body>
<header>
  <h1>Grok bot</h1>
  <span class="model">__MODEL__</span>
  <button id="reset" type="button">New chat</button>
</header>
<div id="log"><div class="wrap"><p class="empty">Ask Grok anything.</p></div></div>
<footer>
  <form id="form">
    <textarea id="input" rows="1" placeholder="Message Grok - Enter to send, Shift+Enter for a new line" autofocus></textarea>
    <button id="send" type="submit">Send</button>
  </form>
</footer>
<script>
const log = document.querySelector('#log .wrap');
const form = document.getElementById('form');
const input = document.getElementById('input');
const send = document.getElementById('send');
let history = [];
let busy = false;

function addMessage(role, text) {
  const empty = log.querySelector('.empty');
  if (empty) empty.remove();
  const msg = document.createElement('div');
  msg.className = 'msg ' + role;
  const who = document.createElement('div');
  who.className = 'who';
  who.textContent = role === 'user' ? 'you' : role === 'error' ? 'error' : 'grok';
  const body = document.createElement('div');
  body.className = 'text';
  body.textContent = text;
  msg.append(who, body);
  log.append(msg);
  scrollDown();
  return body;
}

function scrollDown() {
  const container = document.getElementById('log');
  container.scrollTop = container.scrollHeight;
}

function setBusy(value) {
  busy = value;
  send.disabled = value;
  send.textContent = value ? '...' : 'Send';
}

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 200) + 'px';
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.getElementById('reset').addEventListener('click', () => {
  if (busy) return;
  history = [];
  log.innerHTML = '<p class="empty">Ask Grok anything.</p>';
  input.focus();
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || busy) return;

  addMessage('user', text);
  history.push({ role: 'user', content: text });
  input.value = '';
  input.style.height = 'auto';
  setBusy(true);

  const target = addMessage('assistant', '');
  let answer = '';
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Grok-Bot': '1' },
      body: JSON.stringify({ messages: history }),
    });
    if (!response.ok) throw new Error(await response.text() || ('HTTP ' + response.status));
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      answer += decoder.decode(value, { stream: true });
      target.textContent = answer;
      scrollDown();
    }
    history.push({ role: 'assistant', content: answer });
  } catch (error) {
    target.closest('.msg').className = 'msg error';
    target.textContent = String(error.message || error);
    history.pop();
  } finally {
    setBusy(false);
    input.focus();
  }
});
</script>
</body>
</html>
"""


def _make_handler(client: GrokClient, settings: Settings):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "grokbot"

        def log_message(self, *args) -> None:  # keep the terminal readable
            pass

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                page = PAGE.replace("__MODEL__", client.model).encode("utf-8")
                self._respond(200, "text/html; charset=utf-8", page)
            else:
                self._respond(404, "text/plain; charset=utf-8", b"not found")

        def do_POST(self) -> None:
            if self.path != "/api/chat":
                self._respond(404, "text/plain; charset=utf-8", b"not found")
                return
            if not self.headers.get(GUARD_HEADER):
                self._respond(403, "text/plain; charset=utf-8", b"missing bot header")
                return

            try:
                messages = self._read_messages()
            except ValueError as error:
                self._respond(400, "text/plain; charset=utf-8", str(error).encode("utf-8"))
                return

            payload = [{"role": "system", "content": settings.system_prompt}, *messages]
            try:
                stream = client.stream_chat(payload)
                first = next(stream, "")
            except GrokError as error:
                self._respond(502, "text/plain; charset=utf-8", str(error).encode("utf-8"))
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            try:
                for delta in itertools.chain([first], stream):
                    if delta:
                        self.wfile.write(delta.encode("utf-8"))
                        self.wfile.flush()
            except (GrokError, BrokenPipeError, ConnectionResetError):
                pass

        def _read_messages(self) -> list[dict[str, str]]:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError("request body missing or too large")
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError("request body is not valid JSON") from None

            raw = body.get("messages") if isinstance(body, dict) else None
            if not isinstance(raw, list) or not raw:
                raise ValueError("expected a non-empty 'messages' list")

            messages = []
            for item in raw:
                if not isinstance(item, dict):
                    raise ValueError("each message must be an object")
                role, content = item.get("role"), item.get("content")
                if role not in ALLOWED_ROLES or not isinstance(content, str):
                    raise ValueError("each message needs a user/assistant role and string content")
                messages.append({"role": role, "content": content})
            return messages

        def _respond(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(
    client: GrokClient,
    settings: Settings,
    *,
    host: str = "127.0.0.1",
    port: int = 8777,
    open_browser: bool = True,
) -> int:
    try:
        server = ThreadingHTTPServer((host, port), _make_handler(client, settings))
    except OSError as error:
        print(
            f"Could not start the web UI on {host}:{port}: {error}. Try --port {port + 1}.",
            file=sys.stderr,
        )
        return 1
    server.daemon_threads = True
    url = f"http://{host}:{server.server_address[1]}"
    print(f"Grok bot web UI on {url} (model {client.model}). Press Ctrl-C to stop.")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0
