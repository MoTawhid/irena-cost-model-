"""1. COST DATABASE: synthetic project-level generation, QA/verification pipeline, learning curves."""
import numpy as np, pandas as pd
from .config import *

def cum_series(t):
    p = TECH[t] if t in TECH else ENABLING[t]
    return {y: round(p["cum10"] * (p["cum24"] / p["cum10"]) ** ((y - 2010) / 14), 2) for y in YEARS}

def generate_raw(seed=SEED):
    rng = np.random.default_rng(seed); rows = []; pid = 0
    for t, p in TECH.items():
        b = np.log2(1 - p["lr"]) if p["lr"] > 0 else 0.0
        shock = {y: rng.normal(0, .03) for y in YEARS}
        cum = cum_series(t)
        for y in YEARS:
            capex_y = p["capex"] * (cum[y] / p["cum24"]) ** b if p["lr"] > 0 else p["capex"] * (1 + p["drift"]) ** (y - 2024)
            cf_y = np.interp(y, [2010, 2024], [p["cf10"], p["cf24"]])
            fom_y = p["fom"] * (1 + .012 * (2024 - y))
            for _ in range(rng.integers(8, 15)):
                c = rng.choice(TECH_COUNTRIES[t]); reg, m = COUNTRIES[c]; pid += 1
                rows.append(dict(project_id=f"P{pid:04d}", technology=t, country=c, region=reg, year=y,
                    capacity_mw=round(float(p["size"] * rng.lognormal(0, .6)), 1),
                    capex_usd_kw=round(float(capex_y * m * np.exp(rng.normal(0, .10) + shock[y])), 0),
                    cf=round(float(np.clip(cf_y * rng.lognormal(0, .08), .05, .95)), 3),
                    fom_usd_kw_yr=round(float(fom_y * m ** .5 * np.exp(rng.normal(0, .10))), 1),
                    var_cost_usd_mwh=round(float(p["var"] * np.exp(rng.normal(0, .10))), 1),
                    life_yrs=p["life"]))
    df = pd.DataFrame(rows)
    # ---- inject realistic data problems to exercise QA ----
    n = len(df); pick = lambda k: rng.choice(n, k, replace=False)
    df.loc[pick(8), "capex_usd_kw"] *= 1000            # unit error (USD/MW)
    df.loc[pick(8), "cf"] *= 100                        # % instead of fraction
    i = pick(8); df.loc[i, "capex_usd_kw"] = (df.loc[i, "capex_usd_kw"] * rng.choice([2.8, .33], 8)).round(0)  # outliers
    df.loc[pick(10), "cf"] = np.nan                     # missing
    df.loc[pick(5), "capex_usd_kw"] = np.nan
    df.loc[pick(3), "cf"] = 1.3                         # impossible
    df.loc[pick(2), "capex_usd_kw"] = -500
    df = pd.concat([df, df.iloc[pick(12)]], ignore_index=True)  # duplicates
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)

