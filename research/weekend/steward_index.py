"""The Steward on index funds (docs/STEWARD_INDEX_PREREG.md, 12 Nov 2026). Three arms over the same
weekly expiries: N (cash-secured puts on his twelve names), N10 (the same without earnings weeks)
and X (put spreads on SPY, QQQ, IWM sized to a $5,000 worst case a fund).

    steward_index.py [COST]      reads data/<SYM>_opt.pkl and data/<SYM>_stk.pkl from fetch.py;
                                 writes data/steward_index_<cost>.json and prints the tables"""
import sys, json, datetime as dt
import numpy as np, pandas as pd
import bs
from alp import DATA

COST = float(sys.argv[1]) if len(sys.argv) > 1 else 0.01      # per share, every fill, each leg
NAMES = ["XOM", "CVX", "KO", "WMT", "BAC", "DIS", "UBER", "PFE", "CSCO", "INTC", "T", "GM"]
FUNDS = {"SPY": 0.012, "QQQ": 0.006, "IWM": 0.012}
R = 0.045
FIRST, LAST = dt.date(2024, 3, 22), dt.date(2026, 11, 6)
T_DELTA, BAND, FLOOR = -0.20, (-0.21, -0.12), 0.0015
WING, MIN_CREDIT_OF_WIDTH, RISK = -0.10, 0.10, 5_000.0
SLEEVE = 70_000.0
FALL = (dt.date(2026, 10, 9), dt.date(2026, 11, 6))            # the expiries of the weeks 6 Oct to 6 Nov 2026


def load(sym):
    opt = pd.read_pickle(DATA / f"{sym}_opt.pkl"); stk = pd.read_pickle(DATA / f"{sym}_stk.pkl")
    L = len(sym)
    con = pd.DataFrame({"sym": opt.sym.unique()})
    con["exp"] = pd.to_datetime(con.sym.str[L:L + 6], format="%y%m%d").dt.date
    con["cp"] = np.where(con.sym.str[L + 6] == "C", 1, -1)
    con["K"] = con.sym.str[L + 7:].astype(int) / 1000
    opt = opt.merge(con[con.cp == -1], on="sym")
    opt["d"] = opt.t.dt.date; opt["h"] = opt.t.dt.hour
    stk["d"] = stk.t.dt.date; stk["h"] = stk.t.dt.hour
    days = sorted(set(stk[stk.h == 9].d))
    S16 = stk[stk.h == 15].drop_duplicates("d").set_index("d").c
    S10 = stk[stk.h == 9].drop_duplicates("d").set_index("d").c
    hourly = opt[(opt.h >= 9) & (opt.h <= 15) & opt.d.isin(set(days))].sort_values("t")
    by_sym = {s: g[["t", "c", "n"]] for s, g in hourly.groupby("sym")}
    return opt, days, S10, S16, by_sym, sorted(e for e in con.exp.unique() if FIRST <= e <= LAST)


def candidates(opt, exp, day, S, q):
    r = opt[(opt.exp == exp) & (opt.d == day) & (opt.h == 9) & (opt.n >= 1)].drop_duplicates("sym")
    if r.empty or S is None or np.isnan(S):
        return r.iloc[0:0]
    T = ((exp - day).days * 24 + 6) / 24 / 365
    if T <= 0:
        return r.iloc[0:0]
    r = r.rename(columns={"c": "O"}).copy()
    r = r[r.O >= 0.05]
    r["iv"] = bs.iv(r.O.values, S, r.K.values, T, R, q, -1)
    r = r[r.iv.notna()].copy()
    r["dl"] = bs.delta(S, r.K.values, T, R, q, r.iv.values, -1)
    return r


def pick_short(c, floor):
    if c.empty or "dl" not in c:      # no priced put that morning
        return None
    c = c[(c.dl >= BAND[0]) & (c.dl <= BAND[1])]
    if floor:
        c = c[c.O / c.K >= FLOOR]
    return None if c.empty else c.iloc[(c.dl - T_DELTA).abs().argsort().iloc[0]]


def run_put(c, entry_t, by_sym, sE):
    """One cash-secured put, dollars a contract."""
    credit = c.O - COST
    p = by_sym[c.sym]
    for t, px, n in p[p.t > entry_t].itertuples(index=False):
        if n < 2:
            continue
        if px <= 0.35 * c.O:
            return (credit - (px + COST)) * 100, "take_profit"
        if px >= 2.0 * c.O:
            return (credit - (px + COST)) * 100, "stop"
    return (credit - max(c.K - sE, 0.0)) * 100, ("assigned" if sE < c.K else "expired")


def run_spread(s, l, entry_t, by_sym, sE):
    """One put spread, dollars a spread. The price is short less long on hours both legs printed."""
    credit0 = s.O - l.O
    credit = credit0 - 2 * COST
    a = by_sym[s.sym]; b = by_sym[l.sym]
    m = a[(a.t > entry_t) & (a.n >= 2)].merge(b[b.t > entry_t], on="t", suffixes=("_s", "_l"))
    for t, cs, ns, cl, nl in m.itertuples(index=False):
        px = cs - cl
        if px <= 0.35 * credit0:
            return (credit - (px + 2 * COST)) * 100, "take_profit"
        if px >= 2.0 * credit0:
            return (credit - (px + 2 * COST)) * 100, "stop"
    return (credit - max(s.K - sE, 0.0) + max(l.K - sE, 0.0)) * 100, ("in the money" if sE < s.K else "expired")


def earnings_history(sym):
    import yfinance as yf
    df = yf.Ticker(sym).get_earnings_dates(limit=24)
    return sorted({d.date() for d in df.index}) if df is not None and len(df) else []


