from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from grok_bot import config
from grok_bot.client import GrokError, iter_chat

STATIC_DIR = Path(__file__).resolve().parent / "static"


class ChatRequest(BaseModel):
    messages: list[dict[str, str]] = Field(default_factory=list)


class SetupRequest(BaseModel):
    api_key: str


def _ensure_localhost(request: Request) -> None:
    host = (request.client.host if request.client else "") or ""
    if host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="This bot only accepts local requests.")


def create_app() -> FastAPI:
    app = FastAPI(title="Grok local bot", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def home() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/status")
    def status() -> dict[str, object]:
        configured = config.is_configured()
        key = config.api_key()
        return {
            "configured": configured,
            "model": config.model_name(),
            "host": "this computer (localhost)",
            "key_hint": f"{key[:7]}…{key[-4:]}" if configured and len(key) > 12 else None,
        }

    @app.post("/api/setup")
    def setup(payload: SetupRequest, request: Request) -> dict[str, object]:
        _ensure_localhost(request)
        try:
            config.save_api_key(payload.api_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True, "model": config.model_name()}

    @app.post("/api/chat")
    def chat(payload: ChatRequest, request: Request) -> StreamingResponse:
        _ensure_localhost(request)
        if not config.is_configured():
            raise HTTPException(
                status_code=400,
                detail="Add your xAI API key first. Get one at https://console.x.ai/",
            )
        messages = [
            {"role": item.get("role", "user"), "content": item.get("content", "")}
            for item in payload.messages
            if item.get("content", "").strip()
        ]
        if not messages:
            raise HTTPException(status_code=400, detail="Type a message first.")

        def events():
            try:
                for chunk in iter_chat(messages):
                    yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
                yield "data: {\"done\": true}\n\n"
            except GrokError as exc:
                yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    return app


app = create_app()
