# The Options Desk — one page

*Generated 01 Sep 2026 20:09 UTC from the running system;
every number below is imported from the code it describes.*

## AI logic

Three agents share one $100,000 paper account. **The Steward** (~$70k) sells the
week's ordinariness: cash-secured puts at the ~20-delta strike on liquid
names, premium ≥ 0.15% of the obligation or no trade, take-profit at
65% of the credit, stop if it doubles. **The Hunter** (~$20k) is Claude
working through **Alpaca's MCP server**: it computes nothing — it *reads*, with
read-only tools it calls itself (positions, bars, option chains), then must
conclude in a strict schema: symbol from a fixed universe, thesis ≤ 280
characters and falsifiable, premium ≤ $2,000, invalidation stated. A
proposal that bends any rule is discarded whole. The desk — not Claude — turns
surviving theses into ~35-delta weekly contracts and sizes them. At
weekends a mechanical spot-crypto rule (≥ 1.5% 24h momentum, $2,500
sleeve, ±4% exits) keeps the book earning while options sleep.

## Risk gates (deterministic — not an LLM, on purpose)

1. No naked short options — every put cash-secured, every spread defined-risk.
2. Sleeve caps absolute: Steward $70,000, Hunter $20,000.
3. Daily drawdown gate: > 2.5% down on the day → no new risk today.
4. Kill switch: equity below $96,000 → flat, income-only thereafter.
5. Concentration: ≤ 20% of the account in any one underlying.
6. Time gate: no new positions in the final 3 hours; the last session de-risks.
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

124 logged decisions · 21 trades/exits · 70 deliberate holds ·
14 Risk Officer vetoes · by agent: {'risk': 14, 'steward': 83, 'desk': 17, 'hunter': 10}.
The full plain-English log: [`logs/decisions.md`](../logs/decisions.md).
New to options? [`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) explains the whole desk without jargon.
