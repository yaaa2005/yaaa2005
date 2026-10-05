"""Minimal client for the xAI (Grok) chat completions API, stdlib only."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Iterable, Iterator, Mapping, Sequence

Message = Mapping[str, str]


class GrokError(Exception):
    """Raised when the API cannot be reached or returns an error."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class GrokClient:
    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        base_url: str = "https://api.x.ai/v1",
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, payload: dict | None = None, *, method: str = "GET"):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            return urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as error:
            raise GrokError(_describe_http_error(error), status=error.code) from None
        except urllib.error.URLError as error:
            raise GrokError(
                f"Could not reach {self.base_url}: {error.reason}. Check your internet connection."
            ) from None
        except TimeoutError:
            raise GrokError(f"The request timed out after {self.timeout:g}s.") from None
        except OSError as error:  # socket-level failures on older Pythons
            raise GrokError(f"Network error talking to {self.base_url}: {error}") from None

    def stream_chat(self, messages: Sequence[Message]) -> Iterator[str]:
        """Yield answer fragments as the model produces them."""
        payload = {"model": self.model, "messages": list(messages), "stream": True}
        response = self._request("/chat/completions", payload, method="POST")
        with response:
            try:
                for chunk in _iter_sse_data(response):
                    for delta in _deltas(chunk):
                        yield delta
            except OSError as error:
                raise GrokError(f"The answer was cut short: {error}") from None

    def chat(self, messages: Sequence[Message]) -> str:
        """Return the complete answer in one call."""
        payload = {"model": self.model, "messages": list(messages), "stream": False}
        response = self._request("/chat/completions", payload, method="POST")
        with response:
            body = json.loads(response.read().decode("utf-8"))
        choices = body.get("choices") or []
        if not choices:
            raise GrokError("The API returned no answer.")
        return choices[0].get("message", {}).get("content", "")

    def list_models(self) -> list[str]:
        response = self._request("/models")
        with response:
            body = json.loads(response.read().decode("utf-8"))
        return sorted(item.get("id", "") for item in body.get("data", []) if item.get("id"))


def _iter_sse_data(lines: Iterable[bytes]) -> Iterator[dict]:
    for raw_line in lines:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line or not line.startswith("data:"):
            continue
        data = line[len("data:") :].strip()
        if data == "[DONE]":
            return
        try:
            yield json.loads(data)
        except json.JSONDecodeError:
            continue


def _deltas(chunk: dict) -> Iterator[str]:
    if "error" in chunk:
        raise GrokError(_error_message(chunk) or "The API reported an error mid-answer.")
    for choice in chunk.get("choices") or []:
        content = (choice.get("delta") or {}).get("content")
        if content:
            yield content


def _error_message(body: dict) -> str:
    error = body.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
    if isinstance(error, str):
        return error
    message = body.get("message")
    return message if isinstance(message, str) else ""


def _describe_http_error(error: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(error.read().decode("utf-8"))
        detail = _error_message(body) if isinstance(body, dict) else ""
    except (ValueError, OSError):
        detail = ""

    if error.code in (401, 403):
        return detail or "The API rejected your key. Check XAI_API_KEY at https://console.x.ai/."
    if error.code == 404:
        return detail or "Model or endpoint not found. Try --list-models to see what your key allows."
    if error.code == 429:
        return detail or "Rate limited by the API. Wait a moment and try again."
    return detail or f"The API returned HTTP {error.code}."
