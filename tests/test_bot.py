from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from grok_bot import config
from grok_bot.client import GrokError, iter_chat
from grok_bot.server import create_app


class ConfigTests(unittest.TestCase):
    def test_validate_api_key(self) -> None:
        self.assertEqual(config.validate_api_key(" xai-abcdefghij "), "xai-abcdefghij")
        with self.assertRaises(ValueError):
            config.validate_api_key("")
        with self.assertRaises(ValueError):
            config.validate_api_key("sk-not-xai")

    def test_save_api_key_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            env_path = Path(raw) / ".env"
            env_path.write_text("OWM_API_KEY=keep-me\n", encoding="utf-8")
            with patch.object(config, "ENV_PATH", env_path):
                config.save_api_key("xai-testdummykey")
                text = env_path.read_text(encoding="utf-8")
                self.assertIn("OWM_API_KEY=keep-me", text)
                self.assertIn("XAI_API_KEY=xai-testdummykey", text)
                with patch.dict(os.environ, {}, clear=False):
                    # load_dotenv already ran in save_api_key
                    self.assertEqual(os.environ.get("XAI_API_KEY"), "xai-testdummykey")


class ClientTests(unittest.TestCase):
    def test_iter_chat_streams_tokens(self) -> None:
        chunks = [
            b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n',
            b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n',
            b"data: [DONE]\n\n",
        ]

        def handler(request):
            import httpx

            self.assertEqual(str(request.url), "https://api.x.ai/v1/chat/completions")
            return httpx.Response(200, content=b"".join(chunks))

        import httpx

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        with patch.object(config, "api_key", return_value="xai-testkey123"):
            with patch.object(config, "model_name", return_value="grok-4-fast"):
                with patch.object(config, "base_url", return_value="https://api.x.ai/v1"):
                    text = "".join(
                        iter_chat(
                            [{"role": "user", "content": "hi"}],
                            client=client,
                        )
                    )
        self.assertEqual(text, "Hello")

    def test_iter_chat_requires_key(self) -> None:
        with patch.object(config, "api_key", return_value=""):
            with self.assertRaises(GrokError):
                list(iter_chat([{"role": "user", "content": "hi"}]))


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_home_page(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("live on this computer", response.text)

    def test_status_without_key(self) -> None:
        with patch.object(config, "is_configured", return_value=False):
            with patch.object(config, "api_key", return_value=""):
                response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["configured"])

    def test_setup_saves_key(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            env_path = Path(raw) / ".env"
            with patch.object(config, "ENV_PATH", env_path):
                response = self.client.post(
                    "/api/setup", json={"api_key": "xai-localkey99"}
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("XAI_API_KEY=xai-localkey99", env_path.read_text(encoding="utf-8"))

    def test_setup_rejects_bad_key(self) -> None:
        response = self.client.post("/api/setup", json={"api_key": "nope"})
        self.assertEqual(response.status_code, 400)

    def test_chat_streams(self) -> None:
        def fake_iter(_messages):
            yield "Hi "
            yield "there"

        with patch.object(config, "is_configured", return_value=True):
            with patch("grok_bot.server.iter_chat", side_effect=fake_iter):
                with self.client.stream(
                    "POST",
                    "/api/chat",
                    json={"messages": [{"role": "user", "content": "hey"}]},
                ) as response:
                    body = "".join(response.iter_text())
        self.assertEqual(response.status_code, 200)
        self.assertIn('"text": "Hi "', body)
        self.assertIn('"text": "there"', body)
        self.assertIn('"done": true', body)

    def test_chat_without_key(self) -> None:
        with patch.object(config, "is_configured", return_value=False):
            response = self.client.post(
                "/api/chat", json={"messages": [{"role": "user", "content": "hey"}]}
            )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
