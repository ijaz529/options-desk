"""Pool the Steward's names: weekend vs weeknight option returns, and the two put-selling cycles
run as one book (all names each week, as the Steward does).

    pool.py NAME [NAME ...]      reads data/<NAME>_*.pkl from analyse.py; writes data/POOL_summary.json"""
import sys, json
import numpy as np, pandas as pd
from alp import DATA

NAMES = sys.argv[1:]
P, T = [], []
for n in NAMES:
    try:
        p = pd.read_pickle(DATA / f"{n}_periods.pkl"); p["name"] = n; P.append(p)
        t = pd.read_pickle(DATA / f"{n}_steward_trades.pkl"); t["name"] = n; T.append(t)
    except FileNotFoundError:
        print("missing", n)
p = pd.concat(P); tr = pd.concat(T)
out = {"names": NAMES}

def compare(sub, col, label):
    s = sub.dropna(subset=[col])
    g = s.groupby(["kind", "d"])[col].mean().reset_index()
    r = {}
    for k in ("weekend", "weeknight"):
        x = g[g.kind == k][col]
        r[k] = (x.mean(), x.std(ddof=1) / np.sqrt(len(x)), len(x), x.median(), int((s.kind == k).sum()))
    (mw, sw, nw, dw, cw), (mn, sn, nn, dn, cn) = r["weekend"], r["weeknight"]
    t = (mw - mn) / np.sqrt(sw ** 2 + sn ** 2)
    print(f"{label:60s} weekend {mw:+7.2f} (±{sw:4.2f}, {nw}d, {cw} obs)  weeknight {mn:+7.2f} (±{sn:4.2f}, {nn}d)  diff {mw - mn:+6.2f}  t {t:+5.2f}  medians {dw:+6.2f}/{dn:+6.2f}")
    return {"test": label, "weekend": round(mw, 2), "weekend_se": round(sw, 2), "weeknight": round(mn, 2),
            "weeknight_se": round(sn, 2), "diff": round(mw - mn, 2), "t": round(t, 2),
            "weekend_median": round(dw, 2), "weeknight_median": round(dn, 2), "weekend_days": nw, "weeknight_days": nn}

print("=== pooled names: long-option returns, % of premium (a seller earns the negative) ===")
rows = []
for calm in (False, True):
    pc = p[p.move <= 0.04] if calm else p
    tag = " [no 4%+ moves]" if calm else ""
    for cp, name in ((-1, "puts"), (1, "calls")):
        for lo, hi in ((0.10, 0.30), (0.40, 0.60)):
            base = pc[(pc.cp == cp) & (pc.absd >= lo) & (pc.absd < hi)]
            w7 = base[((base.kind == "weekend") & (base.dte == 7)) | ((base.kind == "weeknight") & base.dte.isin([1, 2, 3, 4, 8, 9, 10, 11]))]
            for col, how in (("hedged_cc", "hedged, close->close"), ("unhedged_cc", "unhedged, close->close")):
                rows.append(compare(w7, col, f"{name} |d| {lo:.2f}-{hi:.2f}, {how}{tag}"))
out["returns"] = rows

print("\n=== pooled names: the Steward's weekly put, % of cash secured (after $0.01/share each side) ===")
summ = []
for floor in (True, False):
    for pol in ("A: Monday 10:00, this Friday", "B: Friday close, next Friday"):
        x = tr[(tr.policy == pol) & (tr.floor == floor) & tr.traded]
        if x.empty: continue
        book = x.groupby("exp").ret.mean()          # the week's book: every name traded that week, equal cash
        row = {"policy": pol, "premium_floor": floor, "positions": len(x),
               "position_mean": round(x.ret.mean(), 4), "position_hit": round((x.ret > 0).mean(), 3),
               "position_worst": round(x.ret.min(), 2), "assigned": int((x.how == "assigned").sum()),
               "stops": int((x.how == "stop").sum()), "take_profits": int((x.how == "take_profit").sum()),
               "weeks": len(book), "book_mean_pct_week": round(book.mean(), 4), "book_sd": round(book.std(), 4),
               "book_worst_week": round(book.min(), 3), "book_sharpe_ann": round(book.mean() / book.std() * np.sqrt(52), 2),
               "book_total_pct": round(book.sum(), 2),
               "weekend_leg_mean": round(x.weekend_leg.mean(), 4) if x.weekend_leg.notna().any() else None}
        summ.append(row); print(json.dumps(row))
out["steward"] = summ
for floor in (True, False):
    x = tr[tr.traded & (tr.floor == floor)]
    pa = x.pivot_table(index=["name", "exp"], columns="policy", values="ret").dropna()
    if pa.shape[1] == 2:
        dif = pa["B: Friday close, next Friday"] - pa["A: Monday 10:00, this Friday"]
        wk = dif.groupby(level="exp").mean()
        r = {"premium_floor": floor, "paired_positions": len(dif), "B_minus_A_mean": round(dif.mean(), 4),
             "t_by_week": round(wk.mean() / (wk.std() / np.sqrt(len(wk))), 2), "weeks": len(wk)}
        print("paired (same name, same expiry):", r); out.setdefault("paired", []).append(r)
json.dump(out, open(DATA / "POOL_summary.json", "w"), indent=1, default=str)
