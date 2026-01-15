"""Model manager for LLM provider abstraction."""

from enum import Enum
from typing import Optional

from geo_lm.config import settings
from geo_lm.exceptions import ConfigurationError
from .providers.base import BaseLLMProvider
from .providers.anthropic import AnthropicProvider
from .providers.openai import OpenAIProvider, LlamaProvider


class LLMProviderType(str, Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LLAMA = "llama"


class ModelManager:
    """
    Manages LLM providers and model instantiation.

    Example:
        manager = ModelManager()
        provider = await manager.get_provider("anthropic")
        response = await provider.generate("Hello!")
    """

    def __init__(self):
        """Initialize the model manager."""
        self._providers: dict[str, BaseLLMProvider] = {}

    async def get_provider(
        self,
        provider_type: str = "anthropic",
        model: Optional[str] = None,
    ) -> BaseLLMProvider:
        """
        Get or create an LLM provider.

        Args:
            provider_type: The provider type (anthropic, openai, llama).
            model: Optional model name override.

        Returns:
            The LLM provider instance.

        Raises:
            ConfigurationError: If provider not configured.
        """
        cache_key = f"{provider_type}:{model or 'default'}"

        if cache_key in self._providers:
            return self._providers[cache_key]

        provider = self._create_provider(provider_type, model)
        self._providers[cache_key] = provider
        return provider

    def _create_provider(
        self, provider_type: str, model: Optional[str] = None
    ) -> BaseLLMProvider:
        """Create a new provider instance."""
        if provider_type == LLMProviderType.ANTHROPIC.value:
            api_key = settings.anthropic_api_key
            if not api_key:
                raise ConfigurationError(
                    "ANTHROPIC_API_KEY not configured. "
                    "Set GEO_LM_ANTHROPIC_API_KEY environment variable."
                )
            return AnthropicProvider(
                api_key=api_key,
                model=model or settings.default_model,
            )

        elif provider_type == LLMProviderType.OPENAI.value:
            api_key = settings.openai_api_key
            if not api_key:
                raise ConfigurationError(
                    "OPENAI_API_KEY not configured. "
                    "Set GEO_LM_OPENAI_API_KEY environment variable."
                )
            return OpenAIProvider(
                api_key=api_key,
                model=model or "gpt-4o",
            )

        elif provider_type == LLMProviderType.LLAMA.value:
            api_key = settings.llama_api_key
            if not api_key:
                raise ConfigurationError(
                    "LLAMA_API_KEY not configured. "
                    "Set GEO_LM_LLAMA_API_KEY or LLAMA_API_KEY environment variable."
                )
            return LlamaProvider(
                api_key=api_key,
                model=model or "Llama-4-Maverick-17B-128E-Instruct-FP8",
            )

        else:
            raise ConfigurationError(f"Unknown provider type: {provider_type}")

    async def get_default_provider(self) -> BaseLLMProvider:
        """
        Get the default LLM provider.

        Tries providers in order: anthropic, openai, llama.
        """
        # Try providers in preference order
        for provider_type in [
            LLMProviderType.ANTHROPIC,
            LLMProviderType.OPENAI,
            LLMProviderType.LLAMA,
        ]:
            try:
                return await self.get_provider(provider_type.value)
            except ConfigurationError:
                continue

        raise ConfigurationError(
            "No LLM provider configured. "
            "Set one of: GEO_LM_ANTHROPIC_API_KEY, GEO_LM_OPENAI_API_KEY, LLAMA_API_KEY"
        )


# Global model manager instance
model_manager = ModelManager()
