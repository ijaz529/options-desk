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

from alpaca.trading.enums import AssetClass, OrderSide

from desk import broker, gates, run
from desk.gates import Proposal, review


def _order(symbol, side, qty=1, limit=None, filled=0):
    return SimpleNamespace(id="o-1", symbol=symbol, side=side, qty=str(qty), limit_price=limit,
                           filled_qty=str(filled), created_at="2026-10-21T13:50:53+00:00", legs=None)


class _Trading:
    def __init__(self, orders=(), account=None, positions=()):
        self.orders, self.account, self.positions = list(orders), account, list(positions)

    def get_orders(self, _req):
        return self.orders

    def get_account(self):
        return self.account

    def get_all_positions(self):
        return self.positions


def _account(equity=90_000.0, last_equity=None):
    """An account as alpaca-py gives it: numbers as strings, last_equity the previous close."""
    return SimpleNamespace(equity=str(equity), cash=str(equity), buying_power=str(equity),
                           options_trading_level=3,
                           last_equity=str(equity if last_equity is None else last_equity))


def _state(monkeypatch, positions, orders, equity=90_000.0, last_equity=None, diary=()):
    """desk_state through the REAL broker.account_state and broker.open_orders."""
    monkeypatch.setattr(run, "read_positions", lambda: positions)
    monkeypatch.setattr(broker, "trading", lambda: _Trading(orders, _account(equity, last_equity)))
    monkeypatch.setattr(run, "hunter_trial_pnl", lambda: 0.0)
    monkeypatch.setattr(run.log, "rows", lambda *a, **k: list(diary))
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


def test_a_working_buy_back_on_a_spread_leaves_it_a_spread(monkeypatch):
    # counted as a second long, the buy-back would break the pair and the short leg would
    # read as a $17,250 cash-secured put instead of the spread's $750 width
    st = _state(monkeypatch, [_short("XOM261023P00172500"), _long("XOM261023P00165000", 1, 40.0)],
                [_order("XOM261023P00172500", OrderSide.BUY, limit="0.30")])
    assert st.sleeve_used["steward"] == 750.0


def test_a_working_hunter_buy_counts_the_premium_promised(monkeypatch):
    # the second thesis of a session must see the first one's order, filled or not
    st = _state(monkeypatch, [_long("GOOGL261030P00325000", 2, 2_360.0)],
                [_order("AMD261030P00520000", OrderSide.BUY, qty=2, limit="9.50")])
    assert st.sleeve_used["hunter"] == 2_360.0 + 1_900.0
    assert st.underlying_notional["AMD"] == 1_900.0


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


def test_a_part_filled_hunter_buy_counts_what_is_still_working(monkeypatch):
    # 1 of 5 filled: the booked lot is in the book, the other 4 are still promised
    st = _state(monkeypatch, [_long("AMD261030P00520000", 1, 400.0)],
                [_order("AMD261030P00520000", OrderSide.BUY, qty=5, limit="4.00", filled=1)])
    assert st.sleeve_used["hunter"] == 400.0 + 1_600.0


def test_a_part_filled_covered_call_still_covers_what_it_promised(monkeypatch):
    # 200 shares; a call order for 2 has 1 filled. Both are spoken for: no third call.
    rows, sent = [], []
    monkeypatch.setattr(run.log, "record", lambda agent, action, because, **kw: rows.append((agent, action, because)))
    monkeypatch.setattr(broker, "sell_call", lambda *a, **k: sent.append(a) or "c-1")
    stock = {"symbol": "KO", "qty": 200.0, "market_value": 18_600.0, "cost_basis": 17_560.0,
             "unrealized_pl": 1_040.0, "asset_class": "us_equity"}
    short_call = _short("KO261030C00094000", qty=-1)
    monkeypatch.setattr(broker, "trading", lambda: _Trading([_order("KO261030C00094000", OrderSide.SELL, qty=2, filled=1)]))
    st = gates.AccountState(equity=90_000.0, day_start_equity=90_000.0, sleeve_used={"steward": 0.0, "hunter": 0.0},
                            underlying_notional={}, minutes_to_expiry=6_000.0)
    from datetime import date
    run.covered_call_round("KO", stock, [stock, short_call], broker.open_orders(), date(2026, 10, 30), st)
    assert not sent
    assert any("covered by the call already written" in r[2] for r in rows)


