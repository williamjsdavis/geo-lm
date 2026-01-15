"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            The generated text.
        """
        pass

    @abstractmethod
    async def generate_with_retry(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_retries: int = 3,
    ) -> str:
        """
        Generate text with retry logic.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            max_retries: Maximum number of retries.

        Returns:
            The generated text.
        """
        pass
