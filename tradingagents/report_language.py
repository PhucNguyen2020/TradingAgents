"""Optional output language for LLM-generated reports (see DEFAULT_CONFIG / env)."""

from __future__ import annotations

from typing import Final

_VI_INSTRUCTION: Final[str] = (
    "\n\nLanguage requirement: Write your entire response in Vietnamese, "
    "including markdown tables and narrative. "
    "Keep stock tickers, numbers, dates, and tool parameter names (e.g. indicator ids) "
    "in the exact English form required for tool calls. "
    "When a line must state the transaction decision, end with this exact English line: "
    "FINAL TRANSACTION PROPOSAL: **BUY** or **HOLD** or **SELL** (use only one of BUY, HOLD, SELL)."
)


def get_report_language_instruction() -> str:
    """Return extra prompt text to steer report language; empty if English (default)."""
    from tradingagents.dataflows.config import get_config

    lang = (get_config().get("report_language") or "en").strip().lower()
    if lang in ("vi", "vietnamese", "vn"):
        return _VI_INSTRUCTION
    return ""
