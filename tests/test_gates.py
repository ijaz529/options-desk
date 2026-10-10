"""One test per gate, plus the two always-allowed paths."""
from desk import gates
from desk.gates import AccountState, Proposal, review


def state(**over) -> AccountState:
    base = dict(equity=100_000.0, day_start_equity=100_000.0,
                sleeve_used={"steward": 0.0, "hunter": 0.0},
                underlying_notional={}, minutes_to_expiry=5_000.0)
    base.update(over)
    return AccountState(**base)


def csp(notional=14_000.0, **over) -> Proposal:
    base = dict(agent="steward", symbol="AAPL", kind="csp", notional=notional)
    base.update(over)
    return Proposal(**base)


def test_clean_proposal_is_approved():
    v = review(csp(), state())
    assert v.approved and v.gate is None and "Approved" in v.because


def test_closing_always_allowed_even_past_kill_switch():
    v = review(csp(kind="close"), state(equity=90_000.0, minutes_to_expiry=10.0))
    assert v.approved


def test_naked_short_vetoed_before_anything_else():
    v = review(csp(short_uncovered=True), state())
    assert not v.approved and v.gate == "no-naked-shorts"


def test_kill_switch_below_the_switch_blocks_the_hunter():
    # income-only: the Steward's CSPs pass (covered by the dedicated test below);
    # anything that is not income is vetoed. Derived from the constant, not a
    # magic number — the switch is a fraction of a baseline that gets re-based.
    under = gates.KILL_SWITCH_EQUITY - 1.0
    v = review(Proposal(agent="hunter", symbol="AMD", kind="long_option", notional=1_500),
               state(equity=under, day_start_equity=under))
    assert not v.approved and v.gate == "kill-switch"


def test_daily_drawdown_gate():
    v = review(csp(), state(equity=97_400.0, day_start_equity=100_000.0))
    assert not v.approved and v.gate == "daily-drawdown"


def test_drawdown_measured_from_day_start_not_100k():
    # up on the week, flat on the day: fine
    v = review(csp(), state(equity=104_000.0, day_start_equity=104_000.0))
    assert v.approved


def test_sleeve_cap():
    v = review(csp(notional=14_000.0), state(sleeve_used={"steward": 60_000.0}))
    assert not v.approved and v.gate == "sleeve-cap"


def test_hunter_sleeve_is_smaller():
    v = review(csp(agent="hunter", kind="long_option", notional=6_000.0),
               state(sleeve_used={"hunter": 15_000.0}))
    assert not v.approved and v.gate == "sleeve-cap"


def test_concentration_cap_is_account_wide():
    v = review(csp(notional=10_000.0),
               state(underlying_notional={"AAPL": 12_000.0}))
    assert not v.approved and v.gate == "concentration"


def test_time_gate_final_three_hours():
    v = review(csp(), state(minutes_to_expiry=179.0))
    assert not v.approved and v.gate == "time-gate"


def test_every_verdict_explains_itself():
    for s in (state(), state(equity=90_000.0), state(minutes_to_expiry=10.0)):
        v = review(csp(), s)
        assert len(v.because) > 20


def test_kill_switch_is_income_only_not_a_freeze():
    """Below the switch the Hunter shuts but the Steward keeps selling insurance."""
    under = gates.KILL_SWITCH_EQUITY - 500
    poor = AccountState(equity=under, day_start_equity=under,
                        sleeve_used={"steward": 0, "hunter": 0},
                        underlying_notional={}, minutes_to_expiry=5_000)
    csp = review(Proposal(agent="steward", symbol="XOM", kind="csp", notional=15_000), poor)
    assert csp.approved, csp.because
    ticket = review(Proposal(agent="hunter", symbol="AMD", kind="long_option", notional=1_500), poor)
    assert not ticket.approved and ticket.gate == "kill-switch"
    crypto = review(Proposal(agent="hunter", symbol="BTC/USD", kind="crypto_spot", notional=1_000), poor)
    assert not crypto.approved and crypto.gate == "kill-switch"