def run_qa(raw):
    """Sequential checks: duplicates -> missing -> unit fixes -> plausibility ranges -> robust outliers."""
    df = raw.copy(); log = []
    def L(r, check, action, field, orig, new=""): log.append(dict(project_id=r.project_id, technology=r.technology, year=r.year,
                                                                   check=check, action=action, field=field, original=orig, corrected=new))
    dup = df.duplicated("project_id", keep="first")
    for r in df[dup].itertuples(): L(r, "Duplicate ID", "Removed", "project_id", r.project_id)
    df = df[~dup].copy(); df["qa_status"] = "OK"
    for f in ["capex_usd_kw", "cf"]:
        m = df[f].isna()
        for r in df[m].itertuples(): L(r, "Missing value", "Excluded", f, "blank")
        df = df[~m]
    for idx, r in df.iterrows():  # unit fixes
        lo, hi, clo, chi = BOUNDS[r.technology]
        if 1 < r.cf <= 100 and clo <= r.cf / 100 <= chi:
            L(r, "Unit (% vs fraction)", "Corrected", "cf", r.cf, r.cf / 100); df.loc[idx, ["cf", "qa_status"]] = [r.cf / 100, "Corrected: CF unit"]
        if r.capex_usd_kw > 20 * hi and lo <= r.capex_usd_kw / 1000 <= hi:
            L(r, "Unit (USD/MW vs USD/kW)", "Corrected", "capex_usd_kw", r.capex_usd_kw, r.capex_usd_kw / 1000)
            df.loc[idx, ["capex_usd_kw", "qa_status"]] = [r.capex_usd_kw / 1000, "Corrected: capex unit"]
    bad = pd.Series(False, index=df.index)
    for idx, r in df.iterrows():
        lo, hi, clo, chi = BOUNDS[r.technology]
        if not (lo <= r.capex_usd_kw <= hi): L(r, "Range check", "Excluded", "capex_usd_kw", r.capex_usd_kw); bad[idx] = True
        elif not (clo <= r.cf <= chi): L(r, "Range check", "Excluded", "cf", r.cf); bad[idx] = True
    df = df[~bad].copy()
    df["lncap"] = np.log(df.capex_usd_kw)
    med = df.groupby(["technology", "year"])["lncap"].transform("median")
    mad = (df.lncap - med).abs().groupby([df.technology, df.year]).transform("median")
    z = 0.6745 * (df.lncap - med) / mad.replace(0, np.nan)
    out = z.abs() > 5
    for r in df[out].itertuples(): L(r, "Robust outlier (MAD z>5)", "Excluded", "capex_usd_kw", r.capex_usd_kw)
    df = df[~out].drop(columns="lncap").sort_values(["technology", "year", "project_id"]).reset_index(drop=True)
    return df, pd.DataFrame(log)

def generate_enabling(seed=SEED):
    rng = np.random.default_rng(seed + 1); rows = []; pid = 0
    for t, p in ENABLING.items():
        b = np.log2(1 - p["lr"]); cum = cum_series(t)
        for y in YEARS:
            for _ in range(rng.integers(6, 11)):
                c = rng.choice(list(COUNTRIES)); pid += 1
                eff = np.interp(y, [2010, 2024], p["eff"] if "BESS" in t else p["eff"][::-1])
                rows.append(dict(project_id=f"E{pid:04d}", technology=t, country=c, year=y,
                    size_mw=round(float(rng.lognormal(np.log(60 if "BESS" in t else 20), .6)), 1),
                    capex=round(float(p["capex"] * (cum[y] / p["cum24"]) ** b * COUNTRIES[c][1] ** .7 * np.exp(rng.normal(0, .10))), 0),
                    unit=p["unit"], efficiency=round(float(eff * rng.normal(1, .01)), 3), qa_status="OK"))
    return pd.DataFrame(rows)

def weighted(df, col, by):
    d = df.assign(_w=df.capacity_mw, _x=df[col] * df.capacity_mw).groupby(by)[["_x", "_w"]].sum()
    return d._x / d._w

def baseline_assumptions(clean, year=BASE_YEAR):
    d = clean[clean.year == year]
    out = pd.DataFrame({c: weighted(d, c, "technology") for c in ["capex_usd_kw", "cf", "fom_usd_kw_yr", "var_cost_usd_mwh"]}).loc[GEN_TECHS]
    out.columns = ["capex", "cf", "fom", "var"]
    for k in ["life", "degr", "constr"]: out[k] = [TECH[t][k] for t in out.index]
    out["wacc"] = WACC_BASE
    return out

def learning_curves(clean):
    rows = []
    for t in GEN_TECHS:
        capex = weighted(clean[clean.technology == t], "capex_usd_kw", "year")
        x = np.log(pd.Series(cum_series(t)).loc[capex.index]); y = np.log(capex)
        slope = np.polyfit(x, y, 1)[0]; r2 = np.corrcoef(x, y)[0, 1] ** 2; lr = 1 - 2 ** slope
        rows.append(dict(technology=t, slope=slope, fitted_lr=lr, r2=r2, adopted_lr=max(0, lr) if r2 >= LR_MIN_R2 else 0.0))
    return pd.DataFrame(rows).set_index("technology")
