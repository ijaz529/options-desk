"""Weekend test. (1) Delta-hedged option returns over weekends vs weeknights (Jones & Shemesh
replication). (2) The Steward's weekly put, sold Monday ~10:00 for that Friday (today's rule) vs
sold Friday at the close for next Friday. (3) The Hunter's kind of long option over weekends.

    analyse.py SYMBOL        reads data/<SYMBOL>_*.pkl from fetch.py; writes data/<SYMBOL>_periods.pkl,
                             data/<SYMBOL>_steward_trades.pkl and data/<SYMBOL>_summary.json"""
import sys, json, datetime as dt
import numpy as np, pandas as pd
import bs
from alp import raw, DATA

SYM = sys.argv[1] if len(sys.argv) > 1 else "SPY"
R = 0.045
Q = 0.012 if SYM == "SPY" else 0.0
COST = 0.01                      # per share per side: half a typical spread, taken on every fill
out = {"symbol": SYM}

opt = pd.read_pickle(DATA / f"{SYM}_opt.pkl"); stk = pd.read_pickle(DATA / f"{SYM}_stk.pkl")
L = len(SYM)
con = pd.DataFrame({"sym": opt.sym.unique()})
con["exp"] = pd.to_datetime(con.sym.str[L:L + 6], format="%y%m%d").dt.date
con["cp"] = np.where(con.sym.str[L + 6] == "C", 1, -1)
con["K"] = con.sym.str[L + 7:].astype(int) / 1000
opt = opt.merge(con, on="sym")
opt["d"] = opt.t.dt.date; opt["h"] = opt.t.dt.hour
stk["d"] = stk.t.dt.date; stk["h"] = stk.t.dt.hour
days = sorted(set(stk[stk.h == 9].d))
nxt = {a: b for a, b in zip(days[:-1], days[1:])}
S16 = stk[stk.h == 15].drop_duplicates("d").set_index("d").c
S10 = stk[stk.h == 9].drop_duplicates("d").set_index("d").c

# ex-dividend dates: a period spanning one carries the dividend drop, not option pricing
ca = raw("https://data.alpaca.markets/v1/corporate-actions",
         {"symbols": SYM, "types": "cash_dividend", "start": "2024-01-01", "end": str(dt.date.today()), "limit": 1000})
exd = {dt.date.fromisoformat(x["ex_date"]) for x in (ca.get("corporate_actions") or {}).get("cash_dividends", [])}
out["ex_dividend_dates"] = len(exd)

# ---------- observations: the last-hour close (~16:00) and the first-hour close (~10:00) ----------
c16 = opt[opt.h == 15].drop_duplicates(["sym", "d"])[["sym", "d", "exp", "cp", "K", "c", "n"]].rename(columns={"c": "O", "n": "n"})
c10 = opt[opt.h == 9].drop_duplicates(["sym", "d"])[["sym", "d", "c", "n"]].rename(columns={"c": "O10", "n": "n10"})
c16 = c16[c16.d.isin(S16.index)].copy()
c16["S"] = c16.d.map(S16)
c16["T"] = c16.apply(lambda r: (r.exp - r.d).days, axis=1) / 365.0
c16 = c16[(c16["T"] > 0) & (c16.O >= 0.05) & (c16.n >= 3)].copy()
c16["iv"] = bs.iv(c16.O.values, c16.S.values, c16.K.values, c16["T"].values, R, Q, c16.cp.values)
c16 = c16[c16.iv.notna() & (c16.iv < 2.5)].copy()
c16["dl"] = bs.delta(c16.S.values, c16.K.values, c16["T"].values, R, Q, c16.iv.values, c16.cp.values)
c16["dte"] = (c16["T"] * 365).round().astype(int)

