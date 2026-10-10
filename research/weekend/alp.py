"""Read-only Alpaca market data for the weekend test. The keys are the Wheelhouse's, read from
the repo's .env (market data only; never printed, never used to trade)."""
import json, ssl, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

import certifi

# the Python on this Mac does not find the system's CA bundle; certifi's always works
CTX = ssl.create_default_context(cafile=certifi.where())
ENV = Path(__file__).resolve().parents[2] / ".env"
DATA = Path(__file__).resolve().parent / "data"


def _keys():
    k = {}
    for line in open(ENV):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            a, b = line.split("=", 1)
            k[a.strip()] = b.strip().strip('"').strip("'")
    return k["ALPACA_API_KEY_ID"], k["ALPACA_API_SECRET_KEY"]


KEY, SECRET = _keys()


def raw(url, params):
    """One request, the JSON as sent."""
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                 headers={"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SECRET})
    last = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(3 * (attempt + 1)); continue
            raise RuntimeError(f"{e.code} {e.read()[:300]!r}")
        except Exception as e:
            last = e; time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"gave up after retries: {last!r}")


def get(url, params):
    """Every page of a bars request, merged into {"bars": {symbol: [bar, ...]}}."""
    out, token = {"bars": {}}, None
    while True:
        p = dict(params)
        if token:
            p["page_token"] = token
        d = raw(url, p)
        for s, bars in (d.get("bars") or {}).items():
            out["bars"].setdefault(s, []).extend(bars)
        token = d.get("next_page_token")
        if not token:
            return out
