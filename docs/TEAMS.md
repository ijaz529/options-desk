# The desk's teams — what runs, and what could run beside it

*Research and plan, 2 October 2026. Nothing here is built except Team 1. Each new team
becomes real only when its rules are written into `docs/STRATEGY.md` first and the code
follows them. Figures quoted from index providers and papers are historical; past
performance does not predict future results. Not investment advice.*

---

## Team 1 — The Wheelhouse (running since 26 Aug 2026)

The existing desk, named on 2 Oct 2026. Three roles, one account, one record:

| Role | Job |
|---|---|
| **The Steward** | Sells weekly cash-secured puts on liquid large caps (~20-delta); takes profit at 65%, stops at 2×; assigned stock is meant to be sold with a covered call — the options "wheel", hence the name. |
| **The Hunter** | Buys short-dated calls and puts on fresh catalysts, read by Claude; small, convex, on trial since 30 Sep (budget $2,000, verdict by 28 Oct). |
| **The Risk Officer** | Deterministic gates on every order: no naked shorts, sleeve caps, concentration, daily drawdown, kill switch, market-hours rule. |

It stays as it is. Everything below is about what could run **beside** it.

---

## How a second team would have to work

- **Its own account.** Teams sharing one account share one drawdown and have no record of
  their own (the same reasoning that keeps the Wheelhouse one team, eureka docs/03 §21).
  Alpaca allows **three paper accounts per owner**, each with its own API keys and all with
  multi-leg (Level 3) options enabled — so the Wheelhouse plus **two more teams** fits
  exactly.
- **Its own Risk Officer settings**, same gate code.
- **Deterministic, no language model.** Every candidate below is a published rule that needs
  no AI calls — only the Hunter spends API credits.
- **End-of-day cadence.** The desk runs on scheduled sessions, not a live feed, so anything
  that needs intraday hedging or same-day expiries is out.
- **US equity and ETF options only** (Alpaca): no index options (SPX, VIX), no futures.
  Index strategies run on SPY/QQQ/IWM instead.

---

## What the large firms actually run

| Strategy | Who runs it, at what size | Evidence | Fits this desk? |
|---|---|---|---|
| **Covered call / buy-write** | JPMorgan Equity Premium Income (JEPI, ~$44bn) and its Nasdaq sibling; Cboe's BXM index is the benchmark | BXM 8.5% a year vs the S&P 500's 11.1% since 1986, with ~30% less volatility. In the last decade it built about half the S&P's wealth: it gives up the big up-years | Yes — but it is the **same trade as the Steward** (a covered call and a cash-secured put are equivalent by put-call parity). Not a new team. |
| **Put-writing on the index** | Cboe PUT index; WisdomTree and others | PUT 10.1% vs S&P 9.8% (1986–2015) with 36% less volatility; has beaten BXM by ~1% a year over the past decade | Yes — again the Steward's cousin (index instead of single names). A possible *amendment* to the Steward, not a team. |
| **Put-spread collar ("hedged equity")** | JPMorgan Hedged Equity (JHEQX, ~$21bn) — the largest single options position in the market, reset every quarter | Own the index; buy a put ~5% below, sell a put ~20% below, sell a call a few % above to pay for it. Held to expiry, never adjusted. Gives up upside for a defined cushion | **Yes — the best fit.** Quarterly, three legs, no intraday work, nothing like the Wheelhouse. |
| **Iron condor** | Cboe CNDR index; a staple of systematic premium funds | Lowest volatility of Cboe's option-selling indexes (7.2%, 1986–2015) with fewer severe losing months than the S&P — and correspondingly modest returns | **Yes.** Monthly, four legs, defined risk both ways, market-neutral. |
| **Defined-outcome "buffer" funds** | Innovator, First Trust and others, ~$50bn in ETFs | AQR (2025): only 14% of the funds it studied beat a plain mix of the S&P 500 and Treasury bills; 81% had *worse* drawdowns | Possible, but it is a one-year structure (a record takes years) and the collar covers the same idea with better evidence. Not recommended. |
| **Tail-risk hedging (long far-out puts)** | Universa and other "black swan" funds | Pays enormously in crashes (Universa reported +3,612% in March 2020) and bleeds every other year. AQR argues trend-following hedges more cheaply; CalPERS famously cancelled its hedge just before 2020 | Possible as a small overlay; as a stand-alone team it loses most years by design. Later, if at all. |
| **Selling volatility around earnings** | Many volatility funds | Academic evidence that options were overpriced before earnings — but recent studies on weekly options find the edge no longer reliable | No. Event risk on single names, a contested edge, and it needs an earnings calendar. |
| **Dispersion, volatility arbitrage, delta-hedged straddles** | Bank desks and volatility hedge funds | Real, but the edge is in continuous hedging and index-vs-single-stock volatility | No — needs intraday hedging and index options. |
| **Same-day (0DTE) options** | A large share of S&P option volume today | Mostly intraday | No — the desk cannot trade intraday. |
| **VIX strategies** | Volatility funds | — | No — no VIX options at Alpaca. |

---

## Recommendation: two new teams

Chosen to be as different as possible from the Wheelhouse and from each other.

