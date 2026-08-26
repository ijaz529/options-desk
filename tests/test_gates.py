"""One test per gate, plus the two always-allowed paths."""
from desk.gates import AccountState, Proposal, review


def state(**over) -> AccountState:
    base = dict(equity=100_000.0, day_start_equity=100_000.0,
                sleeve_used={"steward": 0.0, "hunter": 0.0},
                underlying_notional={}, minutes_to_contest_end=5_000.0)
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
    v = review(csp(kind="close"), state(equity=90_000.0, minutes_to_contest_end=10.0))
    assert v.approved


def test_naked_short_vetoed_before_anything_else():
    v = review(csp(short_uncovered=True), state())
    assert not v.approved and v.gate == "no-naked-shorts"


def test_kill_switch_below_96k():
    v = review(csp(), state(equity=95_999.0))
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
    v = review(csp(), state(minutes_to_contest_end=179.0))
    assert not v.approved and v.gate == "time-gate"


def test_every_verdict_explains_itself():
    for s in (state(), state(equity=90_000.0), state(minutes_to_contest_end=10.0)):
        v = review(csp(), s)
        assert len(v.because) > 20
