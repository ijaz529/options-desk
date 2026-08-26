from datetime import date

from desk.broker import PutQuote
from desk.steward import exit_action, pick


def q(strike, delta, bid, ask, spot=250.0):
    return PutQuote(symbol=f"TEST{strike}", underlying="TEST", strike=strike,
                    expiry=date(2026, 9, 4), bid=bid, ask=ask, delta=delta, spot=spot)


def test_picks_nearest_to_20_delta():
    chain = [q(230, -0.14, 0.55, 0.65), q(238, -0.21, 1.05, 1.15), q(244, -0.27, 1.80, 1.90)]
    assert pick(chain).strike == 238


def test_rejects_thin_premium():
    # 0.10 mid on a 240 strike = 0.04% yield — obligation unpaid
    assert pick([q(240, -0.20, 0.05, 0.15)]) is None


def test_rejects_wide_markets():
    # 0.50/1.50: spread = mid — nobody knows the price
    assert pick([q(240, -0.20, 0.50, 1.50)]) is None


def test_rejects_outside_delta_band():
    assert pick([q(248, -0.45, 4.0, 4.2), q(220, -0.05, 0.42, 0.48)]) is None


def test_no_delta_no_trade():
    assert pick([q(240, None, 1.0, 1.1)]) is None


def test_take_profit_at_65_percent():
    kind, because = exit_action(entry_credit=2.00, current_mid=0.70)
    assert kind == "take_profit" and "banked" in because


def test_stop_when_doubled():
    kind, because = exit_action(entry_credit=2.00, current_mid=4.10)
    assert kind == "stop"


def test_holds_in_between():
    assert exit_action(entry_credit=2.00, current_mid=1.20) is None
