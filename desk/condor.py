"""Team 3 — The Condor (STRATEGY.md "Team 3"): monthly iron condors on SPY, QQQ and IWM.

Sell the 20-delta put and call, buy wings 4% of spot further out, one contract each, the standard
monthly expiry 25–45 days out. Take profit at half the credit, stop at twice it, out at
seven days to expiry. Pure rules here; the session that meets the broker is in teams_run.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from desk.broker import PutQuote

UNIVERSE = ["SPY", "QQQ", "IWM"]
SHORT_DELTA = 0.20
WING_FRACTION = 0.04          # wings sit this share of spot beyond the short strikes (not the
                              # index's 5-delta wings: those were ~$7k of risk a condor on SPY/QQQ)
DTE_MIN, DTE_MAX = 25, 45
MIN_CREDIT_OF_WING = 0.10     # net credit must be at least this share of the wider wing
TAKE_PROFIT_FRAC = 0.50       # buy back at half the credit or less
STOP_MULT = 2.0               # buy back at twice the credit or more
EXIT_DTE = 7
MAX_LOSS_ONE = 0.05           # one condor's worst case, of equity
MAX_LOSS_ALL = 0.15           # all open condors' worst cases together
KILL_SWITCH_FRACTION = 0.92   # of the team's baseline: below it, no new condor
RV_DAYS = 20                  # volatility gate: realised vol over this many daily returns


@dataclass(frozen=True)
class Condor:
    long_put: PutQuote
    short_put: PutQuote
    short_call: PutQuote
    long_call: PutQuote

    @property
    def credit(self) -> float:
        """Net credit per share at the mids."""
        return round(self.short_put.mid + self.short_call.mid - self.long_put.mid - self.long_call.mid, 2)

    @property
    def wing(self) -> float:
        """The wider of the two wings, in dollars of strike."""
        return max(self.short_put.strike - self.long_put.strike,
                   self.long_call.strike - self.short_call.strike)

    @property
    def max_loss(self) -> float:
        """Worst case for one contract set, in dollars."""
        return round((self.wing - self.credit) * 100, 2)

    @property
    def legs(self) -> list[PutQuote]:
        return [self.long_put, self.short_put, self.short_call, self.long_call]


def third_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(4 - d.weekday()) % 7)
    return d + timedelta(days=14)


def monthly_expiry(listed: list[date], today: date) -> date | None:
    """The standard monthly expiry DTE_MIN–DTE_MAX days out: the listed date on the third
    Friday, or the day before when that Friday is a market holiday."""
    for k in range(0, 4):
        y, m = today.year + (today.month - 1 + k) // 12, (today.month - 1 + k) % 12 + 1
        tf = third_friday(y, m)
        for e in (tf, tf - timedelta(days=1)):
            if e in listed and DTE_MIN <= (e - today).days <= DTE_MAX:
                return e
    return None


def _by_delta(quotes: list[PutQuote], target: float) -> PutQuote | None:
    ok = [q for q in quotes if q.delta is not None and q.bid > 0 and q.ask > 0]
    return min(ok, key=lambda q: (abs(abs(q.delta) - target), q.strike)) if ok else None


def _by_strike(quotes: list[PutQuote], strike: float) -> PutQuote | None:
    ok = [q for q in quotes if q.bid > 0 and q.ask > 0]
    return min(ok, key=lambda q: (abs(q.strike - strike), q.strike)) if ok else None


def pick(puts: list[PutQuote], calls: list[PutQuote]) -> tuple[Condor | None, str]:
    """(condor, why-not)."""
    sp, sc = _by_delta(puts, SHORT_DELTA), _by_delta(calls, SHORT_DELTA)
    if not (sp and sc):
        return None, "a leg has no quote or no delta"
    width = WING_FRACTION * sp.spot
    lp, lc = _by_strike(puts, sp.strike - width), _by_strike(calls, sc.strike + width)
    if not (lp and lc):
        return None, "a leg has no quote or no delta"
    c = Condor(lp, sp, sc, lc)
    why = structure_problem(c)
    if why:
        return None, why
    if c.credit < MIN_CREDIT_OF_WING * c.wing:
        return None, (f"the credit ({c.credit:.2f}) is under {MIN_CREDIT_OF_WING:.0%} of the "
                      f"{c.wing:g}-wide wing — not paid enough for the risk")
    return c, ""


def structure_problem(c: Condor) -> str | None:
    if len({q.expiry for q in c.legs}) != 1:
        return "the four legs do not share one expiry"
    if not (c.long_put.strike < c.short_put.strike < c.short_call.strike < c.long_call.strike):
        return "the wings are not outside the short strikes — the risk would not be defined"
    return None


def risk_problem(c: Condor, equity: float, baseline: float, open_max_loss: float) -> str | None:
    """The Condor's own Risk Officer. `open_max_loss`: worst cases of condors already open."""
    if equity < KILL_SWITCH_FRACTION * baseline:
        return (f"equity ${equity:,.0f} is below ${KILL_SWITCH_FRACTION * baseline:,.0f} "
                f"({KILL_SWITCH_FRACTION:.0%} of the ${baseline:,.0f} baseline) — no new condor")
    if c.max_loss > MAX_LOSS_ONE * equity:
        return (f"its worst case ${c.max_loss:,.0f} is more than {MAX_LOSS_ONE:.0%} of the account")
    if open_max_loss + c.max_loss > MAX_LOSS_ALL * equity:
        return (f"with ${open_max_loss:,.0f} already at risk, ${c.max_loss:,.0f} more would pass "
                f"{MAX_LOSS_ALL:.0%} of the account")
    return None


