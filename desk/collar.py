"""Team 2 — The Collar (STRATEGY.md "Team 2"): hedged equity, the JPMorgan structure on SPY.

Own the index; buy a put ~5% below, sell a put ~20% below, sell a call above whose premium
pays for the two puts. All three expire on the last trading day of the quarter; nothing is
adjusted in between. Pure rules here; the session that meets the broker is at the bottom.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from desk.broker import PutQuote

UNDERLYING = "SPY"
EQUITY_FRACTION = 0.95        # share lots bought with at most this much of the account
LONG_PUT_BELOW = 0.05         # long put ~5% under spot
SHORT_PUT_BELOW = 0.20        # short put ~20% under spot


@dataclass(frozen=True)
class Collar:
    long_put: PutQuote
    short_put: PutQuote
    short_call: PutQuote      # same quote shape; a call

    @property
    def net(self) -> float:
        """Net price per share at the mids: positive = we pay, negative = we receive."""
        return round(self.long_put.mid - self.short_put.mid - self.short_call.mid, 2)


def quarter_end(d: date) -> date:
    """Last calendar day of d's quarter."""
    m = ((d.month - 1) // 3 + 1) * 3
    first_next = date(d.year + (m == 12), 1 if m == 12 else m + 1, 1)
    return first_next - timedelta(days=1)


def quarter_expiry(listed: list[date], today: date) -> date | None:
    """The quarter-end expiry: the LAST listed expiry on or before the quarter's last day
    (a holiday or weekend moves it earlier). On the expiry day itself, and after it, the
    answer is the NEXT quarter's — the day's own contracts are the ones being closed."""
    def pick(qe: date) -> date | None:
        inside = [e for e in listed if qe - timedelta(days=6) <= e <= qe]
        return max(inside) if inside else None
    e = pick(quarter_end(today))
    if e is None or e <= today:
        e = pick(quarter_end(quarter_end(today) + timedelta(days=1)))
    return e


def lots(equity: float, spot: float) -> int:
    """Whole 100-share lots that EQUITY_FRACTION of the account buys."""
    return int((equity * EQUITY_FRACTION) // (100 * spot)) if spot > 0 else 0


def _nearest(quotes: list[PutQuote], strike: float) -> PutQuote | None:
    priced = [q for q in quotes if q.bid > 0 and q.ask > 0]
    return min(priced, key=lambda q: (abs(q.strike - strike), q.strike)) if priced else None


def pick(puts: list[PutQuote], calls: list[PutQuote], spot: float) -> tuple[Collar | None, str]:
    """(collar, why-not). Long put nearest 5% below spot, short put nearest 20% below, and
    the call above spot whose mid is nearest the put spread's cost — a tie to the higher strike."""
    lp = _nearest(puts, spot * (1 - LONG_PUT_BELOW))
    sp = _nearest(puts, spot * (1 - SHORT_PUT_BELOW))
    if lp is None or sp is None:
        return None, "the put chain has no priced strikes near 5% and 20% below the market"
    if sp.strike >= lp.strike:
        return None, "the 5% and 20% puts resolved to the same strike — the chain is too thin to build a spread"
    cost = lp.mid - sp.mid
    above = [c for c in calls if c.strike > spot and c.bid > 0 and c.ask > 0]
    if not above:
        return None, "no priced call above the market"
    call = min(above, key=lambda c: (abs(c.mid - cost), -c.strike))
    return Collar(lp, sp, call), ""


def structure_problem(share_lots: int, c: Collar) -> str | None:
    """The Collar's own Risk Officer: covered call, defined-risk put spread, one expiry."""
    if share_lots < 1:
        return "no share lot is held, so a call would be naked"
    if not (c.long_put.expiry == c.short_put.expiry == c.short_call.expiry):
        return "the three legs do not share one expiry"
    if c.short_put.strike >= c.long_put.strike:
        return "the short put is not below the long put — the downside would not be defined"
    if c.short_call.strike <= c.long_put.strike:
        return "the call is not above the long put"
    return None


def because(c: Collar, share_lots: int, spot: float) -> str:
    cap = c.short_call.strike / spot - 1
    floor = 1 - c.long_put.strike / spot
    end = 1 - c.short_put.strike / spot
    net = c.net
    cost = "for nothing net" if abs(net) < 0.005 else (f"for a net cost of ${net:.2f} a share" if net > 0
                                                       else f"for a net credit of ${-net:.2f} a share")
    return (f"Offered the {c.long_put.expiry:%d %b} collar on {share_lots * 100} SPY at {spot:.2f}: "
            f"buy the {c.long_put.strike:g} put, sell the {c.short_put.strike:g} put, sell the "
            f"{c.short_call.strike:g} call, {cost}. Until then the shares keep gains up to "
            f"{cap:+.1%}, take the first {floor:.1%} of a fall, and are cushioned from there to "
            f"{end:.1%} down. One order, a day limit, counts once it fills.")
