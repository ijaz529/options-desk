# Strategy specification

The contract for the week. Code implements this page; if the two diverge, this
page is amended first, then the code. (A habit imported from Alfred.)

## Capital plan — $100,000 paper

| Sleeve | Allocation | Instruments |
|---|---|---|
| Steward | $70,000 | Short cash-secured puts; defined-risk put spreads when IV is thin |
| Hunter | $20,000 | Long short-dated calls/puts (weeklies); spot BTC/ETH at weekends |
| Cash buffer | $10,000 | Never deployed; absorbs assignment and marks |

## The Steward — options income

**Universe (amended 28 Aug, after the first live session):** liquid, boring
large caps priced so ONE contract fits the risk gates — roughly \$80–190/share,
so a cash-secured put obliges \$8–19k against the \$20k-per-name cap. The
original mega-cap list (SPY, QQQ, AAPL…) was 90% untradeable at one-contract
size: the Risk Officer vetoed nine of ten names on sizing, which is the gates
working and the universe wrong. Weekly expiries only.

**Entry rule (deterministic):**
1. Rank universe by 30-day IV rank; take names with IV rank ≥ 40.
2. Sell the put at (or nearest below) the 20-delta strike, expiring the Friday
   of contest end (4 Sep) — the whole position is a bet the week is ordinary.
3. Premium collected must be ≥ 0.15% of strike notional or skip (commission-free,
   but a $6 credit is not worth a $20,000 obligation).
4. Max 1 position per underlying — where "position" counts WORKING ORDERS too,
   not just fills. The per-name ceiling is the Risk Officer's 20%-of-account
   concentration cap (~$20k).

**Exit rules:**
- Take profit at 65% of max premium (buy back).
- Stop: buy back if the option doubles against entry.
- Assignment is acceptable — the strikes are prices we'd own at. Assigned stock
  is sold with a covered call the next session (the wheel's second half).
- Everything is flat or defined-risk by the final Friday's close.

## The Hunter — convexity

**Cadence:** twice per session (post-open, pre-close) Claude reviews, via
Alpaca MCP tools plus a headline feed: unusual movers, fresh catalysts.

**Entry rule:** Claude proposes at most 2 trades per session in this exact,
machine-checkable shape — the Risk Officer rejects anything else:

```
{symbol, direction, thesis (≤280 chars), contract (weekly, ≤10 days out),
 max_premium_usd (≤ $2,000), invalidation (what kills the thesis)}
```

**Exit rules:** −50% premium stop; +100% take-half, run the rest with a
trailing stop; hard exit at expiry minus one session. Weekend crypto sleeve:
spot only, ≤ $5,000 total, 24/7 monitoring via CLI cron, ±4% stop/target.

## The Risk Officer — hard gates (not negotiable, not an LLM)

1. **No naked short options.** Every short put fully cash-secured; every spread
   defined-risk. (Also keeps us within paper option level semantics.)
2. **Sleeve caps are absolute** — an agent at its cap proposes nothing.
3. **Daily drawdown gate:** account down >2.5% on the day → no new risk that day.
4. **Weekly kill switch:** account below $96,000 → everything to flat, desk
   income-only for the remainder.
5. **Concentration:** ≤ 20% of account notional in any single underlying.
6. **Time gate:** no new positions in the final 3 hours of the contest; the
   final session is for de-risking into cash + marked P&L.
7. Every rejection is logged: what was proposed, which gate, in plain English.

## The decision log

Append-only JSONL + rendered markdown. One row per decision or veto:
timestamp, agent, action (or "no action"), instrument, size, price context,
and a plain-English `because`. This is the artefact the one-page write-up and
the judging video are built from.

## Known constraints (checked 26 Aug 2026)

- Alpaca options = US equities/ETFs only; **no crypto options** — crypto is
  spot, hence the Hunter's weekend sleeve is spot BTC/ETH.
- Paper accounts have options enabled by default; stop orders are single-leg
  only, so spread exits use limit orders managed by the desk itself.
- Contest account must be brand-new, starting balance exactly $100,000; the
  account ID ships with the submission and judges read the blotter directly.
