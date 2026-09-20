from desk.hunter import Thesis, drop_held, exit_action, validate


def raw(**over):
    base = dict(symbol="NVDA", direction="call",
                thesis="Gapped +4% on volume, closing on highs; continuation into Friday.",
                max_premium_usd=1500, invalidation="A close back below the gap open.")
    base.update(over)
    return base


def test_valid_proposal_passes():
    valid, rejected = validate([raw()])
    assert len(valid) == 1 and not rejected
    assert isinstance(valid[0], Thesis)


def test_unknown_symbol_rejected():
    valid, rejected = validate([raw(symbol="GME2")])
    assert not valid and "universe" in rejected[0]


def test_premium_cap_enforced():
    valid, rejected = validate([raw(max_premium_usd=5000)])
    assert not valid and "outside" in rejected[0]


def test_thesis_length_capped():
    valid, rejected = validate([raw(thesis="x" * 281)])
    assert not valid


def test_missing_invalidation_rejected():
    valid, rejected = validate([raw(invalidation="  ")])
    assert not valid and "unfalsifiable" in rejected[0]


def test_at_most_two_even_if_claude_sends_three():
    valid, _ = validate([raw(), raw(symbol="AMD"), raw(symbol="TSLA")])
    assert len(valid) == 2


def test_stop_at_half():
    kind, qty, because = exit_action(entry=2.00, current=0.99, qty=3)
    assert kind == "stop" and qty == 3


def test_take_half_when_doubled():
    kind, qty, because = exit_action(entry=2.00, current=4.10, qty=4)
    assert kind == "take_half" and qty == 2


def test_single_lot_banks_whole():
    kind, qty, because = exit_action(entry=2.00, current=4.10, qty=1)
    assert kind == "take_profit" and qty == 1


def test_holds_in_between():
    assert exit_action(entry=2.00, current=2.50, qty=2) is None


def test_malformed_entries_rejected_not_crashed():
    valid, rejected = validate(["AMD calls look good", 42, raw()])
    assert len(valid) == 1 and len(rejected) == 2
    assert "malformed" in rejected[0]


def test_one_position_per_name_drops_held_and_working():
    valid, _ = validate([raw(symbol="GS", direction="put"), raw(symbol="NVDA")])
    kept, dropped = drop_held(valid, held={"GS"})
    assert [t.symbol for t in kept] == ["NVDA"]
    assert [t.symbol for t in dropped] == ["GS"]


def test_one_position_per_name_keeps_everything_when_flat():
    valid, _ = validate([raw(symbol="GS", direction="put"), raw(symbol="NVDA")])
    kept, dropped = drop_held(valid, held=set())
    assert len(kept) == 2 and not dropped


# ── 20 Sep 2026: the three rules the first fortnight taught ───────────────────
from datetime import date, timedelta

from desk import hunter


def test_target_expiry_keeps_this_friday_early_in_the_week():
    fri = date(2026, 9, 25)                                 # a Friday
    assert hunter.target_expiry(date(2026, 9, 21), fri) == fri   # Monday, 4 days
    assert hunter.target_expiry(date(2026, 9, 22), fri) == fri   # Tuesday, 3 days


def test_target_expiry_rolls_a_week_inside_three_days():
    fri, nxt = date(2026, 9, 25), date(2026, 10, 2)
    assert hunter.target_expiry(date(2026, 9, 23), fri) == nxt   # Wednesday, 2 days
    assert hunter.target_expiry(date(2026, 9, 24), fri) == nxt   # Thursday, 1 day
    assert hunter.target_expiry(date(2026, 9, 25), fri) == nxt   # Friday itself — never 0DTE


def test_target_expiry_never_exceeds_the_ten_day_cap():
    fri = date(2026, 9, 25)
    for offset in range(0, 5):                               # Mon..Fri
        today = date(2026, 9, 21) + timedelta(days=offset)
        assert (hunter.target_expiry(today, fri) - today).days <= 10


def test_expiry_exit_fires_the_session_before_and_on_the_day():
    fri = date(2026, 9, 25)
    assert hunter.expiry_exit(fri, date(2026, 9, 23)) is None          # Wednesday: hold
    assert "tomorrow" in hunter.expiry_exit(fri, date(2026, 9, 24))    # Thursday: out
    assert "today" in hunter.expiry_exit(fri, date(2026, 9, 25))       # Friday: out


def test_runner_stops_at_breakeven_after_half_was_banked():
    kind, qty, _ = hunter.exit_action(entry=1.62, current=1.60, qty=3, took_half=True)
    assert kind == "breakeven_stop" and qty == 3


def test_runner_is_not_halved_a_second_time():
    assert hunter.exit_action(entry=1.62, current=4.05, qty=3, took_half=True) is None


def test_breakeven_stop_only_applies_to_a_runner():
    # same prices, no half banked: 1.60 vs 1.62 is nowhere near the −50% stop
    assert hunter.exit_action(entry=1.62, current=1.60, qty=5) is None
