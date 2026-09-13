# Strategy specification

The contract for the week. Code implements this page; if the two diverge, this
page is amended first, then the code. (A habit imported from Alfred.)

## Post-contest operation (amended 13 Sep 2026)

The hackathon ended Fri 4 Sep 2026 at 15:00 UTC with the account at **$93,630**
(−6.4% on the $100,000 start). The desk kept running on its schedule afterwards
and **traded nothing for nine days**, which was the contest scaffolding doing
exactly what it was written to do rather than a fault:

- `CONTEST_END` was a fixed date now in the past, so `minutes_to_contest_end`
  went negative and the **time gate vetoed every new position** as though the
  desk were permanently inside the last three hours.
- The steward also targeted the 4 Sep expiry — a date that no longer exists.
- The **kill switch was a fixed $96,000**, i.e. 4% below the contest's starting
  equity. At $93,630 it was tripped permanently, so the Hunter and the weekend
  sleeve were shut for good and only the Steward could ever have traded.

The desk now runs as an **open-ended paper desk** on the same account, under the
same strategy, so its behaviour can be watched over weeks rather than one week:

1. **No contest clock.** The Steward and Hunter target the **coming weekly
   Friday expiry**, rolling. The time gate is re-expressed against that expiry:
   no new position inside the final **3 hours before the expiry it would trade
   into** — a weekly opened three hours before it expires is a coin toss, which
   was the gate's real purpose.
2. **The kill switch is a fraction, not a figure.** It is **96% of a stated
   baseline**, preserving the original 4% meaning. The baseline is reset to the
   equity at the start of each monitoring period and is written in the code with
   its date; on 13 Sep 2026 it is **$93,630**, so the switch sits at ~$89,885.
   Resetting the baseline is an explicit, dated decision — never silent — because
   it forgives prior losses and must be visible when reading the record.
3. **De-risk is manual only.** It was scheduled for the contest's final session;
   with no final session it runs only on `workflow_dispatch`.

Everything else — sleeve caps, drawdown gate, concentration, no naked shorts,
the diary — is unchanged.

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
2. Sell the put at (or nearest below) the 20-delta strike, expiring the **coming
   Friday** (amended 13 Sep 2026; was the fixed contest Friday, 4 Sep) — the
   whole position is a bet that the week ahead is ordinary.
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
- Everything is flat or defined-risk by each Friday's close.

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
4. **Weekly kill switch (clarified 29 Aug; re-based 13 Sep 2026):** account below
   **96% of the stated baseline** (see "Post-contest operation")
   → the desk goes **income-only**: the Hunter and the weekend crypto sleeve are
   shut for the remainder, while the Steward may keep selling cash-secured puts
   — the defined-outcome income that earns the account back. The first
   implementation blocked EVERY opening trade, which contradicted this clause
   and would have frozen the desk entirely on one bad Tuesday; the code now
   matches the words. Existing risk still sweeps normally (closing is always
   allowed) and the drawdown/concentration/sleeve gates still bind the Steward.
5. **Concentration:** ≤ 20% of account notional in any single underlying.
6. **Time gate (re-expressed 13 Sep 2026):** no new positions in the final 3
   hours before the expiry they would trade into. De-risking into cash + marked
   P&L is now a manual session rather than a scheduled final one.
7. Every rejection is logged: what was proposed, which gate, in plain English.
8. **No order outlives its session (added 1 Sep).** A working order still open
   from a previous day was priced off a session that no longer exists; a stale
   limit only fills when the market has moved against it. The first sweep of
   each day cancels overnight orders and lets the next session re-price from a
   live chain. (Observed 31 Aug: a late-delivered steward run placed five puts
   at 20:00 UTC — the closing bell — which queued overnight at Monday's mids.)

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
- *(Historical, contest only)* the account had to be brand-new at exactly
  $100,000, and the account ID shipped with the submission for judges to read
  the blotter directly. The desk still trades that same paper account.
