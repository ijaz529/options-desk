# The Options Desk

An autonomous AI trading desk for the [Alpaca AI Trading Agents Hackathon](https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon)
(28 Aug – 4 Sept 2026). Three agents share one $100,000 paper account, and every
decision — including every decision *not* to act — is written down in plain English.

## The desk

| Agent | Capital | Job |
|---|---|---|
| **The Steward** | ~70% | Options income: cash-secured puts and defined-risk spreads on liquid, quality names. Collects premium; the base that keeps the week green. |
| **The Hunter** | ~20% | Convexity: Claude reads the tape and the news, buys short-dated calls/puts on names with fresh catalysts. Small enough to survive being wrong; big enough to matter when right. Runs a spot-crypto sleeve at the weekend, when the options market sleeps. |
| **The Risk Officer** | veto | Not an LLM. Hard, deterministic gates: position sizing caps, max daily drawdown, no naked short options, forced de-risk into the close of the final day. Every veto is logged with its reason. |

## Why it's built this way

A one-week P&L contest rewards a barbell: reliable positive carry plus a bounded
bet on the right tail. The Steward's premium income is the carry; the Hunter is
the tail; the Risk Officer is what lets the two coexist in one account.

The plain-English decision log is not decoration. An agent that can explain
"I sold the 30 Sep 240 put for $1.85 because IV rank is 72 and the strike sits
below the 20-day range" is auditable, debuggable, and honest about its losers.

## Alpaca stack

- **Trading API** (paper) — all order flow, positions, account state.
- **MCP server** — the Hunter's research desk: Claude calls Alpaca's read-only MCP tools itself (positions, bars, option chains) before concluding; the trading tools on that server are never exposed to it.
- **CLI** — the heartbeat's read door: positions and account state come through the official `alpaca` CLI (structured JSON, env auth), SDK as fallback.
- **Market Data API** — equities, options chains, and crypto quotes.

Everything runs against the paper environment. No real money is involved anywhere.

## Licence

MIT.
