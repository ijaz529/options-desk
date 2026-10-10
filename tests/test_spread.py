"""The Steward's put spread, wired into the sessions (STRATEGY.md "Built 10 Oct 2026")."""
from datetime import date

from desk import broker, gates, log, run
from desk.broker import PutQuote

FRIDAY = date(2026, 10, 16)


def leg(sym, qty, mv, cost):
    return {"symbol": sym, "qty": qty, "market_value": mv, "cost_basis": cost,
            "unrealized_pl": 0.0, "asset_class": "us_option"}


SHORT = leg("KO261016P00088000", -1.0, -20.0, -32.0)      # sold at 0.32, worth 0.20
WING = leg("KO261016P00085000", 1.0, 3.0, 8.0)            # bought at 0.08, worth 0.03
HUNTER = leg("AMD261016C00660000", 2.0, 900.0, 800.0)     # someone else's name entirely


def put(strike, delta, bid, ask):
    return PutQuote(symbol=f"KO261016P{int(strike * 1000):08d}", underlying="KO", strike=strike,
                    expiry=FRIDAY, bid=bid, ask=ask, delta=delta, spot=89.0)


def state(minutes=5_000.0, equity=90_000.0):
    return gates.AccountState(equity=equity, day_start_equity=equity,
                              sleeve_used={"steward": 0.0, "hunter": 0.0},
                              underlying_notional={}, minutes_to_expiry=minutes)


def diary(monkeypatch):
    rows = []
    monkeypatch.setattr(log, "record", lambda agent, action, because, **kw: rows.append((agent, action, because, kw)))
    return rows


def test_a_long_put_beside_a_short_put_is_the_spreads_wing():
    spreads = run.steward_spreads([SHORT, WING, HUNTER])
    assert list(spreads) == [("KO", FRIDAY)] and spreads[("KO", FRIDAY)] == (SHORT, WING)
    assert run.steward_spreads([SHORT]) == {} and run.steward_spreads([WING, HUNTER]) == {}


def test_a_two_leg_order_names_its_underlying():
    mleg = {"id": "1", "symbol": None, "side": "buy", "qty": 1.0, "created_at": "",
            "legs": ["KO261016P00088000", "KO261016P00085000"]}
    assert run.parse_occ(None) is None
    assert run.order_symbols(mleg) == ["KO261016P00088000", "KO261016P00085000"]


def test_a_spread_counts_its_width_not_a_cash_secured_obligation(monkeypatch):
    monkeypatch.setattr(broker, "account_state", lambda: {"equity": 90_000.0, "cash": 80_000.0,
                                                          "buying_power": 0.0, "options_level": 3})
    monkeypatch.setattr(run, "read_positions", lambda: [SHORT, WING, HUNTER])
    monkeypatch.setattr(broker, "open_orders", lambda: [])
    monkeypatch.setattr(run, "hunter_trial_pnl", lambda: 0.0)
    st, _ = run.desk_state()
    assert st.sleeve_used == {"steward": 300.0, "hunter": 900.0}    # 3 wide x 100; the wing is not the Hunter's
    assert st.underlying_notional == {"KO": 300.0, "AMD": 900.0}


def test_a_working_spread_order_counts_too(monkeypatch):
    monkeypatch.setattr(broker, "account_state", lambda: {"equity": 90_000.0, "cash": 80_000.0,
                                                          "buying_power": 0.0, "options_level": 3})
    monkeypatch.setattr(run, "read_positions", lambda: [])
    monkeypatch.setattr(broker, "open_orders", lambda: [{"id": "1", "symbol": None, "side": "buy", "qty": 1.0,
                                                        "created_at": "", "legs": [SHORT["symbol"], WING["symbol"]]}])
    monkeypatch.setattr(run, "hunter_trial_pnl", lambda: 0.0)
    st, _ = run.desk_state()
    assert st.sleeve_used["steward"] == 300.0 and st.underlying_notional == {"KO": 300.0}


def test_no_put_pays_so_the_spread_is_offered(monkeypatch):
    rows, sent = diary(monkeypatch), []
    monkeypatch.setattr(broker, "mleg", lambda legs, px, qty=1: sent.append((legs, px, qty)) or "m-1")
    chain = [put(88, -0.20, 0.38, 0.42), put(85, -0.09, 0.07, 0.09)]
    assert run.put_spread_round("KO", chain, state()) is True
    assert sent == [([("KO261016P00085000", "buy", "buy_to_open"),
                      ("KO261016P00088000", "sell", "sell_to_open")], -0.32, 1)]
    assert rows[-1][1] == "sell_spread" and rows[-1][3]["max_loss"] == 268.0


def test_a_spread_that_does_not_pay_is_a_hold_and_the_gates_still_bind(monkeypatch):
    rows, sent = diary(monkeypatch), []
    monkeypatch.setattr(broker, "mleg", lambda *a, **k: sent.append(a) or "m-1")
    assert run.put_spread_round("KO", [put(88, -0.20, 0.38, 0.42), put(87, -0.10, 0.34, 0.36)], state()) is False
    assert rows[-1][1] == "hold"
    assert run.put_spread_round("KO", [put(88, -0.20, 0.38, 0.42), put(85, -0.09, 0.07, 0.09)], state(minutes=60.0)) is False
    assert sent == [] and rows[-1][1] == "veto" and rows[-1][3]["gate"] == "time-gate"


def test_sweep_closes_the_spread_as_one_order_and_never_hands_the_wing_to_the_hunter(monkeypatch):
    rows, sent, sold = diary(monkeypatch), [], []
    monkeypatch.setattr(broker, "open_orders", lambda: [])
    monkeypatch.setattr(broker, "mleg", lambda legs, px, qty=1: sent.append((legs, px, qty)) or "m-1")
    monkeypatch.setattr(broker, "sell_option", lambda *a: sold.append(a) or "s-1")
    monkeypatch.setattr(broker, "buy_to_close", lambda *a, **k: sold.append(a) or "b-1")
    # 0.24 credit; buying it back costs 0.08 - 0.01 = 0.07, under 35% of the credit: take profit
    won = [leg(SHORT["symbol"], -1.0, -8.0, -32.0), leg(WING["symbol"], 1.0, 1.0, 8.0)]
    monkeypatch.setattr(run, "read_positions", lambda: won)
    run.sweep()
    assert sent == [([(SHORT["symbol"], "buy", "buy_to_close"), (WING["symbol"], "sell", "sell_to_close")], 0.07, 1)]
    assert rows[-1][1] == "take_profit" and sold == []
    # the wing is down 62% — a Hunter long would be stopped out; it is the spread's, so nothing
    sent.clear(); rows.clear()
    calm = [leg(SHORT["symbol"], -1.0, -20.0, -32.0), leg(WING["symbol"], 1.0, 3.0, 8.0)]
    monkeypatch.setattr(run, "read_positions", lambda: calm)
    run.sweep()
    assert sent == [] and sold == [] and rows == []
