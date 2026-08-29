# How this desk makes (or loses) money — in plain English

*No options knowledge assumed. `STRATEGY.md` is the exact contract; this page is
the same thing explained to a human.*

## The one-sentence version

**The desk runs a tiny insurance company, plus a small bet-shop next door, with
a compliance officer who can shut either of them down.**

## The Steward: selling insurance (~70% of the money)

Some investors are nervous about a stock falling. They will pay real money for a
promise that someone else absorbs the fall. That promise is called a **put**, and
the Steward sells them.

A live example from this desk's first day:

> Exxon was trading around **$156**. Someone paid us **$86** for this promise:
> *"if Exxon is below $152.50 on Friday, you buy 100 shares from me at $152.50."*

Three things to hold onto:

1. **The $86 is ours immediately and permanently.** Nothing can take it back.
2. **We set aside $15,250** ($152.50 × 100 shares) in case we have to honour the
   promise. That money isn't spent — it's reserved. This is what "cash-secured"
   means, and it's why the desk can never owe more than it has.
3. **The promise itself has a price that moves all week.** We can end the deal
   early at any time by buying an identical promise back. If it gets cheap, we
   pocket the difference; if it gets expensive, we cut the loss.

**How each trade ends** (only one of these happens):

| | What the market did | What we do | Result |
|---|---|---|---|
| **Take-profit** | Stock drifts up or sideways; fear fades; the promise gets cheap (≈$30) | Buy it back | **+$56 kept**, week over early |
| **Stop-loss** | Fear rises; the promise doubles in price (≈$172) | Buy it back | **−$86**, small and deliberate |
| **Expires safe** | Stock above $152.50 on Friday | Nothing | **+$86 kept** |
| **Assigned** | Stock below $152.50 on Friday | Buy 100 shares at $152.50 | **We own Exxon**, at a price we pre-approved, and keep the $86 |

Note that the stop-loss can fire while the stock is still *above* the strike —
it reacts to the *cost of the risk*, not the stock's level. Most weeks, most
positions end in the first or third row.

**Why this works when it works:** most weeks are ordinary. Selling insurance
against the unusual, over and over, collects many small premiums. **Why it can
hurt:** one genuinely bad week can cost more than several good ones earned —
which is exactly what the position caps and stops exist to bound.

## The Hunter: buying lottery tickets (~20% of the money)

The mirror image. Instead of selling promises, the Hunter *buys* them — paying a
small premium for the right to profit if a specific stock moves sharply. Maximum
loss is the premium paid; upside is many times that.

What makes it unusual: **Claude picks the ideas, but never touches an order.**
Twice a session it reads the day's tape through Alpaca's MCP server — pulling
price bars and option chains itself — and must finish with a proposal in a rigid
format: a named stock, a thesis under 280 characters, a spending cap, and
**what would prove the thesis wrong**. No invalidation, no trade. Anything
malformed is thrown away whole. The desk's own code then converts a surviving
thesis into an actual contract and sizes it.

Proposing nothing is an allowed and frequent answer.

## The Risk Officer: the one that isn't an AI

Deliberately plain code, no language model, with the final say over both agents:
no uncovered promises, hard caps per sleeve and per stock, a daily
drawdown brake, an account-level kill switch, and no new positions in the
contest's last three hours. **Closing a position is always permitted** — risk can
always be reduced, never silently increased.

Every verdict is written down, including refusals. On day one it vetoed nine of
ten proposed trades because each would have breached a size limit. That was the
system working correctly and the *stock list* being wrong; the list was changed,
the limits were not.

## Weekends

Options markets close; crypto doesn't. A simple mechanical rule may buy a small
amount of Bitcoin or Ethereum if either moved more than 1.5% in a day, with
tight exits. If neither moved, the log says so — *"cash is a position"* — and
the desk sits out.

## How to read the scoreboard

The honest measure of a week is **premium collected minus stops paid**, plus
whatever the Hunter's tickets returned. Because selling insurance *adds* cash up
front, the account balance rising slightly is not yet profit — it's money we may
still have to work for. The real story lives in `logs/decisions.md`, where every
action, and every deliberate inaction, explains itself in a sentence.
