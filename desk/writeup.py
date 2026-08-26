"""The one-page write-up, generated from the code that is being written up.

`python -m desk.writeup` renders docs/WRITEUP.md (the submission's required
page: AI logic, risk gates, Alpaca infrastructure) and refreshes
logs/decisions.md. Numbers and gate values are imported from the live modules
— the page cannot drift from the desk, because it is the desk, printed.
"""
from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, timezone

from desk import gates, hunter, log, steward, weekend

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "WRITEUP.md")


def render() -> str:
    rows = log.rows()
    by_agent = Counter(r["agent"] for r in rows)
    vetoes = [r for r in rows if r["action"] == "veto"]
    holds = sum(1 for r in rows if r["action"] == "hold")
    trades = sum(1 for r in rows if r["action"].startswith(("sell_put", "buy_", "take", "stop", "close")))
    return f"""# The Options Desk — one page

*Generated {datetime.now(timezone.utc):%d %b %Y %H:%M} UTC from the running system;
every number below is imported from the code it describes.*

## AI logic

Three agents share one $100,000 paper account. **The Steward** (~$70k) sells the
week's ordinariness: cash-secured puts at the ~{abs(steward.TARGET_DELTA):.0%}-delta strike on liquid
names, premium ≥ {steward.MIN_PREMIUM_YIELD:.2%} of the obligation or no trade, take-profit at
{steward.TAKE_PROFIT_FRAC:.0%} of the credit, stop if it doubles. **The Hunter** (~$20k) is Claude
working through **Alpaca's MCP server**: it computes nothing — it *reads*, with
read-only tools it calls itself (positions, bars, option chains), then must
conclude in a strict schema: symbol from a fixed universe, thesis ≤ {hunter.THESIS_MAX_CHARS}
characters and falsifiable, premium ≤ ${hunter.MAX_PREMIUM_USD:,.0f}, invalidation stated. A
proposal that bends any rule is discarded whole. The desk — not Claude — turns
surviving theses into ~{hunter.TARGET_DELTA_ABS:.0%}-delta weekly contracts and sizes them. At
weekends a mechanical spot-crypto rule (≥ {weekend.ENTRY_THRESHOLD:.1%} 24h momentum, ${weekend.SLEEVE_TOTAL:,.0f}
sleeve, ±{weekend.STOP_FRAC:.0%} exits) keeps the book earning while options sleep.

## Risk gates (deterministic — not an LLM, on purpose)

1. No naked short options — every put cash-secured, every spread defined-risk.
2. Sleeve caps absolute: Steward ${gates.SLEEVE_CAP['steward']:,.0f}, Hunter ${gates.SLEEVE_CAP['hunter']:,.0f}.
3. Daily drawdown gate: > {gates.DAILY_DRAWDOWN_GATE:.1%} down on the day → no new risk today.
4. Kill switch: equity below ${gates.KILL_SWITCH_EQUITY:,.0f} → flat, income-only thereafter.
5. Concentration: ≤ {gates.CONCENTRATION_CAP:.0%} of the account in any one underlying.
6. Time gate: no new positions in the final {gates.FINAL_QUIET_MINUTES / 60:.0f} hours; the last session de-risks.
7. Closing risk is always allowed. Every verdict — approve or veto — is logged
   with a plain-English reason.

## Alpaca infrastructure

**Trading API** (paper, hard-pinned) for all order flow · **MCP server**
(official, stdio) as the Hunter's research desk, `get_*` tools only ·
**CLI** (official Go binary) as the heartbeat's read door — positions and
account state as structured JSON with env auth · **Market Data API** for
equities/options/crypto, IEX + overnight feeds. Sessions run on a GitHub
Actions schedule; each run commits the decision log back to the repo, so the
audit trail builds itself in public.

## The record so far

{len(rows)} logged decisions · {trades} trades/exits · {holds} deliberate holds ·
{len(vetoes)} Risk Officer vetoes · by agent: {dict(by_agent)}.
The full plain-English log: [`logs/decisions.md`](../logs/decisions.md).
"""


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render())
    md = os.path.join(log.LOG_DIR, "decisions.md")
    os.makedirs(log.LOG_DIR, exist_ok=True)
    with open(md, "w", encoding="utf-8") as f:
        f.write(log.render())
    print(f"wrote {OUT} and {md}")


if __name__ == "__main__":
    main()
