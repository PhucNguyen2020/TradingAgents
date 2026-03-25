"""Load CLI run configuration from environment variables (non-interactive mode).

Enable with TRADINGAGENTS_CLI_FROM_ENV=1 (or true/yes).
Requires STOCK_LIST (or TRADINGAGENTS_STOCK_LIST) and other variables listed in .env.example.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

from cli.models import AnalystType


def _truthy(val: str | None) -> bool:
    if val is None:
        return False
    return val.strip().lower() in ("1", "true", "yes", "on")


def _default_backend_url(provider_lower: str) -> str:
    llama_cpp = os.getenv("LLAMA_CPP_BASE_URL", "http://127.0.0.1:8080/v1")
    openai_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    defaults = {
        "openai": openai_base,
        "google": "https://generativelanguage.googleapis.com/v1",
        "anthropic": "https://api.anthropic.com/",
        "xai": "https://api.x.ai/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "ollama": "http://localhost:11434/v1",
        "vllm": "http://localhost:8000/v1",
        "llama_cpp": llama_cpp,
        "cerebras": "https://api.cerebras.ai/v1",
    }
    return defaults.get(provider_lower, "https://api.openai.com/v1")


def _parse_stock_ticker() -> str:
    raw = (os.getenv("STOCK_LIST") or os.getenv("TRADINGAGENTS_STOCK_LIST") or "").strip()
    if not raw:
        raise ValueError("STOCK_LIST (or TRADINGAGENTS_STOCK_LIST) is required when TRADINGAGENTS_CLI_FROM_ENV is set.")
    first = raw.split(",")[0].strip().upper()
    if not first:
        raise ValueError("STOCK_LIST must contain at least one non-empty ticker.")
    return first


def _parse_analysis_date() -> str:
    raw = (os.getenv("TRADINGAGENTS_ANALYSIS_DATE") or os.getenv("ANALYSIS_DATE") or "").strip()
    if not raw:
        return datetime.now().strftime("%Y-%m-%d")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        raise ValueError("TRADINGAGENTS_ANALYSIS_DATE must be YYYY-MM-DD.")
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError("TRADINGAGENTS_ANALYSIS_DATE is not a valid calendar date.") from e
    if dt.date() > datetime.now().date():
        raise ValueError("TRADINGAGENTS_ANALYSIS_DATE cannot be in the future.")
    return raw


_ANALYST_ALIASES = {
    "market": AnalystType.MARKET,
    "social": AnalystType.SOCIAL,
    "news": AnalystType.NEWS,
    "fundamentals": AnalystType.FUNDAMENTALS,
}


def _parse_analysts() -> list[AnalystType]:
    raw = (os.getenv("TRADINGAGENTS_ANALYSTS") or "").strip().lower()
    if not raw:
        raise ValueError(
            "TRADINGAGENTS_ANALYSTS is required when TRADINGAGENTS_CLI_FROM_ENV is set "
            "(comma-separated: market,social,news,fundamentals)."
        )
    keys = [p.strip() for p in raw.split(",") if p.strip()]
    if not keys:
        raise ValueError("TRADINGAGENTS_ANALYSTS must list at least one analyst.")
    out: list[AnalystType] = []
    for k in keys:
        if k not in _ANALYST_ALIASES:
            raise ValueError(
                f"Unknown analyst '{k}' in TRADINGAGENTS_ANALYSTS. "
                f"Use: {', '.join(_ANALYST_ALIASES)}."
            )
        t = _ANALYST_ALIASES[k]
        if t not in out:
            out.append(t)
    return out


_DEPTH_ALIASES = {"shallow": 1, "medium": 3, "deep": 5, "1": 1, "3": 3, "5": 5}


def _parse_research_depth() -> int:
    raw = (os.getenv("TRADINGAGENTS_RESEARCH_DEPTH") or "").strip().lower()
    if not raw:
        raise ValueError(
            "TRADINGAGENTS_RESEARCH_DEPTH is required when TRADINGAGENTS_CLI_FROM_ENV is set "
            "(1, 3, 5 or shallow, medium, deep)."
        )
    if raw in _DEPTH_ALIASES:
        return _DEPTH_ALIASES[raw]
    raise ValueError("TRADINGAGENTS_RESEARCH_DEPTH must be 1, 3, 5, shallow, medium, or deep.")


_VALID_PROVIDERS = frozenset(
    {
        "openai",
        "google",
        "anthropic",
        "xai",
        "openrouter",
        "ollama",
        "vllm",
        "llama_cpp",
        "cerebras",
    }
)


def _parse_llm_provider() -> tuple[str, str]:
    raw = (os.getenv("TRADINGAGENTS_LLM_PROVIDER") or "").strip().lower()
    if not raw:
        raise ValueError(
            "TRADINGAGENTS_LLM_PROVIDER is required when TRADINGAGENTS_CLI_FROM_ENV is set "
            f"({_VALID_PROVIDERS})."
        )
    if raw not in _VALID_PROVIDERS:
        raise ValueError(f"TRADINGAGENTS_LLM_PROVIDER must be one of: {', '.join(sorted(_VALID_PROVIDERS))}.")
    backend = (os.getenv("TRADINGAGENTS_BACKEND_URL") or "").strip()
    if not backend:
        backend = _default_backend_url(raw)
    return raw, backend


def _parse_model_ids(provider_lower: str) -> tuple[str, str]:
    quick = (os.getenv("TRADINGAGENTS_QUICK_THINK_LLM") or "").strip()
    deep = (os.getenv("TRADINGAGENTS_DEEP_THINK_LLM") or "").strip()
    if not quick or not deep:
        raise ValueError(
            "TRADINGAGENTS_QUICK_THINK_LLM and TRADINGAGENTS_DEEP_THINK_LLM are required "
            "when TRADINGAGENTS_CLI_FROM_ENV is set (model ids for quick and deep agents)."
        )
    return quick, deep


def _parse_google_thinking() -> str | None:
    raw = (os.getenv("TRADINGAGENTS_GOOGLE_THINKING_LEVEL") or "").strip().lower()
    if not raw:
        return None
    if raw not in ("high", "minimal"):
        raise ValueError("TRADINGAGENTS_GOOGLE_THINKING_LEVEL must be high or minimal.")
    return raw


def _parse_openai_reasoning() -> str | None:
    raw = (os.getenv("TRADINGAGENTS_OPENAI_REASONING_EFFORT") or "").strip().lower()
    if not raw:
        return None
    if raw not in ("medium", "high", "low"):
        raise ValueError("TRADINGAGENTS_OPENAI_REASONING_EFFORT must be medium, high, or low.")
    return raw


def load_cli_selections_from_env() -> dict[str, Any] | None:
    """If TRADINGAGENTS_CLI_FROM_ENV is enabled, return selections dict; else None."""
    if not _truthy(os.getenv("TRADINGAGENTS_CLI_FROM_ENV")):
        return None
    ticker = _parse_stock_ticker()
    analysis_date = _parse_analysis_date()
    analysts = _parse_analysts()
    research_depth = _parse_research_depth()
    llm_provider, backend_url = _parse_llm_provider()
    shallow, deep = _parse_model_ids(llm_provider)

    thinking_level = None
    reasoning_effort = None
    if llm_provider == "google":
        thinking_level = _parse_google_thinking()
    elif llm_provider == "openai":
        reasoning_effort = _parse_openai_reasoning()

    return {
        "ticker": ticker,
        "analysis_date": analysis_date,
        "analysts": analysts,
        "research_depth": research_depth,
        "llm_provider": llm_provider,
        "backend_url": backend_url,
        "shallow_thinker": shallow,
        "deep_thinker": deep,
        "google_thinking_level": thinking_level,
        "openai_reasoning_effort": reasoning_effort,
    }
