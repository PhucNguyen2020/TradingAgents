# TradingAgents/graph/signal_processing.py

from langchain_openai import ChatOpenAI

from tradingagents.report_language import get_report_language_instruction


class SignalProcessor:
    """Processes trading signals to extract actionable decisions."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Initialize with an LLM for processing."""
        self.quick_thinking_llm = quick_thinking_llm

    def process_signal(self, full_signal: str) -> str:
        """
        Process a full trading signal to extract the core decision.

        Args:
            full_signal: Complete trading signal text

        Returns:
            Extracted decision (BUY, SELL, or HOLD)
        """
        system = (
            "You are an efficient assistant designed to analyze paragraphs or financial reports "
            "provided by a group of analysts. Your task is to extract the investment decision: "
            "SELL, BUY, or HOLD. Provide only the extracted decision (SELL, BUY, or HOLD) as your "
            "output, without adding any additional text or information."
        )
        if get_report_language_instruction():
            system += (
                " The report text may be written in Vietnamese; infer the decision and still respond "
                "with exactly one English token: BUY, SELL, or HOLD."
            )

        messages = [
            ("system", system),
            ("human", full_signal),
        ]

        return self.quick_thinking_llm.invoke(messages).content