def arm_names():
    rows, missing = [], []
    for sym in NAMES:
        try:
            opt, days, S10, S16, by_sym, expiries = load(sym)
        except FileNotFoundError:
            missing.append(sym); continue
        try:
            earn = earnings_history(sym)
        except Exception as e:
            earn = None; print(f"{sym}: no earnings history ({str(e)[:80]})")
        for exp in expiries:
            wk = [d for d in days if exp - dt.timedelta(days=exp.weekday()) <= d <= exp]
            if not wk or exp not in S16.index:
                continue
            mon = wk[0]
            c = pick_short(candidates(opt, exp, mon, S10.get(mon), 0.0), floor=True)
            if c is None:
                continue
            entry_t = pd.Timestamp(dt.datetime.combine(mon, dt.time(9, 59)), tz="America/New_York")
            pnl, how = run_put(c, entry_t, by_sym, S16.get(exp))
            rows.append({"arm": "N", "sym": sym, "exp": exp, "pnl": pnl, "how": how, "risk": c.K * 100,
                         "earnings": None if earn is None else any(mon <= e <= exp for e in earn)})
    return pd.DataFrame(rows), missing


def arm_funds():
    rows, missing = [], []
    for sym, q in FUNDS.items():
        try:
            opt, days, S10, S16, by_sym, expiries = load(sym)
        except FileNotFoundError:
            missing.append(sym); continue
        for exp in expiries:
            wk = [d for d in days if exp - dt.timedelta(days=exp.weekday()) <= d <= exp]
            if not wk or exp not in S16.index:
                continue
            mon = wk[0]
            cands = candidates(opt, exp, mon, S10.get(mon), q)
            s = pick_short(cands, floor=False)
            if s is None:
                continue
            wings = cands[cands.K < s.K]
            if wings.empty:
                continue
            l = wings.iloc[(wings.dl - WING).abs().argsort().iloc[0]]
            width, credit = s.K - l.K, s.O - l.O
            if credit <= 0 or credit < MIN_CREDIT_OF_WIDTH * width:
                continue
            qty = max(1, int(RISK // ((width - credit) * 100)))
            entry_t = pd.Timestamp(dt.datetime.combine(mon, dt.time(9, 59)), tz="America/New_York")
            pnl, how = run_spread(s, l, entry_t, by_sym, S16.get(exp))
            rows.append({"arm": "X", "sym": sym, "exp": exp, "pnl": pnl * qty, "how": how, "qty": qty,
                         "risk": (width - credit) * 100 * qty, "width": width, "credit": credit})
    return pd.DataFrame(rows), missing


def book(df, label):
    """One arm as one book: dollars by expiry week."""
    if df.empty:
        return {"arm": label, "trades": 0}
    w = df.groupby("exp").pnl.sum().sort_index()
    yrs = (w.index[-1] - w.index[0]).days / 365.25
    run = w.cumsum(); fall = float((run - run.cummax()).min())
    mid = w.index[len(w) // 2]
    fallw = w[(w.index >= FALL[0]) & (w.index <= FALL[1])]
    return {"arm": label, "trades": len(df), "weeks": len(w), "total": round(float(w.sum())),
            "a_year": round(float(w.sum()) / yrs), "pct_of_sleeve_a_year": round(float(w.sum()) / yrs / SLEEVE * 100, 2),
            "trades_won": round(float((df.pnl > 0).mean()), 3), "weeks_won": round(float((w > 0).mean()), 3),
            "worst_week": round(float(w.min())), "deepest_fall": round(fall),
            "first_half": round(float(w[w.index < mid].sum())), "second_half": round(float(w[w.index >= mid].sum())),
            "oct_nov_2026": round(float(fallw.sum())), "avg_risk_a_week": round(float(df.groupby("exp").risk.sum().mean())),
            "exits": df.how.value_counts().to_dict()}


if __name__ == "__main__":
    n, miss_n = arm_names(); x, miss_x = arm_funds()
    out = {"cost": COST, "missing": miss_n + miss_x, "arms": []}
    out["arms"].append(book(n, "N"))
    if not n.empty and n.earnings.notna().all():
        out["arms"].append(book(n[~n.earnings.astype(bool)], "N10"))
        out["earnings_weeks_dropped"] = int(n.earnings.astype(bool).sum())
        out["earnings_weeks_pnl"] = round(float(n[n.earnings.astype(bool)].pnl.sum()))
    else:
        out["n10"] = "not run: no earnings history for " + ", ".join(sorted(n[n.earnings.isna()].sym.unique())) if not n.empty else "no data"
    out["arms"].append(book(x, "X"))
    out["by_fund"] = {s: book(g, s) for s, g in x.groupby("sym")} if not x.empty else {}
    out["by_name"] = {s: round(float(g.pnl.sum())) for s, g in n.groupby("sym")} if not n.empty else {}
    if not x.empty:
        out["spread_shape"] = {s: {"avg_width": round(float(g.width.mean()), 2), "avg_credit": round(float(g.credit.mean()), 2),
                                   "avg_qty": round(float(g.qty.mean()), 1)} for s, g in x.groupby("sym")}
    json.dump(out, open(DATA / f"steward_index_{COST:.2f}.json", "w"), indent=1, default=str)
    for a in out["arms"]:
        print(json.dumps(a, default=str))
    for k in ("missing", "earnings_weeks_dropped", "earnings_weeks_pnl", "n10", "by_fund", "by_name", "spread_shape"):
        if k in out:
            print(k, json.dumps(out[k], default=str))
