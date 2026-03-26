from __future__ import annotations

import asyncio
import logging
import os
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.reporting import save_complete_report_to_disk


def _try_load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    load_dotenv()


@dataclass(frozen=True)
class BotConfig:
    token: str
    chat_id: int
    allowed_chat_ids: set[int]
    results_dir: str
    send_report_as_text: bool
    also_send_report_file: bool


def _parse_int_set(raw: str | None) -> set[int]:
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.split(","):
        p = part.strip()
        if not p:
            continue
        out.add(int(p))
    return out


def load_bot_config() -> BotConfig:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN")

    chat_id_raw = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not chat_id_raw:
        raise ValueError("Missing TELEGRAM_CHAT_ID")
    chat_id = int(chat_id_raw)

    allowed = _parse_int_set(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS"))
    results_dir = os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results")
    send_report_as_text = (os.getenv("TELEGRAM_SEND_REPORT_AS_TEXT") or "1").strip().lower() in ("1", "true", "yes", "on")
    also_send_report_file = (os.getenv("TELEGRAM_SEND_REPORT_FILE") or "0").strip().lower() in ("1", "true", "yes", "on")
    return BotConfig(
        token=token,
        chat_id=chat_id,
        allowed_chat_ids=allowed,
        results_dir=results_dir,
        send_report_as_text=send_report_as_text,
        also_send_report_file=also_send_report_file,
    )


def _load_runtime_config() -> dict[str, Any]:
    """Build TradingAgents config from env + defaults."""
    cfg = DEFAULT_CONFIG.copy()

    # Allow overriding core fields via env (optional)
    if os.getenv("TRADINGAGENTS_LLM_PROVIDER"):
        cfg["llm_provider"] = os.getenv("TRADINGAGENTS_LLM_PROVIDER", cfg["llm_provider"]).strip().lower()
    if os.getenv("TRADINGAGENTS_BACKEND_URL"):
        cfg["backend_url"] = os.getenv("TRADINGAGENTS_BACKEND_URL", cfg.get("backend_url")).strip()
    if os.getenv("TRADINGAGENTS_QUICK_THINK_LLM"):
        cfg["quick_think_llm"] = os.getenv("TRADINGAGENTS_QUICK_THINK_LLM", cfg["quick_think_llm"]).strip()
    if os.getenv("TRADINGAGENTS_DEEP_THINK_LLM"):
        cfg["deep_think_llm"] = os.getenv("TRADINGAGENTS_DEEP_THINK_LLM", cfg["deep_think_llm"]).strip()

    # Optional: language
    if os.getenv("TRADINGAGENTS_REPORT_LANGUAGE"):
        cfg["report_language"] = os.getenv("TRADINGAGENTS_REPORT_LANGUAGE", cfg.get("report_language", "en")).strip()
    if (os.getenv("TELEGRAM_FORCE_VI_REPORT_LANGUAGE") or "0").strip().lower() in ("1", "true", "yes", "on"):
        cfg["report_language"] = "vi"

    # Provider-specific base URL defaults for the Telegram service.
    provider = (cfg.get("llm_provider") or "").strip().lower()
    if provider == "ollama":
        ollama_base = (os.getenv("OLLAMA_BASE_URL") or "").strip()
        # Default to Ollama local, but support Ollama Cloud if configured.
        if not ollama_base:
            ollama_base = "http://localhost:11434/v1"
        # If backend_url is missing or looks like a non-Ollama local endpoint (common when switching providers),
        # prefer the explicit Ollama base URL.
        backend_url = str(cfg.get("backend_url") or "").strip()
        if (not backend_url) or ("localhost:11434" not in backend_url and "ollama.com" not in backend_url):
            cfg["backend_url"] = ollama_base

    return cfg


def _default_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _format_help() -> str:
    return (
        "Commands:\n"
        "- /analyze <TICKER> [YYYY-MM-DD]\n"
        "- /status\n\n"
        "Examples:\n"
        "- /analyze NVDA\n"
        "- /analyze BTC-USD 2026-03-25\n\n"
        "You can also just send a ticker symbol as a message."
    )


def _is_allowed_chat(cfg: BotConfig, incoming_chat_id: int) -> bool:
    if incoming_chat_id == cfg.chat_id:
        return True
    if cfg.allowed_chat_ids and incoming_chat_id in cfg.allowed_chat_ids:
        return True
    return False


def _clip_for_telegram(text: str, max_len: int = 3800) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 16] + "\n...[truncated]..."


