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
    kind: str                   # "csp" | "spread" | "covered_call" | "long_option" | "crypto_spot" | "close"
    notional: float             # cash at risk: strike*100 for a CSP, premium for longs
    short_uncovered: bool = False


@dataclass(frozen=True)
class AccountState:
    equity: float
    day_start_equity: float
    sleeve_used: dict[str, float]         # agent -> notional already deployed
    underlying_notional: dict[str, float] # symbol -> account-wide notional
    minutes_to_expiry: float               # to the expiry a new position would trade into
    hunter_trial_pnl: float = 0.0          # Hunter P&L since HUNTER_TRIAL_START, fills + marks


SLEEVE_CAP = {"steward": 70_000.0, "hunter": 20_000.0}
DAILY_DRAWDOWN_GATE = 0.025

# The kill switch is a FRACTION of a stated baseline, not a figure (STRATEGY.md
# "Post-contest operation", 13 Sep 2026). As a fixed $96,000 it was 4% below the
# contest's $100,000 start; when the contest ended at $93,630 it was tripped
# permanently, shutting the Hunter and the weekend sleeve for good. Re-basing is
# an explicit, DATED decision because it forgives prior losses — never change
# BASELINE_EQUITY without saying so here and in STRATEGY.md.
# Re-based 30 Sep 2026 (STRATEGY.md "Re-based 30 Sep 2026"): was $93,630 on 13 Sep. The
# −5.0% between the two is not erased — it stays in the log and the write-up.
BASELINE_EQUITY = 88_983.0        # equity on 29 Sep 2026, the last session before the Hunter's trial
# The Hunter's own budget for the trial: locked out on his own at −$2,000 from this date.
HUNTER_TRIAL_START = "2026-09-30"
HUNTER_TRIAL_BUDGET = 2_000.0
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

    if p.kind == "covered_call":
        # A call written against shares already held opens no new risk: it trades their upside
        # above the strike for the premium. No sleeve, no concentration, allowed under
        # income-only; only the time gate still binds (STRATEGY.md "Built 10 Oct 2026").
        if a.minutes_to_expiry <= FINAL_QUIET_MINUTES:
            return Verdict(False, "time-gate",
                           f"Vetoed: only {a.minutes_to_expiry / 60:.1f} hours to the expiry this would "
                           "trade into — a weekly opened this late is a coin toss, not a thesis.")
        return Verdict(True, None,
                       f"Approved: {p.agent} writes a covered call on {p.symbol} against shares held — "
                       "income on stock the account already carries, no new risk.")

    # defined-risk put spreads count as income here since 26 Sep 2026 (STRATEGY.md); the code
    # caught up on 10 Oct 2026, when the spread was built
    if a.equity < KILL_SWITCH_EQUITY and not (p.agent == "steward" and p.kind in ("csp", "spread")):
        # income-only means exactly that: the Hunter and the weekend sleeve are
        # shut, but the Steward may keep selling cash-secured puts — the
        # defined-outcome income that earns the account back. The first version
        # blocked EVERYTHING, contradicting its own log message, and one bad
        # Tuesday would have frozen the desk for the rest of the contest.
        return Verdict(False, "kill-switch",
                       f"Vetoed: account equity ${a.equity:,.0f} is below the ${KILL_SWITCH_EQUITY:,.0f} "
                       f"kill switch — the desk is income-only, and a {p.agent} {p.kind} is not income.")

    if p.agent == "hunter" and a.hunter_trial_pnl <= -HUNTER_TRIAL_BUDGET:
        return Verdict(False, "hunter-trial",
                       f"Vetoed: the Hunter is ${-a.hunter_trial_pnl:,.0f} down since "
                       f"{HUNTER_TRIAL_START}, past his ${HUNTER_TRIAL_BUDGET:,.0f} trial budget — "
                       "locked out on his own; the Steward carries on.")

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


# Rule 9 (STRATEGY.md, 29 Sep 2026): no opening order without a live session to fill in.
MIN_MINUTES_BEFORE_CLOSE = 60


def session_open_for_entries(is_open: bool, minutes_to_close: float) -> str | None:
    """None if an opening order may be placed now, else the plain-English reason it may not.
    Fed from the broker's own market clock, so DST and holidays need no table here."""
    if not is_open:
        return ("The market is closed, so no opening order goes in: a limit placed on a shut "
                "market sits at the last session's prices until the sweep cancels it (rule 9). "
                "A late slot costs a retry, not a placement.")
    if minutes_to_close < MIN_MINUTES_BEFORE_CLOSE:
        return (f"Only {minutes_to_close:.0f} minutes to the close — under the "
                f"{MIN_MINUTES_BEFORE_CLOSE}-minute floor for a new position to fill (rule 9). "
                "No opening order this round.")
    return None
