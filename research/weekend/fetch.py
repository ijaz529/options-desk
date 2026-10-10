"""Fetch hourly bars for weekly options around every weekly expiry, plus the underlying's hourly
bars. Read-only Alpaca market data (option history starts Feb 2024).

    fetch.py SYMBOL [START [END]]      dates as YYYY-MM-DD; END defaults to yesterday

Output: data/<SYMBOL>_opt.pkl, data/<SYMBOL>_stk.pkl."""
import datetime as dt, sys, math
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from zoneinfo import ZoneInfo
from alp import get, DATA

NY = ZoneInfo("America/New_York")
OPT = "https://data.alpaca.markets/v1beta1/options/bars"
STK = "https://data.alpaca.markets/v2/stocks/bars"
SYM = sys.argv[1] if len(sys.argv) > 1 else "SPY"
START = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2024, 2, 5)
END = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date.today() - dt.timedelta(days=1)
WINDOW = 14                      # calendar days before expiry: covers the 14- and 7-day weekends
# the free data plan refuses share prices under 15 minutes old: stop well short of now
STK_END = min(dt.datetime.combine(END + dt.timedelta(days=1), dt.time(), dt.timezone.utc),
              dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20))
DATA.mkdir(exist_ok=True)

def frame(bars, sym):
    df = pd.DataFrame(bars.get(sym, []))
    if df.empty: return df
    df["t"] = pd.to_datetime(df["t"], utc=True).dt.tz_convert(NY)
    return df[["t", "o", "c", "n", "v"]]

stk = frame(get(STK, {"symbols": SYM, "timeframe": "1Hour", "start": f"{START - dt.timedelta(days=20)}T00:00:00Z",
                      "end": STK_END.strftime("%Y-%m-%dT%H:%M:%SZ"), "feed": "sip", "adjustment": "raw",
                      "limit": 10000})["bars"], SYM)
stk.to_pickle(DATA / f"{SYM}_stk.pkl")
# trading days = days with a regular-session 9:00 ET bar
days = sorted({t.date() for t in stk["t"] if t.hour == 9})
close_px = {t.date(): c for t, c in zip(stk["t"], stk["c"]) if t.hour == 15}
# weekly expiry = last trading day of each Mon–Fri week
weeks = {}
for d in days:
    if d < START or d > END: continue
    k = d - dt.timedelta(days=d.weekday())
    weeks[k] = max(weeks.get(k, d), d)
expiries = sorted(weeks.values())

def step_for(px):
    return 1.0 if (SYM in ("SPY", "QQQ", "IWM") or px >= 100) else 0.5

def symbols(exp):
    ref_day = max([d for d in days if d <= exp - dt.timedelta(days=WINDOW)] or [days[0]])
    s = close_px.get(ref_day)
    if s is None: return [], None
    st = step_for(s)
    out = []
    for cp, lo, hi in (("P", 0.88, 1.03), ("C", 0.97, 1.12)):
        k = math.floor(s * lo / st) * st
        while k <= s * hi + 1e-9:
            out.append(f"{SYM}{exp:%y%m%d}{cp}{int(round(k * 1000)):08d}")
            k = round(k + st, 2)
    return out, s

def fetch(exp):
    syms, s = symbols(exp)
    rows = []
    for i in range(0, len(syms), 100):
        chunk = syms[i:i + 100]
        try:
            d = get(OPT, {"symbols": ",".join(chunk), "timeframe": "1Hour",
                          "start": f"{exp - dt.timedelta(days=WINDOW)}T00:00:00Z",
                          "end": f"{exp + dt.timedelta(days=1)}T00:00:00Z", "limit": 10000})
        except Exception as e:
            print("ERR", exp, e, flush=True); continue
        for sym, bars in d["bars"].items():
            for b in bars:
                rows.append((sym, b["t"], b["o"], b["c"], b["n"], b["v"]))
    return exp, rows

all_rows = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for n, (exp, rows) in enumerate(ex.map(fetch, expiries), 1):
        all_rows.extend(rows)
        if n % 20 == 0 or n == len(expiries):
            print(f"{SYM}: {n}/{len(expiries)} expiries, {len(all_rows):,} bars", flush=True)
opt = pd.DataFrame(all_rows, columns=["sym", "t", "o", "c", "n", "v"])
opt["t"] = pd.to_datetime(opt["t"], utc=True).dt.tz_convert(NY)
opt.to_pickle(DATA / f"{SYM}_opt.pkl")
print(SYM, "done:", len(opt), "bars,", opt["sym"].nunique(), "contracts,", len(expiries), "expiries")
