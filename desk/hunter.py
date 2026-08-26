"""The Hunter — convexity, with Claude deciding *what* and the desk deciding *how*.

The division of labour is deliberate:
- The desk computes the tape (movers, gaps, ranges) from Alpaca snapshots —
  deterministic inputs, reproducible after the fact.
- Claude reads that tape and proposes at most two trades in a strict,
  machine-checkable shape. A proposal that fails validation is discarded and
  logged; there is no "mostly valid".
- The desk turns an approved thesis into an actual contract by rule
  (~35-delta weekly), sizes it, and the Risk Officer still has the last word.

Claude never touches an order. It writes theses; the machinery trades them.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date

from anthropic import Anthropic

from desk import broker
from desk.broker import PutQuote

CANDIDATES = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "AVGO", "NFLX",
    "JPM", "GS", "XOM", "CVX", "UNH", "LLY", "CAT", "BA", "DIS", "UBER",
    "PLTR", "COIN", "MU", "INTC", "ORCL", "CRM", "QCOM", "SHOP", "SQ", "PYPL",
]
MAX_TRADES_PER_SESSION = 2
MAX_PREMIUM_USD = 2_000.0
THESIS_MAX_CHARS = 280
TARGET_DELTA_ABS = 0.35
DELTA_BAND_ABS = (0.25, 0.45)
MODEL = os.environ.get("HUNTER_MODEL", "claude-sonnet-5")


@dataclass(frozen=True)
class Thesis:
    symbol: str
    direction: str          # "call" | "put"
    thesis: str
    max_premium_usd: float
    invalidation: str


def tape() -> list[dict]:
    """Today's tape for the candidate list, from Alpaca snapshots: last price,
    day change, gap at the open, and where in the day's range we sit."""
    from alpaca.data.enums import DataFeed
    from alpaca.data.historical.stock import StockHistoricalDataClient
    from alpaca.data.requests import StockSnapshotRequest
    c = StockHistoricalDataClient(broker._KEY, broker._SECRET)
    # feed=iex: the default SIP feed needs a paid data plan and 401s at the edge
    snaps = c.get_stock_snapshot(StockSnapshotRequest(symbol_or_symbols=CANDIDATES,
                                                      feed=DataFeed.IEX))
    rows = []
    for sym, s in snaps.items():
        day, prev = getattr(s, "daily_bar", None), getattr(s, "previous_daily_bar", None)
        if not day or not prev or not prev.close:
            continue
        rng = (day.high - day.low) or 1e-9
        rows.append({
            "symbol": sym,
            "last": round(day.close, 2),
            "day_change_pct": round((day.close / prev.close - 1) * 100, 2),
            "gap_pct": round((day.open / prev.close - 1) * 100, 2),
            "range_position": round((day.close - day.low) / rng, 2),  # 1 = closing on highs
            "volume_vs_prev": round(day.volume / prev.volume, 2) if prev.volume else None,
        })
    rows.sort(key=lambda r: abs(r["day_change_pct"]), reverse=True)
    return rows


PROMPT = """You are the Hunter on a small options desk in a one-week paper-trading \
contest. Below is today's tape for your candidate universe (sorted by absolute move). \
Propose 0, 1 or 2 convex trades: buy a weekly call (if you expect continuation/reversal \
up) or a weekly put (down) on a name where TODAY'S tape gives a concrete reason. \
No trade is a fine answer — premium spent on a weak thesis is the only way this sleeve \
dies. Rules: symbols only from the list; thesis ≤ {chars} characters, concrete, \
falsifiable; max_premium_usd ≤ {cap}; state the invalidation (what would prove the \
thesis wrong). Respond ONLY with the tool call.

TAPE:
{tape}
"""


