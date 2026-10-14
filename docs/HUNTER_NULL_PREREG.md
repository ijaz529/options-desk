# Hunter null-arm comparison: pre-registration

Written 14 Oct 2026, about 12:20 UTC. At that point no option or stock price data had been fetched and no replay had run. I had read the desk's code and its decision log (logs/decisions.jsonl as on GitHub at 13 Oct 23:06 UTC). That log already shows the Hunter's buys, stops and take-halfs, so his outcome is partly known in advance. For that reason every arm, statistic and threshold below is fixed by rule and has no tunable parameter. None of them may be changed after the replay is seen.

Source idea: map-options-desk.md, "[1] Pre-register a null-arm comparison for the Hunter's verdict". Paper canon rules 1, 3, 13, 15 and 17.

## Question

Under the same timing, the same premium per ticket, the same contract rule and the same exits, can the Hunter's selection be told apart from mechanical selection? His selection means which name he picks and whether he buys a call or a put.

This does **not** test his timing (which sessions he trades in) or his sizing. Both are held fixed and shared by every arm.

## Held fixed: shared by every arm

- **Sessions.** Every Hunter session since 30 Sep 2026 that ended in at least one `buy_call` or `buy_put` row. The session timestamp is that buy row's `ts`, truncated to the minute. A session's tickets are the buy rows that share that `ts`.
- **Tickets and premium.** Each arm places exactly as many tickets per session as the Hunter did. Ticket j gets the premium of his j-th ticket in log order.
- **Contract rule.** The desk's own `hunter.target_expiry(today, next_weekly_friday(today))`, imported read-only, gives the expiry. For calls the chain is every listed contract of that expiry with strike in [1.00, 1.12] × spot; for puts, [0.88, 1.00] × spot. Spot is the last SIP 1-minute trade close at or before the timestamp.
  - A contract is usable when it printed (had a 1-minute trade bar) at or before the timestamp, on the same trading day, no more than 60 minutes earlier. Its price is that bar's close.
  - Delta is Black–Scholes with r = 4.5% and q = 0. Implied vol is backed out of that price, using the spot at the print's minute. T runs in calendar years to 20:00 UTC on the expiry date.
  - The pick is the usable contract with |delta| nearest 0.35, inside [0.25, 0.45]. Quantity is floor(premium / (price × 100)).
  - The live 25%-of-mid spread filter cannot be applied, because there are no historical option quotes. Print recency stands in for it.
  - No usable contract, or quantity < 1, makes the candidate ineligible. This mirrors "the idea dies at the chain".
- **Entry fill.** Price + c per share.
- **Exits.** The desk's own `hunter.exit_action` and `hunter.expiry_exit`, imported read-only.
  - Sweeps run on each trading day at 13:35 UTC, then at :03, :23 and :43 from 14:03 to 19:43 UTC.
  - At each sweep after entry, the mark is the contract's last 1-minute trade close at or before the sweep time, on the same day. With no print that day, nothing is evaluated.
  - On the session before expiry, the expiry exit sells everything at the first sweep that has a mark.
  - Otherwise exit_action runs with `took_half` carried per position. Any close fills at mark − c per share.
  - Triggers compare the mark with the entry print, not the cost-loaded fill, as the live desk compares its mark with its fill.
- **One position per name.** This applies within each arm's own book. A name is held from its entry until its last lot is closed.
- **Censoring.** A position still open at the cutoff is valued at its last print at or before the cutoff, minus c (liquidation value).
- **Costs.** c = $0.05 per share each side (primary); a rerun at c = $0.10. 100 shares per contract.
- **Sleeve gates and trial budget.** None are applied to the arms. They trade only when and as much as the Hunter did.

## Arms

