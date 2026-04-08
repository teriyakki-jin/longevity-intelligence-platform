"""Anthropic Claude API client for the AI health coach."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, AsyncGenerator, Generator

import anthropic

from longevity.common.config import get_settings
from longevity.common.exceptions import CoachError
from longevity.common.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT_PATH = Path("src/longevity/coach/prompts/system.txt")

COACH_TOOLS = [
    {
        "name": "run_intervention_simulation",
        "description": (
            "Simulate the effect of lifestyle interventions on biological age. "
            "Use this when the user asks 'what if I exercise more', 'what if I quit smoking', etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "interventions": {
                    "type": "array",
                    "description": "List of interventions to simulate",
                    "items": {
                        "type": "object",
                        "properties": {
                            "variable": {
                                "type": "string",
                                "enum": [
                                    "exercise_minutes_per_week",
                                    "sleep_hours",
                                    "drinks_per_week",
                                    "bmi",
                                    "smoking_status_encoded",
                                ],
                            },
                            "current": {"type": "number"},
                            "target": {"type": "number"},
                        },
                        "required": ["variable", "current", "target"],
                    },
                },
            },
            "required": ["interventions"],
        },
    },
    {
        "name": "lookup_food_nutrition",
        "description": "Look up nutritional content of a food and its impact on biological age",
        "input_schema": {
            "type": "object",
            "properties": {
                "food_name": {"type": "string", "description": "Name of the food to look up"},
                "portion_grams": {"type": "number", "description": "Portion size in grams"},
            },
            "required": ["food_name"],
        },
    },
]


def _load_system_prompt() -> str:
    if _SYSTEM_PROMPT_PATH.exists():
        return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return "You are a helpful health coach. Never diagnose or prescribe."


class HealthCoachClient:
    """Claude API client with retry, streaming, and tool use support."""

    def __init__(
        self,
        model: str = "claude-opus-4-6",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise CoachError("ANTHROPIC_API_KEY not configured")

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._max_retries = max_retries
        self._system_prompt = _load_system_prompt()

    def chat(
        self,
        messages: list[dict[str, Any]],
        health_context: str | None = None,
    ) -> str:
        """Send a chat message and return the full response.

        Args:
            messages: List of {role, content} dicts.
            health_context: Optional user health context to prepend to system prompt.
        """
        system = self._system_prompt
        if health_context:
            system = f"{system}\n\n## Current User Health Context\n{health_context}"

        for attempt in range(self._max_retries):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system,
                    messages=messages,
                    tools=COACH_TOOLS,
                    temperature=self._temperature,
                )
                return self._extract_text(response)
            except anthropic.RateLimitError:
                wait = 2 ** attempt
                logger.warning("rate_limit_hit", attempt=attempt + 1, wait_secs=wait)
                time.sleep(wait)
            except anthropic.APIError as e:
                logger.error("claude_api_error", error=str(e))
                raise CoachError(f"Claude API error: {e}") from e

        raise CoachError("Max retries exceeded for Claude API call")

    def stream_chat(
        self,
        messages: list[dict[str, Any]],
        health_context: str | None = None,
    ) -> Generator[str, None, None]:
        """Stream chat response token by token."""
        system = self._system_prompt
        if health_context:
            system = f"{system}\n\n## Current User Health Context\n{health_context}"

        try:
            with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=messages,
                temperature=self._temperature,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except anthropic.APIError as e:
            raise CoachError(f"Streaming error: {e}") from e

    def _extract_text(self, response: anthropic.types.Message) -> str:
        """Extract text content from a Claude message response."""
        texts = []
        for block in response.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "\n".join(texts)
