"""Sessions for Team 2 (the Collar) and Team 3 (the Condor) — STRATEGY.md "Teams 2 and 3".

Each session is idempotent and reads its state from the broker's own positions and working
orders, like the Wheelhouse's: a slot that fires twice does nothing the second time.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from desk import broker, collar, condor, gates, log, team

_OCC = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")


def occ(symbol: str | None) -> tuple[str, date, str, float] | None:
    m = _OCC.match(symbol or "")
    if not m:
        return None
    u, ymd, cp, k = m.groups()
    return u, datetime.strptime(ymd, "%y%m%d").date(), cp, int(k) / 1000.0


def _order_symbols(o: dict) -> list[str]:
    return [s for s in [o.get("symbol"), *o.get("legs", [])] if s]


def _clear_stale_orders(agent: str, today: date) -> list[dict]:
    """Rule 8: cancel anything left from an earlier day. Returns today's working orders."""
    working = []
    for o in broker.open_orders():
        if datetime.fromisoformat(o["created_at"]).date() < today:
            broker.cancel_order(o["id"])
            log.record(agent, "cancel", "Cancelled an order left over from an earlier session: "
                       "its limit was priced off a market that no longer exists (rule 8). "
                       "This session re-prices from live quotes.", symbols=_order_symbols(o))
        else:
            working.append(o)
    return working


def _per_share(p: dict) -> float:
    """A position's current value per share of the underlying (always positive)."""
    return abs(p["market_value"]) / (100 * max(abs(p["qty"]), 1))


# ---------------------------------------------------------------- Team 2: the Collar