def test_kill_switch_is_a_fraction_of_a_stated_baseline():
    """It was a fixed $96,000 — 4% below the contest's $100k start. When the
    contest ended at $93,630 that figure was tripped permanently and shut the
    Hunter for good, so it is now 96% of a baseline that is re-based, dated, in
    the code and in STRATEGY.md (13 Sep 2026)."""
    assert gates.KILL_SWITCH_EQUITY == gates.BASELINE_EQUITY * gates.KILL_SWITCH_FRACTION
    assert gates.KILL_SWITCH_FRACTION == 0.96
    # the live account must sit ABOVE its own switch, or the desk is frozen again
    assert gates.BASELINE_EQUITY > gates.KILL_SWITCH_EQUITY


# Rule 9 (29 Sep 2026): no opening order without a live session to fill in.
from desk.gates import MIN_MINUTES_BEFORE_CLOSE, session_open_for_entries


def test_closed_market_blocks_entries():
    # Mon 28 Sep: the steward slot arrived at 20:13 UTC, 13 minutes after the close
    assert "closed" in session_open_for_entries(False, 1_000)


def test_last_hour_blocks_entries():
    assert session_open_for_entries(True, MIN_MINUTES_BEFORE_CLOSE - 1) is not None


def test_open_market_with_time_allows_entries():
    assert session_open_for_entries(True, 360) is None
    assert session_open_for_entries(True, MIN_MINUTES_BEFORE_CLOSE) is None


# The Hunter's trial after the 20 Sep fixes (STRATEGY.md "Re-based 30 Sep 2026").
from desk.gates import BASELINE_EQUITY, HUNTER_TRIAL_BUDGET, KILL_SWITCH_EQUITY


def test_rebased_switch_lets_the_hunter_trade_at_todays_equity():
    assert BASELINE_EQUITY == 88_983.0
    v = review(Proposal("hunter", "SPY", "long_option", 500.0), state(equity=88_983.0, day_start_equity=88_983.0))
    assert v.approved, v.because


def test_account_floor_still_binds_after_the_rebase():
    below = KILL_SWITCH_EQUITY - 1
    v = review(Proposal("hunter", "SPY", "long_option", 500.0), state(equity=below, day_start_equity=below))
    assert not v.approved and v.gate == "kill-switch"


def test_trial_budget_locks_out_the_hunter_alone():
    s = state(equity=88_983.0, day_start_equity=88_983.0, hunter_trial_pnl=-HUNTER_TRIAL_BUDGET)
    hunter = review(Proposal("hunter", "SPY", "long_option", 500.0), s)
    steward = review(Proposal("steward", "XOM", "csp", 10_000.0), s)
    assert not hunter.approved and hunter.gate == "hunter-trial"
    assert steward.approved, steward.because


def test_trial_budget_not_yet_spent():
    s = state(equity=88_983.0, day_start_equity=88_983.0, hunter_trial_pnl=-HUNTER_TRIAL_BUDGET + 1)
    assert review(Proposal("hunter", "SPY", "long_option", 500.0), s).approved


# ---- the covered call (STRATEGY.md "Built 10 Oct 2026")
def covered(**over) -> Proposal:
    base = dict(agent="steward", symbol="KO", kind="covered_call", notional=0.0)
    base.update(over)
    return Proposal(**base)


def test_covered_call_adds_no_risk_so_full_sleeves_and_the_switch_do_not_block_it():
    under = gates.KILL_SWITCH_EQUITY - 500
    v = review(covered(), state(equity=under, day_start_equity=under,
                                sleeve_used={"steward": 80_000.0, "hunter": 0.0},
                                underlying_notional={"KO": 30_000.0}))
    assert v.approved, v.because


def test_uncovered_call_is_a_naked_short():
    v = review(covered(short_uncovered=True), state())
    assert not v.approved and v.gate == "no-naked-shorts"


def test_covered_call_still_minds_the_time_gate():
    v = review(covered(), state(minutes_to_expiry=60.0))
    assert not v.approved and v.gate == "time-gate"
