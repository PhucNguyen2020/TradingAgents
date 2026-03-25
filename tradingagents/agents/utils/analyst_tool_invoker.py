"""Analyst LLM invoke with tool calling: native bind_tools or JSON-in-text fallback for Ollama."""

from __future__ import annotations

import json
import os
import re
from typing import Any, List

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_core.runnables import Runnable

_OLLAMA_TEXT_TOOLS_CACHE: bool = False


def _is_unsupported_native_tools_error(exc: BaseException) -> bool:
    s = str(exc).lower()
    if "does not support" in s and "tool" in s:
        return True
    if "not support" in s and "tool" in s:
        return True
    if "400" in s and "tool" in s and ("support" in s or "registry.ollama" in s):
        return True
    return False


def _tool_catalog_text(tools: list) -> str:
    lines = []
    for t in tools:
        desc = getattr(t, "description", None) or ""
        lines.append(f"- `{t.name}`: {desc.strip()}")
    return "\n".join(lines)


def _protocol_human_message(tools: list) -> HumanMessage:
    catalog = _tool_catalog_text(tools)
    body = f"""This API does not support native function/tool calling. To request data, reply with ONLY one markdown fenced JSON block (tag it json), using exactly this shape:
```json
{{"tool_calls": [{{"name": "<tool_name>", "arguments": {{...}}}}]}}
```
You may list multiple objects inside `tool_calls`. Valid tool names: {", ".join(repr(t.name) for t in tools)}.

Tool reference:
{catalog}

After each tool result (sent to you as the next user message), either call more tools with the same JSON format, or output your final markdown report with no JSON tool block."""
    return HumanMessage(content=body)


def _extract_tool_calls_from_content(content: str) -> List[dict[str, Any]] | None:
    if not content or not content.strip():
        return None
    for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", content):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            tcs = data.get("tool_calls")
            if isinstance(tcs, list) and len(tcs) > 0:
                return tcs
    stripped = content.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                tcs = data.get("tool_calls")
                if isinstance(tcs, list) and len(tcs) > 0:
                    return tcs
        except json.JSONDecodeError:
            pass
    return None


def _run_tool(name: str, arguments: Any, tools: list) -> str:
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return f"Error: arguments for {name} must be a JSON object, got {type(arguments).__name__}"
    for t in tools:
        if t.name != name:
            continue
        try:
            return str(t.invoke(arguments))
        except Exception as e:
            return f"Error executing {name}: {e!s}"
    return f"Error: unknown tool {name!r}"


def _run_text_tool_loop(
    chain: Runnable, tools: list, messages: List[BaseMessage], max_steps: int = 24
) -> AIMessage:
    conv: List[BaseMessage] = [_protocol_human_message(tools)] + list(messages)
    for _ in range(max_steps):
        ai = chain.invoke({"messages": conv})
        if not isinstance(ai, AIMessage):
            ai = AIMessage(content=str(ai))
        content = ai.content or ""
        tcalls = _extract_tool_calls_from_content(content)
        if tcalls:
            conv.append(AIMessage(content=content))
            for tc in tcalls:
                if not isinstance(tc, dict):
                    continue
                name = tc.get("name")
                if not name:
                    continue
                args = tc.get("arguments")
                if args is None:
                    args = tc.get("args")
                obs = _run_tool(str(name), args, tools)
                conv.append(
                    HumanMessage(
                        content=f"Tool `{name}` result:\n{obs}"
                    )
                )
            continue
        return ai
    raise RuntimeError(
        f"Analyst text-tool loop exceeded max_steps={max_steps}; try a model with native tool support or simplify the task."
    )


def invoke_analyst_with_tools(
    llm: Any,
    prompt: Runnable,
    tools: list,
    messages: List[BaseMessage],
) -> AIMessage:
    """Invoke analyst chain with tools.

    Uses JSON-in-text fallback on Ollama/vLLM/llama.cpp when native tools fail.
    """
    global _OLLAMA_TEXT_TOOLS_CACHE

    from tradingagents.dataflows.config import get_config

    cfg = get_config()
    provider = (cfg.get("llm_provider") or "").lower()
    mode = (
        cfg.get("ollama_analyst_tool_mode")
        or os.getenv("OLLAMA_ANALYST_TOOL_MODE")
        or "auto"
    ).strip().lower()

    if provider not in ("ollama", "vllm", "llama_cpp"):
        chain = prompt | llm.bind_tools(tools)
        return chain.invoke({"messages": messages})

    if mode == "text" or _OLLAMA_TEXT_TOOLS_CACHE:
        chain_plain = prompt | llm
        return _run_text_tool_loop(chain_plain, tools, messages)

    if mode == "native":
        chain = prompt | llm.bind_tools(tools)
        return chain.invoke({"messages": messages})

    # auto
    try:
        chain = prompt | llm.bind_tools(tools)
        return chain.invoke({"messages": messages})
    except Exception as e:
        if _is_unsupported_native_tools_error(e):
            _OLLAMA_TEXT_TOOLS_CACHE = True
            chain_plain = prompt | llm
            return _run_text_tool_loop(chain_plain, tools, messages)
        raise


def reset_ollama_tool_fallback_cache() -> None:
    """For tests: clear cached decision to use text tool protocol."""
    global _OLLAMA_TEXT_TOOLS_CACHE
    _OLLAMA_TEXT_TOOLS_CACHE = False
