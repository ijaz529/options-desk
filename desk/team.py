"""Which team this process is — and the wall between teams (STRATEGY.md "How teams are
kept apart").

One process serves one team, chosen by DESK_TEAM (default: the Wheelhouse). A team has its
own paper account, its own key pair, its own diary. `guard()` is the wall: it reads the
account number from the broker and refuses to continue unless it is the one written here.
"""
from __future__ import annotations

import os

TEAM = os.environ.get("DESK_TEAM", "wheelhouse").strip().lower() or "wheelhouse"

# account: the ONLY Alpaca paper account this team may trade. None = not assigned; the
# team's session refuses to run. baseline: equity the team's own gates measure against.
TEAMS: dict[str, dict] = {
    "wheelhouse": {"account": "PA3G3BG7TIBD", "baseline": 88_983.0},
    "collar":     {"account": "PA3SKVNYTFJK", "baseline": 100_000.0},
    "condor":     {"account": None,           "baseline": None},
}

if TEAM not in TEAMS:
    raise SystemExit(f"unknown team {TEAM!r} — expected one of {sorted(TEAMS)}")

# The Wheelhouse keeps the original, unsuffixed secret names and diary path.
KEY_SUFFIX = "" if TEAM == "wheelhouse" else "_" + TEAM.upper()
LOG_SUBDIR = "" if TEAM == "wheelhouse" else TEAM


def config() -> dict:
    return TEAMS[TEAM]


def account_problem(actual: str | None, team: str = TEAM) -> str | None:
    """None if `actual` is this team's account, else the plain-English reason to stop."""
    want = TEAMS[team]["account"]
    if want is None:
        return (f"The {team.title()} has no paper account assigned yet (STRATEGY.md) — "
                "nothing is read and nothing is placed.")
    if actual != want:
        return (f"These keys open account {actual or 'unknown'}, but the {team.title()} may only "
                f"trade {want}. Refusing to continue — a team never touches another team's account.")
    return None
