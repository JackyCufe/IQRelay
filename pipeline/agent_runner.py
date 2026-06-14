"""
agent_runner.py — Agent Execution Engine
Uses OpenAI SDK (DeepSeek API) to drive 6 agents.
Supports tool_use loops, JSON extraction, multi-turn conversations.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

from config.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

AGENTS_DIR = Path(__file__).parent.parent / "agents"

_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

# ─── Tool Whitelist: per Agent filtering ──────────────
# 01 Gatekeeper: needs submit_gatekeeping_result
# 02/05/06: text-only output, no tools
# 03/04: needs Teams notification + AI Search retrieval

def quick_completion(prompt: str, max_tokens: int = 512) -> str:
    """Fast single-turn LLM call — no tools, no agent loop.
    Use for lightweight tasks like form pre-fill."""
    try:
        response = _client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"[quick_completion] failed: {e}")
        return ""


_AGENT_TOOL_WHITELIST: dict[str, set[str]] = {
    "01-gatekeeper.md":       {"submit_gatekeeping_result"},
    "02-value-transform.md":  set(),
    "03-scenario-test.md":    {"send_teams_message", "search_similar_requirements"},
    "04-release-review.md":   {"send_teams_message", "search_similar_requirements"},
    "05-feedback-collect.md": set(),
    "06-retrospective.md":    set(),
}

_AGENT_MAX_TOKENS: dict[str, int] = {
    "01-gatekeeper.md":       4500,
    "02-value-transform.md":  8192,
    "03-scenario-test.md":    4096,
    "04-release-review.md":   2048,
    "05-feedback-collect.md": 2048,
    "06-retrospective.md":    6000,
}
_DEFAULT_MAX_TOKENS = 4096


def _load_system_prompt(agent_file: str) -> str:
    """Load agent system prompt (strip YAML frontmatter)."""
    path = AGENTS_DIR / agent_file
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.index("---", 3)
        text = text[end + 3:].strip()
    return text


def run_agent(
    agent_file: str,
    user_message: str,
    extra_context: dict | None = None,
    tools: list[dict] | None = None,
    tool_handlers: dict[str, callable] | None = None,
) -> dict:
    """Run a single Agent.

    Args:
        agent_file: Agent filename (e.g. "01-gatekeeper.md")
        user_message: User input message
        extra_context: Extra context injected into system prompt
        tools: Tool definitions (OpenAI function calling format)
        tool_handlers: tool_name → handler function mapping

    Returns:
        {"text": "...", "tool_calls": [...]}
    """
    tool_handlers = tool_handlers or {}

    # Build system prompt
    system_prompt = _load_system_prompt(agent_file)
    if extra_context:
        context_block = (
            "\n\n<pipeline_context>\n"
            + json.dumps(extra_context, ensure_ascii=False, indent=2)
            + "\n</pipeline_context>"
        )
        system_prompt += context_block

    # Determine tools
    allowed = _AGENT_TOOL_WHITELIST.get(agent_file)
    agent_tool_defs = _build_openai_tools(tools or [], allowed) if allowed else []
    max_tokens = _AGENT_MAX_TOKENS.get(agent_file, _DEFAULT_MAX_TOKENS)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    tool_log: list[dict] = []
    accumulated_text = ""

    print(f"\n{'='*60}")
    print(f"  Agent: {agent_file}  (max_tokens={max_tokens}, tools={len(agent_tool_defs)})")
    print(f"{'='*60}")

    max_turns = 5  # prevent infinite loop
    for turn in range(max_turns):
        kwargs = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if agent_tool_defs:
            kwargs["tools"] = agent_tool_defs

        try:
            response = _client.chat.completions.create(**kwargs)
        except Exception as e:
            print(f"  [ERROR] {e}")
            return {"text": f"Error: {e}", "tool_calls": tool_log}

        choice = response.choices[0]
        msg = choice.message

        # Collect text
        if msg.content:
            accumulated_text += msg.content

        # Check for tool calls
        if msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                func_name = tc.function.name
                try:
                    func_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                print(f"  → tool_use: {func_name}({json.dumps(func_args, ensure_ascii=False)[:120]})")

                handler = tool_handlers.get(func_name)
                if handler:
                    try:
                        result = handler(func_args)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"unknown tool: {func_name}"}

                tool_log.append({
                    "tool": func_name,
                    "input": func_args,
                    "result": result,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
        else:
            # No tool calls, end loop
            print(f"  [finish_reason={choice.finish_reason}] text_len={len(accumulated_text)}")
            break
    else:
        print(f"  [max_turns={max_turns}] ⚠️ Max turns reached")

    return {"text": accumulated_text, "tool_calls": tool_log}


def _build_openai_tools(
    all_tools: list[dict],
    allowed: set[str] | None,
) -> list[dict]:
    """Build OpenAI function calling tool definitions from dict list."""
    defs = []
    for tool in all_tools:
        name = tool.get("name", "")
        if allowed is None or name in allowed:
            defs.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {}),
                },
            })
    return defs


# ─── JSON Extraction Utilities ──────────────────────────

def extract_json_from_response(text: str) -> dict | None:
    """Extract Schema JSON from Agent response text."""
    candidates = _extract_all_json_objects(text)
    if not candidates:
        return None
    for obj in candidates:
        if "schema_version" in obj:
            return obj
    return candidates[0]


def extract_gatekeeping_result(tool_calls: list) -> dict | None:
    """Extract atomic fields from submit_gatekeeping_result."""
    for call in tool_calls:
        if call.get("tool") == "submit_gatekeeping_result":
            inp = call.get("input", {})
            if isinstance(inp, dict) and "verdict" in inp:
                return inp
    return None


def extract_value_transform_result(text: str) -> dict | None:
    """Extract Schema 2 JSON from Agent 02 output."""
    if not text:
        return None
    # Prefer ```json code block extraction
    blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', text)
    for block in blocks:
        raw = block.strip()
        try:
            parsed = json.loads(_repair_json_text(raw))
            if isinstance(parsed, dict) and ("structured_criteria" in parsed or "test_cases" in parsed):
                print("  [extract_value_transform] ✅ extracted from ```json block")
                return {
                    **parsed,
                    "structured_criteria": _coerce_list(parsed.get("structured_criteria", [])),
                    "test_cases": _coerce_list(parsed.get("test_cases", [])),
                }
        except (json.JSONDecodeError, Exception) as e:
            print(f"  [extract_value_transform] ⚠️ JSON parse failed: {e}")
    # Fallback: generic JSON extraction
    parsed = extract_json_from_response(text)
    if isinstance(parsed, dict) and ("structured_criteria" in parsed or "test_cases" in parsed):
        return {
            **parsed,
            "structured_criteria": _coerce_list(parsed.get("structured_criteria", [])),
            "test_cases": _coerce_list(parsed.get("test_cases", [])),
        }
    return None


# ─── Internal Helpers ───────────────────────────────────

def _extract_all_json_objects(text: str) -> list[dict]:
    """Extract all top-level JSON objects from text."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.replace("```", "")

    results = []
    i = 0
    while i < len(cleaned):
        if cleaned[i] != "{":
            i += 1
            continue
        depth = 0
        for j in range(i, len(cleaned)):
            if cleaned[j] == "{":
                depth += 1
            elif cleaned[j] == "}":
                depth -= 1
                if depth == 0:
                    candidate = cleaned[i:j + 1]
                    try:
                        repaired = _repair_json_text(candidate)
                        obj = json.loads(repaired)
                        if isinstance(obj, dict):
                            results.append(obj)
                    except json.JSONDecodeError:
                        pass
                    i = j + 1
                    break
        else:
            break
    return results


def _repair_json_text(text: str) -> str:
    """Fix common AI output JSON issues: unescaped quotes, newlines, etc."""
    chars = list(text)
    i = 0
    n = len(chars)
    result = []
    in_string = False
    escape_next = False

    def _next_non_space(start: int) -> str:
        k = start
        while k < n and chars[k] in (" ", "\t", "\n", "\r"):
            k += 1
        return chars[k] if k < n else ""

    while i < n:
        ch = chars[i]
        if escape_next:
            result.append(ch)
            escape_next = False
            i += 1
            continue
        if ch == "\\":
            result.append(ch)
            escape_next = True
            i += 1
            continue
        if ch == '"':
            if not in_string:
                in_string = True
                result.append(ch)
                i += 1
                continue
            else:
                nxt = _next_non_space(i + 1)
                if nxt in (",", ":", "]", "}", ""):
                    in_string = False
                    result.append(ch)
                else:
                    result.append("\\\"")
                i += 1
                continue
        if in_string:
            if ch == "\n":
                result.append("\\n")
            elif ch == "\r":
                result.append("\\r")
            elif ch == "\t":
                result.append("\\t")
            elif ord(ch) < 32:
                result.append(f"\\u{ord(ch):04x}")
            else:
                result.append(ch)
            i += 1
            continue
        result.append(ch)
        i += 1
    return "".join(result)


def _coerce_list(val: Any) -> list:
    """Coerce value to list."""
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return []
