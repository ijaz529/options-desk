"""The desk's sessions — where the agents actually meet the market.

`python -m desk.run steward`  — the income round: pick, gate, place, log.
`python -m desk.run sweep`    — the exit round: apply the mechanical exits.
`python -m desk.run status`   — account, sleeves, positions, no side effects.

Sleeve accounting is derived from the broker's own positions every run (an OCC
symbol carries its underlying, expiry and strike), so there is no state file
to drift from the truth.
"""
from __future__ import annotations

import re
import sys
from datetime import date, datetime, timedelta, timezone

from desk import broker, gates, log, steward

# Liquid, boring, penny-wide — the Steward's whole world.
UNIVERSE = ["SPY", "QQQ", "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "META", "JPM", "XOM"]
CONTEST_END = datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc)  # 17:00 CEST Fri

OCC = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")


def parse_occ(symbol: str) -> tuple[str, date, str, float] | None:
    m = OCC.match(symbol)
    if not m:
        return None
    u, ymd, cp, strike = m.groups()
    return u, datetime.strptime(ymd, "%y%m%d").date(), cp, int(strike) / 1000


def desk_state() -> tuple[gates.AccountState, dict]:
    """AccountState for the Risk Officer, derived live from the broker."""
    acct = broker.account_state()
    pos = broker.positions()
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
    held_unders = {parse_occ(p["symbol"])[0] for p in broker.positions() if parse_occ(p["symbol"])}
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


def sweep() -> None:
    """Mechanical exits on every open short put; always allowed by the gates."""
    for p in broker.positions():
        occ = parse_occ(p["symbol"])
        if not occ or p["qty"] >= 0:
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
    for p in broker.positions():
        print(f"  {p['symbol']:>22} qty {p['qty']:>10} mv ${p['market_value']:>10,.2f} "
              f"pl ${p['unrealized_pl']:>8,.2f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"steward": steward_session, "sweep": sweep, "status": status}[cmd]()
