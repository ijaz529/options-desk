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

## Reading order

- **[docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md)** — the whole desk in plain English, no options knowledge assumed
- **[docs/WRITEUP.md](docs/WRITEUP.md)** — the one-page submission summary, regenerated from the live system
- **[docs/STRATEGY.md](docs/STRATEGY.md)** — the exact rules the code implements
- **[logs/decisions.md](logs/decisions.md)** — every decision and every deliberate non-decision, as it happened

## Alpaca stack

- **Trading API** (paper) — all order flow, positions, account state.
- **MCP server** — the Hunter's research desk: Claude calls Alpaca's read-only MCP tools itself (positions, bars, option chains) before concluding; the trading tools on that server are never exposed to it.
- **CLI** — the heartbeat's read door: positions and account state come through the official `alpaca` CLI (structured JSON, env auth), SDK as fallback.
- **Market Data API** — equities, options chains, and crypto quotes.

Everything runs against the paper environment. No real money is involved anywhere.

## Licence

MIT.

## Runbook

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # then fill in the three keys
.venv/bin/python -m pytest    # 36 tests, no network needed

.venv/bin/python -m desk.run status     # account, sleeves, positions (read-only)
.venv/bin/python -m desk.run steward    # the income round: pick, gate, place, log
.venv/bin/python -m desk.run hunter     # Claude researches via MCP, desk trades survivors
.venv/bin/python -m desk.run sweep      # mechanical exits, both sleeves
.venv/bin/python -m desk.run weekend    # Saturday's crypto decision
.venv/bin/python -m desk.run derisk     # contest end: everything to flat (refuses to run early)
.venv/bin/python -m desk.writeup        # regenerate docs/WRITEUP.md from the live system
```

In contest week nobody runs these by hand: `.github/workflows/desk.yml` runs the
sessions on schedule and commits the decision log back to this repo after each one.
The audit trail you are reading was written by the desk itself.
