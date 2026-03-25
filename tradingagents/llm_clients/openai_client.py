import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from .base_client import BaseLLMClient
from .validators import validate_model


class UnifiedChatOpenAI(ChatOpenAI):
    """ChatOpenAI subclass that strips temperature/top_p for GPT-5 family models.

    GPT-5 family models use reasoning natively. temperature/top_p are only
    accepted when reasoning.effort is 'none'; with any other effort level
    (or for older GPT-5/GPT-5-mini/GPT-5-nano which always reason) the API
    rejects these params. Langchain defaults temperature=0.7, so we must
    strip it to avoid errors.

    Non-GPT-5 models (GPT-4.1, xAI, Ollama, etc.) are unaffected.
    """

    def __init__(self, **kwargs):
        if "gpt-5" in kwargs.get("model", "").lower():
            kwargs.pop("temperature", None)
            kwargs.pop("top_p", None)
        super().__init__(**kwargs)


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI-compatible providers (OpenAI, Ollama, OpenRouter, xAI, vLLM, llama.cpp, Cerebras)."""

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        provider: str = "openai",
        **kwargs,
    ):
        super().__init__(model, base_url, **kwargs)
        self.provider = provider.lower()

    def get_llm(self) -> Any:
        """Return configured ChatOpenAI instance."""
        llm_kwargs = {"model": self.model}

        if self.provider == "openai":
            # Allow overriding OpenAI-compatible base URL (for proxies / custom endpoints).
            llm_kwargs["base_url"] = (
                self.base_url
                or os.getenv("OPENAI_BASE_URL")
                or "https://api.openai.com/v1"
            )
        if self.provider == "xai":
            llm_kwargs["base_url"] = "https://api.x.ai/v1"
            api_key = os.environ.get("XAI_API_KEY")
            if api_key:
                llm_kwargs["api_key"] = api_key
        elif self.provider == "openrouter":
            llm_kwargs["base_url"] = "https://openrouter.ai/api/v1"
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if api_key:
                llm_kwargs["api_key"] = api_key
        elif self.provider == "cerebras":
            # Cerebras Inference API (OpenAI-compatible). See https://inference-docs.cerebras.ai/resources/openai
            llm_kwargs["base_url"] = self.base_url or "https://api.cerebras.ai/v1"
            api_key = os.environ.get("CEREBRAS_API_KEY")
            if api_key:
                llm_kwargs["api_key"] = api_key
        elif self.provider == "vllm":
            # vLLM is typically an OpenAI-compatible server at /v1.
            llm_kwargs["base_url"] = self.base_url or "http://localhost:8000/v1"
            # Most local vLLM deployments are unauthenticated; LangChain still expects api_key.
            if "api_key" not in self.kwargs:
                llm_kwargs["api_key"] = "vllm"
        elif self.provider == "ollama":
            # Ollama supports OpenAI-compatible API at `<host>/v1/chat/completions`.
            # Local defaults to http://localhost:11434/v1.
            llm_kwargs["base_url"] = (
                self.base_url
                or os.getenv("OLLAMA_BASE_URL")
                or "http://localhost:11434/v1"
            )
            # Ollama Cloud requires auth via `Authorization: Bearer <OLLAMA_API_KEY>`.
            # For local endpoints, api_key can be any value (ignored by Ollama).
            api_key = os.getenv("OLLAMA_API_KEY")
            if api_key:
                llm_kwargs["api_key"] = api_key
            else:
                llm_kwargs["api_key"] = "ollama"
        elif self.provider == "llama_cpp":
            # llama.cpp server can expose OpenAI-compatible endpoints.
            llm_kwargs["base_url"] = self.base_url or "http://localhost:8000/v1"
            # Local llama.cpp deployments are usually unauthenticated.
            if "api_key" not in self.kwargs:
                llm_kwargs["api_key"] = "llama.cpp"
        elif self.base_url:
            llm_kwargs["base_url"] = self.base_url

        for key in ("timeout", "max_retries", "reasoning_effort", "api_key", "callbacks", "http_client", "http_async_client"):
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]

        return UnifiedChatOpenAI(**llm_kwargs)

    def validate_model(self) -> bool:
        """Validate model for the provider."""
        return validate_model(self.provider, self.model)
