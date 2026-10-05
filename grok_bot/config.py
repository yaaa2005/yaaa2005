from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"
DEFAULT_MODEL = "grok-4-fast"
DEFAULT_BASE_URL = "https://api.x.ai/v1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
KEY_PATTERN = re.compile(r"^xai-\S{8,}$")


def load_env() -> None:
    load_dotenv(ENV_PATH, override=True)


def api_key() -> str:
    load_env()
    return (os.getenv("XAI_API_KEY") or "").strip()


def model_name() -> str:
    load_env()
    return (os.getenv("GROK_MODEL") or DEFAULT_MODEL).strip()


def base_url() -> str:
    load_env()
    return (os.getenv("GROK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def is_configured() -> bool:
    return bool(api_key())


def validate_api_key(value: str) -> str:
    key = value.strip()
    if not key:
        raise ValueError("API key is empty.")
    if "\n" in key or "\r" in key:
        raise ValueError("API key must be a single line.")
    if not KEY_PATTERN.match(key):
        raise ValueError("That does not look like an xAI key. It should start with xai-")
    return key


def upsert_env_value(key: str, value: str, path: Path | None = None) -> Path:
    target = path or ENV_PATH
    lines: list[str] = []
    if target.exists():
        lines = target.read_text(encoding="utf-8").splitlines()

    prefix = f"{key}="
    export_prefix = f"export {key}="
    replaced = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(prefix) or stripped.startswith(export_prefix):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        if out and out[-1] != "":
            out.append("")
        out.append(f"{key}={value}")

    target.write_text("\n".join(out) + "\n", encoding="utf-8")
    load_dotenv(target, override=True)
    return target


def save_api_key(value: str) -> Path:
    key = validate_api_key(value)
    return upsert_env_value("XAI_API_KEY", key)
