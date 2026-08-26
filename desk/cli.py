"""Alpaca's official CLI as the desk's second door.

The heartbeat's read paths — positions for the exit sweeps, account state for
status — go through `alpaca` (the official Go CLI) when it's on the PATH, with
the SDK as fallback. Structured JSON out, environment auth, paper by default:
built for exactly this kind of long-running agent loop, which is why the desk
uses it rather than merely name-checks it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess


def available() -> bool:
    return shutil.which("alpaca") is not None


def _run(*args: str):
    env = {**os.environ,
           # the CLI's env names differ from the SDK convention we store
           "ALPACA_API_KEY": os.environ.get("ALPACA_API_KEY_ID", os.environ.get("ALPACA_API_KEY", "")),
           "ALPACA_SECRET_KEY": os.environ.get("ALPACA_API_SECRET_KEY", os.environ.get("ALPACA_SECRET_KEY", ""))}
    out = subprocess.run(["alpaca", *args], capture_output=True, text=True, timeout=60, env=env)
    if out.returncode != 0:
        raise RuntimeError(f"alpaca {' '.join(args)} -> {out.returncode}: {out.stderr[:200]}")
    data = json.loads(out.stdout)
    # the CLI wraps errors in a {code, error} envelope with exit 0
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"alpaca {' '.join(args)}: {data['error']}")
    return data


def account() -> dict:
    a = _run("account", "get")
    return {"equity": float(a["equity"]), "cash": float(a["cash"]),
            "buying_power": float(a["buying_power"]),
            "options_level": a.get("options_trading_level")}


def positions() -> list[dict]:
    """Same shape as broker.positions(), so the runner can use either door."""
    rows = _run("position", "list")
    out = []
    for p in rows if isinstance(rows, list) else rows.get("positions", []):
        out.append({"symbol": p["symbol"], "qty": float(p["qty"]),
                    "market_value": float(p.get("market_value") or 0),
                    "cost_basis": float(p.get("cost_basis") or 0),
                    "unrealized_pl": float(p.get("unrealized_pl") or 0),
                    "asset_class": str(p.get("asset_class", ""))})
    return out
