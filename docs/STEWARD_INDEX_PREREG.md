# The Steward on index funds: pre-registration

Written 12 Nov 2026, about 11:45 UTC. The option history this test reads was being downloaded
when this was written (`research/weekend/fetch.py`, started 11:10 UTC) and none of it had been
opened. Everything below is fixed before it is.

## Why

Six weeks of the Steward's own fills (STRATEGY.md, "Amended 12 Nov 2026"): 70 short puts, 38
winners, −$2,808. The average winner kept $29 and the average loser cost $122. Rules 10 to 12
answer the three faults that had a name. What they do not answer is whether twelve single
shares, one contract each, are the right thing to sell puts on at all. The owner asked for that
to change (12 Nov 2026); the review goals say a change of this kind is made by a test written
down first. This is that test.

## What is already known, and so cannot count as evidence

- The replay of 10 Oct 2026 (`research/weekend`, "Tested 10 Oct 2026") gave, as a by-product,
  the Steward's rules on his twelve names at about −0.5% of the cash secured over 136 weeks, and
  the same rules on SPY cash-secured at +6.7%. Both figures were seen.
- A cash-secured put on SPY, QQQ or IWM does not fit his gates: one contract obliges $28,000 to
  $76,000 against a $20,000 limit per name. So "index funds" can only mean **put spreads** on
  them, which the desk already knows how to place (STRATEGY.md, "Built 10 Oct 2026"). A put
  spread on an index was **not** replayed on 10 Oct. That is the fresh question.
- The Tollgate sells monthly iron condors on the same three funds. A weekly put spread is half
  of that structure on a shorter clock. If this passes, the two teams hold related risk, and
  that is said in the result.

## The arms

Every arm trades the same weeks: each weekly expiry from 22 Mar 2024 to 6 Nov 2026 for which
its own series has prices. Entry is on the first trading day of the expiry week at the ~10:00
mark (the close of the 9:30 to 10:00 bar), for that week's expiry. One trade per name per week.

