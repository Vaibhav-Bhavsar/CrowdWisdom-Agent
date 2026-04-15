"""
tools/openrouter_client.py

Thin wrapper around the OpenAI-compatible OpenRouter endpoint.
Handles retries, rate-limit back-off, and structured JSON extraction.
"""
import json
import logging
import time
from typing import Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config

logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self, model: str = config.DEFAULT_MODEL):
        self.model = model
        self.client = OpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL,
        )

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1500,
        system: Optional[str] = None,
    ) -> str:
        """Send a chat request and return the assistant's text response."""
        if system:
            messages = [{"role": "system", "content": system}] + messages

        logger.debug("Sending request to OpenRouter | model=%s | msgs=%d", self.model, len(messages))
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_headers={
                "HTTP-Referer": "https://github.com/cwt-marketing-agent",
                "X-Title": "CWT Marketing Agent",
            },
        )
        content = resp.choices[0].message.content or ""
        logger.debug("Got response (%d chars)", len(content))
        return content.strip()

    def chat_json(self, messages: list[dict], system: Optional[str] = None, **kwargs) -> dict:
        """
        Same as chat() but forces a JSON response and parses it.
        Adds a reminder in the system prompt to return only JSON.
        """
        json_system = (system or "") + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation."
        raw = self.chat(messages, system=json_system, **kwargs)
        # strip any accidental markdown fences
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("JSON parse failed; returning raw text under 'raw' key")
            return {"raw": raw}
