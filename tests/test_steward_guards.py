"""The Steward's three guards and the paged order read (STRATEGY.md "Amended 12 Nov 2026")."""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from alpaca.trading.enums import OrderSide

from desk import broker, gates, log, run, steward
from desk.broker import PutQuote

EXPIRY = date(2026, 10, 30)
TODAY = date(2026, 10, 28)


# rule 10: no put through an earnings report

def test_a_report_before_the_expiry_blocks_the_put():
    # INTC reported on 29 Oct 2026; the 30 Oct 86 put was sold the day before and cost $1,664
    assert "29 Oct" in steward.earnings_block([date(2026, 10, 29)], TODAY, EXPIRY)
    assert steward.earnings_block([TODAY], TODAY, EXPIRY)          # today counts
    assert steward.earnings_block([EXPIRY], TODAY, EXPIRY)         # so does expiry day


def test_a_report_after_the_expiry_or_recently_past_does_not():
    assert steward.earnings_block([date(2026, 11, 19)], TODAY, EXPIRY) is None
    assert steward.earnings_block([date(2026, 10, 20)], TODAY, EXPIRY) is None


def test_a_stale_date_means_the_next_report_is_due():
    # Yahoo still showing July's report in late October: the next one is due and undated
    assert "due" in steward.earnings_block([date(2026, 7, 24)], TODAY, EXPIRY)
    assert steward.earnings_block([EXPIRY - timedelta(days=steward.EARNINGS_DUE_DAYS)], TODAY, EXPIRY) is None


def test_a_fund_has_no_report():
    assert steward.earnings_block([], TODAY, EXPIRY) is None


# rule 11: no second put on a name stopped out for the same expiry

def test_stopped_names_reads_the_diary_for_this_expiry_only():
    rows = [{"agent": "steward", "action": "stop", "symbol": "INTC261030P00086000"},
            {"agent": "steward", "action": "stop", "symbols": ["GM261030P00078000", "GM261030P00075000"]},
            {"agent": "steward", "action": "stop", "symbol": "BAC261023P00050000"},          # last week's
            {"agent": "steward", "action": "take_profit", "symbol": "KO261030P00088000"},     # a win
            {"agent": "hunter", "action": "stop", "symbol": "ORCL261030P00129000"},           # not his
            {"agent": "steward", "action": "hold"}]
    assert run.stopped_names(rows, EXPIRY) == {"INTC", "GM"}
    assert run.stopped_names(rows, date(2026, 11, 6)) == set()


def _session(monkeypatch, earnings, diary_rows=()):
    """One Steward session on a single name with a put that qualifies; returns (rows, sold)."""
    rows, sold = [], []
    monkeypatch.setattr(run, "UNIVERSE", ["INTC"])
    monkeypatch.setattr(run, "_entries_blocked", lambda agent: False)
    monkeypatch.setattr(run, "next_weekly_friday", lambda today=None: EXPIRY)
    state = gates.AccountState(equity=90_000.0, day_start_equity=90_000.0,
                               sleeve_used={"steward": 0.0, "hunter": 0.0},
                               underlying_notional={}, minutes_to_expiry=3_000.0)
    monkeypatch.setattr(run, "desk_state", lambda expiry=None: (state, {}))
    monkeypatch.setattr(run, "read_positions", lambda: [])
    monkeypatch.setattr(broker, "open_orders", lambda: [])
    monkeypatch.setattr(log, "rows", lambda *a: list(diary_rows))
    monkeypatch.setattr(log, "record", lambda agent, action, because, **kw: rows.append((agent, action, because)))
    monkeypatch.setattr(broker, "earnings_dates", earnings)
    put = PutQuote(symbol="INTC261030P00086000", underlying="INTC", strike=86.0, expiry=EXPIRY,
                   bid=1.28, ask=1.34, delta=-0.20, spot=95.5)
    monkeypatch.setattr(broker, "weekly_puts", lambda u, e: [put])
    monkeypatch.setattr(broker, "sell_put", lambda sym, px: sold.append((sym, px)) or "o-1")
    run.steward_session()
    return rows, sold


def test_the_session_sells_when_nothing_blocks(monkeypatch):
    rows, sold = _session(monkeypatch, lambda u: [date(2027, 1, 29)])
    assert sold == [("INTC261030P00086000", 1.31)] and rows[-1][1] == "sell_put"


def test_the_session_holds_through_a_report(monkeypatch):
    today = datetime.now(timezone.utc).date()
    expiry = today + timedelta(days=2)
    rows, sold = [], []
    monkeypatch.setattr(run, "UNIVERSE", ["INTC"])
    monkeypatch.setattr(run, "_entries_blocked", lambda agent: False)
    monkeypatch.setattr(run, "next_weekly_friday", lambda t=None: expiry)
    state = gates.AccountState(equity=90_000.0, day_start_equity=90_000.0,
                               sleeve_used={"steward": 0.0, "hunter": 0.0},
                               underlying_notional={}, minutes_to_expiry=3_000.0)
    monkeypatch.setattr(run, "desk_state", lambda expiry=None: (state, {}))
    monkeypatch.setattr(run, "read_positions", lambda: [])
    monkeypatch.setattr(broker, "open_orders", lambda: [])
    monkeypatch.setattr(log, "rows", lambda *a: [])
    monkeypatch.setattr(log, "record", lambda agent, action, because, **kw: rows.append((agent, action, because)))
    monkeypatch.setattr(broker, "earnings_dates", lambda u: [today + timedelta(days=1)])
    monkeypatch.setattr(broker, "weekly_puts", lambda u, e: (_ for _ in ()).throw(AssertionError("no chain is read")))
    monkeypatch.setattr(broker, "sell_put", lambda sym, px: sold.append(sym) or "o-1")
    run.steward_session()
    assert sold == [] and rows == [("steward", "hold", rows[0][2])] and "rule 10" in rows[0][2]


