from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx

from grok_bot import config

SYSTEM_PROMPT = (
    "You are Grok, a helpful assistant running as a local chatbot on the user's "
    "own computer. Be clear, concise, and useful. Reply in the same language "
    "the user writes in."
)


class GrokError(RuntimeError):
    """Raised when the xAI API cannot complete a chat request."""


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _payload(messages: list[dict[str, str]], stream: bool) -> dict[str, Any]:
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    return {
        "model": config.model_name(),
        "messages": full_messages,
        "stream": stream,
    }


def _error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
        err = data.get("error")
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
        if isinstance(err, str):
            return err
    except Exception:
        pass
    text = response.text.strip()
    return text or f"xAI API returned HTTP {response.status_code}"


def iter_chat(
    messages: list[dict[str, str]],
    *,
    timeout: float = 180.0,
    client: httpx.Client | None = None,
) -> Iterator[str]:
    """Yield text chunks from Grok using the Chat Completions stream."""
    api_key = config.api_key()
    if not api_key:
        raise GrokError(
            "No XAI_API_KEY found. Open the setup page and paste your key from https://console.x.ai/"
        )
    if not messages:
        raise GrokError("Message list is empty.")

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        with http.stream(
            "POST",
            f"{config.base_url()}/chat/completions",
            headers=_auth_headers(api_key),
            json=_payload(messages, stream=True),
        ) as response:
            if response.status_code >= 400:
                response.read()
                raise GrokError(_error_message(response))
            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("data:"):
                    data = line[5:].strip()
                else:
                    data = line.strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content
    except httpx.HTTPError as exc:
        raise GrokError(f"Could not reach xAI: {exc}") from exc
    finally:
        if owns_client:
            http.close()