# ---------- (1) periods: close -> next close, and close -> next ~10:00 ----------
p = c16.copy(); p["d2"] = p.d.map(nxt)
p = p.dropna(subset=["d2"])
nx16 = c16[["sym", "d", "O", "n"]].rename(columns={"d": "d2", "O": "O2", "n": "n2"})
p = p.merge(nx16, on=["sym", "d2"], how="left").merge(c10.rename(columns={"d": "d2"}), on=["sym", "d2"], how="left")
p["S2"] = p.d2.map(S16); p["S2_10"] = p.d2.map(S10)
gap = p.apply(lambda r: (r.d2 - r.d).days, axis=1)
p["kind"] = np.where((gap == 3) & (pd.to_datetime(p.d).dt.weekday == 4), "weekend", np.where(gap == 1, "weeknight", "other"))
p = p[p.kind != "other"]
p = p[~p.apply(lambda r: any(r.d < x <= r.d2 for x in exd), axis=1)]
p["hedged_cc"] = ((p.O2 - p.O) - p.dl * (p.S2 - p.S)) / p.O * 100          # % of premium, long side
p["unhedged_cc"] = (p.O2 - p.O) / p.O * 100
p["hedged_co"] = ((p.O10 - p.O) - p.dl * (p.S2_10 - p.S)) / p.O * 100
p["unhedged_co"] = (p.O10 - p.O) / p.O * 100
p["absd"] = p.dl.abs()
p["move"] = np.maximum((p.S2 / p.S - 1).abs(), (p.S2_10 / p.S - 1).abs())
p.to_pickle(DATA / f"{SYM}_periods.pkl")

def compare(sub, col, label):
    """Date-level means (contracts on one date move together), weekend vs weeknight."""
    s = sub.dropna(subset=[col])
    g = s.groupby(["kind", "d"])[col].mean().reset_index()
    res = {}
    for k in ("weekend", "weeknight"):
        x = g[g.kind == k][col]
        res[k] = (x.mean(), x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan, len(x), int((s.kind == k).sum()))
    (mw, sw, nw, cw), (mn, sn, nn, cn) = res["weekend"], res["weeknight"]
    t = (mw - mn) / np.sqrt(sw ** 2 + sn ** 2)
    row = {"test": label, "weekend_mean": round(mw, 2), "weekend_se": round(sw, 2), "weekend_days": nw, "weekend_obs": cw,
           "weeknight_mean": round(mn, 2), "weeknight_se": round(sn, 2), "weeknight_days": nn, "weeknight_obs": cn,
           "diff": round(mw - mn, 2), "t": round(t, 2)}
    row["weekend_median"] = round(g[g.kind == "weekend"][col].median(), 2)
    row["weeknight_median"] = round(g[g.kind == "weeknight"][col].median(), 2)
    print(f"{label:58s} weekend {mw:+7.2f} (±{sw:4.2f}, {nw} days)  weeknight {mn:+7.2f} (±{sn:4.2f}, {nn} days)  diff {mw - mn:+6.2f}  t {t:+5.2f}  medians {row['weekend_median']:+6.2f} / {row['weeknight_median']:+6.2f}")
    return row

print(f"\n=== {SYM}: long-option returns in % of premium (a seller earns the negative) ===")
rows = []
near = lambda dte: p.dte.isin([dte]) if isinstance(dte, int) else p.dte.isin(dte)
for cp, name in ((-1, "puts"), (1, "calls")):
    for lo, hi in ((0.10, 0.30), (0.40, 0.60)):
        base = p[(p.cp == cp) & (p.absd >= lo) & (p.absd < hi)]
        # weekend from Friday (7 days to expiry) vs the weeknights either side of it (8–11 and 1–4 days)
        w7 = base[((base.kind == "weekend") & (base.dte == 7)) | ((base.kind == "weeknight") & base.dte.isin([1, 2, 3, 4, 8, 9, 10, 11]))]
        rows.append(compare(w7, "hedged_cc", f"{name} |d| {lo:.2f}-{hi:.2f}, hedged, close->close"))
        rows.append(compare(w7, "hedged_co", f"{name} |d| {lo:.2f}-{hi:.2f}, hedged, close->10:00"))
        rows.append(compare(w7, "unhedged_cc", f"{name} |d| {lo:.2f}-{hi:.2f}, unhedged, close->close"))
        rows.append(compare(w7, "unhedged_co", f"{name} |d| {lo:.2f}-{hi:.2f}, unhedged, close->10:00"))
