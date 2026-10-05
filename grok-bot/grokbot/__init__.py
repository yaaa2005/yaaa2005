"""A small Grok chat bot that runs locally with no third-party packages."""

from .client import GrokClient, GrokError
from .config import Settings, load_settings

__all__ = ["GrokClient", "GrokError", "Settings", "load_settings"]
__version__ = "1.0.0"
