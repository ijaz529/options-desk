"""The Steward — options income, by rule.

Sells the week's ordinariness: cash-secured puts at the ~20-delta strike on
liquid names, premium floor enforced, exits mechanical. `pick` is pure logic
over quotes the broker module fetched, so the entry rule is testable without
a market. The Risk Officer still reviews everything this module proposes.
"""
from __future__ import annotations

from desk.broker import PutQuote

TARGET_DELTA = -0.20          # puts carry negative delta; we want ~20-delta
DELTA_BAND = (-0.28, -0.12)   # acceptable window around the target
MIN_PREMIUM_YIELD = 0.0015    # mid ≥ 0.15% of strike, or the obligation isn't paid for
MAX_SPREAD_FRAC = 0.20        # bid/ask wider than 20% of mid = market too thin to trust
TAKE_PROFIT_FRAC = 0.65       # buy back at 65% of max premium
STOP_MULT = 2.0               # buy back if the option doubles against entry


def pick(quotes: list[PutQuote]) -> PutQuote | None:
    """The one put this underlying's chain earns, or None with no regrets.

    Filter to the delta band, require the premium floor and a market tight
    enough to believe, then take the strike nearest the 20-delta target.
    """
    ok = [q for q in quotes
          if q.delta is not None and DELTA_BAND[0] <= q.delta <= DELTA_BAND[1]
          and q.premium_yield >= MIN_PREMIUM_YIELD
          and q.mid > 0 and (q.ask - q.bid) <= MAX_SPREAD_FRAC * q.mid]
    if not ok:
        return None
    return min(ok, key=lambda q: abs(q.delta - TARGET_DELTA))


def entry_because(q: PutQuote) -> str:
    return (f"Sold the {q.underlying} {q.expiry:%d %b} {q.strike:g} put at ~{q.mid:.2f} "
            f"({q.premium_yield:.2%} of the ${q.strike * 100:,.0f} obligation). "
            f"Delta {q.delta:+.2f} puts the strike {(1 - q.strike / q.spot):.1%} below spot — "
            "a price we would own this name at. The trade is a bet the week stays ordinary.")


def exit_action(entry_credit: float, current_mid: float) -> tuple[str, str] | None:
    """('take_profit'|'stop', because) when an exit rule fires, else None."""
    if entry_credit <= 0:
        return None
    if current_mid <= entry_credit * (1 - TAKE_PROFIT_FRAC):
        return ("take_profit",
                f"Buying back at {current_mid:.2f}: {1 - current_mid / entry_credit:.0%} of the "
                f"{entry_credit:.2f} credit is banked, and the last cents are not worth the tail.")
    if current_mid >= entry_credit * STOP_MULT:
        return ("stop",
                f"Buying back at {current_mid:.2f}: the option has doubled against the "
                f"{entry_credit:.2f} credit. The week is not ordinary — the rule says leave.")
    return None