out["returns"] = rows
print(f"\n=== {SYM}: the same, without periods where the stock moved more than 4% ===")
calm_rows = []
pc = p[p.move <= 0.04]
for cp, name in ((-1, "puts"), (1, "calls")):
    for lo, hi in ((0.10, 0.30), (0.40, 0.60)):
        base = pc[(pc.cp == cp) & (pc.absd >= lo) & (pc.absd < hi)]
        w7 = base[((base.kind == "weekend") & (base.dte == 7)) | ((base.kind == "weeknight") & base.dte.isin([1, 2, 3, 4, 8, 9, 10, 11]))]
        calm_rows.append(compare(w7, "hedged_cc", f"{name} |d| {lo:.2f}-{hi:.2f}, hedged, close->close"))
        calm_rows.append(compare(w7, "hedged_co", f"{name} |d| {lo:.2f}-{hi:.2f}, hedged, close->10:00"))
out["returns_calm"] = calm_rows

# ---------- (2) the Steward: Monday ~10:00 for this Friday vs Friday's close for next Friday ----------
# trading days only: the feed carries Saturday test-session prints (INTC/GM puts at $9-10 on
# Saturday 1 Jun 2024), and a stop is never fired on a single print
hourly = opt[(opt.h >= 9) & (opt.h <= 15) & opt.d.isin(set(days))].sort_values("t")
by_sym = {s: g[["t", "d", "h", "c", "n"]].to_numpy() for s, g in hourly.groupby("sym")}
expiries = sorted(con.exp.unique())
T_DELTA, BAND, FLOOR = -0.20, (-0.21, -0.12), 0.0015

def pick(cands, floor=True):
    c = cands[(cands.dl >= BAND[0]) & (cands.dl <= BAND[1])]
    if floor: c = c[c.O / c.K >= FLOOR]
    if c.empty: return None
    return c.iloc[(c.dl - T_DELTA).abs().argsort().iloc[0]]

def candidates(exp, day, at):
    """Puts for `exp` priced at `day`'s ~10:00 (at=10) or ~16:00 (at=16) bar."""
    h = 9 if at == 10 else 15
    rows_ = opt[(opt.exp == exp) & (opt.cp == -1) & (opt.d == day) & (opt.h == h) & (opt.n >= 1)].drop_duplicates("sym")
    if rows_.empty: return rows_
    S = S10.get(day) if at == 10 else S16.get(day)
    if S is None or np.isnan(S): return rows_.iloc[0:0]
    hrs = (exp - day).days * 24 + (6 if at == 10 else 0)
    T = hrs / 24 / 365
    if T <= 0: return rows_.iloc[0:0]
    r = rows_.rename(columns={"c": "O"}).copy()
    r = r[r.O >= 0.05]
    r["S"] = S; r["iv"] = bs.iv(r.O.values, S, r.K.values, T, R, Q, -1)
    r = r[r.iv.notna()].copy()
    r["dl"] = bs.delta(S, r.K.values, T, R, Q, r.iv.values, -1)
    return r