def test_an_unreadable_date_sells_nothing(monkeypatch):
    def boom(u):
        raise RuntimeError("Yahoo is away")
    rows, sold = _session(monkeypatch, boom)
    assert sold == [] and rows[-1][1] == "hold" and "not sold blind" in rows[-1][2]


def test_a_stop_this_expiry_closes_the_name_for_the_week(monkeypatch):
    stop = {"agent": "steward", "action": "stop", "symbol": "INTC261030P00089000", "ts": "2026-10-27T15:35:00+00:00"}
    rows, sold = _session(monkeypatch, lambda u: [], diary_rows=[stop])
    assert sold == [] and rows[-1][1] == "hold" and "rule 11" in rows[-1][2]


# rule 12: a stop is not placed on a price a put cannot have

def test_the_pfe_mark_is_not_believed_and_the_intc_one_is():
    assert not steward.believable_put_mark(strike=29.0, spot=30.0, mark=4.90)     # 29 Oct 2026
    assert steward.believable_put_mark(strike=86.0, spot=66.0, mark=17.95)        # 30 Oct 2026: a real loss
    assert steward.believable_put_mark(strike=29.0, spot=30.0, mark=0.16)         # an ordinary double


def _short_put(symbol, credit, mark):
    return {"symbol": symbol, "qty": -1.0, "market_value": -mark * 100, "cost_basis": -credit * 100,
            "unrealized_pl": 0.0, "asset_class": "us_option"}


def _sweep(monkeypatch, position, spot):
    rows, bought = [], []
    monkeypatch.setattr(broker, "open_orders", lambda: [])
    monkeypatch.setattr(run, "read_positions", lambda: [position])
    monkeypatch.setattr(log, "record", lambda agent, action, because, **kw: rows.append((agent, action, because)))
    monkeypatch.setattr(broker, "buy_to_close", lambda sym, px, qty=1: bought.append((sym, px, qty)) or "b-1")
    monkeypatch.setattr(broker, "spot_price", spot)
    run.sweep()
    return rows, bought


def test_sweep_places_no_stop_on_an_impossible_mark(monkeypatch):
    rows, bought = _sweep(monkeypatch, _short_put("PFE261030P00029000", 0.08, 4.90), lambda u: 30.0)
    assert bought == [] and rows[-1][1] == "hold" and "rule 12" in rows[-1][2]


def test_sweep_still_stops_a_real_loss(monkeypatch):
    rows, bought = _sweep(monkeypatch, _short_put("INTC261030P00086000", 1.31, 17.95), lambda u: 66.0)
    assert bought == [("INTC261030P00086000", 18.31, 1)] and rows[-1][1] == "stop"


def test_sweep_stops_as_before_when_the_share_price_cannot_be_read(monkeypatch):
    def boom(u):
        raise RuntimeError("no trade")
    rows, bought = _sweep(monkeypatch, _short_put("PFE261030P00029000", 0.08, 0.20), boom)
    assert len(bought) == 1 and rows[-1][1] == "stop"


def test_take_profit_never_asks_for_the_share_price(monkeypatch):
    def boom(u):
        raise AssertionError("not needed")
    rows, bought = _sweep(monkeypatch, _short_put("KO261030P00088000", 0.20, 0.05), boom)
    assert len(bought) == 1 and rows[-1][1] == "take_profit"


# the trial figure reads every page of orders

class _Paged:
    """A broker that returns closed orders newest first, 500 a call, honouring `until`."""
    def __init__(self, orders):
        self.orders, self.calls = sorted(orders, key=lambda o: o.submitted_at, reverse=True), 0

    def get_orders(self, req):
        self.calls += 1
        pool = [o for o in self.orders if req.until is None or o.submitted_at < req.until]
        return pool[:req.limit]

    def get_all_positions(self):
        return []


def test_pnl_since_reads_past_the_first_500_orders(monkeypatch):
    t0 = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)
    def order(i, side, px):
        return SimpleNamespace(id=f"o{i}", symbol="MU261023P00875000", side=side, filled_qty="1",
                               filled_avg_price=str(px), submitted_at=t0 + timedelta(minutes=i))
    # the oldest order is the buy; 600 later orders on another contract push it off the first page
    noise = [SimpleNamespace(id=f"n{i}", symbol="KO261023P00088000", side=OrderSide.SELL, filled_qty="1",
                             filled_avg_price="0.20", submitted_at=t0 + timedelta(minutes=10 + i)) for i in range(600)]
    fake = _Paged([order(0, OrderSide.BUY, 16.75), order(5, OrderSide.SELL, 20.00), *noise])
    monkeypatch.setattr(broker, "trading", lambda: fake)
    assert broker.pnl_since({"MU261023P00875000"}, "2026-09-30T00:00:00Z") == 325.0
    assert fake.calls == 2 and len(broker.closed_orders_since("2026-09-30T00:00:00Z")) == 602
