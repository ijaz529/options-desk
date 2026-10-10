"""The wheel's second half, wired into the sessions (STRATEGY.md "Built 10 Oct 2026")."""
from datetime import date

from desk import broker, gates, log, run
from desk.broker import PutQuote

FRIDAY = date(2026, 10, 16)
KO = {"symbol": "KO", "qty": 100.0, "market_value": 8805.0, "cost_basis": 8780.0,
      "unrealized_pl": 25.0, "asset_class": "us_equity"}
KO_CALL = {"symbol": "KO261016C00090000", "qty": -1.0, "market_value": -15.0, "cost_basis": -19.0,
           "unrealized_pl": 4.0, "asset_class": "us_option"}


def call(strike, delta, bid, ask):
    return PutQuote(symbol=f"KO261016C{int(strike * 1000):08d}", underlying="KO", strike=strike,
                    expiry=FRIDAY, bid=bid, ask=ask, delta=delta, spot=88.05)


def state(minutes=5_000.0):
    return gates.AccountState(equity=90_000.0, day_start_equity=90_000.0,
                              sleeve_used={"steward": 8_805.0, "hunter": 0.0},
                              underlying_notional={"KO": 8_805.0}, minutes_to_expiry=minutes)


def diary(monkeypatch):
    rows = []
    monkeypatch.setattr(log, "record", lambda agent, action, because, **kw: rows.append((agent, action, because, kw)))
    return rows


def test_held_shares_get_one_covered_call(monkeypatch):
    rows, sold = diary(monkeypatch), []
    monkeypatch.setattr(broker, "weekly_calls", lambda u, e: [call(89, 0.30, 0.40, 0.44), call(90, 0.19, 0.18, 0.20)])
    monkeypatch.setattr(broker, "sell_call", lambda sym, qty, px: sold.append((sym, qty, px)) or "order-1")
    run.covered_call_round("KO", KO, [KO], [], FRIDAY, state())
    assert sold == [("KO261016C00090000", 1, 0.19)]
    agent, action, because, kw = rows[-1]
    assert (agent, action) == ("steward", "sell_call") and "covered call" in because and kw["qty"] == 1


def test_covered_shares_are_left_alone(monkeypatch):
    rows, sold = diary(monkeypatch), []
    monkeypatch.setattr(broker, "weekly_calls", lambda u, e: [call(90, 0.19, 0.18, 0.20)])
    monkeypatch.setattr(broker, "sell_call", lambda *a: sold.append(a) or "x")
    run.covered_call_round("KO", KO, [KO, KO_CALL], [], FRIDAY, state())               # booked
    run.covered_call_round("KO", KO, [KO], [{"symbol": "KO261016C00090000", "side": "sell",
                                             "qty": 1.0}], FRIDAY, state())            # still working
    assert sold == [] and [r[1] for r in rows] == ["hold", "hold"] and "covered" in rows[0][2]


def test_no_call_at_or_above_what_the_shares_cost_means_hold(monkeypatch):
    rows, sold = diary(monkeypatch), []
    monkeypatch.setattr(broker, "weekly_calls", lambda u, e: [call(87, 0.20, 0.30, 0.32)])
    monkeypatch.setattr(broker, "sell_call", lambda *a: sold.append(a) or "x")
    run.covered_call_round("KO", KO, [KO], [], FRIDAY, state())
    assert sold == [] and rows[-1][1] == "hold" and "87.80" in rows[-1][2]


def test_the_time_gate_still_binds(monkeypatch):
    rows, sold = diary(monkeypatch), []
    monkeypatch.setattr(broker, "weekly_calls", lambda u, e: [call(90, 0.19, 0.18, 0.20)])
    monkeypatch.setattr(broker, "sell_call", lambda *a: sold.append(a) or "x")
    run.covered_call_round("KO", KO, [KO], [], FRIDAY, state(minutes=60.0))
    assert sold == [] and rows[-1][1] == "veto" and rows[-1][3]["gate"] == "time-gate"


def test_a_covered_call_adds_nothing_to_the_sleeves(monkeypatch):
    monkeypatch.setattr(broker, "account_state", lambda: {"equity": 90_000.0, "cash": 80_000.0,
                                                          "buying_power": 0.0, "options_level": 3})
    monkeypatch.setattr(run, "read_positions", lambda: [KO, KO_CALL])
    monkeypatch.setattr(broker, "open_orders", lambda: [])
    monkeypatch.setattr(run, "hunter_trial_pnl", lambda: 0.0)
    st, _ = run.desk_state()
    assert st.sleeve_used == {"steward": 8805.0, "hunter": 0.0}      # was counted as a Hunter long
    assert st.underlying_notional == {"KO": 8805.0}


def test_sweep_takes_profit_on_the_call_and_never_stops_it(monkeypatch):
    rows, bought = diary(monkeypatch), []
    monkeypatch.setattr(broker, "open_orders", lambda: [])
    monkeypatch.setattr(broker, "buy_to_close", lambda sym, px, qty=1: bought.append((sym, px, qty)) or "b-1")
    cheap = dict(KO_CALL, market_value=-6.0)                         # 0.06 against a 0.19 credit
    monkeypatch.setattr(run, "read_positions", lambda: [KO, cheap])
    run.sweep()
    assert bought == [("KO261016C00090000", 0.06, 1)] and rows[-1][1] == "take_profit"
    rows.clear(); bought.clear()
    dear = dict(KO_CALL, market_value=-45.0)                         # more than double: no stop
    monkeypatch.setattr(run, "read_positions", lambda: [KO, dear])
    run.sweep()
    assert bought == [] and rows == []
