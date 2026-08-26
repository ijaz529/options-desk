"""The decision log — the desk's memory and its honesty.

Append-only JSONL, one row per decision or veto, each carrying a plain-English
`because`. `render` turns the log into the markdown the write-up and the video
walk through. Nothing here talks to a broker; it only writes things down.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_PATH = os.path.join(LOG_DIR, "decisions.jsonl")


def record(agent: str, action: str, because: str, **detail) -> dict:
    """Write one decision down. `action` is short ("sell_put", "veto", "hold",
    "close"); `because` is the sentence a human reads. Extra keyword details
    (symbol, contract, qty, price, order_id…) ride along verbatim."""
    row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "agent": agent, "action": action, "because": because, **detail}
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def rows(path: str = LOG_PATH) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def render(path: str = LOG_PATH) -> str:
    """The log as markdown, newest day first — the artefact judges read."""
    by_day: dict[str, list[dict]] = {}
    for r in rows(path):
        by_day.setdefault(r["ts"][:10], []).append(r)
    out = ["# The desk's decision log", ""]
    for day in sorted(by_day, reverse=True):
        out.append(f"## {day}")
        out.append("")
        for r in by_day[day]:
            t = r["ts"][11:16]
            tag = {"veto": "🛑", "hold": "·"}.get(r["action"], "→")
            out.append(f"- **{t}** {tag} `{r['agent']}` **{r['action']}** — {r['because']}")
        out.append("")
    return "\n".join(out)
