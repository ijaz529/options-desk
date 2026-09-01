"""The desk's one door to Alpaca — paper only, and loud about it.

Everything the agents know about the account comes through here, and every
order leaves through here (after the Risk Officer has spoken). The trading
host is hard-pinned to paper: this desk must be physically unable to touch a
live endpoint, keys or no keys.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import AssetStatus, ContractType, OrderSide, TimeInForce
from alpaca.trading.requests import (GetOptionContractsRequest, LimitOrderRequest,
                                     MarketOrderRequest)
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionSnapshotRequest, StockLatestTradeRequest

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

_KEY = os.environ.get("ALPACA_API_KEY_ID", "")
_SECRET = os.environ.get("ALPACA_API_SECRET_KEY", "")


def trading() -> TradingClient:
    # paper=True pins the host to paper-api.alpaca.markets — not configurable here
    return TradingClient(_KEY, _SECRET, paper=True)


@dataclass(frozen=True)
class PutQuote:
    """One candidate contract for the Steward, with everything the entry rule needs."""
    symbol: str            # OCC option symbol
    underlying: str
    strike: float
    expiry: date
    bid: float
    ask: float
    delta: float | None
    spot: float

    @property
    def mid(self) -> float:
        return round((self.bid + self.ask) / 2, 2)

    @property
    def premium_yield(self) -> float:
        """Credit as a fraction of the cash the put obliges — the entry floor."""
        return self.mid / self.strike if self.strike else 0.0


def spot_price(underlying: str) -> float:
    c = StockHistoricalDataClient(_KEY, _SECRET)
    t = c.get_stock_latest_trade(StockLatestTradeRequest(symbol_or_symbols=underlying))
    return float(t[underlying].price)


def option_chain(underlying: str, expiry: date, kind: str,
                 lo_frac: float, hi_frac: float) -> list[PutQuote]:
    """One expiry's chain (kind: "put"|"call") joined with live snapshots (greeks
    included), strikes bounded to [lo_frac, hi_frac] × spot."""
    spot = spot_price(underlying)
    contracts = trading().get_option_contracts(GetOptionContractsRequest(
        underlying_symbols=[underlying], status=AssetStatus.ACTIVE,
        expiration_date=expiry, type=ContractType.PUT if kind == "put" else ContractType.CALL,
        strike_price_gte=str(round(spot * lo_frac, 2)), strike_price_lte=str(round(spot * hi_frac, 2)),
        limit=250,
    )).option_contracts or []
    if not contracts:
        return []
    data = OptionHistoricalDataClient(_KEY, _SECRET)
    # the snapshot endpoint caps at 100 symbols per call — QQQ's dollar-strike
    # chain runs past that (111 on 28 Aug, the desk's first live session)
    symbols = [c.symbol for c in contracts]
    snaps: dict = {}
    for i in range(0, len(symbols), 100):
        snaps.update(data.get_option_snapshot(OptionSnapshotRequest(
            symbol_or_symbols=symbols[i:i + 100])))
    out: list[PutQuote] = []
    for c in contracts:
        s = snaps.get(c.symbol)
        q = getattr(s, "latest_quote", None)
        if not s or not q or q.bid_price is None or q.ask_price is None:
            continue
        greeks = getattr(s, "greeks", None)
        out.append(PutQuote(
            symbol=c.symbol, underlying=underlying,
            strike=float(c.strike_price), expiry=expiry,
            bid=float(q.bid_price), ask=float(q.ask_price),
            delta=float(greeks.delta) if greeks and greeks.delta is not None else None,
            spot=spot,
        ))
    return out


def weekly_puts(underlying: str, expiry: date) -> list[PutQuote]:
    """The Steward's slice: puts from 85% of spot up to the money."""
    return option_chain(underlying, expiry, "put", 0.85, 1.0)


def sell_put(occ_symbol: str, limit_price: float) -> str:
    """Cash-secured put: sell 1 contract at a limit. Returns the order id."""
    o = trading().submit_order(LimitOrderRequest(
        symbol=occ_symbol, qty=1, side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY, limit_price=limit_price))
    return str(o.id)


def buy_to_close(occ_symbol: str, limit_price: float) -> str:
    o = trading().submit_order(LimitOrderRequest(
        symbol=occ_symbol, qty=1, side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY, limit_price=limit_price))
    return str(o.id)


def buy_option(occ_symbol: str, qty: int, limit_price: float) -> str:
    """The Hunter's long options — always defined-risk (premium is the max loss)."""
    o = trading().submit_order(LimitOrderRequest(
        symbol=occ_symbol, qty=qty, side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY, limit_price=limit_price))
    return str(o.id)


def sell_option(occ_symbol: str, qty: int, limit_price: float) -> str:
    """Close (part of) a long option position at a limit."""
    o = trading().submit_order(LimitOrderRequest(
        symbol=occ_symbol, qty=qty, side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY, limit_price=limit_price))
    return str(o.id)


def crypto_notional(pair: str, side: str, notional: float) -> str:
    """The weekend sleeve: spot BTC/ETH by dollar notional (24/7, GTC)."""
    o = trading().submit_order(MarketOrderRequest(
        symbol=pair, notional=round(notional, 2),
        side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.GTC))
    return str(o.id)


def open_orders() -> list[dict]:
    """Working orders — obligations the account has promised but not yet booked."""
    from alpaca.trading.requests import GetOrdersRequest
    from alpaca.trading.enums import QueryOrderStatus
    out = trading().get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN, limit=100))
    return [{"id": str(o.id), "symbol": o.symbol, "side": str(o.side), "qty": float(o.qty or 0),
             "created_at": str(o.created_at)}
            for o in out]


def order_status(order_id: str) -> dict:
    o = trading().get_order_by_id(order_id)
    return {"id": str(o.id), "status": str(o.status), "symbol": o.symbol,
            "filled_qty": float(o.filled_qty or 0),
            "filled_avg_price": float(o.filled_avg_price) if o.filled_avg_price else None}


def cancel_order(order_id: str) -> None:
    trading().cancel_order_by_id(order_id)


def account_state() -> dict:
    a = trading().get_account()
    return {"equity": float(a.equity), "cash": float(a.cash),
            "buying_power": float(a.buying_power), "options_level": a.options_trading_level}


def positions() -> list[dict]:
    return [{"symbol": p.symbol, "qty": float(p.qty), "market_value": float(p.market_value or 0),
             "cost_basis": float(p.cost_basis or 0), "unrealized_pl": float(p.unrealized_pl or 0),
             "asset_class": str(p.asset_class)}
            for p in trading().get_all_positions()]
