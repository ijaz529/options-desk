# The Steward's strike and premium floor: pre-registration

Drafted by Claude on 14 Nov 2026 (on top of commit 4d0d766), for the owner's review; **not yet
adopted**. No data has been opened for it beyond what is listed below as already read; its
hold-out has not begun trading. *(Owner)* marks a proposal for the owner to decide.

## Why

His review row (STRATEGY.md, "Review goals") asks, after 60 sessions from 30 Sep 2026 (the 60th is
Wed 23 Dec), for equity above the $88,983 baseline after costs, no kill-switch trip and stops under
a third of puts sold. If missed, "the strike and premium-floor rules go to a pre-registered test
(not changed by hand)". At session 33 (13 Nov) equity is $84,332.30, −5.23%; the switch tripped on
9 Nov, so that line is lost. Of the 75 puts sold from 30 Sep that the diary shows closed by a stop
or a take-profit, 34 were stopped (35 of 78 counting the three puts sold on 28 Sep and closed
from 30 Sep, among them the BAC 54 stopped on 1 Oct). The test is owed.

## What is already known, and so cannot count as evidence

- **N and N10 on the seen span.** The index test of 12 Nov (`docs/STEWARD_INDEX_PREREG.md`)
  replayed his rules on his names over the expiries 22 Mar 2024 to 6 Nov 2026, **the seen span**
  below: N10 −$546 at a cent a share, −$4,938 at three. No candidate below has been run on that
  span; that is the fresh question lines 1 to 5 ask.
- **The 10 Oct replay** also ran his rules without the 0.15% floor, and printed the result. No
  figure from it is in the repo, but it may have been seen, so no arm lowers the floor.
- **The live record** was watched: 75 puts, −$3,042 at diary marks, each credit the fill its exit
  row states. In drafting it was cut at three credits a share, fills at the cut counted on the
  kept side: at $0.25, the 23 below lost $815 and the 52 at or above $2,227; at $0.30, 34 lost
  $661 and 41 lost $2,381; at $0.40, 50 lost $1,217 and 25 lost $1,825. On the offers' credits,
  a cent or more lower on 18 of the 75, the figures are −$3,064; 23 −$824 and 52 −$2,240; 34 −$672
  and 41 −$2,392; 51 −$1,204 and 24 −$1,860. At every cut the dearer puts lost more each. C30's
  $0.30 was chosen after these cuts were read; they argue against it, not for it.
- The 13 Nov expiry was traded live and is in neither span.

## The arms

Every arm is N10 but for one rule: his twelve names, one contract, one trade per name a week,
entered on the week's first trading day at the close of the 9:30 to 10:00 bar, no earnings weeks
(rule 10; a name with no Yahoo history leaves every arm).

| Arm | Delta band, nearest | Premium floor, on the entry print |
|---|---|---|
| **N10**, as he is (the reference) | −0.21 to −0.12, −0.20 | 0.15% of the strike |
| **D10**, strike further out | −0.11 to −0.06, −0.10 | 0.15% of the strike |
| **D30**, strike nearer the money | −0.31 to −0.22, −0.30 | 0.15% of the strike |
| **C30**, a floor in cents | −0.21 to −0.12, −0.20 | 0.15% of the strike **and** $0.30 a share |

C30 because the cost is per share: 0.15% of a $22 strike is 3.3 cents, which a three-cent fill
eats; at $0.30 a round trip at three cents is a fifth of the credit. D30 re-admits trades like the
KO 88 put at −0.26 that the 26 Sep reading of rule 2 removed.

*(Owner.)* The values −0.10, −0.30 and $0.30; three candidates, no more; the scope, read as rules 2
and 3 (STRATEGY.md:356-361). Not moved: exits, size, universe, structure, the spread's wing and
credit floor, the market test, the call's band. The market test cannot be replayed from prints.
The 20/10 spread and the covered call could be, and are left out by choice, as on 12 Nov.

