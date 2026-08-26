"""The desk's sessions — where the agents actually meet the market.

`python -m desk.run steward`  — the income round: pick, gate, place, log.
`python -m desk.run sweep`    — the exit round: apply the mechanical exits.
`python -m desk.run status`   — account, sleeves, positions, no side effects.

Sleeve accounting is derived from the broker's own positions every run (an OCC
symbol carries its underlying, expiry and strike), so there is no state file
to drift from the truth.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

from desk import broker, cli, gates, hunter, log, steward, weekend

# Liquid, boring, penny-wide — the Steward's whole world.
UNIVERSE = ["SPY", "QQQ", "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "META", "JPM", "XOM"]
CONTEST_END = datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc)  # 17:00 CEST Fri

OCC = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")


def read_positions() -> list[dict]:
    """Positions via the official Alpaca CLI when present (structured JSON,
    env auth — built for agent loops), the SDK as fallback. Same shape either
    way, so every consumer is door-agnostic."""
    if cli.available():
        try:
            return cli.positions()
        except Exception as e:
            log.record("desk", "note", f"CLI read failed ({str(e)[:80]}) — using the SDK door.")
    return broker.positions()


def parse_occ(symbol: str) -> tuple[str, date, str, float] | None:
    m = OCC.match(symbol)
    if not m:
        return None
    u, ymd, cp, strike = m.groups()
    return u, datetime.strptime(ymd, "%y%m%d").date(), cp, int(strike) / 1000


def desk_state() -> tuple[gates.AccountState, dict]:
    """AccountState for the Risk Officer, derived live from the broker."""
    acct = broker.account_state()
    pos = read_positions()
    sleeve = {"steward": 0.0, "hunter": 0.0}
    under: dict[str, float] = {}
    for p in pos:
        occ = parse_occ(p["symbol"])
        if occ:
            u, _, cp, strike = occ
            if p["qty"] < 0 and cp == "P":       # short put: the obligation is the risk
                notional = strike * 100 * abs(p["qty"])
                sleeve["steward"] += notional
            else:                                 # long options: premium is the risk
                notional = abs(p["market_value"])
                sleeve["hunter"] += notional
            under[u] = under.get(u, 0.0) + notional
        elif p["asset_class"] == "us_equity":     # assigned stock counts against its name
            under[p["symbol"]] = under.get(p["symbol"], 0.0) + abs(p["market_value"])
    minutes = (CONTEST_END - datetime.now(timezone.utc)).total_seconds() / 60
    return gates.AccountState(
        equity=acct["equity"],
        day_start_equity=acct.get("last_equity", acct["equity"]),
        sleeve_used=sleeve, underlying_notional=under,
        minutes_to_contest_end=minutes,
    ), acct


def next_contest_friday() -> date:
    return date(2026, 9, 4)


def steward_session() -> None:
    state, acct = desk_state()
    held_unders = {parse_occ(p["symbol"])[0] for p in read_positions() if parse_occ(p["symbol"])}
    expiry = next_contest_friday()
    for u in UNIVERSE:
        if u in held_unders:
            log.record("steward", "hold", f"Already carrying {u} risk — one position per name.")
            continue
        quotes = broker.weekly_puts(u, expiry)
        p = steward.pick(quotes)
        if p is None:
            log.record("steward", "hold",
                       f"No {u} put earns its keep today: nothing in the delta band paid "
                       "the premium floor with a market tight enough to trust.")
            continue
        proposal = gates.Proposal(agent="steward", symbol=u, kind="csp",
                                  notional=p.strike * 100)
        verdict = gates.review(proposal, state)
        if not verdict.approved:
            log.record("risk", "veto", verdict.because, gate=verdict.gate, symbol=u)
            continue
        order_id = broker.sell_put(p.symbol, p.mid)
        log.record("steward", "sell_put", steward.entry_because(p),
                   symbol=p.symbol, credit=p.mid, order_id=order_id)
        # refresh the sleeve picture so the NEXT name is judged against reality
        state, acct = desk_state()


def hunter_session() -> None:
    """Twice a session: Claude reads the tape (and researches it through Alpaca's
    MCP server when available), the desk trades what survives."""
    rows = hunter.tape()
    import shutil
    if shutil.which("uvx") and os.environ.get("ANTHROPIC_API_KEY"):
        from desk import mcp_bridge
        theses, rejected, trail = mcp_bridge.propose_via_mcp(rows)
        if trail:
            log.record("hunter", "research",
                       f"Worked the tape through Alpaca's MCP server: {len(trail)} read-only "
                       f"tool calls before concluding. Trail: {'; '.join(trail[:6])}")
    else:
        theses, rejected = hunter.propose(rows)
    for why in rejected:
        log.record("hunter", "veto", f"Proposal discarded before the gates: {why}")
    if not theses:
        log.record("hunter", "hold", "Claude read the tape and proposed nothing — "
                   "premium spent on a weak thesis is the only way this sleeve dies.")
        return
    state, _ = desk_state()
    for t in theses:
        picked = hunter.contract_for(t, next_contest_friday())
        if picked is None:
            log.record("hunter", "hold",
                       f"{t.symbol} thesis approved but no {t.direction} in the delta band "
                       "with a believable market — the idea dies at the chain, not at the desk.")
            continue
        q, qty = picked
        premium = qty * q.mid * 100
        verdict = gates.review(gates.Proposal(agent="hunter", symbol=t.symbol,
                                              kind="long_option", notional=premium), state)
        if not verdict.approved:
            log.record("risk", "veto", verdict.because, gate=verdict.gate, symbol=t.symbol)
            continue
        order_id = broker.buy_option(q.symbol, qty, q.mid)
        log.record("hunter", f"buy_{t.direction}",
                   f"{t.thesis} — {qty}× {q.symbol} at ~{q.mid:.2f} (${premium:,.0f} premium, "
                   f"the whole downside). Invalidation: {t.invalidation}",
                   symbol=q.symbol, qty=qty, premium=premium, order_id=order_id)
        state, _ = desk_state()


def weekend_session() -> None:
    """Saturday: the crypto sleeve decides. Long the mover or stay in cash."""
    held = {p["symbol"] for p in read_positions() if p["asset_class"] == "crypto"}
    if held:
        log.record("hunter", "hold", f"Weekend sleeve already deployed ({', '.join(sorted(held))}) "
                   "— one decision per weekend; the exits do the rest.")
        return
    state, _ = desk_state()
    for pair, notional, because in weekend.entries(weekend.momentum_24h()):
        if not pair:
            log.record("hunter", "hold", because)
            continue
        verdict = gates.review(gates.Proposal(agent="hunter", symbol=pair,
                                              kind="crypto_spot", notional=notional), state)
        if not verdict.approved:
            log.record("risk", "veto", verdict.because, gate=verdict.gate, symbol=pair)
            continue
        order_id = broker.crypto_notional(pair, "buy", notional)
        log.record("hunter", "buy_crypto", because, symbol=pair, notional=notional, order_id=order_id)


def derisk() -> None:
    """The final session is for de-risking: everything to flat, P&L marked.
    Refuses to run early — outside the last 26 hours it only says why."""
    state, _ = desk_state()
    if state.minutes_to_contest_end > 26 * 60:
        log.record("desk", "hold", "De-risk requested outside the final day — refused. "
                   f"{state.minutes_to_contest_end / 1440:.1f} days still to run.")
        return
    for p in read_positions():
        occ = parse_occ(p["symbol"])
        if occ:
            qty = int(abs(p["qty"]))
            per = abs(p["market_value"]) / (100 * max(qty, 1))
            if p["qty"] < 0:
                order_id = broker.buy_to_close(p["symbol"], round(per * 1.03, 2))
                log.record("steward", "close", "Contest end: buying back the short leg — flat is the trade.",
                           symbol=p["symbol"], order_id=order_id)
            else:
                order_id = broker.sell_option(p["symbol"], qty, round(per * 0.97, 2))
                log.record("hunter", "close", "Contest end: selling the long leg — flat is the trade.",
                           symbol=p["symbol"], order_id=order_id)
        elif p["asset_class"] == "crypto" and p["qty"] > 0:
            order_id = broker.crypto_notional(p["symbol"], "sell", abs(p["market_value"]))
            log.record("hunter", "close", "Contest end: weekend sleeve to cash.",
                       symbol=p["symbol"], order_id=order_id)


def sweep() -> None:
    """Mechanical exits, both sleeves; closing risk is always allowed."""
    for p in read_positions():
        if p["asset_class"] == "crypto" and p["qty"] > 0:
            fire = weekend.exit_action(entry_cost=abs(p["cost_basis"]), market_value=abs(p["market_value"]))
            if fire:
                kind, because = fire
                order_id = broker.crypto_notional(p["symbol"], "sell", abs(p["market_value"]))
                log.record("hunter", kind, because, symbol=p["symbol"], order_id=order_id)
            continue
        occ = parse_occ(p["symbol"])
        if not occ:
            continue
        if p["qty"] > 0:      # hunter long options
            qty = int(p["qty"])
            entry = abs(p["cost_basis"]) / (100 * qty)
            current = abs(p["market_value"]) / (100 * qty)
            fire = hunter.exit_action(entry=entry, current=current, qty=qty)
            if fire:
                kind, close_qty, because = fire
                order_id = broker.sell_option(p["symbol"], close_qty, round(current * 0.98, 2))
                log.record("hunter", kind, because, symbol=p["symbol"], qty=close_qty, order_id=order_id)
            continue
        u, _, cp, strike = occ
        if cp != "P":
            continue
        credit = abs(p["cost_basis"]) / (100 * abs(p["qty"]))
        current = abs(p["market_value"]) / (100 * abs(p["qty"]))
        fire = steward.exit_action(entry_credit=credit, current_mid=current)
        if fire:
            kind, because = fire
            order_id = broker.buy_to_close(p["symbol"], round(current * 1.02, 2))
            log.record("steward", kind, because, symbol=p["symbol"], order_id=order_id)


def status() -> None:
    state, acct = desk_state()
    print(f"equity ${state.equity:,.2f} · steward ${state.sleeve_used['steward']:,.0f} deployed "
          f"· hunter ${state.sleeve_used['hunter']:,.0f} · "
          f"{state.minutes_to_contest_end / 1440:.1f} days to contest end")
    for p in read_positions():
        print(f"  {p['symbol']:>22} qty {p['qty']:>10} mv ${p['market_value']:>10,.2f} "
              f"pl ${p['unrealized_pl']:>8,.2f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"steward": steward_session, "hunter": hunter_session, "sweep": sweep, "weekend": weekend_session, "derisk": derisk, "status": status}[cmd]()
