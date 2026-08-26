from desk.weekend import ENTRY_THRESHOLD, entries, exit_action


def test_no_qualifier_stays_in_cash_and_says_so():
    out = entries({"BTC/USD": 0.004, "ETH/USD": -0.02})
    assert len(out) == 1 and out[0][0] == "" and "Cash is a position" in out[0][2]


def test_single_mover_gets_the_sleeve():
    out = entries({"BTC/USD": 0.031, "ETH/USD": 0.002})
    assert out[0][0] == "BTC/USD" and out[0][1] == 2500.0


def test_both_movers_split_it():
    out = entries({"BTC/USD": 0.02, "ETH/USD": 0.05})
    assert [o[0] for o in out] == ["ETH/USD", "BTC/USD"] and all(o[1] == 1250.0 for o in out)


def test_negative_momentum_never_entered():
    out = entries({"BTC/USD": -0.06, "ETH/USD": -0.03})
    assert out[0][0] == ""


def test_exits_at_four_percent():
    assert exit_action(1000, 959)[0] == "stop"
    assert exit_action(1000, 1041)[0] == "take_profit"
    assert exit_action(1000, 1015) is None
