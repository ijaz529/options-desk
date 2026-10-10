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


def test_at_or_below_20_delta_only():
    # The KO 88 put of 24 Sep 2026: -0.26 delta, 0.7% below spot, 0.18% of strike.
    # Rule 2 says "at (or nearest below) the 20-delta strike"; it was assigned.
    assert pick([q(88, -0.26, 0.15, 0.17, spot=88.6)]) is None
    # "at" still counts, and the far edge is unchanged
    assert pick([q(240, -0.20, 1.0, 1.1)]).strike == 240
    assert pick([q(232, -0.13, 0.50, 0.56)]).strike == 232


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


def test_entry_row_says_offered_not_sold():
    # a placement is an offer; only a fill is a sale (rule 9's log amendment)
    from desk.steward import entry_because
    text = entry_because(q(238, -0.21, 1.05, 1.15))
    assert text.startswith("Offered to sell") and "counts once it fills" in text


# ---- the covered call: the wheel's second half (STRATEGY.md "Built 10 Oct 2026")
from desk.steward import call_because, call_exit_action, pick_call


def c(strike, delta, bid, ask, spot=88.0):
    return PutQuote(symbol=f"KO261016C{int(strike * 1000):08d}", underlying="KO", strike=strike,
                    expiry=date(2026, 10, 16), bid=bid, ask=ask, delta=delta, spot=spot)


def test_call_picks_nearest_to_20_delta():
    chain = [c(89, 0.30, 0.40, 0.44), c(90, 0.19, 0.18, 0.20), c(91, 0.13, 0.14, 0.16)]
    assert pick_call(chain, cost_basis=87.80).strike == 90


def test_call_never_below_what_the_shares_cost():
    # the one 20-delta call sits under the $90 the shares cost: holding uncovered beats
    # selling the shares at a loss if they are called away
    assert pick_call([c(89, 0.20, 0.30, 0.32)], cost_basis=90.0) is None
    assert pick_call([c(90, 0.20, 0.30, 0.32)], cost_basis=90.0).strike == 90


def test_call_keeps_the_puts_floor_market_and_band():
    assert pick_call([c(90, 0.20, 0.05, 0.07)], cost_basis=87.80) is None    # 0.07% of strike
    assert pick_call([c(90, 0.20, 0.10, 0.40)], cost_basis=87.80) is None    # spread wider than 20% of mid
    assert pick_call([c(89, 0.35, 0.50, 0.54), c(95, 0.05, 0.14, 0.16)], cost_basis=87.80) is None
    assert pick_call([c(90, None, 0.18, 0.20)], cost_basis=87.80) is None


def test_covered_call_takes_profit_but_has_no_stop():
    kind, because = call_exit_action(entry_credit=0.20, current_mid=0.06)
    assert kind == "take_profit" and "banked" in because
    # doubled against us: the shares gained more than the call lost — no stop
    assert call_exit_action(entry_credit=0.20, current_mid=0.45) is None
    assert call_exit_action(entry_credit=0.20, current_mid=0.15) is None


def test_call_row_names_the_shares_and_what_they_cost():
    text = call_because(c(90, 0.19, 0.18, 0.20), cost_basis=87.80, shares=100)
    assert text.startswith("Offered to sell") and "counts once it fills" in text
    assert "100 shares" in text and "87.80" in text and "covered call" in text
