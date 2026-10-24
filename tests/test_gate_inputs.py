"""What the Risk Officer reads from the broker (17 and 24 Oct 2026 reviews).

Two hard gates were fed the wrong inputs, and the tests passed because their fixtures wrote
order sides as "buy"/"sell" by hand. The broker's objects carry an OrderSide enum, whose str()
is "OrderSide.SELL", so `"sell" in side` never matched and a WORKING put was never counted
against the Steward's sleeve (rule 2): on 20-21 Oct the book reached $73,150 of a $70,000 cap.
And the account call never returned last_equity, so the daily drawdown gate (rule 3) compared
equity with itself and could not fire. These tests build orders and accounts the way alpaca-py
does, so the same mistake fails here first.
"""
from types import SimpleNamespace

from alpaca.trading.enums import OrderSide

from desk import broker, gates, run
from desk.gates import Proposal, review


def _order(symbol, side, qty=1):
    return SimpleNamespace(id="o-1", symbol=symbol, side=side, qty=str(qty),
                           created_at="2026-10-21T13:50:53+00:00", legs=None)


class _Trading:
    def __init__(self, orders=(), account=None):
        self.orders, self.account = list(orders), account

    def get_orders(self, _req):
        return self.orders

    def get_account(self):
        return self.account


def _state(monkeypatch, positions, orders, equity=90_000.0, last_equity=None):
    acct = {"equity": equity, "cash": equity, "buying_power": equity, "options_level": 3,
            "last_equity": equity if last_equity is None else last_equity}
    monkeypatch.setattr(broker, "account_state", lambda: acct)
    monkeypatch.setattr(run, "read_positions", lambda: positions)
    monkeypatch.setattr(broker, "trading", lambda: _Trading(orders))
    monkeypatch.setattr(run, "hunter_trial_pnl", lambda: 0.0)
    st, _ = run.desk_state()
    return st


def _long(symbol, qty, mv):
    return {"symbol": symbol, "qty": qty, "market_value": mv, "cost_basis": mv,
            "unrealized_pl": 0.0, "asset_class": "us_option"}


def _short(symbol, qty=-1):
    return {"symbol": symbol, "qty": qty, "market_value": -20.0, "cost_basis": -30.0,
            "unrealized_pl": 10.0, "asset_class": "us_option"}


def test_open_orders_reports_the_brokers_word_for_the_side(monkeypatch):
    monkeypatch.setattr(broker, "trading", lambda: _Trading([
        _order("INTC261023P00087000", OrderSide.SELL), _order("CAT261030P00667500", OrderSide.BUY)]))
    assert [o["side"] for o in broker.open_orders()] == ["sell", "buy"]


def test_a_working_put_counts_against_the_stewards_sleeve(monkeypatch):
    # the 21 Oct case: the INTC 87 put was approved while PFE 29 was still working
    st = _state(monkeypatch, [], [_order("PFE261023P00029000", OrderSide.SELL)])
    assert st.sleeve_used["steward"] == 2_900.0
    assert st.underlying_notional["PFE"] == 2_900.0


def test_the_sleeve_gate_now_sees_working_puts(monkeypatch):
    booked = [_short("XOM261023P00172500"), _short("KO261023P00092000"), _short("UBER261023P00067000"),
              _short("WMT261023P00116000"), _short("BAC261023P00049500"), _short("CSCO261023P00103000")]
    working = [_order("PFE261023P00029000", OrderSide.SELL), _order("DIS261023P00109000", OrderSide.SELL)]
    st = _state(monkeypatch, booked, working)
    assert st.sleeve_used["steward"] == 60_000.0 + 2_900.0 + 10_900.0
    v = review(Proposal("steward", "INTC", "csp", 8_700.0), st)
    assert not v.approved and v.gate == "sleeve-cap"


def test_a_working_close_of_a_booked_long_is_not_a_new_obligation(monkeypatch):
    # the Hunter's stop on two GOOGL puts must not read as a $65,000 Steward put
    st = _state(monkeypatch, [_long("GOOGL261030P00325000", 2, 2_360.0)],
                [_order("GOOGL261030P00325000", OrderSide.SELL, 2)])
    assert st.sleeve_used == {"steward": 0.0, "hunter": 2_360.0}


def test_a_working_buy_back_does_not_count_twice(monkeypatch):
    st = _state(monkeypatch, [_short("XOM261023P00172500")],
                [_order("XOM261023P00172500", OrderSide.BUY)])
    assert st.sleeve_used["steward"] == 17_250.0


def test_a_working_covered_call_covers_its_shares(monkeypatch):
    rows = []
    monkeypatch.setattr(run.log, "record", lambda agent, action, because, **kw: rows.append((agent, action, because)))
    monkeypatch.setattr(broker, "trading", lambda: _Trading([_order("KO261030C00094000", OrderSide.SELL)]))
    stock = {"symbol": "KO", "qty": 100.0, "market_value": 9_300.0, "cost_basis": 8_780.0,
             "unrealized_pl": 520.0, "asset_class": "us_equity"}
    st = gates.AccountState(equity=90_000.0, day_start_equity=90_000.0, sleeve_used={"steward": 0.0, "hunter": 0.0},
                            underlying_notional={}, minutes_to_expiry=6_000.0)
    from datetime import date
    run.covered_call_round("KO", stock, [stock], broker.open_orders(), date(2026, 10, 30), st)
    assert any("covered by the call already written" in r[2] for r in rows)


def test_account_state_carries_the_previous_close(monkeypatch):
    acct = SimpleNamespace(equity="89730.86", cash="80000", last_equity="92500.10",
                           buying_power="160000", options_trading_level=3)
    monkeypatch.setattr(broker, "trading", lambda: _Trading(account=acct))
    assert broker.account_state()["last_equity"] == 92_500.10


def test_the_daily_drawdown_gate_can_fire(monkeypatch):
    st = _state(monkeypatch, [], [], equity=89_730.86, last_equity=92_500.10)   # down 3.0% on the day
    assert st.day_start_equity == 92_500.10
    v = review(Proposal("hunter", "TSLA", "long_option", 1_392.0), st)
    assert not v.approved and v.gate == "daily-drawdown"
    calm = _state(monkeypatch, [], [], equity=91_000.0, last_equity=92_500.10)  # down 1.6%
    assert review(Proposal("hunter", "TSLA", "long_option", 1_392.0), calm).gate != "daily-drawdown"
