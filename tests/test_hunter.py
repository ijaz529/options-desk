from desk.hunter import Thesis, exit_action, validate


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