def _markdown_to_plain_text(md: str) -> str:
    """Best-effort markdown -> plain text for Telegram readability."""
    if not md:
        return md

    lines = md.splitlines()
    out: list[str] = []
    in_code = False
    for raw in lines:
        line = raw.rstrip("\n")

        if line.strip().startswith("```"):
            in_code = not in_code
            continue

        if in_code:
            out.append(line)
            continue

        if line.lstrip().startswith("#"):
            out.append(line.lstrip("#").strip())
            continue

        # Inline code
        line = line.replace("`", "")

        # Tables: remove pipes for easier reading
        if "|" in line and line.strip().startswith("|"):
            out.append(line.replace("|", " ").strip())
            continue

        out.append(line)

    # Collapse excessive blank lines
    cleaned: list[str] = []
    blank = False
    for l in out:
        if l.strip() == "":
            if blank:
                continue
            blank = True
            cleaned.append("")
        else:
            blank = False
            cleaned.append(l)
    return "\n".join(cleaned).strip()

async def _run_analysis_sync(ticker: str, trade_date: str, config: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    """Run analysis in a worker thread (blocking code)."""
    selected_analysts = ["market", "social", "news", "fundamentals"]
    ta = TradingAgentsGraph(selected_analysts=selected_analysts, debug=False, config=config)
    final_state, _decision = ta.propagate(ticker, trade_date)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(config.get("results_dir", "./results")) / "telegram" / f"{ticker}_{ts}"
    report_file = save_complete_report_to_disk(final_state, ticker, out_dir)
    return final_state, report_file


def _run_analysis_blocking(ticker: str, trade_date: str, config: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    selected_analysts = ["market", "social", "news", "fundamentals"]
    ta = TradingAgentsGraph(selected_analysts=selected_analysts, debug=False, config=config)
    final_state, _decision = ta.propagate(ticker, trade_date)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(config.get("results_dir", "./results")) / "telegram" / f"{ticker}_{ts}"
    report_file = save_complete_report_to_disk(final_state, ticker, out_dir)
    return final_state, report_file


def main() -> None:
    _try_load_dotenv()

    from telegram import Update
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

    logging.basicConfig(
        level=os.getenv("TRADINGAGENTS_TELEGRAM_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Avoid leaking secrets in logs (Telegram bot token appears in request URLs).
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)
    logging.getLogger("openai").setLevel(logging.INFO)

    bot_cfg = load_bot_config()
    runtime_cfg = _load_runtime_config()
    runtime_cfg["results_dir"] = bot_cfg.results_dir

    max_workers = int(os.getenv("TELEGRAM_ANALYSIS_MAX_WORKERS", "2"))
    executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ta-analyze")
    last_job: dict[str, str] = {"status": "idle"}
    jobs: dict[str, str] = {}  # job_id -> status (lightweight)

    async def _send_text(ctx: ContextTypes.DEFAULT_TYPE, text: str) -> None:
        # Telegram message max is 4096; keep small.
        if len(text) <= 3800:
            await ctx.bot.send_message(chat_id=bot_cfg.chat_id, text=text)
            return
        await ctx.bot.send_message(chat_id=bot_cfg.chat_id, text=text[:3800] + "\n...[truncated]...")

    async def _send_long_text(ctx: ContextTypes.DEFAULT_TYPE, text: str) -> None:
        # Split into safe chunks for Telegram (4096 max).
        chunk_size = int(os.getenv("TELEGRAM_TEXT_CHUNK_SIZE", "3200"))
        per_message_delay_s = float(os.getenv("TELEGRAM_PER_MESSAGE_DELAY_S", "0.8"))
        if len(text) <= chunk_size:
            await _send_text(ctx, text)
            return
        parts = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        for i, part in enumerate(parts, start=1):
            header = f"[{i}/{len(parts)}]\n" if len(parts) > 1 else ""
            while True:
                try:
                    await ctx.bot.send_message(chat_id=bot_cfg.chat_id, text=header + part)
                    break
                except Exception as e:
                    # Telegram flood control: wait and retry.
                    retry_after = getattr(e, "retry_after", None)
                    if retry_after is not None:
                        await asyncio.sleep(float(retry_after) + 1.0)
                        continue
                    raise
            if per_message_delay_s > 0:
                await asyncio.sleep(per_message_delay_s)

    def _runtime_backend_summary() -> str:
        provider = str(runtime_cfg.get("llm_provider", "")).strip()
        backend = str(runtime_cfg.get("backend_url", "")).strip()
        quick = str(runtime_cfg.get("quick_think_llm", "")).strip()
        deep = str(runtime_cfg.get("deep_think_llm", "")).strip()
        return (
            f"Provider: {provider or 'n/a'}\n"
            f"Backend URL: {backend or 'n/a'}\n"
            f"Quick model: {quick or 'n/a'}\n"
            f"Deep model: {deep or 'n/a'}"
        )

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat is None:
            return
        if not _is_allowed_chat(bot_cfg, update.effective_chat.id):
            return
        await _send_text(context, "TradingAgents bot is running.\n\n" + _format_help())

    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat is None:
            return
        if not _is_allowed_chat(bot_cfg, update.effective_chat.id):
            return
        running = [k for k, v in jobs.items() if v.startswith("running")]
        msg = f"Status: {last_job['status']}\nActive jobs: {len(running)}/{max_workers}"
        if running:
            msg += "\n" + "\n".join(running[-5:])
        await _send_text(context, msg)

    async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat is None:
            return
        if not _is_allowed_chat(bot_cfg, update.effective_chat.id):
            return

        args = context.args or []
        if not args:
            await _send_text(context, "Usage: /analyze <TICKER> [YYYY-MM-DD]")
            return
        ticker = args[0].strip().upper()
        trade_date = args[1].strip() if len(args) > 1 else os.getenv("TRADINGAGENTS_ANALYSIS_DATE", _default_date())

        # Simple concurrency limit
        running_count = sum(1 for v in jobs.values() if v.startswith("running"))
        if running_count >= max_workers:
            await _send_text(context, f"Server busy: {running_count}/{max_workers} jobs running. Please wait.")
            return

        job_id = uuid.uuid4().hex[:8]
        jobs[job_id] = f"running {ticker} {trade_date}"
        last_job["status"] = jobs[job_id]
        await _send_text(context, f"Queued job {job_id}: analyzing {ticker} on {trade_date}...")

        loop = asyncio.get_running_loop()
        future = executor.submit(_run_analysis_blocking, ticker, trade_date, runtime_cfg)

        async def _finalize() -> None:
            try:
                final_state, report_file = await asyncio.wrap_future(future)
            except Exception as e:
                jobs[job_id] = f"error {ticker} {trade_date}: {e!s}"
                last_job["status"] = jobs[job_id]
                err_summary = (
                    f"Job {job_id} failed for {ticker} on {trade_date}:\n{e!s}\n\n{_runtime_backend_summary()}"
                )
                await _send_text(context, _clip_for_telegram(err_summary))
                tb = traceback.format_exc()
                tb_tail_lines = int(os.getenv("TELEGRAM_TRACEBACK_TAIL_LINES", "80"))
                tb_lines = tb.splitlines()
                tb_tail = "\n".join(tb_lines[-tb_tail_lines:]) if len(tb_lines) > tb_tail_lines else tb
                await _send_long_text(context, "Traceback (tail):\n" + tb_tail)
                return

            jobs[job_id] = f"done {ticker} {trade_date}"
            last_job["status"] = jobs[job_id]
            summary = f"Done job {job_id}: {ticker} {trade_date}\nReport: {report_file.name}"
            await _send_text(context, summary)

            if bot_cfg.send_report_as_text:
                try:
                    report_text = report_file.read_text(encoding="utf-8")
                except Exception:
                    report_text = report_file.read_text(errors="replace")
                if (os.getenv("TELEGRAM_REPORT_PLAIN_TEXT") or "1").strip().lower() in ("1", "true", "yes", "on"):
                    report_text = _markdown_to_plain_text(report_text)
                await _send_long_text(context, report_text)

            if bot_cfg.also_send_report_file:
                with report_file.open("rb") as f:
                    await context.bot.send_document(
                        chat_id=bot_cfg.chat_id,
                        document=f,
                        filename=report_file.name,
                        caption=f"TradingAgents complete report for {ticker} ({trade_date})",
                    )

        # Don't block the handler; run finalize in background.
        context.application.create_task(_finalize())

    async def plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat is None or update.message is None:
            return
        if not _is_allowed_chat(bot_cfg, update.effective_chat.id):
            return
        text = (update.message.text or "").strip()
        if not text:
            return
        if text.startswith("/"):
            return
        # Treat as ticker
        context.args = [text]
        await analyze(update, context)

    app = ApplicationBuilder().token(bot_cfg.token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("analyze", analyze))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text))

    # `run_polling()` manages its own event loop internally.
    logging.getLogger(__name__).info(
        "Telegram bot starting. Sending to chat_id=%s; allowed_chat_ids=%s",
        bot_cfg.chat_id,
        sorted(bot_cfg.allowed_chat_ids) if bot_cfg.allowed_chat_ids else [],
    )
    app.run_polling()


if __name__ == "__main__":
    main()

