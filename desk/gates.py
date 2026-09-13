"""The Risk Officer — hard, deterministic gates. Not an LLM, on purpose.

Every proposed order passes through `review` before it may reach the broker.
The return value is a verdict with a plain-English reason either way; the
desk logs both approvals and vetoes. Gates are numbered as in docs/STRATEGY.md.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Proposal:
    agent: str                  # "steward" | "hunter"
    symbol: str                 # underlying (or crypto pair for the weekend sleeve)
    kind: str                   # "csp" | "spread" | "long_option" | "crypto_spot" | "close"
    notional: float             # cash at risk: strike*100 for a CSP, premium for longs
    short_uncovered: bool = False


@dataclass(frozen=True)
class AccountState:
    equity: float
    day_start_equity: float
    sleeve_used: dict[str, float]         # agent -> notional already deployed
    underlying_notional: dict[str, float] # symbol -> account-wide notional
    minutes_to_expiry: float               # to the expiry a new position would trade into


SLEEVE_CAP = {"steward": 70_000.0, "hunter": 20_000.0}
DAILY_DRAWDOWN_GATE = 0.025

# The kill switch is a FRACTION of a stated baseline, not a figure (STRATEGY.md
# "Post-contest operation", 13 Sep 2026). As a fixed $96,000 it was 4% below the
# contest's $100,000 start; when the contest ended at $93,630 it was tripped
# permanently, shutting the Hunter and the weekend sleeve for good. Re-basing is
# an explicit, DATED decision because it forgives prior losses — never change
# BASELINE_EQUITY without saying so here and in STRATEGY.md.
BASELINE_EQUITY = 93_630.0        # equity at 13 Sep 2026, start of the open-ended run
KILL_SWITCH_FRACTION = 0.96
KILL_SWITCH_EQUITY = BASELINE_EQUITY * KILL_SWITCH_FRACTION
CONCENTRATION_CAP = 0.20
FINAL_QUIET_MINUTES = 180.0


@dataclass(frozen=True)
class Verdict:
    approved: bool
    gate: str | None
    because: str


def review(p: Proposal, a: AccountState) -> Verdict:
    """Closing risk is always allowed; opening risk must clear every gate."""
    if p.kind == "close":
        return Verdict(True, None, f"{p.agent} may always reduce risk — closing {p.symbol}.")

    if p.short_uncovered:
        return Verdict(False, "no-naked-shorts",
                       f"Vetoed: the {p.symbol} short option is not fully covered. "
                       "Every short put is cash-secured, every spread defined-risk — no exceptions.")

    if a.equity < KILL_SWITCH_EQUITY and not (p.agent == "steward" and p.kind == "csp"):
        # income-only means exactly that: the Hunter and the weekend sleeve are
        # shut, but the Steward may keep selling cash-secured puts — the
        # defined-outcome income that earns the account back. The first version
        # blocked EVERYTHING, contradicting its own log message, and one bad
        # Tuesday would have frozen the desk for the rest of the contest.
        return Verdict(False, "kill-switch",
                       f"Vetoed: account equity ${a.equity:,.0f} is below the ${KILL_SWITCH_EQUITY:,.0f} "
                       f"kill switch — the desk is income-only, and a {p.agent} {p.kind} is not income.")

    dd = 1.0 - a.equity / a.day_start_equity if a.day_start_equity else 0.0
    if dd > DAILY_DRAWDOWN_GATE:
        return Verdict(False, "daily-drawdown",
                       f"Vetoed: down {dd:.1%} today, past the {DAILY_DRAWDOWN_GATE:.1%} gate. "
                       "No new risk until tomorrow.")

    cap = SLEEVE_CAP.get(p.agent, 0.0)
    used = a.sleeve_used.get(p.agent, 0.0)
    if used + p.notional > cap:
        return Verdict(False, "sleeve-cap",
                       f"Vetoed: {p.agent} has ${used:,.0f} of ${cap:,.0f} deployed; "
                       f"${p.notional:,.0f} more would breach the sleeve.")

    held = a.underlying_notional.get(p.symbol, 0.0)
    if held + p.notional > CONCENTRATION_CAP * a.equity:
        return Verdict(False, "concentration",
                       f"Vetoed: {p.symbol} would be ${held + p.notional:,.0f}, past "
                       f"{CONCENTRATION_CAP:.0%} of the account in one name.")

    if a.minutes_to_expiry <= FINAL_QUIET_MINUTES:
        return Verdict(False, "time-gate",
                       f"Vetoed: only {a.minutes_to_expiry / 60:.1f} hours to the expiry this would "
                       "trade into — a weekly opened this late is a coin toss, not a thesis.")

    return Verdict(True, None,
                   f"Approved: {p.agent} risks ${p.notional:,.0f} on {p.symbol} ({p.kind}) — "
                   "inside every gate.")
