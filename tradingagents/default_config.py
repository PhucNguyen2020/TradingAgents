import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "llama_cpp",
    "deep_think_llm": "Qwen3.5-4B.Q8_0.gguf",
    "quick_think_llm": "Qwen3.5-4B.Q8_0.gguf",
    "backend_url": os.getenv("LLAMA_CPP_BASE_URL", "http://127.0.0.1:8080/v1"),
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    # Report language: "en" (default) or "vi" / "vietnamese" for Vietnamese output
    "report_language": os.getenv("TRADINGAGENTS_REPORT_LANGUAGE", "en"),
    # Analyst tool calling:
    # - "auto" (try native, then JSON-in-text fallback) for Ollama/vLLM/llama.cpp
    # - "native" (force native tool calling)
    # - "text" (force JSON-in-text tool protocol)
    #
    # Models like deepseek-r1 need "auto" or "text" — they do not support native tools.
    "ollama_analyst_tool_mode": os.getenv("OLLAMA_ANALYST_TOOL_MODE", "auto"),
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, yfinance
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
}
