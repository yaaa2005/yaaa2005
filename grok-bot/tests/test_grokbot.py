"""Tests for the local Grok bot, run against a fake xAI API on localhost."""

from __future__ import annotations

import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from grokbot import config
from grokbot.client import GrokClient, GrokError
from grokbot.config import Settings, load_env_file, load_settings
from grokbot.web import _make_handler


class FakeAPIHandler(BaseHTTPRequestHandler):
    """Stands in for api.x.ai. The requested model selects the scenario."""

    protocol_version = "HTTP/1.1"

    def log_message(self, *args) -> None:
        pass

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._json(200, {"data": [{"id": "grok-4"}, {"id": "grok-3"}]})
        else:
            self._json(404, {"error": {"message": "nope"}})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        self.server.last_request = body  # type: ignore[attr-defined]
        self.server.last_auth = self.headers.get("Authorization")  # type: ignore[attr-defined]
        model = body.get("model")

        if model == "unauthorized":
            self._json(401, {"error": {"message": "Incorrect API key provided"}})
        elif model == "boom":
            self._json(500, {})
        elif not body.get("stream"):
            self._json(200, {"choices": [{"message": {"content": "whole answer"}}]})
        elif model == "mid-failure":
            self._sse(["data: " + json.dumps(_delta("partial")), "data: " + json.dumps({"error": {"message": "upstream exploded"}})])
        else:
            self._sse(
                [
                    ": warm-up comment",
                    "data: " + json.dumps(_delta("Hello")),
                    "",
                    "data: " + json.dumps(_delta(", ")),
                    "data: not-json",
                    "data: " + json.dumps(_delta("world!")),
                    "data: [DONE]",
                    "data: " + json.dumps(_delta("after done")),
                ]
            )

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse(self, lines: list[str]) -> None:
        body = ("\n\n".join(lines) + "\n\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _delta(text: str) -> dict:
    return {"choices": [{"delta": {"content": text}}]}


def start_server(handler_class) -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server, cls.url = start_server(FakeAPIHandler)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def client(self, model: str = "grok-4") -> GrokClient:
        return GrokClient("test-key", model=model, base_url=f"{self.url}/v1", timeout=10)

    def test_stream_yields_deltas_until_done(self) -> None:
        deltas = list(self.client().stream_chat([{"role": "user", "content": "hi"}]))
        self.assertEqual(deltas, ["Hello", ", ", "world!"])

    def test_stream_sends_key_and_messages(self) -> None:
        list(self.client().stream_chat([{"role": "user", "content": "hi"}]))
        self.assertEqual(self.server.last_auth, "Bearer test-key")
        self.assertEqual(self.server.last_request["messages"], [{"role": "user", "content": "hi"}])
        self.assertTrue(self.server.last_request["stream"])

    def test_non_streaming_chat(self) -> None:
        self.assertEqual(self.client().chat([{"role": "user", "content": "hi"}]), "whole answer")

    def test_list_models(self) -> None:
        self.assertEqual(self.client().list_models(), ["grok-3", "grok-4"])

    def test_bad_key_explains_itself(self) -> None:
        with self.assertRaises(GrokError) as caught:
            list(self.client("unauthorized").stream_chat([{"role": "user", "content": "hi"}]))
        self.assertEqual(caught.exception.status, 401)
        self.assertIn("Incorrect API key", str(caught.exception))

    def test_server_error_without_detail(self) -> None:
        with self.assertRaises(GrokError) as caught:
            list(self.client("boom").stream_chat([{"role": "user", "content": "hi"}]))
        self.assertIn("HTTP 500", str(caught.exception))

    def test_error_inside_stream(self) -> None:
        stream = self.client("mid-failure").stream_chat([{"role": "user", "content": "hi"}])
        self.assertEqual(next(stream), "partial")
        with self.assertRaises(GrokError) as caught:
            next(stream)
        self.assertIn("upstream exploded", str(caught.exception))

    def test_unreachable_host(self) -> None:
        client = GrokClient("k", model="grok-4", base_url="http://127.0.0.1:1/v1", timeout=5)
        with self.assertRaises(GrokError) as caught:
            client.chat([{"role": "user", "content": "hi"}])
        self.assertIn("Could not reach", str(caught.exception))


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.dict(os.environ, {}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ("XAI_API_KEY", "GROK_API_KEY", "GROK_MODEL", "GROK_TIMEOUT", "XAI_BASE_URL"):
            os.environ.pop(name, None)
        finder = mock.patch.object(config, "_find_env_file", return_value=None)
        finder.start()
        self.addCleanup(finder.stop)

    def test_env_file_parsing_keeps_existing_values(self) -> None:
        os.environ["GROK_MODEL"] = "already-set"
        with TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "# a comment\n"
                'XAI_API_KEY="quoted-key"\n'
                "export GROK_SYSTEM_PROMPT=be brief\n"
                "GROK_MODEL=from-file\n"
                "nonsense line\n",
                encoding="utf-8",
            )
            load_env_file(env_file)
        self.assertEqual(os.environ["XAI_API_KEY"], "quoted-key")
        self.assertEqual(os.environ["GROK_SYSTEM_PROMPT"], "be brief")
        self.assertEqual(os.environ["GROK_MODEL"], "already-set")

    def test_missing_key_is_a_clear_error(self) -> None:
        with self.assertRaises(config.ConfigError) as caught:
            load_settings()
        self.assertIn("XAI_API_KEY", str(caught.exception))

    def test_defaults_and_overrides(self) -> None:
        os.environ["XAI_API_KEY"] = "env-key"
        os.environ["GROK_MODEL"] = "grok-3"
        settings = load_settings()
        self.assertEqual((settings.api_key, settings.model), ("env-key", "grok-3"))
        self.assertEqual(settings.base_url, config.DEFAULT_BASE_URL)

        overridden = load_settings(model="grok-4", base_url="http://localhost:9/v1/", timeout=5)
        self.assertEqual(overridden.model, "grok-4")
        self.assertEqual(overridden.base_url, "http://localhost:9/v1")
        self.assertEqual(overridden.timeout, 5)

    def test_api_key_falls_back_to_grok_api_key(self) -> None:
        os.environ["GROK_API_KEY"] = "legacy-key"
        self.assertEqual(load_settings().api_key, "legacy-key")

    def test_bad_timeout_is_rejected(self) -> None:
        os.environ["XAI_API_KEY"] = "env-key"
        os.environ["GROK_TIMEOUT"] = "soon"
        with self.assertRaises(config.ConfigError):
            load_settings()


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.api, api_url = start_server(FakeAPIHandler)
        client = GrokClient("test-key", model="grok-4", base_url=f"{api_url}/v1", timeout=10)
        settings = Settings(api_key="test-key", model="grok-4", system_prompt="be brief")
        cls.web, cls.url = start_server(_make_handler(client, settings))

    @classmethod
    def tearDownClass(cls) -> None:
        for server in (cls.web, cls.api):
            server.shutdown()
            server.server_close()

    def post(self, payload: dict, *, guard: bool = True) -> tuple[int, str]:
        headers = {"Content-Type": "application/json"}
        if guard:
            headers["X-Grok-Bot"] = "1"
        request = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8")

    def test_page_is_served_with_the_model_name(self) -> None:
        with urllib.request.urlopen(f"{self.url}/", timeout=10) as response:
            page = response.read().decode("utf-8")
        self.assertIn("Grok bot", page)
        self.assertIn("grok-4", page)
        self.assertNotIn("__MODEL__", page)

    def test_chat_streams_the_answer(self) -> None:
        status, body = self.post({"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(status, 200)
        self.assertEqual(body, "Hello, world!")

    def test_system_prompt_is_added_server_side(self) -> None:
        self.post({"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(
            self.api.last_request["messages"][0],
            {"role": "system", "content": "be brief"},
        )

    def test_guard_header_is_required(self) -> None:
        status, _ = self.post({"messages": [{"role": "user", "content": "hi"}]}, guard=False)
        self.assertEqual(status, 403)

    def test_invalid_payloads_are_rejected(self) -> None:
        self.assertEqual(self.post({})[0], 400)
        self.assertEqual(self.post({"messages": []})[0], 400)
        self.assertEqual(self.post({"messages": [{"role": "system", "content": "x"}]})[0], 400)
        self.assertEqual(self.post({"messages": [{"role": "user", "content": 7}]})[0], 400)

    def test_unknown_path(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(f"{self.url}/secrets", timeout=10)
        self.assertEqual(caught.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
