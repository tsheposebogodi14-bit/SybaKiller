"""Agent base — optional Ollama LLM hook for research narratives."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx


class Agent(ABC):
    name: str = "agent"

    def __init__(self, ollama_url: str = "http://127.0.0.1:11434") -> None:
        self._ollama_url = ollama_url.rstrip("/")

    def llm_prompt(self, model: str, prompt: str) -> str | None:
        """Query local Ollama; returns None if unavailable."""
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{self._ollama_url}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
                return str(data.get("response", ""))
        except httpx.HTTPError:
            return None

    @abstractmethod
    def run(self, **kwargs: Any) -> dict[str, Any]: ...