def propose(tape_rows: list[dict]) -> tuple[list[Thesis], list[str]]:
    """Ask Claude for theses; return (valid, rejection_reasons)."""
    client = Anthropic()
    tool = {
        "name": "propose_trades",
        "description": "Propose the session's convex trades (possibly none).",
        "input_schema": {
            "type": "object",
            "properties": {"trades": {"type": "array", "maxItems": MAX_TRADES_PER_SESSION,
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
    msg = client.messages.create(
        model=MODEL, max_tokens=1500,
        tools=[tool], tool_choice={"type": "tool", "name": "propose_trades"},
        messages=[{"role": "user", "content": PROMPT.format(
            chars=THESIS_MAX_CHARS, cap=int(MAX_PREMIUM_USD),
            tape=json.dumps(tape_rows, indent=1))}],
    )
    raw = next((b.input for b in msg.content if b.type == "tool_use"), {"trades": []})
    return validate(raw.get("trades", []))


def validate(raw_trades: list[dict]) -> tuple[list[Thesis], list[str]]:
    """Strict shape-checking — a proposal that bends any rule is discarded whole."""
    valid: list[Thesis] = []
    rejected: list[str] = []
    for t in raw_trades[:MAX_TRADES_PER_SESSION]:
        sym = str(t.get("symbol", "")).upper()
        if sym not in CANDIDATES:
            rejected.append(f"{sym or '?'}: not in the candidate universe."); continue
        if t.get("direction") not in ("call", "put"):
            rejected.append(f"{sym}: direction must be call or put."); continue
        thesis = str(t.get("thesis", "")).strip()
        if not thesis or len(thesis) > THESIS_MAX_CHARS:
            rejected.append(f"{sym}: thesis empty or over {THESIS_MAX_CHARS} chars."); continue
        try:
            prem = float(t.get("max_premium_usd", 0))
        except (TypeError, ValueError):
            rejected.append(f"{sym}: max_premium_usd not a number."); continue
        if not 0 < prem <= MAX_PREMIUM_USD:
            rejected.append(f"{sym}: premium ${prem:,.0f} outside (0, {MAX_PREMIUM_USD:,.0f}]."); continue
        inval = str(t.get("invalidation", "")).strip()
        if not inval:
            rejected.append(f"{sym}: no invalidation stated — an unfalsifiable thesis is a hope."); continue
        valid.append(Thesis(sym, t["direction"], thesis, prem, inval))
    return valid, rejected


def contract_for(t: Thesis, expiry: date) -> tuple[PutQuote, int] | None:
    """Deterministic 'how': the ~35-delta weekly in the thesis direction, sized
    so qty × mid × 100 fits inside the thesis's own premium cap."""
    lo, hi = (1.0, 1.12) if t.direction == "call" else (0.88, 1.0)
    chain = broker.option_chain(t.symbol, expiry, t.direction, lo, hi)
    ok = [q for q in chain
          if q.delta is not None and DELTA_BAND_ABS[0] <= abs(q.delta) <= DELTA_BAND_ABS[1]
          and q.mid > 0 and (q.ask - q.bid) <= 0.25 * q.mid]
    if not ok:
        return None
    pick = min(ok, key=lambda q: abs(abs(q.delta) - TARGET_DELTA_ABS))
    qty = int(t.max_premium_usd // (pick.mid * 100))
    return (pick, qty) if qty >= 1 else None


# ── exits ─────────────────────────────────────────────────────────────────────
STOP_FRAC = 0.50        # premium halves → out
TAKE_FRAC = 1.00        # premium doubles → bank half (or all, if only 1 lot)


def exit_action(entry: float, current: float, qty: int) -> tuple[str, int, str] | None:
    """(kind, qty_to_close, because) when a rule fires."""
    if entry <= 0:
        return None
    if current <= entry * (1 - STOP_FRAC):
        return ("stop", qty,
                f"Premium {current:.2f} vs {entry:.2f} entry: the thesis is half gone — all out. "
                "Losses are capped by construction; this is the cap doing its job.")
    if current >= entry * (1 + TAKE_FRAC):
        half = qty // 2
        if half == 0:
            return ("take_profit", qty,
                    f"Premium doubled ({entry:.2f} → {current:.2f}) on a single lot — banked whole.")
        return ("take_half", half,
                f"Premium doubled ({entry:.2f} → {current:.2f}): banking {half} of {qty}, "
                "the rest rides for free.")
    return None