| Arm | Selection per ticket |
|---|---|
| **H** (primary Hunter statistic) | His logged (symbol, call/put), with the contract re-derived by the replay's contract rule. If the rule finds no usable contract for his pick, his actual OCC contract is used and the fallback is flagged. |
| H-actual (descriptive) | His actual OCC contract and quantity from the buy row, through the same fill and exit engine. |
| H-fills (descriptive) | Realised P&L from broker fills plus the marks of open positions. This is what run.py's `hunter_trial_pnl` computes: closed orders since 2026-09-30 on PA3G3BG7TIBD, read-only GET. |
| **A** random | 1,000 draws, `numpy.random.default_rng(20260930)`; draws run in sequence from one generator. For each draw, sessions go in time order, then tickets in order: a symbol uniform over the 30 `hunter.CANDIDATES`, excluding names held in this draw's book or already taken this session, and a direction uniform over {call, put}. An ineligible draw is redrawn, up to 200 tries; after that the ticket is not placed. |
| **B** follow | The 30 names are ranked by \|day change\| at the timestamp. The tape is rebuilt the way hunter.tape() builds it: last IEX 1-minute trade close at or before the timestamp, against the previous trading day's IEX daily-bar close. Ticket j goes to the j-th name in rank order that is not held in B's book and has an eligible contract in the direction of the move: a call if the day change is > 0, otherwise a put. |
| **C** fade | The same ranking and skip rules, using C's own book, in the opposite direction: a put if the day change is > 0, otherwise a call. |

## Windows

- **Trial window (primary).** Sessions from 30 Sep 2026 to the verdict, which is the 20th trade or 28 Oct 2026. Every session is out of sample by construction.
  - **Preliminary read (this run):** sessions 30 Sep–13 Oct, cutoff 13 Oct 2026 20:00 UTC. This is a progress read only.
  - **Hold-out:** the remaining sessions, 14 Oct to the verdict. The final read reruns this exact script, unchanged, over the full trial window. Nothing in the preliminary read may change an arm, a rule, a parameter or the bar.
- **Secondary window (descriptive, no bar).** 1–18 Sep 2026 under the pre-fix rules: expiry = coming Friday, no 3-day minimum, no hard exit before expiry, no breakeven stop. It runs only if the data allow; it never enters the verdict.

## Metrics: every arm, at c = 0.05 and c = 0.10

- Total P&L in USD.
- Tickets placed.
- Win rate: tickets with P&L > 0.
- Stop rate: tickets with any `stop` exit.
- Max drawdown of a $20,000 sleeve, marked at every sweep.
- Per-day P&L, clustered by the market day of entry. The interval is a day-clustered bootstrap (10,000 resamples of entry days, seed 7) giving a 95% CI on the per-day mean.
- The Hunter's percentile within A: the share of A draws with total below H, ties counting half. A's median, 10th and 90th percentiles are also reported.
- Paired per-day differences H − B and H − C, with a day-clustered bootstrap 95% CI.
- Descriptive only, for the timing-luck floor (canon rule 17): H, B and C rerun with every entry shifted +15 minutes. Exit sweeps are unchanged.

## Pass bar (set in advance; tightened from the mapping, never loosened)

The Hunter shows **selection skill** only if all three hold, at **both** c = $0.05 and c = $0.10:
1. H's total P&L is above the 90th percentile of arm A's 1,000 totals;
2. H > B; and
3. H > C.

Otherwise the verdict must state: *"the Hunter's record cannot be told apart from random selection under the same exits."*

The bar is not read for a verdict on the preliminary read. A preliminary read is reported as such. The day-clustered CIs are reported, but cannot carry a skill claim. With roughly 7–15 entry days they are expected to span zero whatever the sign, and that is the honest reading.

## Known limits, stated before running

- There are no historical option quotes. Entries and exits are priced from trade prints with a flat c per share. Thin strikes (CAT, GS, UNH, LLY) may have stale prints, and the 60-minute recency rule handles this the same way for every arm.
- The Hunter's live fills were limit orders at mid that might not fill (the QCOM 177.5 put has no exit row). The replay assumes every placed ticket fills.
- Live exits fired off the broker's mark and sometimes outside the session. The replay fires at its fixed sweep schedule on prints, for every arm alike.
- IEX-only tape: B and C rankings can differ from what the Hunter saw when two moves are close. As a check, the reconstructed tape is compared with the numbers quoted in his theses.
