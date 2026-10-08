# Strategy specification

The contract for the week. Code implements this page; if the two diverge, this
page is amended first, then the code. (A habit imported from Alfred.)

**This page is the contract for Team 1, "The Wheelhouse"** (named 2 Oct 2026): the Steward,
the Hunter and the Risk Officer, sharing one account and one record. Other teams, each on
its own account, are researched in `docs/TEAMS.md`; none exists until its rules are written
here.

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

## Re-based 30 Sep 2026 — the Hunter's trial after the 20 Sep fixes

**Why.** The kill switch tripped around 16 Sep, and the Hunter's three fixes (min 3
DTE, hard exit before expiry, breakeven stop — "The Hunter's first fortnight") went
in on 20 Sep. He has not traded since, so the fixes are untested and the switch
now blocks the one question he still has to answer. The desk is paper; the price
of the answer is paper. A plain reset would be moving the goalposts after a loss,
so the reset comes with a budget of its own.

1. **Baseline re-based to $88,983** (equity on 29 Sep 2026, the last session before
   the trial). The account-wide switch stays at 96% of it, **~$85,424**: a hard
   floor for the whole desk still exists. **The drawdown before this date is not
   erased** — from $93,630 (13 Sep) to $88,983 is −5.0%, almost all of it the
   Hunter's, and it stays in the log and the write-up.
2. **The Hunter's trial budget: $2,000.** From **30 Sep 2026** his profit and loss
   is tracked on its own — every Hunter buy logged since then (options and the
   weekend crypto sleeve), priced from the broker's own fills plus the market
   value of anything still open. If it reaches **−$2,000**, the Hunter is locked
   out on his own, even while the account is above its floor. The Steward is
   unaffected.
3. **The verdict comes after 20 Hunter trades or 4 weeks (28 Oct 2026), whichever
   is first.** Net positive or close to flat, inside the budget: the fixes work
   and the budget becomes a permanent Hunter rule. Otherwise the Hunter is retired
   and the desk runs the Steward alone. The verdict is written here, dated.

Everything else — sleeve caps, drawdown gate, concentration, no naked shorts,
the diary — is unchanged.

## Amended 26 Sep 2026 — the Steward, read against its own contract

A read of the account, the diary and the code on 26 Sep 2026, thirteen days
into the open-ended run. Equity **$89,018**, $867 under the switch and drifting
up ~$50–80 a session; **$80,237 cash and one position: 100 KO shares**. The
risk machinery is doing exactly what this document says. The income engine is
not, and the gap is between these words and the code.

**What the diary showed.** Sell-puts went 8 → 5 → 3 → 2 → 0 a day over 21–25
Sep while take-profits kept firing: the Steward closes winners and finds no
replacements. Its stated reason, eight names in ten, is *"nothing in the delta
band paid the premium floor"* — twelve names chosen for one-contract sizing
are low-IV names, and at 20-delta they do not pay 0.15% a week in this tape.
Meanwhile the Hunter ran a full research pass twice a session and was vetoed
by the switch every time, and the KO 88 put sold on 24 Sep at −0.26 delta,
0.7% below spot, for 0.18% — a trade rule 2 as written excludes — was assigned.

**Fixed in code the same day, because the contract already said so:**

- *Rule 2.* The delta band's near edge was −0.28; "at or nearest below the
  20-delta strike" means at most −0.20. Now (−0.21, −0.12). The KO trade would
  not have been placed.
- *Assigned stock is visible.* Shares carry no option symbol, so one-position-
  per-name and the Steward sleeve could not see the 100 KO shares; a second KO
  put would have cleared concentration by $223. Both now count stock.
- *The Hunter asks the switch before reading the tape.* Same verdict, none of
  the research spend, one honest diary row.
- *The diary keeps the broker's whole refusal.* Fifty-one buying-power skips
  were logged with the message cut before "available:".

**Decided, dated, and still to build:**

- *Rule 1 (IV rank ≥ 40) is not implemented and never was.* The desk keeps no
  IV history, so it cannot be as written. It stays as intent, marked
  unimplemented above; rule 3's floor is the IV screen in practice. Building an
  IV history is a small table and a decision for later, not a silent gap.
- *Defined-risk put spreads are permitted under income-only.* The Steward's
  section has always said "spreads when IV is thin"; the kill-switch clause
  only allowed cash-secured puts. In exactly the current state — thin IV and
  income-only — the two rules together left the Steward no tool. A defined-risk
  spread is income and its loss is capped; the clause now admits it. **The
  spread leg is specified here and not yet built.** The Risk Officer's
  `no-naked-shorts` gate already requires every spread to be defined-risk.
