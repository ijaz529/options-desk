"""The weekend sleeve — spot crypto while the options market sleeps.

Equity options are shut from Friday close to Monday open; BTC and ETH are not.
A small, mechanical momentum rule keeps the desk earning (or deliberately flat)
through the weekend: ride what moved, cap the size, exits at ±4%. No Claude
here — weekends are thin, and a rule that can be printed is a rule that can be
trusted at 3am on a Sunday.

Entry (Saturday session):
  momentum = 24h change of BTC/USD and ETH/USD from Alpaca crypto snapshots.
  A pair qualifies if it moved ≥ +1.5% (long-only: spot can't short).
  One qualifier: buy $2,500 of it. Both: $1,250 each. None: stay in cash, and
  say so in the log.

Exit (hourly weekend sweep + Friday de-risk): ±4% on entry, or contest end.
"""
from __future__ import annotations

import os

PAIRS = ("BTC/USD", "ETH/USD")
ENTRY_THRESHOLD = 0.015      # 24h move to qualify
SLEEVE_TOTAL = 2_500.0       # per weekend, well inside the $5k crypto cap
STOP_FRAC = 0.04
TAKE_FRAC = 0.04


def momentum_24h() -> dict[str, float]:
    """{pair: 24h fractional change} from Alpaca crypto snapshots (free tier)."""
    from alpaca.data.historical.crypto import CryptoHistoricalDataClient
    from alpaca.data.requests import CryptoSnapshotRequest
    c = CryptoHistoricalDataClient(os.environ.get("ALPACA_API_KEY_ID", ""),
                                   os.environ.get("ALPACA_API_SECRET_KEY", ""))
    snaps = c.get_crypto_snapshot(CryptoSnapshotRequest(symbol_or_symbols=list(PAIRS)))
    out: dict[str, float] = {}
    for pair, s in snaps.items():
        day, prev = getattr(s, "daily_bar", None), getattr(s, "previous_daily_bar", None)
        if day and prev and prev.close:
            out[pair] = day.close / prev.close - 1
    return out


def entries(momentum: dict[str, float]) -> list[tuple[str, float, str]]:
    """[(pair, notional, because)] — the Saturday decision, pure and testable."""
    qualifiers = [(p, m) for p, m in momentum.items() if m >= ENTRY_THRESHOLD]
    if not qualifiers:
        moves = ", ".join(f"{p} {m:+.1%}" for p, m in sorted(momentum.items())) or "no data"
        return [("", 0.0, f"No entry this weekend: nothing moved ≥ {ENTRY_THRESHOLD:.1%} "
                          f"({moves}). Cash is a position.")]
    each = SLEEVE_TOTAL / len(qualifiers)
    return [(p, each,
             f"{p} is {m:+.1%} over 24h — riding the mover with ${each:,.0f} of spot. "
             f"Exits at ±{STOP_FRAC:.0%}; the options market is shut and this sleeve "
             "is the only thing awake.")
            for p, m in sorted(qualifiers, key=lambda x: -x[1])]


def exit_action(entry_cost: float, market_value: float) -> tuple[str, str] | None:
    """(kind, because) when the ±4% rule fires on a crypto position."""
    if entry_cost <= 0:
        return None
    r = market_value / entry_cost - 1
    if r <= -STOP_FRAC:
        return ("stop", f"Down {r:.1%} on entry — the weekend rule says out, no debate.")
    if r >= TAKE_FRAC:
        return ("take_profit", f"Up {r:.1%} on entry — banked; weekend moves are borrowed, not owned.")
    return None