**What live would do that this test does not.** A name-week an arm refuses scores nought here.
Live, it goes to the 20/10 put spread (run.py:295-300), whose short leg keeps today's band
(−0.21 to −0.12) and has no premium floor. N10 on 12 Nov was scored the same way, so the comparison is fair, but a candidate
that refuses many more weeks than N10 would, live, sell many more spreads than this test has
seen. The count is reported per arm, and the result says so.

## Exits, costs, prices

The index test's: take profit when the price falls to 35% of the entry print (65% banked), stop
at twice it, on later hourly closes with two trades or more, else cash at the expiry close. A cent
a share each fill; a rerun at three. Trade prints of $0.05 or more, not quotes, so the market test
cannot apply and floors are read off the print. Black–Scholes, r 4.5%, q 0.

**Changes from the N10 of 12 Nov, all stated here:**
1. **Half-days.** Closes are the 15:00 bar's (`steward_index.py:34`, `fetch.py:37`). After a 13:00
   close (27 Nov 2026; three expiries in the seen span) that bar is after hours or missing. Here a
   close is the last hourly bar that opens before the close in the broker's calendar, as the desk
   has read it since 14 Nov.
2. **The put window** widens from 0.88–1.03 of the reference price to **0.77–1.06**. A −0.10 put
   at a volatility of 0.8 (Intel this autumn; D10, the farthest arm) then keeps a fetched strike
   through a 14% fall from the reference close, and D30's −0.30 at 0.15 through a 6.8% rise. The
   wider window can change N10's own pick in a week where its strike lay outside the old one.
3. **A name with no Yahoo history** leaves every arm, where on 12 Nov it stopped N10 being run.

As a check, N10 is also run on the 0.88–1.03 strikes alone, and the difference is reported before
any candidate is read.

**Code, committed with this file before any fetch, and nothing else:**
1. `research/weekend/fetch.py`: the put window (:55) becomes two optional arguments, defaults
   unchanged; the half-day close at :37.
2. A new `research/weekend/steward_strike.py`, from the name arm of `steward_index.py`, which stays
   as it ran: four arms over one set of candidates per name-week; its own expiries and cost, not
   that file's `LAST` or `sys.argv`; the half-day close; 13 Nov skipped; everything below saved.

## What is measured

**Seen span:** expiries 22 Mar 2024 to 6 Nov 2026. **Hold-out:** the five from 20 Nov to 18 Dec
2026, inside his 60 sessions; nobody has these prices.

Each arm and span, at a cent and at three, as one book against his $70,000 sleeve: trades; exits by
kind; stops as a share of trades; total, and a year; worst week; deepest fall; each half; expiries
9 Oct to 6 Nov 2026; median credit; each name; name-weeks the band or the floor refused; apart
from those, name-weeks with no fetched strike inside the arm's band (the window, not the rule:
Intel's 6 Nov expiry, after a fall of a quarter, is one); picks at the window's edge. Each candidate's weekly difference from N10, a week with no trade as nought:
total and t.

The halves are the expiries before 18 Jul 2025 and from it, 69 each, the same for every arm, N10
included. "A year" is the span's total divided by its length in years (22 Mar 2024 to 6 Nov 2026),
the same divisor for every arm.

## The bar

A candidate **passes** only if all six hold, at a cent and at three cents a share: 1 to 5 on the
seen span, 6 on the hold-out.

1. It is above zero over the span and in each half.
2. It earns at least **$1,050 a year** (1.5% of the sleeve) more than N10, also with the name that
   adds most to its lead left out of both.
3. Its weekly difference from N10 has a t of at least **2.15**: one-sided 5%, split three ways.
4. Its deepest fall is no deeper than N10's; in the expiries 9 Oct to 6 Nov 2026 it is above zero
   or loses less than N10.
