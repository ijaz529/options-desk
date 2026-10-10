# The weekend test

Do listed options lose more over a weekend than over a weeknight, and should the Steward sell
Friday-to-Friday instead of Monday-to-Friday? First run 10 Oct 2026; the answer and the numbers
are in `docs/STRATEGY.md`, "Tested 10 Oct 2026 — the weekend, and not adopted". Run it again
when there is another year of data.

## Run

From the repo root, with the desk's own environment (it already has numpy, pandas and certifi):

```
cd research/weekend
../../.venv/bin/python fetch.py SPY                      # ~15 min; Feb 2024 to yesterday
for s in XOM CVX KO WMT BAC DIS UBER PFE CSCO INTC T GM; do
  ../../.venv/bin/python fetch.py $s 2024-03-04          # ~5–8 min each; March avoids WMT's 3:1 split
done
for s in SPY XOM CVX KO WMT BAC DIS UBER PFE CSCO INTC T GM; do ../../.venv/bin/python analyse.py $s; done
../../.venv/bin/python pool.py XOM CVX KO WMT BAC DIS UBER PFE CSCO INTC T GM
```

`fetch.py SYMBOL [START [END]]` downloads hourly bars for every weekly expiry and the two weeks
before it (strikes 12% below to 12% above the price), plus the stock's hourly bars, into `data/`
(git-ignored). `analyse.py` prints, per symbol, weekend against weeknight returns (hedged and
not) and the Steward's two cycles; `pool.py` runs the twelve names as one book, as he does.

## What it assumes

- Prices are **trade prints** from the hourly bars, not quotes: the ~16:00 mark is the last trade
  before the close, the ~10:00 mark the last before 10:00. A cent a share is charged on every fill.
- The Steward's rules as written on 10 Oct 2026: delta band −0.21 to −0.12 nearest −0.20,
  premium at least 0.15% of the strike, take profit at 65%, stop at 2×, otherwise held to expiry.
  The spread filter is not applied (no quotes). Exits are checked on hourly closes with at least
  two trades in the hour.
- Weekend = Friday close to Monday close; weeknight = one day to the next. Holidays and periods
  across an ex-dividend date are left out. Black–Scholes deltas use r 4.5%, SPY's yield 1.2%.

## Gotchas found on the first run

- Alpaca's option bars include **Saturday test-session prints** (INTC and GM puts at $9–10 on
  Saturday 1 Jun 2024). Everything here keeps to trading days; anything else reading bars must too.
- The free data plan refuses share prices under 15 minutes old; `fetch.py` stops 20 minutes short.
- This Mac's Python does not find the system's certificates; `alp.py` uses certifi's.
- The keys are the Wheelhouse's, read from the repo's `.env`, for market data only.
