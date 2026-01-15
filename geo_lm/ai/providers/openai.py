"""OpenAI LLM provider."""

import asyncio
from typing import Optional

import openai

from geo_lm.exceptions import LLMError
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
    ):
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key.
            model: Model name to use.
            base_url: Optional base URL for API (for OpenAI-compatible endpoints).
        """
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = openai.OpenAI(**client_kwargs)
        self._async_client = openai.AsyncOpenAI(**client_kwargs)

    @property
    def provider_name(self) -> str:
        return "openai"

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
        """Generate text using OpenAI."""
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            response = await self._async_client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            return ""

        except openai.APIError as e:
            raise LLMError(f"OpenAI API error: {e}")
        except Exception as e:
            raise LLMError(f"Error generating with OpenAI: {e}")

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


class LlamaProvider(OpenAIProvider):
    """Llama API provider (uses OpenAI-compatible endpoint)."""

    def __init__(
        self,
        api_key: str,
        model: str = "Llama-4-Maverick-17B-128E-Instruct-FP8",
    ):
        """
        Initialize the Llama provider.

        Args:
            api_key: Llama API key.
            model: Model name to use.
        """
        super().__init__(
            api_key=api_key,
            model=model,
            base_url="https://api.llama.com/compat/v1/",
        )

    @property
    def provider_name(self) -> str:
        return "llama"