def exit_action(credit: float, cost_to_close: float, days_to_expiry: int) -> tuple[str, str] | None:
    """(action, because) or None. Prices per share; cost_to_close is what buying the four
    legs back costs now."""
    if days_to_expiry <= EXIT_DTE:
        return ("time_exit", f"{days_to_expiry} days to expiry — inside the last week, where a "
                             f"condor's risk concentrates. Buying it back at {cost_to_close:.2f} "
                             f"against the {credit:.2f} collected.")
    if cost_to_close <= credit * TAKE_PROFIT_FRAC:
        return ("take_profit", f"Buying back at {cost_to_close:.2f}: {1 - cost_to_close / credit:.0%} "
                               f"of the {credit:.2f} credit is banked.")
    if cost_to_close >= credit * STOP_MULT:
        return ("stop", f"Buying back at {cost_to_close:.2f}: twice the {credit:.2f} collected. "
                        "The market has left the range — the rule says leave.")
    return None


def hold_because(held: list[tuple[str, date, float, float, int]]) -> str:
    """The session's one hold row: (underlying, expiry, credit, cost_to_close, days left) for
    each open condor that no exit rule touched."""
    parts = []
    for u, expiry, credit, cost, days in held:
        state = (f"{1 - cost / credit:.0%} of the {credit:.2f} credit banked" if 0 < credit and cost <= credit
                 else f"buying it back costs {cost:.2f} against the {credit:.2f} collected")
        parts.append(f"{u} {expiry:%d %b} ({state}, {days} days left)")
    return (f"Holding {', '.join(parts)}. None is at an exit: each closes at half its credit, "
            f"at twice it, or with {EXIT_DTE} days left.")


def realised_vol(closes: list[float]) -> float | None:
    """Annualised volatility of the last RV_DAYS daily log returns (needs RV_DAYS + 1 closes)."""
    if len(closes) < RV_DAYS + 1:
        return None
    c = closes[-(RV_DAYS + 1):]
    r = [math.log(b / a) for a, b in zip(c, c[1:])]
    mean = sum(r) / len(r)
    return math.sqrt(sum((x - mean) ** 2 for x in r) / (len(r) - 1) * 252)


def atm_iv(puts: list[PutQuote], calls: list[PutQuote], spot: float) -> float | None:
    """Mean implied vol of the put and the call struck nearest spot; None if either is missing."""
    ivs = []
    for side in (puts, calls):
        quoted = [q for q in side if q.iv]
        if not quoted:
            return None
        ivs.append(min(quoted, key=lambda q: abs(q.strike - spot)).iv)
    return sum(ivs) / 2


def vol_gate(iv: float | None, rv: float | None) -> str | None:
    """STRATEGY.md "Volatility gate": None when a condor may open, else the plain reason it may not."""
    if iv is None or rv is None:
        return "there is no implied- or realised-volatility reading, and a missing reading never passes the gate"
    if iv <= rv:
        return (f"its options price {iv:.0%} a year of movement, no more than the {rv:.0%} it has actually "
                f"moved over the last {RV_DAYS} days — the premium does not pay for the risk")
    return None


def because(c: Condor, spot: float) -> str:
    u = c.short_put.underlying
    return (f"Offered the {u} {c.short_put.expiry:%d %b} iron condor with {u} at {spot:.2f}: sell the "
            f"{c.short_put.strike:g} put and {c.short_call.strike:g} call, buy the "
            f"{c.long_put.strike:g} put and {c.long_call.strike:g} call, for a credit of "
            f"{c.credit:.2f} (${c.credit * 100:,.0f}). It keeps the credit if {u} finishes between "
            f"{c.short_put.strike:g} and {c.short_call.strike:g}; the most it can lose is "
            f"${c.max_loss:,.0f}. One order, a day limit, counts once it fills.")