| Arm | What it sells | Size |
|---|---|---|
| **N** (as he was) | A cash-secured put on each of XOM CVX KO WMT BAC DIS UBER PFE CSCO INTC T GM: delta −0.21 to −0.12 nearest −0.20, premium at least 0.15% of the strike | one contract |
| **N10** (as he is from 12 Nov) | Arm N without any name-week that holds an earnings date (Yahoo's history, through yfinance). If Yahoo gives no history for a name, the arm is not run and the result says so | one contract |
| **X** (the candidate) | A put spread on each of SPY, QQQ, IWM: sell the put in the same delta band nearest −0.20, buy the put below it nearest −0.10, credit at least 10% of the width | as many spreads as keep the worst case (width less credit) at or under **$5,000 a fund**, at least one |

Rule 11 cannot bind here (one entry per name per week). Rule 12 is a check on a broker's mark
and has no meaning on trade prints.

**Exits, all arms, as the desk's:** buy back when 65% of the credit is banked, or when the
price has doubled against the credit; otherwise held to expiry and settled against the
fund's or share's close. Checked on each hourly close after entry. For a spread the price is
short leg less long leg, and an hour counts only when the short leg has at least two trades and
the long leg at least one.

**Costs.** A cent a share on every fill, each leg (primary). A rerun at three cents.

**Prices** are trade prints from hourly bars on trading days only, not quotes. Black–Scholes
deltas, r 4.5%, dividend yield 1.2% for SPY, 0.6% QQQ, 1.2% IWM, 0 for the names.

## What is measured

The weekly dollar result of each arm as one book, against his **$70,000 sleeve**: total, a
year, per cent of the sleeve a year, weeks won, the worst week, the deepest fall of the running
total, and the same for each half of the window (split at the middle expiry).

## The bar

Arm X **passes** only if all six hold:

1. X is above zero after costs over the whole window and in each half.
2. X earns at least **1.5% of the sleeve a year ($1,050)** more than arm N10 (or N, if N10
   cannot be run).
3. X's deepest fall is no deeper than that arm's.
4. Lines 1 and 2 still hold at three cents a share.
5. At least two of the three funds are above zero on their own.
6. X is above zero in the weeks from 6 Oct to 6 Nov 2026 taken alone, or loses less there than
   the names did. A structure for a put seller is judged in the fall, not only in the rise.

## What follows

- **Pass:** the Steward's universe and structure are amended in STRATEGY.md, dated, the spread's
  size rule ($5,000 a fund) written as a rule, the code built with tests, and his 60-session
  record restarts on that date with the earlier sessions kept and labelled.
- **Fail:** he stays on his twelve names with rules 10 to 12, and the question is closed until
  his review (about 24 Dec 2026).

## What a pass would not show

The window is 2.7 years and mostly a rising market, which flatters every put seller. A pass
says the index spread did better than the names over this window under these exits. It does
not say the Steward has an edge. Eureka's docs/37 makes the point: an edge of a few points a
year needs years to tell from luck.

## Expectation, before the data is read

X is above zero and ahead of the names, by less than the bar asks, and it does not hold at three
cents: four fills a spread on credits of a dollar or two leave little. N10 is better than N by
about the size of two or three earnings gaps. If this is wrong the result says so.

---

## Results (appended 12 Nov 2026, after the three commits above)

Run: `research/weekend/steward_index.py 0.01` and `0.03`, on the history fetched 11:10 to
12:10 UTC. One code fault was mended before the first full run (a morning with no priced put
crashed the picker); no rule, arm or threshold was touched.

**Arm X fails all six lines. The Steward stays on his twelve names.**

| Arm | Trades | Trades won | Total | A year | Of the sleeve a year | Worst week | Deepest fall | First half | Second half | 6 Oct to 6 Nov 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| N, his names as he was | 1,223 | 70% | −$195 | −$74 | −0.1% | −$740 | −$1,775 | −$437 | +$242 | −$244 |
| N10, without earnings weeks | 1,100 | 70% | −$546 | −$208 | −0.3% | −$641 | −$1,723 | −$755 | +$209 | −$253 |
| X, spreads on SPY, QQQ, IWM | 338 | 66% | −$16,579 | −$6,314 | −9.0% | −$6,065 | −$19,317 | −$4,022 | −$12,557 | −$1,581 |

At three cents a share: N −$5,079, N10 −$4,938, X −$49,163.

| Line | Asked | Found | Met |
|---|---|---|---|
| 1 | X above zero, whole window and each half | −$16,579; −$4,022; −$12,557 | no |
| 2 | X at least $1,050 a year ahead of N10 | $6,106 a year behind | no |
| 3 | X's deepest fall no deeper | −$19,317 against −$1,723 | no |
| 4 | Lines 1 and 2 at three cents | −$49,163 | no |
| 5 | Two funds of three above zero | SPY −$8,789, QQQ −$3,246, IWM −$4,544 | no |
| 6 | Above zero, or a smaller loss than the names, in the fall | −$1,581 against −$253 | no |

**Why the spread loses.** The average spread took in about 12% of its width (SPY 0.78 on 6.91,
QQQ 0.95 on 8.09, IWM 0.39 on 3.19). A structure that collects 12 and risks 88 has to win about
nine times in ten, and a put sold at a fifth of a delta does not. It was stopped out in 116 of
338 trades.

**A check made after the fact, as description only.** A spread's price here is two prints taken
at different moments in an hour, which could fire a stop that a quoted market would not. So the
same spreads were also settled at expiry with no exits, where no option print enters after the
entry: −$26,752, worse, with a worst week of −$14,705. The loss belongs to the structure, not to
the prints.

**What the test says about the names, which nobody asked.**
- His rules on his own twelve names earned about nothing in 2.7 years at a cent a share, and
  lost $1,900 a year at three cents. The credits are too small to carry any cost. This agrees
  with the by-product of 10 Oct.
- **Rule 10 is not supported as an earner.** The 123 name-weeks that held an earnings date made
  $351 between them: taking them out left the book $351 worse, with a worst week $99 better.
  The rule was made by hand this morning on one $1,664 loss. On this evidence it buys a little
  protection against a gap and costs a little income, and the replay cannot see the case that
  hurt, a put re-sold in mid-week the day before a report. It stays, as the owner's decision
  stands, and this paragraph is the evidence against it for whoever reviews it.

**The expectation, marked.**

| Stated before the data was read | Result |
|---|---|
| X above zero and ahead of the names | wrong: far behind, and below zero |
| X short of the bar | right, by much more than expected |
| X does not hold at three cents | right |
| N10 better than N by two or three earnings gaps | wrong: $351 worse |

**What follows.** As written above for a fail: he stays on his twelve names with rules 10 to 12,
and the question of index funds is closed until his review, about 24 Dec 2026. That review now
has a harder question in front of it than the one this test asked: his rules have not earned
their costs on anything they have been replayed on.