def collar_session() -> None:
    today = datetime.now(timezone.utc).date()
    working = _clear_stale_orders("collar", today)
    is_open, minutes_to_close = broker.market_clock()
    closed = gates.session_open_for_entries(is_open, minutes_to_close)
    if closed:
        log.record("collar", "hold", closed)
        return
    if working:
        log.record("collar", "hold", "An order from earlier today is still working — "
                   "waiting for it to fill or lapse before doing anything else.")
        return

    positions = broker.positions()
    shares = sum(p["qty"] for p in positions if p["symbol"] == collar.UNDERLYING)
    legs = [(p, occ(p["symbol"])) for p in positions if occ(p["symbol"])]
    legs = [(p, o) for p, o in legs if o[0] == collar.UNDERLYING]
    acct = broker.account_state()
    bid, ask = broker.stock_quote(collar.UNDERLYING)
    spot = round((bid + ask) / 2, 2)

    # 1. the shares — bought at inception, re-bought only if an expiry took them
    if shares < 100:
        if legs:
            log.record("collar", "note", "Option legs are open but no share lot is held — "
                       "this needs a human look before anything is placed.")
            return
        n = collar.lots(acct["equity"], ask)
        if n < 1:
            log.record("collar", "hold", f"One lot of {collar.UNDERLYING} costs ${ask * 100:,.0f}, more "
                       f"than {collar.EQUITY_FRACTION:.0%} of the ${acct['equity']:,.0f} account. Nothing bought.")
            return
        order_id = broker.buy_shares(collar.UNDERLYING, n * 100, ask)
        log.record("collar", "buy_shares",
                   f"Offered to buy {n * 100} {collar.UNDERLYING} at {ask:.2f} (${n * 100 * ask:,.0f}, "
                   f"{n * 100 * ask / acct['equity']:.0%} of the account) — the holding the collar "
                   "protects. The collar itself goes on next session, once the shares are in.",
                   symbol=collar.UNDERLYING, qty=n * 100, order_id=order_id)
        return
    share_lots = int(shares // 100)

    # 2. a collar already in place: never adjusted — except on its expiry day, when it is closed
    if legs:
        expiry = legs[0][1][1]
        if len(legs) != 3 or any(o[1] != expiry for _, o in legs):
            log.record("collar", "note", f"Expected three legs on one expiry, found {len(legs)} — "
                       "left alone for a human look.")
            return
        if expiry > today:
            log.record("collar", "hold", f"The collar is in place until {expiry:%d %b}. It is never "
                       "adjusted in between — that is the rule, whatever the market does.")
            return
        # expiry day: close all three in one order; the next slot opens the next quarter's
        net = sum(_per_share(p) * (1 if p["qty"] < 0 else -1) for p, _ in legs)   # debit if positive
        order = [(p["symbol"], "buy" if p["qty"] < 0 else "sell",
                  "buy_to_close" if p["qty"] < 0 else "sell_to_close") for p, _ in legs]
        order_id = broker.mleg(order, round(net + 0.05, 2), qty=share_lots)
        log.record("collar", "reset_close",
                   f"Quarter end: closing the expiring collar in one order at a net {net:+.2f} a "
                   "share. The next session opens the new quarter's collar from today's prices.",
                   symbols=[p["symbol"] for p, _ in legs], order_id=order_id)
        return

    # 3. shares held, no collar: open one to the quarter's end
    expiry = collar.quarter_expiry(broker.expiries(collar.UNDERLYING, today, today + timedelta(days=200)), today)
    if expiry is None:
        log.record("collar", "hold", "No quarter-end expiry is listed yet — nothing placed.")
        return
    puts = broker.option_chain(collar.UNDERLYING, expiry, "put", 0.75, 1.0)
    calls = broker.option_chain(collar.UNDERLYING, expiry, "call", 1.0, 1.20)
    c, why = collar.pick(puts, calls, spot)
    if c is None:
        log.record("collar", "hold", f"No collar today: {why}.")
        return
    problem = collar.structure_problem(share_lots, c)
    if problem:
        log.record("risk", "veto", f"Vetoed: {problem}.", gate="collar-structure")
        return
    order_id = broker.mleg([(c.long_put.symbol, "buy", "buy_to_open"),
                            (c.short_put.symbol, "sell", "sell_to_open"),
                            (c.short_call.symbol, "sell", "sell_to_open")], c.net, qty=share_lots)
    log.record("collar", "open_collar", collar.because(c, share_lots, spot),
               symbols=[c.long_put.symbol, c.short_put.symbol, c.short_call.symbol],
               net=c.net, expiry=expiry.isoformat(), order_id=order_id)


# ---------------------------------------------------------------- Team 3: the Condor

def _groups(positions: list[dict]) -> dict[tuple[str, date], list[tuple[dict, tuple]]]:
    out: dict = {}
    for p in positions:
        o = occ(p["symbol"])
        if o and o[0] in condor.UNIVERSE:
            out.setdefault((o[0], o[1]), []).append((p, o))
    return out


def _group_numbers(legs: list[tuple[dict, tuple]]) -> tuple[float, float, float]:
    """(credit, cost_to_close, max_loss $) for an open four-leg condor, from the broker's book."""
    credit = sum(abs(p["cost_basis"]) / (100 * abs(p["qty"])) * (1 if p["qty"] < 0 else -1) for p, _ in legs)
    cost = sum(_per_share(p) * (1 if p["qty"] < 0 else -1) for p, _ in legs)
    puts = sorted(o[3] for p, o in legs if o[2] == "P")
    calls = sorted(o[3] for p, o in legs if o[2] == "C")
    wing = max(puts[-1] - puts[0], calls[-1] - calls[0]) if len(puts) == 2 and len(calls) == 2 else 0.0
    return round(credit, 2), round(cost, 2), round((wing - credit) * 100, 2)


def condor_session() -> None:
    today = datetime.now(timezone.utc).date()
    working = _clear_stale_orders("condor", today)
    is_open, minutes_to_close = broker.market_clock()
    if not is_open:
        log.record("condor", "hold", "The market is closed — nothing is priced, so nothing is "
                   "opened or closed this round.")
        return
    busy = {o_[0] for o in working for s in _order_symbols(o) if (o_ := occ(s))}
    positions = broker.positions()
    groups = _groups(positions)
    open_max_loss = 0.0

    # exits first — closing risk is always allowed
    for (u, expiry), legs in groups.items():
        if len(legs) != 4:
            log.record("condor", "note", f"{u} {expiry:%d %b}: expected four legs, found {len(legs)} — "
                       "left alone for a human look.")
            continue
        credit, cost, max_loss = _group_numbers(legs)
        open_max_loss += max_loss
        if u in busy:
            continue
        fire = condor.exit_action(credit, cost, (expiry - today).days)
        if fire:
            kind, because = fire
            order = [(p["symbol"], "buy" if p["qty"] < 0 else "sell",
                      "buy_to_close" if p["qty"] < 0 else "sell_to_close") for p, _ in legs]
            order_id = broker.mleg(order, round(cost * 1.05, 2))
            log.record("condor", kind, f"{u} {expiry:%d %b}: {because}",
                       symbols=[p["symbol"] for p, _ in legs], order_id=order_id)

    # entries — rule 9, then one condor per underlying
    blocked = gates.session_open_for_entries(is_open, minutes_to_close)
    held = {u for (u, _e) in groups}
    acct = broker.account_state()
    baseline = team.config()["baseline"] or acct["equity"]
    for u in condor.UNIVERSE:
        if u in held or u in busy:
            continue
        if blocked:
            log.record("condor", "hold", blocked)
            return
        expiry = condor.monthly_expiry(broker.expiries(u, today + timedelta(days=condor.DTE_MIN - 2),
                                                       today + timedelta(days=condor.DTE_MAX + 2)), today)
        if expiry is None:
            log.record("condor", "hold", f"No {u} condor today: no standard monthly expiry is "
                       f"{condor.DTE_MIN}–{condor.DTE_MAX} days away.")
            continue
        c, why = condor.pick(broker.option_chain(u, expiry, "put", 0.75, 1.0),
                             broker.option_chain(u, expiry, "call", 1.0, 1.25))
        if c is None:
            log.record("condor", "hold", f"No {u} condor today: {why}.")
            continue
        problem = condor.risk_problem(c, acct["equity"], baseline, open_max_loss)
        if problem:
            log.record("risk", "veto", f"Vetoed the {u} condor: {problem}.", gate="condor-risk", symbol=u)
            continue
        order_id = broker.mleg([(c.long_put.symbol, "buy", "buy_to_open"),
                                (c.short_put.symbol, "sell", "sell_to_open"),
                                (c.short_call.symbol, "sell", "sell_to_open"),
                                (c.long_call.symbol, "buy", "buy_to_open")], -c.credit)
        log.record("condor", "open_condor", condor.because(c, c.short_put.spot),
                   symbols=[q.symbol for q in c.legs], credit=c.credit, max_loss=c.max_loss,
                   expiry=expiry.isoformat(), order_id=order_id)
        open_max_loss += c.max_loss