- *The wheel's second half.* "Assigned stock is sold with a covered call the
  next session" has been in the exit rules since August and has no code. The
  KO shares are held, logged as such each session, and no put is sold on top;
  the covered call is the next piece of options code, alongside spreads.

**Not done: re-basing the switch.** The gap is two weeks of ordinary income with
$80k in cash. The warning in `gates.py` stands.

## The Hunter's first fortnight, read honestly (20 Sep 2026)

From the broker's fills, 1–18 Sep: **21 Hunter positions, 4 winners, 17
losers, realised −$11,109** — which is the account's whole drawdown to within
fees (equity −$11,140 from the $100,000 start). The Steward is flat. Three
rule changes follow, each above in the Hunter's section: contracts at least
three days out, the hard exit the spec always promised, and a breakeven stop
on the runner. None widens what the Hunter may do; all narrow where it loses.
What they do not fix is the win rate, which is Claude's tape-reading and is
outside a rule's reach — a 19% hit rate needs the winners to be five times the
losers, and they have been under two. That is the number to watch next.

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
1. Rank universe by 30-day IV rank; take names with IV rank ≥ 40. *(Not
   implemented — see "Amended 26 Sep 2026". The desk keeps no IV history; in
   practice rule 3's premium floor is the IV screen.)*
2. Sell the put at (or nearest below) the 20-delta strike, expiring the **coming
   Friday** (amended 13 Sep 2026; was the fixed contest Friday, 4 Sep) — the
   whole position is a bet that the week ahead is ordinary. *(Code matched to
   this wording on 26 Sep 2026 — the band had reached −0.28; see below.)*
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
{symbol, direction, thesis (≤280 chars), contract (weekly, 3–10 days out),
 max_premium_usd (≤ $2,000), invalidation (what kills the thesis)}
```

**The contract is the nearest Friday at least three days away (amended 20 Sep
2026; was always the coming Friday).** Monday and Tuesday buy this week's
expiry; Wednesday, Thursday and Friday buy next week's — 7 to 9 days out, still
inside the ten-day cap. The evidence is in the fills, not a preference: of 21
Hunter positions since 1 Sep, the 13 bought inside three days of expiry lost
$7,134 with three winners; a thesis with a stated invalidation needs room to be
right or wrong, and a one-day option has only room to decay. This also ends
Friday-morning entries into that day's expiry, which the three-hour time gate
alone permitted: on 18 Sep two were opened at the bell and one had lost 95% by
mid-afternoon.

**One position per name (added 15 Sep 2026).** The Hunter does not re-enter an
underlying it already carries, and a *working* order claims its name as much as
a fill does — the same rule the Steward has always run. The 90-minute cooldown
guards against a retried cron slot; it reads the diary, and on 14 Sep two
delayed sessions ran back to back before the first had committed its rows, so
the second bought the GS 975 put again. The broker's own book is the truth the
diary is not: a thesis on a name already held or working is a hold, logged.

**Exit rules (amended 20 Sep 2026):**
- −50% premium stop.
- +100% take-half, once. After it, the remainder's stop rises to **entry**: it
  rides for free, not for nothing. (Was written as "a trailing stop", which the
  code never had and a stateless desk cannot keep — the broker's book carries no
  high-water mark. A breakeven stop is what the words meant and what runs. On
  18 Sep three ORCL calls that had been banked-half at 4.05 rode to 0.14; a
  breakeven stop would have let them go at 1.62.)
- **Hard exit on the session before expiry, at that session's first sweep,
  whatever the P&L.** This line has been in the specification since the
  contest and was never implemented — the divergence this page exists to
  forbid. Without it, Thursday's book rode into Friday's decay: ORCL 4.05 →
  0.14, BA 3.15 → 0.92, roughly $3,180 given back against Thursday's marks.
- Weekend crypto sleeve: spot only, ≤ $5,000 total, 24/7 monitoring via CLI
  cron, ±4% stop/target.

## The Risk Officer — hard gates (not negotiable, not an LLM)

1. **No naked short options.** Every short put fully cash-secured; every spread
   defined-risk. (Also keeps us within paper option level semantics.)
2. **Sleeve caps are absolute** — an agent at its cap proposes nothing.
3. **Daily drawdown gate:** account down >2.5% on the day → no new risk that day.
4. **Weekly kill switch (clarified 29 Aug; re-based 13 Sep 2026):** account below
   **96% of the stated baseline** (see "Post-contest operation")
   → the desk goes **income-only**: the Hunter and the weekend crypto sleeve are
   shut for the remainder, while the Steward may keep selling cash-secured puts
   — and, from 26 Sep 2026, **defined-risk put spreads** (see "Amended 26 Sep")
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
9. **No opening order without a live session to fill in (added 29 Sep 2026).**
   An opening order — a Steward put or a Hunter entry — is placed only while the
   broker's own market clock says the market is open **and at least 60 minutes
   remain before the close**. Otherwise the round places nothing and logs why.
   Closing orders are never blocked. The clock is the broker's, not a table of
   UTC times, so daylight saving (the close moves to 21:00 UTC on 1 Nov) and
   market holidays are handled by the same rule. *Why:* rule 8 cleans up a stale
   order the morning after; it never stopped one being placed. On Mon 28 Sep
   GitHub delivered all five morning Steward slots about six hours late, the
   first at 20:13 UTC — after the close — and four puts were offered on a shut
   market at its last mids. One filled the next morning at a price nobody chose;
   three sat until the sweep cancelled them. The same thing happened on 31 Aug.
   A late slot should cost a retry, not a placement.

   *The log, amended the same day:* the Steward's entry row said "Sold the XOM
   put" at the moment of *placing* a day limit. A placement is an offer; only a
   fill is a sale. The row now says "Offered to sell … — counts once it fills".

## The decision log

Append-only JSONL + rendered markdown. One row per decision or veto:
timestamp, agent, action (or "no action"), instrument, size, price context,
and a plain-English `because`. This is the artefact the one-page write-up and
the judging video are built from.

**A failed read is a row too (added 2 Oct 2026).** If the Hunter cannot read the tape —
the model call fails, the API refuses (an empty credit balance did, 30 Sep–1 Oct: every
in-session Hunter run crashed and wrote nothing, so the diary read as if he had quietly
held) — the session writes `hunter / error` with the reason in plain words and places
nothing. A silent crash is the one thing the diary must never be.

## Known constraints (checked 26 Aug 2026)

- Alpaca options = US equities/ETFs only; **no crypto options** — crypto is
  spot, hence the Hunter's weekend sleeve is spot BTC/ETH.
- Paper accounts have options enabled by default; stop orders are single-leg
  only, so spread exits use limit orders managed by the desk itself.
- *(Historical, contest only)* the account had to be brand-new at exactly
  $100,000, and the account ID shipped with the submission for judges to read
  the blotter directly. The desk still trades that same paper account.

---

# Teams 2 and 3 (specified 2 Oct 2026 — research in `docs/TEAMS.md`)

Everything above this line is Team 1, the Wheelhouse. The two teams below are separate
desks: **each trades its own paper account, keeps its own diary, and answers to its own
gates.** Nothing they do touches the Wheelhouse's account or record.

## How teams are kept apart

1. **One account per team, checked before every session.** A team's session reads the
   account number from the broker and refuses to run unless it is the account written here.
   A missing or wrong key therefore stops the session; it can never trade another team's
   account.

   | Team | Paper account | Baseline |
   |---|---|---|
   | Wheelhouse | PA3G3BG7TIBD | $88,983 (re-based 30 Sep 2026) |
   | The Harbour (`collar`) | PA3SKVNYTFJK | $100,000 (untouched at assignment) |
   | The Tollgate (`condor`) | PA3G4NEQHCUC | $99,789 (cash at assignment, 5 Oct 2026) |

   The Tollgate's account was Alfred's SnapTrade paper account until 5 Oct 2026. Alfred's
   managers were sold out, the remainders closed, the connection archived on Alfred's side
   and the key pair regenerated, so nothing but this team can reach it.
2. **Keys** live in GitHub secrets, one pair per team, named for the team:
   `ALPACA_API_KEY_ID_WHEELHOUSE` / `ALPACA_API_SECRET_KEY_WHEELHOUSE`, and the same with
   `_HARBOUR` and `_TOLLGATE` (renamed 5 Oct 2026; the earlier unsuffixed, `_COLLAR` and
   `_CONDOR` names are still read until they are deleted). Paper keys only — the
   broker client is pinned to the paper host.
3. **Diaries:** `logs/collar/decisions.jsonl`, `logs/condor/decisions.jsonl`. Same rule as
   the Wheelhouse: one row per decision, refusal or failure, in plain English.
4. **Shared rules that bind every team:** rule 8 (no order outlives its session) and rule 9
   (no opening order without a live session — market open, at least 60 minutes to the
   close). Neither team uses a language model.

## Team 2 — The Harbour (hedged equity; code name `collar`)

**What it is.** The JPMorgan Hedged Equity structure, on SPY: own the index, buy a put a
little below the market, pay for it by selling a deeper put and a call above. Reset every
quarter; never adjusted in between.

**Holdings.** As many 100-share lots of **SPY** as 95% of account equity buys (one lot at
$100,000 with SPY near $770). The rest stays in cash. Lots are bought once, at inception,
and re-bought only if they were called away or put at an expiry.

**The collar, per lot, opened as one three-leg order:**
1. **Buy** the put at the listed strike nearest **5% below** spot.
2. **Sell** the put at the listed strike nearest **20% below** spot.
3. **Sell** the call, at a strike **above spot**, whose mid price is nearest the cost of
   legs 1 and 2 together — so the three legs cost roughly nothing. A tie goes to the higher
   strike.

All three expire on **the last trading day of the calendar quarter**. At inception the
collar is opened for whatever remains of the current quarter.

**Reset.** On the expiry day, in a live session: close the three expiring legs in one order
and open the next quarter's collar from that day's prices. If the close does not fill and a
leg is exercised or assigned over the weekend, the next session re-buys any missing shares
and opens the new collar — the diary says which happened.

**Never.** No adjustment, no early close, no rolling a leg because the market moved. The
structure is the discipline; a manager who "defends" a collar is running a different fund.

**Gates (the Harbour's own Risk Officer):** the call count never exceeds the share lots held
(covered); the short put is always paired with the long put above it, same expiry
(defined-risk); rule 9. **There is no equity kill switch**, deliberately: a hedged-equity
fund is expected to fall with the market for the first 5% and the collar *is* the risk
control. Stopping it at −4% would switch it off exactly when it starts working.

**What could go wrong:** it gives up everything above the call strike in a strong quarter;
it protects nothing in the first 5% of a fall and nothing beyond 20%; a slow grind that
resets the collar lower each quarter protects little.

## Team 3 — The Tollgate (range income, defined risk; code name `condor`)

**Universe.** SPY, QQQ, IWM. One condor per underlying at a time.

**Entry.** In any live session where an underlying has no open condor and no working
order: take the **standard monthly expiry (third Friday) that is 25–45 days away**, and sell
an iron condor as one four-leg order:
1. **Sell** the put nearest **20 delta**; **buy** the put at the listed strike nearest
   **4% of spot below it**.
2. **Sell** the call nearest **20 delta**; **buy** the call at the listed strike nearest
   **4% of spot above it**.

*Why 4% wings and not the index's 5-delta wings (amended before the first trade, 2 Oct
2026):* priced on the live 20 Nov chain, 5-delta wings were 70 points wide on SPY and 77 on
QQQ — a worst case near $7,000 a condor, past this team's 5% limit on a $100,000 account, so
only IWM would ever have traded. The gates were right and the structure was wrong for the
account's size — the same lesson as the Wheelhouse's first session. A 4% wing caps one
condor's worst case at about 4% of the ETF's price per share, which all three fit.

One contract per leg. Skip — and say why — if any leg has no quote or delta, if the net
credit at the mids is under **10% of the wider wing**, or if a gate refuses.

**Exits, checked every session, each as one four-leg closing order:**
- **Take profit** when the condor can be bought back for half the credit or less.
- **Stop** when buying it back costs twice the credit or more.
- **Time:** close at **7 days to expiry**, whatever the price — the last week is where a
  condor's risk concentrates.

Holding is a decision too (8 Oct 2026): a live session that leaves its open condors alone
writes one hold row naming each, how much of its credit is banked and the days left. Until
then a quiet session wrote nothing, and the diary looked as if the team had stopped.

**Gates (the Tollgate's own Risk Officer):** every short leg has its long wing further out,
same expiry (defined-risk); one condor's worst case (wider wing × 100 − credit) is at most
**5% of equity**; all open condors' worst cases together at most **15%**; below **92% of the
baseline** no new condor opens (closing is always allowed); rule 9.

**What could go wrong:** a strong trend either way runs through a short strike; three index
condors are one bet on calm, not three; wins are small and a full-width loss erases several
of them.