### Team 2 — "The Harbour" (hedged equity, JPMorgan-style; code name `collar`)

- **What it does.** Holds an S&P 500 ETF position and, each quarter, buys a put ~5% below
  the market, sells a put ~20% below, and sells a call above the market sized so the three
  legs cost roughly nothing. Holds to expiry; never adjusts mid-quarter.
- **What the customer gets.** Stock-market returns up to a cap, with the first ~5% of a fall
  taken on the chin and the next ~15% cushioned. "Equity you can sleep with."
- **Why it's different.** The Wheelhouse sells insurance; the Harbour buys it — a sheltered place to hold the index.
- **Honest costs.** It lags badly in strong years (the cap), and offers no protection past
  the lower put. In a slow grind down it protects little.
- **Open at build time:** which ETF and how many shares fit the account (one lot of SPY is
  most of a $100,000 account); how the call strike is solved for zero cost.

### Team 3 — "The Tollgate" (range-bound income, defined risk; code name `condor`)

- **What it does.** Once a month on SPY, QQQ and IWM: sells a put and a call each ~20-delta
  and buys wings further out, so the most it can lose on each is fixed on day one. Takes
  profit early, exits before expiry week.
- **What the customer gets.** Income when the market goes nowhere, with a known worst case — a toll collected while the index stays inside the gates.
- **Why it's different.** Market-neutral; makes money in the quiet months the Hunter hates.
- **Honest costs.** Small wins, occasional full-width losses; returns are modest by
  construction (the index version's are). A trending market in either direction hurts.

### Not now

- **A tail-hedge team** would be an honest and interesting record (what insurance really
  costs), but it loses most years. Revisit once the first two have records.
- **Index put-writing and covered calls** belong to the Steward if anywhere.

---

## What it takes to start

1. **Two more Alpaca paper accounts** (owner's step — the dashboard allows three per login),
   funded at the same $100,000, and their keys added as separate GitHub secrets.
2. **Spec first:** each team's rules written into `docs/STRATEGY.md`, including its own
   kill-switch baseline.
3. **Code:** a small "team" layer so `desk.run` can address an account by name; the Collar
   and Condor are each one new module beside `steward.py`, reusing the broker, the gates, the
   diary and the pg_cron trigger.
4. **Run in parallel** for at least a quarter before any release decision — the Collar's
   first full cycle is three months.

---

## Sources

- JPMorgan Hedged Equity collar: [SpotGamma](https://spotgamma.com/jpm-collar-explained/), [The Option Premium](https://www.theoptionpremium.com/p/jpm-collar-explained-how-it-works), [MenthorQ](https://menthorq.com/guide/jp-morgan-collar-trade-explained/)
- Cboe option-selling indexes (BXM, PUT, CNDR): [Cboe study, 2016](https://ir.cboe.com/news/news-details/2016/Study-Analyzes-Performance-of-CBOE-SP-500-SPX-Options-Selling-Indexes-02-23-2016/default.aspx), [Wilshire for Cboe, 2019](https://cdn.cboe.com/resources/spx/wilshire-options-based-benchmark-indexes-2019.pdf), [Cboe PutWrite index](https://en.wikipedia.org/wiki/CBOE_S%26P_500_PutWrite_Index)
- Covered calls over 40 years and the last decade: [Thetaloop on BXM](https://thetaloop.app/learn/covered-calls), [WisdomTree on put- vs call-writing](https://www.wisdomtree.com/investments/blog/2025/10/02/why-fear-pays-the-case-for-put-writing-over-call-writing)
- JEPI: [JPMorgan fact sheet, Aug 2026](https://am.jpmorgan.com/content/dam/jpm-am-aem/americas/us/en/literature/fact-sheet/etfs/fs-jepi.pdf), [Morningstar](https://www.morningstar.com/etfs/arcx/jepi/quote)
- Buffer ETFs and AQR's critique: [Financial Advisor](https://www.fa-mag.com/news/cliff-asness-s-aqr-slams-buffer-etf-boom-on--investment-failure-81859.html), [Morningstar](https://www.morningstar.com/funds/buffer-funds-are-rise-they-may-not-make-sense-most-investors), [Innovator mechanics](https://www.innovatoretfs.com/pdf/defined_outcome_mechanics.pdf)
- Tail hedging: [AQR, Journal of Systematic Investing](https://www.aqr.com/-/media/AQR/Documents/Journal-Articles/Journal-of-Systematic-Investing-Vol-1-Issue-1--Tail-Risk-Hedging-AQR.pdf?sc_lang=en), [Institutional Investor on CalPERS](https://www.institutionalinvestor.com/article/2bsxabrnayd009kkvsd1c/portfolio/the-inside-story-of-calpers-untimely-tail-hedge-unwind)
- Earnings volatility: [Weekly option prices around earnings (MDPI)](https://www.mdpi.com/1911-8074/16/5/270), [Retail option trading and announcement volatility](https://www.timdesilva.me/files/papers/losing_optional.pdf)
- Alpaca: [Level 3 multi-leg options](https://alpaca.markets/blog/level-3-options-trading-now-available-with-alpacas-trading-api/), [paper-account limit](https://forum.alpaca.markets/t/feature-request-more-paper-trading-accounts/18125)
