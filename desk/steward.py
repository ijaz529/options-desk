"""The Steward — options income, by rule.

Sells the week's ordinariness: cash-secured puts at the ~20-delta strike on
liquid names, premium floor enforced, exits mechanical. `pick` is pure logic
over quotes the broker module fetched, so the entry rule is testable without
a market. The Risk Officer still reviews everything this module proposes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from desk.broker import PutQuote

TARGET_DELTA = -0.20          # puts carry negative delta; we want ~20-delta
# STRATEGY.md rule 2: "at (or nearest below) the 20-delta strike" — below meaning further
# out of the money, so the band's near edge IS the target. The old near edge of -0.28 let
# the desk sell a KO 88 put at -0.26, 0.7% below spot, for 0.18% of strike; the contract's
# own wording excludes that trade, and it was the one that got assigned (25 Sep 2026).
# -0.21 leaves a hundredth for "at"; -0.12 stays as the far edge where nothing pays.
DELTA_BAND = (-0.21, -0.12)   # at-or-below 20-delta, per the contract (26 Sep 2026)
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
    # an offer, not a sale: a day limit counts once it fills (STRATEGY.md rule 9, 29 Sep 2026)
    return (f"Offered to sell the {q.underlying} {q.expiry:%d %b} {q.strike:g} put at ~{q.mid:.2f}, "
            f"a day limit at the mid that counts once it fills "
            f"({q.premium_yield:.2%} of the ${q.strike * 100:,.0f} obligation). "
            f"Delta {q.delta:+.2f} puts the strike {(1 - q.strike / q.spot):.1%} below spot — "
            "a price we would own this name at. The trade is a bet the week stays ordinary.")


# The put spread (STRATEGY.md "Built 10 Oct 2026"): when no cash-secured put qualifies, sell
# the same 20-delta put and buy the 10-delta below it, for at least a tenth of the width.
WING_DELTA = -0.10
MIN_SPREAD_CREDIT_OF_WIDTH = 0.10


@dataclass(frozen=True)
class PutSpread:
    short: PutQuote
    long: PutQuote

    @property
    def width(self) -> float:
        return round(self.short.strike - self.long.strike, 2)

    @property
    def credit(self) -> float:
        """Net credit per share at the mids."""
        return round(self.short.mid - self.long.mid, 2)

    @property
    def max_loss(self) -> float:
        """Dollars, one spread: the width less the credit."""
        return round((self.width - self.credit) * 100, 2)


def pick_spread(quotes: list[PutQuote]) -> PutSpread | None:
    """The spread a name earns when its cash-secured put does not, or None."""
    shorts = [q for q in quotes
              if q.delta is not None and DELTA_BAND[0] <= q.delta <= DELTA_BAND[1]
              and q.mid > 0 and (q.ask - q.bid) <= MAX_SPREAD_FRAC * q.mid]
    if not shorts:
        return None
    short = min(shorts, key=lambda q: abs(q.delta - TARGET_DELTA))
    wings = [q for q in quotes if q.strike < short.strike and q.delta is not None and q.ask > 0]
    if not wings:
        return None
    s = PutSpread(short, min(wings, key=lambda q: abs(q.delta - WING_DELTA)))
    if s.credit <= 0 or s.credit < MIN_SPREAD_CREDIT_OF_WIDTH * s.width:
        return None
    return s


def spread_because(s: PutSpread) -> str:
    return (f"No cash-secured {s.short.underlying} put paid its floor, so offered the {s.short.expiry:%d %b} "
            f"{s.short.strike:g}/{s.long.strike:g} put spread for a credit of {s.credit:.2f} "
            f"(${s.credit * 100:,.0f}, {s.credit / s.width:.0%} of the {s.width:g} width): sell the "
            f"{s.short.strike:g} put (delta {s.short.delta:+.2f}), buy the {s.long.strike:g} "
            f"(delta {s.long.delta:+.2f}). The most it can lose is ${s.max_loss:,.0f}. One order, a day "
            "limit, counts once it fills.")


# The wheel's second half (STRATEGY.md "Built 10 Oct 2026"): a call on shares the puts were
# assigned, at or nearest ABOVE the 20-delta strike — the put band mirrored.
CALL_DELTA_BAND = (0.12, 0.21)
TARGET_CALL_DELTA = 0.20


def pick_call(quotes: list[PutQuote], cost_basis: float) -> PutQuote | None:
    """The covered call these shares earn, or None. The put's band, floor and market test,
    plus one rule of its own: never a strike below what the shares cost, so a call-away
    always sells them at or above their price."""
    ok = [q for q in quotes
          if q.delta is not None and CALL_DELTA_BAND[0] <= q.delta <= CALL_DELTA_BAND[1]
          and q.strike >= cost_basis
          and q.premium_yield >= MIN_PREMIUM_YIELD
          and q.mid > 0 and (q.ask - q.bid) <= MAX_SPREAD_FRAC * q.mid]
    if not ok:
        return None
    return min(ok, key=lambda q: abs(q.delta - TARGET_CALL_DELTA))


def call_because(q: PutQuote, cost_basis: float, shares: float) -> str:
    return (f"Offered to sell the {q.underlying} {q.expiry:%d %b} {q.strike:g} call at ~{q.mid:.2f} "
            f"against the {shares:g} shares held — a covered call, a day limit at the mid that counts "
            f"once it fills ({q.premium_yield:.2%} of the strike). Delta {q.delta:+.2f} puts the strike "
            f"{(q.strike / q.spot - 1):.1%} above spot and ${q.strike - cost_basis:.2f} over the "
            f"${cost_basis:.2f} the shares cost: if they are called away, the wheel turns back to puts.")


def call_exit_action(entry_credit: float, current_mid: float) -> tuple[str, str] | None:
    """('take_profit', because) at 65% banked, else None. No stop: the call can only lose
    what the shares gain above the strike."""
    if entry_credit <= 0:
        return None
    if current_mid <= entry_credit * (1 - TAKE_PROFIT_FRAC):
        return ("take_profit",
                f"Buying back the covered call at {current_mid:.2f}: {1 - current_mid / entry_credit:.0%} "
                f"of the {entry_credit:.2f} credit is banked, and the shares can be covered again.")
    return None


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


# No put through an earnings report (STRATEGY.md "Amended 12 Nov 2026", rule 10). The INTC 86
# put sold on 28 Oct 2026 met a report the next evening and cost $1,664 of the Steward's $2,808.
EARNINGS_DUE_DAYS = 80        # a company reports about every 91 days: past this, the next one is due


def earnings_block(dates: list[date], today: date, expiry: date) -> str | None:
    """Why this name gets no new put for this expiry, or None. `dates` are the earnings dates
    the source holds (none for a fund). A report between today and the expiry blocks; so does a
    newest date so old that the next report is due and not yet dated."""
    inside = [d for d in dates if today <= d <= expiry]
    if inside:
        return (f"it reports earnings on {min(inside):%d %b}, on or before the {expiry:%d %b} expiry, and a put "
                "is a bet on an ordinary week (rule 10)")
    if dates and (expiry - max(dates)).days > EARNINGS_DUE_DAYS:
        return (f"its last report was {max(dates):%d %b %Y}, so the next is due and not yet dated; "
                "no put is sold until it is (rule 10)")
    return None


# A stop is not placed on a price a put cannot have (rule 12). On 29 Oct 2026 the PFE 29 put was
# bought back at 4.90 with the shares above 29.50: the broker's mark was believed, and paid.
MARK_TIME_VALUE_CAP = 0.06    # of the strike, for a contract with a week or less to run


def believable_put_mark(strike: float, spot: float, mark: float) -> bool:
    """A put is worth at most its intrinsic value plus time value; the time value of a weekly
    is capped at MARK_TIME_VALUE_CAP of the strike."""
    return mark <= max(strike - spot, 0.0) + MARK_TIME_VALUE_CAP * strike
