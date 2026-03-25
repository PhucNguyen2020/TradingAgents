import threading
from typing import Any, Dict, List, Union

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import AIMessage


class StatsCallbackHandler(BaseCallbackHandler):
    """Callback handler that tracks LLM calls, tool calls, and token usage."""

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self.llm_calls = 0
        self.tool_calls = 0
        self.tokens_in = 0
        self.tokens_out = 0

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Increment LLM call counter when an LLM starts."""
        with self._lock:
            self.llm_calls += 1

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],
        **kwargs: Any,
    ) -> None:
        """Increment LLM call counter when a chat model starts."""
        with self._lock:
            self.llm_calls += 1

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Extract token usage from LLM response."""
        tokens_in = 0
        tokens_out = 0

        try:
            generation = response.generations[0][0]
        except (IndexError, TypeError):
            generation = None

        if generation is not None and hasattr(generation, "message"):
            message = generation.message
            if isinstance(message, AIMessage) and getattr(
                message, "usage_metadata", None
            ):
                um = message.usage_metadata
                if isinstance(um, dict):
                    tokens_in = int(um.get("input_tokens") or 0)
                    tokens_out = int(um.get("output_tokens") or 0)

        # OpenAI-compatible APIs (including some Ollama builds) expose usage on llm_output only
        if tokens_in == 0 and tokens_out == 0 and response.llm_output:
            tu = response.llm_output.get("token_usage")
            if isinstance(tu, dict):
                tokens_in = int(
                    tu.get("prompt_tokens") or tu.get("input_tokens") or 0
                )
                tokens_out = int(
                    tu.get("completion_tokens") or tu.get("output_tokens") or 0
                )

        if tokens_in == 0 and tokens_out == 0 and generation is not None:
            gi = getattr(generation, "generation_info", None) or {}
            if isinstance(gi, dict):
                tu = gi.get("token_usage")
                if isinstance(tu, dict):
                    tokens_in = int(
                        tu.get("prompt_tokens") or tu.get("input_tokens") or 0
                    )
                    tokens_out = int(
                        tu.get("completion_tokens") or tu.get("output_tokens") or 0
                    )

        if tokens_in or tokens_out:
            with self._lock:
                self.tokens_in += tokens_in
                self.tokens_out += tokens_out

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Increment tool call counter when a tool starts."""
        with self._lock:
            self.tool_calls += 1

    def get_stats(self) -> Dict[str, Any]:
        """Return current statistics."""
        with self._lock:
            return {
                "llm_calls": self.llm_calls,
                "tool_calls": self.tool_calls,
                "tokens_in": self.tokens_in,
                "tokens_out": self.tokens_out,
            }
