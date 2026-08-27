# Submission checklist & scripts

Deadline: **Friday 4 Sep, 17:00 CEST** on lablab.ai. Everything here maps 1:1 to
the submission form.

## Requirements → status

| Requirement | Status |
|---|---|
| Autonomous AI trading agent on the Trading API | ✅ three-agent desk, runs on a schedule |
| Uses Alpaca's MCP server **or** CLI | ✅ both: Claude researches through the MCP server; the CLI is the heartbeat's read door |
| Strategy incorporates options | ✅ options income core + long-options convexity |
| Brand-new paper account at exactly $100,000 | ✅ created 26 Aug (never traded pre-contest) |
| Public GitHub repo, MIT, original | ⬜ flip to public at kickoff (owner's click) |
| Account ID in the submission | ⬜ paste at submission time |
| One-page write-up (AI logic, risk gates, infrastructure) | ✅ docs/WRITEUP.md — regenerates itself every session |
| Video presentation | ⬜ record in contest week (script below) |
| Slide presentation | ⬜ build from the outline below |
| Up to 5 social posts, tagging @lablabai + @AlpacaHQ | ⬜ drafts below, post through the week |

## Video script (~3 minutes)

1. **The hook (20s).** "This is a trading desk with three employees, and none of
   them is a person. Every decision they made this week — including every decision
   *not* to act — is written down in plain English. Let me show you the log first,
   because the log is the product." *(Scroll logs/decisions.md.)*
2. **The desk (40s).** Steward / Hunter / Risk Officer, one slide each sentence:
   income base, convex sleeve, deterministic gates with the last word.
3. **The MCP moment (40s).** Show a hunter session log: Claude calling
   get_stock_bars and get_option_chain *itself*, then concluding — ideally a
   session where it proposed nothing: "we taught it that premium spent on a weak
   thesis is the only way this sleeve dies, and it believed us."
4. **A veto (20s).** Show one Risk Officer rejection with its plain-English reason.
5. **The week's P&L (40s).** The account curve, what worked, what the stops caught.
   Honesty here reads better than bravado — judges have the blotter anyway.
6. **Close (20s).** "Everything ran on a public schedule, committed its own audit
   trail, and never touched a live endpoint — the code physically can't. Repo's
   open; the log reads like a diary."

## Slide outline (7 slides)

1. The Options Desk — three agents, one account, every decision written down
2. Why a barbell: income pays for the week, convexity wins it
3. The Steward's rule card (delta band, premium floor, mechanical exits)
4. The Hunter: Claude reads the tape through Alpaca's MCP server — read-only tools, strict conclusion schema
5. The Risk Officer: seven gates, closing always allowed, every veto logged
6. The week in numbers: P&L, trades, holds, vetoes (from WRITEUP.md)
7. What we'd build next: multi-leg spreads (level 3), IV-rank memory, a second week

## Social drafts (post through the week, tag @lablabai + @AlpacaHQ)

1. **Kickoff (Fri):** "Entering the @AlpacaHQ AI Trading Agents Hackathon with
   The Options Desk: three AI agents sharing one $100k paper account — an income
   Steward, a convex Hunter (Claude researching live through Alpaca's MCP server),
   and a Risk Officer that is deliberately NOT an LLM. Every decision gets written
   down in plain English. The desk commits its own audit log to GitHub after every
   session. @lablabai #buildinpublic"
2. **First trade (Fri/Mon):** screenshot of the decision log entry — the plain-
   English "because" line is the content.
3. **First veto (when it happens):** "Our Risk Officer just vetoed our own AI:
   [veto reason]. This is the feature."
4. **Midweek (Wed):** the account curve + one lesson learned honestly.
5. **Submission (Thu/Fri):** the week's numbers + link to the repo + write-up.

## Go-live sequence (Friday 17:00)

1. Owner: repo → public (Settings → General → Danger Zone → change visibility).
2. Re-enable the schedule: `gh api -X PUT repos/ijaz529/options-desk/actions/workflows/<id>/enable`
3. Dispatch a `status` run to prove the pipeline; check the log commit appears.
4. Watch the kickoff stream for submission-template changes; adjust this file.
5. Post social draft #1.
