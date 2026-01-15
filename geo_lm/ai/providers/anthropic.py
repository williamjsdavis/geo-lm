"""Anthropic Claude LLM provider."""

import asyncio
from typing import Optional

import anthropic

from geo_lm.exceptions import LLMError
from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key.
            model: Model name to use.
        """
        self._api_key = api_key
        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key)
        self._async_client = anthropic.AsyncAnthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate text using Claude."""
        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self._model,
                "max_tokens": max_tokens,
                "messages": messages,
                "temperature": temperature,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = await self._async_client.messages.create(**kwargs)

            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text
            return ""

        except anthropic.APIError as e:
            raise LLMError(f"Anthropic API error: {e}")
        except Exception as e:
            raise LLMError(f"Error generating with Anthropic: {e}")

    async def generate_with_retry(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_retries: int = 3,
    ) -> str:
        """Generate text with retry logic."""
        last_error = None

        for attempt in range(max_retries):
            try:
                return await self.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except LLMError as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2**attempt)

        raise last_error or LLMError("Failed to generate after retries")