5. Its stops are under **a third** of its trades: the review row's line. A model of these exits
   with no edge, variance in calendar time, stops about 31% at D10, 32% at N10 and 33.5% at D30;
   with variance in trading hours only, about 37% at every arm. So this line can fail a candidate
   that merely has no edge, and it leans against D30 by construction. It stays, because it is the
   line he will be judged by again.
6. In the hold-out it is not behind N10, and its stops are under a third of its trades.

If more than one passes, the one with the higher line-3 t at three cents a share is adopted (if
tied, the higher at a cent); never a blend. A fail reads: *"moved one at a time, no strike or
floor met all six lines of the bar"*, followed by each candidate's result line by line, including
any that beat N10 but missed lines 1 or 5.

## What follows

- **Pass:** rule 2 or 3 is amended in STRATEGY.md, dated. In the same commit, "Built 10 Oct 2026"
  is rewritten so that the spread's short leg (its item 2) and the covered call's floor (its item
  4) state today's figures rather than pointing to rule 2 or 3; neither was replayed. The spread's
  item 1 keeps "no cash-secured put qualifies", under the amended rule, as run.py:295-300 does. `desk/steward.py` gets separate constants for them,
  `desk/writeup.py`'s Steward line names the new rule, and tests are added in
  `tests/test_steward.py` (C30's floor on the mid, as the 0.15% is). His 60 sessions are judged at
  his review as they stand, and kept and labelled (to 11 Nov; 12 Nov to the amendment).
  *(Owner.)* Whether a new record then starts, and against which baseline, is not this test's to
  say: it is a dated amendment to his review row, written before this test is run.
- **Fail:** rules 2 and 3 stay as written, with rules 10 to 12. The row's remedy is spent: he missed
  his bar, and its test found nothing to mend. The row names no next step; whether he keeps running
  is the owner's dated decision at his review *(flagged)*. No other strike or floor is tried on this
  history.

## What a pass would not show

Line 3 caps luck across three candidates; it does not undo that the seen span was opened first.
The hold-out, at most 60 name-weeks an arm, can refute a candidate, not confirm one. The window is
2.6 mostly rising years, which flatters a put seller, and a print is least like a fill on a −0.10
put. One Monday entry stands for a week of offers; assignment is cash, with no covered call; a
refused week is nought, where live it is a spread; half-dollar strikes above $100 (XOM 157.5) are
never fetched. A pass says a rule did better here, not that he has an edge (eureka docs/37).

## Expectation, before the data is read

- **N10:** within $150 of −$546 at a cent; −$300 to +$300 in the hold-out; stops a fifth to 30% of
  trades.
- **D10:** under half N10's trades (a −0.10 put pays 0.15% only above a volatility of about 0.28);
  below zero at three cents; fails lines 1 and 2.
- **D30:** credits about 1.7 times N10's (model); the largest total of the four at a cent; a deeper
  fall than N10's; fails line 4.
- **C30:** under half N10's trades, mostly XOM, CVX and Uber; ahead of N10 at three cents by under
  $1,050 a year, about level at a cent; fails line 2.
- **No arm passes.** If this is wrong the result says so.

## When it is run

- On or after the close of Wed 23 Dec 2026, his 60th session. Nothing changes before.
- By the owner, or Claude at the owner's instruction: `fetch.py SYM 2024-03-04 2026-12-18 0.77
  1.06` per name, then `steward_strike.py 0.01` and `0.03`. The commit, fetch times and results
  are appended here, expectations marked.
- N10 is read first, alone, on both windows. If the wider-window N10 is more than $150 from −$546
  at a cent, the gap is traced and written down before any candidate is read. A fault found mid-run
  is mended in the code only, never a rule, arm or threshold, and the results say so.
- Adopted, as it stands or amended, before the open (9:30 New York) on **Mon 16 Nov 2026**. If
  later, the hold-out starts at the first expiry entered after adoption: the desk trades those
  weeks in plain view.
