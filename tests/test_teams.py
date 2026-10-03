"""Teams 2 and 3 and the wall between teams (STRATEGY.md "Teams 2 and 3", 2 Oct 2026)."""
from datetime import date

from desk import collar, condor, team
from desk.broker import PutQuote
from desk.teams_run import occ


def q(strike, bid, ask, delta=None, expiry=date(2026, 12, 31), u="SPY", spot=770.0, kind="P"):
    return PutQuote(symbol=f"{u}{expiry:%y%m%d}{kind}{int(strike * 1000):08d}", underlying=u,
                    strike=strike, expiry=expiry, bid=bid, ask=ask, delta=delta, spot=spot)


# ---- the wall
def test_a_team_only_trades_its_own_account():
    assert team.account_problem("PA3SKVNYTFJK", "collar") is None
    assert "may only trade PA3SKVNYTFJK" in team.account_problem("PA3G3BG7TIBD", "collar")
    assert team.account_problem("PA3G3BG7TIBD", "wheelhouse") is None


def test_a_team_without_an_account_refuses():
    assert "no paper account assigned" in team.account_problem("PA3G4NEQHCUC", "condor")


# ---- the Collar
def test_quarter_expiry_takes_the_last_listed_day_and_rolls_on_expiry_day():
    listed = [date(2026, 12, 18), date(2026, 12, 31), date(2027, 3, 19), date(2027, 3, 31)]
    assert collar.quarter_expiry(listed, date(2026, 10, 2)) == date(2026, 12, 31)
    assert collar.quarter_expiry(listed, date(2026, 12, 31)) == date(2027, 3, 31)   # the reset day
    # a quarter that ends on a weekend: the Friday before is the last listed day
    assert collar.quarter_expiry([date(2027, 6, 30)], date(2027, 4, 1)) == date(2027, 6, 30)


def test_lots_fit_ninety_five_per_cent_of_the_account():
    assert collar.lots(100_000, 769.0) == 1
    assert collar.lots(70_000, 769.0) == 0
    assert collar.lots(250_000, 769.0) == 3


def test_collar_strikes_and_the_call_that_pays_for_the_puts():
    puts = [q(615, 3.9, 4.1), q(620, 4.0, 4.2), q(730, 11.9, 12.1), q(735, 12.9, 13.1)]
    calls = [q(800, 11.9, 12.1, kind="C"), q(810, 8.7, 8.9, kind="C"), q(820, 6.0, 6.2, kind="C"),
             q(760, 30.0, 30.4, kind="C")]                       # below spot: never used
    c, why = collar.pick(puts, calls, spot=770.0)
    assert why == ""
    assert c.long_put.strike == 730 and c.short_put.strike == 615     # nearest 731.5 and 616
    assert c.short_call.strike == 810                                  # 8.8 ≈ 12.0 − 4.0 = 8.0
    assert abs(c.net) < 1.0
    assert collar.structure_problem(1, c) is None
    assert "naked" in collar.structure_problem(0, c)


def test_collar_refuses_a_thin_chain():
    c, why = collar.pick([q(730, 12, 12.2)], [q(800, 12, 12.2, kind="C")], spot=770.0)
    assert c is None and "same strike" in why


# ---- the Condor
def chain():
    # spot 770 → wings 4% (≈31 points) beyond the 20-delta shorts
    puts = [q(690, 1.0, 1.1, -0.05, date(2026, 11, 20)), q(705, 1.6, 1.8, -0.09, date(2026, 11, 20)),
            q(735, 4.0, 4.2, -0.20, date(2026, 11, 20)), q(750, 6.5, 6.7, -0.30, date(2026, 11, 20))]
    calls = [q(800, 3.0, 3.2, 0.20, date(2026, 11, 20), kind="C"), q(830, 0.5, 0.6, 0.05, date(2026, 11, 20), kind="C"),
             q(790, 5.0, 5.2, 0.31, date(2026, 11, 20), kind="C")]
    return puts, calls


def test_condor_sells_twenty_delta_and_buys_wings_four_per_cent_out():
    c, why = condor.pick(*chain())
    assert why == ""
    assert (c.long_put.strike, c.short_put.strike, c.short_call.strike, c.long_call.strike) == (705, 735, 800, 830)
    assert c.credit == round(4.1 + 3.1 - 1.7 - 0.55, 2)
    assert c.wing == 30 and c.max_loss == round((30 - c.credit) * 100, 2)


def test_condor_skips_when_underpaid_or_a_leg_is_unpriced():
    puts, calls = chain()
    thin = [q(735, 0.9, 1.0, -0.20, date(2026, 11, 20)), puts[1]]
    c, why = condor.pick(thin, calls)
    assert c is None and "not paid enough" in why
    c, why = condor.pick([puts[1]], [])
    assert c is None and "no quote or no delta" in why


def test_monthly_expiry_is_the_third_friday_25_to_45_days_out():
    assert condor.third_friday(2026, 11) == date(2026, 11, 20)
    listed = [date(2026, 10, 16), date(2026, 10, 30), date(2026, 11, 20), date(2026, 12, 18)]
    assert condor.monthly_expiry(listed, date(2026, 10, 19)) == date(2026, 11, 20)   # 32 days
    assert condor.monthly_expiry(listed, date(2026, 10, 2)) is None                   # 14 and 49 days


def test_condor_risk_gates():
    c, _ = condor.pick(*chain())
    assert condor.risk_problem(c, 100_000, 100_000, 0) is None
    assert "more than 5%" in condor.risk_problem(c, 40_000, 40_000, 0)
    assert "already at risk" in condor.risk_problem(c, 100_000, 100_000, 13_000)
    assert "no new condor" in condor.risk_problem(c, 91_000, 100_000, 0)


def test_condor_exits():
    assert condor.exit_action(5.0, 2.4, 20)[0] == "take_profit"
    assert condor.exit_action(5.0, 10.0, 20)[0] == "stop"
    assert condor.exit_action(5.0, 4.0, 7)[0] == "time_exit"
    assert condor.exit_action(5.0, 4.0, 20) is None


def test_occ_parses_and_tolerates_a_multi_leg_order_with_no_symbol():
    assert occ("SPY261231P00730000") == ("SPY", date(2026, 12, 31), "P", 730.0)
    assert occ(None) is None and occ("SPY") is None
