"""Claude on Alpaca's official MCP server — the Hunter's research desk.

The bridge spawns `alpaca-mcp-server` (stdio) and lets Claude call its tools
directly while forming theses: live positions, account state, quotes, chains —
whatever it wants to look at, it looks at itself. Two hard rules:

1. READ-ONLY: only `get_*` tools are exposed. The trading tools (close_*,
   cancel_*, exercise_*) exist on that server and Claude never sees them —
   proposing is Claude's job, placing is the machinery's, same as everywhere
   else on this desk.
2. The conversation must end in a `propose_trades` call (our tool, same strict
   schema as ever) — research without a conclusion is a spent token budget.
"""
from __future__ import annotations

import asyncio
import json
import os

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from desk import hunter

MAX_RESEARCH_CALLS = 8   # tool round-trips before Claude must conclude

PROPOSE_TOOL = {
    "name": "propose_trades",
    "description": "Conclude the session: propose the convex trades (possibly none).",
    "input_schema": {
        "type": "object",
        "properties": {"trades": {"type": "array", "maxItems": hunter.MAX_TRADES_PER_SESSION,
            "items": {"type": "object", "properties": {
                "symbol": {"type": "string"},
                "direction": {"type": "string", "enum": ["call", "put"]},
                "thesis": {"type": "string"},
                "max_premium_usd": {"type": "number"},
                "invalidation": {"type": "string"},
            }, "required": ["symbol", "direction", "thesis", "max_premium_usd", "invalidation"]}}},
        "required": ["trades"],
    },
}

PROMPT = """You are the Hunter on a small options desk in a one-week paper-trading \
contest, working through Alpaca's MCP server. The tape for your candidate universe is \
below. You may use the read-only Alpaca tools (at most {calls} calls) to check anything \
that sharpens or kills a thesis — current positions, quotes, recent bars. Then you MUST \
conclude with propose_trades: 0, 1 or 2 trades, symbols only from the list, thesis ≤ \
{chars} chars and falsifiable, max_premium_usd ≤ {cap}, invalidation stated. No trade \
is a fine answer — premium spent on a weak thesis is the only way this sleeve dies.

CANDIDATES: {candidates}

TAPE:
{tape}
"""


def _mcp_params() -> StdioServerParameters:
    return StdioServerParameters(
        command="uvx", args=["alpaca-mcp-server"],
        env={**os.environ,
             "ALPACA_API_KEY": os.environ.get("ALPACA_API_KEY_ID", os.environ.get("ALPACA_API_KEY", "")),
             "ALPACA_SECRET_KEY": os.environ.get("ALPACA_API_SECRET_KEY", os.environ.get("ALPACA_SECRET_KEY", "")),
             "ALPACA_PAPER_TRADE": "True"})


async def _research(tape_rows: list[dict]) -> tuple[list[dict], list[str]]:
    """(raw trades from Claude's conclusion, research trail for the log)."""
    trail: list[str] = []
    async with stdio_client(_mcp_params()) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            listed = await session.list_tools()
            # read-only by construction: get_* and nothing else
            readonly = [t for t in listed.tools if t.name.startswith("get_")]
            tools = [{"name": t.name, "description": (t.description or "")[:500],
                      "input_schema": t.input_schema} for t in readonly] + [PROPOSE_TOOL]

            client = Anthropic()
            messages = [{"role": "user", "content": PROMPT.format(
                calls=MAX_RESEARCH_CALLS, chars=hunter.THESIS_MAX_CHARS,
                cap=int(hunter.MAX_PREMIUM_USD), candidates=", ".join(hunter.CANDIDATES),
                tape=json.dumps(tape_rows, indent=1))}]
            for round_no in range(MAX_RESEARCH_CALLS + 1):
                force = round_no == MAX_RESEARCH_CALLS
                msg = client.messages.create(
                    model=hunter.MODEL, max_tokens=2000, tools=tools,
                    tool_choice={"type": "tool", "name": "propose_trades"} if force else {"type": "auto"},
                    messages=messages)
                uses = [b for b in msg.content if b.type == "tool_use"]
                conclude = next((u for u in uses if u.name == "propose_trades"), None)
                if conclude:
                    return list(conclude.input.get("trades", [])), trail
                if not uses:
                    messages.append({"role": "assistant", "content": msg.content})
                    messages.append({"role": "user", "content": "Conclude with propose_trades now."})
                    continue
                messages.append({"role": "assistant", "content": msg.content})
                results = []
                for u in uses:
                    trail.append(f"{u.name}({json.dumps(u.input)[:120]})")
                    try:
                        res = await session.call_tool(u.name, u.input)
                        text = "".join(c.text for c in res.content if getattr(c, "type", "") == "text")[:4000]
                    except Exception as e:
                        text = f"tool error: {e}"
                    results.append({"type": "tool_result", "tool_use_id": u.id, "content": text})
                messages.append({"role": "user", "content": results})
    return [], trail


def propose_via_mcp(tape_rows: list[dict]) -> tuple[list[hunter.Thesis], list[str], list[str]]:
    """(valid theses, rejections, research trail) — the MCP-driven session."""
    raw, trail = asyncio.run(_research(tape_rows))
    valid, rejected = hunter.validate(raw)
    return valid, rejected, trail