def run_trade(c, entry_t, exp):
    """Sell at entry, then the Steward's exits on each hourly close: buy back at 35% of the credit
    (take profit) or at 2x (stop); otherwise settle at expiry against the underlying's close."""
    credit = c.O - COST
    path = by_sym.get(c.sym)
    weekend_mark = None
    for t, d, h, px, n in path:
        if t <= entry_t: continue
        if n < 2: continue
        if weekend_mark is None and h == 9: weekend_mark = px          # first ~10:00 mark after entry
        if px <= 0.35 * c.O: return credit - (px + COST), "take_profit", weekend_mark
        if px >= 2.0 * c.O: return credit - (px + COST), "stop", weekend_mark
    sE = S16.get(exp)
    return credit - max(c.K - sE, 0.0), ("assigned" if sE < c.K else "expired"), weekend_mark

trades = []
for exp in expiries:
    wk = [d for d in days if exp - dt.timedelta(days=exp.weekday()) <= d <= exp]
    prev = [d for d in days if exp - dt.timedelta(days=14) < d < exp - dt.timedelta(days=exp.weekday())]
    if not wk or not prev: continue
    mon, fri_prev = wk[0], prev[-1]
    for floor in (True, False):
        for policy, day, at in (("A: Monday 10:00, this Friday", mon, 10), ("B: Friday close, next Friday", fri_prev, 16)):
            cands = candidates(exp, day, at)
            if cands.empty: continue
            c = pick(cands, floor)
            if c is None:
                trades.append({"exp": exp, "policy": policy, "floor": floor, "traded": False}); continue
            entry_t = pd.Timestamp(dt.datetime.combine(day, dt.time(9 if at == 10 else 15, 59)), tz="America/New_York")
            pnl, how, wmark = run_trade(c, entry_t, exp)
            trades.append({"exp": exp, "policy": policy, "floor": floor, "traded": True, "K": c.K, "credit": c.O,
                           "delta": c.dl, "pnl": pnl, "ret": pnl / c.K * 100, "how": how,
                           "weekend_leg": (c.O - COST - (wmark + COST)) / c.K * 100 if (wmark is not None and at == 16) else np.nan})
tr = pd.DataFrame(trades)
tr.to_pickle(DATA / f"{SYM}_steward_trades.pkl")
print(f"\n=== {SYM}: the Steward's weekly 20-delta put, % of cash secured per week (after $0.01/share each side) ===")
summ = []
for floor in (True, False):
    for policy in ("A: Monday 10:00, this Friday", "B: Friday close, next Friday"):
        x = tr[(tr.policy == policy) & (tr.floor == floor)]
        t_ = x[x.traded]
        if t_.empty: continue
        r = t_.ret
        row = {"policy": policy, "premium_floor": floor, "weeks_offered": len(x), "weeks_traded": len(t_),
               "mean_pct_week": round(r.mean(), 4), "sd": round(r.std(), 4), "hit_rate": round((r > 0).mean(), 3),
               "worst_week": round(r.min(), 3), "total_pct": round(r.sum(), 2),
               "sharpe_ann": round(r.mean() / r.std() * np.sqrt(52), 2) if r.std() > 0 else np.nan,
               "avg_credit": round(t_.credit.mean(), 2), "assigned": int((t_.how == "assigned").sum()),
               "stops": int((t_.how == "stop").sum()), "take_profits": int((t_.how == "take_profit").sum()),
               "weekend_leg_mean": round(t_.weekend_leg.mean(), 4) if t_.weekend_leg.notna().any() else None}
        summ.append(row)
        print(json.dumps(row))
out["steward"] = summ
# paired weeks: both policies traded the same expiry
pa = tr[tr.traded & ~tr.floor].pivot_table(index="exp", columns="policy", values="ret")
pa = pa.dropna()
if len(pa.columns) == 2:
    dif = pa.iloc[:, 1] - pa.iloc[:, 0]
    out["paired_no_floor"] = {"weeks": len(pa), "B_minus_A_mean": round(dif.mean(), 4),
                              "t": round(dif.mean() / (dif.std() / np.sqrt(len(dif))), 2)}
    print("paired weeks (no floor):", out["paired_no_floor"])
json.dump(out, open(DATA / f"{SYM}_summary.json", "w"), indent=1, default=str)
