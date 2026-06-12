"""Anthropic LLMProvider adapter."""

from __future__ import annotations

from typing import Any

import anthropic

from tessera_core.ports.providers import LLMProvider
from tessera_api.config import get_settings


class AnthropicLLMProvider(LLMProvider):
    def __init__(self, model: str | None = None, draft_model: str | None = None) -> None:
        settings = get_settings()
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = model or settings.llm_default_model
        self._draft_model = draft_model or settings.llm_draft_model

    async def complete(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        response = await self._client.messages.create(**kwargs)
        return response.content[0].text

    async def classify(self, prompt: str, max_tokens: int = 256) -> str:
        response = await self._client.messages.create(
            model=self._draft_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.content[0].text