def test_a_sell_closing_a_booked_long_call_is_not_a_covered_call(monkeypatch):
    # INTC is in both books: the Hunter's stop on his long call must not read as the
    # Steward's call written against assigned INTC shares
    rows = []
    monkeypatch.setattr(run.log, "record", lambda agent, action, because, **kw: rows.append((agent, action, because)))
    monkeypatch.setattr(broker, "weekly_calls", lambda u, expiry: [])
    stock = {"symbol": "INTC", "qty": 100.0, "market_value": 8_500.0, "cost_basis": 8_700.0,
             "unrealized_pl": -200.0, "asset_class": "us_equity"}
    hunter_call = _long("INTC261030C00090000", 1, 150.0)
    monkeypatch.setattr(broker, "trading", lambda: _Trading([_order("INTC261030C00090000", OrderSide.SELL)]))
    st = gates.AccountState(equity=90_000.0, day_start_equity=90_000.0, sleeve_used={"steward": 0.0, "hunter": 150.0},
                            underlying_notional={}, minutes_to_expiry=6_000.0)
    from datetime import date
    run.covered_call_round("INTC", stock, [stock, hunter_call], broker.open_orders(), date(2026, 10, 30), st)
    assert not any("covered by the call already written" in r[2] for r in rows)
    assert any("uncovered this round" in r[2] for r in rows)


def test_positions_report_the_asset_class_as_the_cli_does(monkeypatch):
    held = [SimpleNamespace(symbol="KO", qty="100", market_value="9300", cost_basis="8780",
                            unrealized_pl="520", asset_class=AssetClass.US_EQUITY),
            SimpleNamespace(symbol="BTCUSD", qty="0.01", market_value="680", cost_basis="670",
                            unrealized_pl="10", asset_class=AssetClass.CRYPTO)]
    monkeypatch.setattr(broker, "trading", lambda: _Trading(positions=held))
    assert [p["asset_class"] for p in broker.positions()] == ["us_equity", "crypto"]


def test_a_closed_spread_order_does_not_break_the_hunters_trial_pnl(monkeypatch):
    spread = SimpleNamespace(symbol=None, side=None, filled_qty="1", filled_avg_price="0.45")
    put = SimpleNamespace(symbol="MU261023P00875000", side=OrderSide.BUY, filled_qty="1", filled_avg_price="16.75")
    monkeypatch.setattr(broker, "trading", lambda: _Trading([spread, put]))
    assert broker.pnl_since({"MU261023P00875000"}, "2026-09-30T00:00:00Z") == -1_675.0


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


def test_the_daily_drawdown_gate_holds_for_the_rest_of_the_day(monkeypatch):
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    fired = {"ts": now.isoformat(timespec="seconds"), "agent": "risk", "action": "veto",
             "gate": "daily-drawdown", "because": "Vetoed: down 3.0% today", "symbol": "TSLA"}
    # recovered to -1.6%, but the gate fired earlier today: still shut
    st = _state(monkeypatch, [], [], equity=91_000.0, last_equity=92_500.10, diary=[fired])
    v = review(Proposal("steward", "KO", "csp", 9_200.0), st)
    assert not v.approved and v.gate == "daily-drawdown" and "until tomorrow" in v.because
    # a veto from yesterday does not carry over, and closing is never blocked
    yday = dict(fired, ts=(now - timedelta(days=1)).isoformat(timespec="seconds"))
    st = _state(monkeypatch, [], [], equity=91_000.0, last_equity=92_500.10, diary=[yday])
    assert review(Proposal("steward", "KO", "csp", 9_200.0), st).gate != "daily-drawdown"
    st = _state(monkeypatch, [], [], equity=91_000.0, last_equity=92_500.10, diary=[fired])
    assert review(Proposal("hunter", "TSLA", "close", 0.0), st).approved
