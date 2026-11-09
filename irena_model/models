"""2-5. COST MODELLING, SCENARIOS, SENSITIVITY, FINANCIAL MODEL."""
import numpy as np, pandas as pd
from scipy.optimize import brentq
from .config import *

# ---------------------------------------------------------------- 2. LCOE methodologies
def crf(r, n): return r * (1 + r) ** n / ((1 + r) ** n - 1)

def lcoe_crf(capex, fom, var, cf, wacc, life, constr=0.0, hours=HOURS):
    """Method 1 (constr=0) / Method 3 (IDC approximation): annuitised capex + O&M, USD/MWh."""
    return (capex * (1 + wacc * constr / 2) * crf(wacc, life) + fom) / (cf * hours / 1000) + var

def lcoe_dcf(capex, fom, var, cf, wacc, life, degr=0.0, hours=HOURS):
    """Method 2: explicit year-by-year discounted cash-flow LCOE with output degradation."""
    t = np.arange(1, int(life) + 1); df = (1 + wacc) ** -t
    energy = cf * hours / 1000 * (1 - degr) ** (t - 1)
    return (capex + (fom * df).sum() + (var * energy * df).sum()) / (energy * df).sum()

def lcoe_components(capex, fom, var, cf, wacc, life):
    e = cf * HOURS / 1000
    return dict(capital=capex * crf(wacc, life) / e, fixed_om=fom / e, variable=var)

def lcoe_table(a):
    rows = []
    for t, r in a.iterrows():
        k = dict(capex=r.capex, fom=r.fom, var=r["var"], cf=r.cf, wacc=r.wacc, life=r.life)
        rows.append(dict(technology=t, lcoe_crf=lcoe_crf(**k), lcoe_dcf_degr=lcoe_dcf(**k, degr=r.degr),
                         lcoe_idc=lcoe_crf(**k, constr=r.constr), **lcoe_components(**k)))
    return pd.DataFrame(rows).set_index("technology")

# ---------------------------------------------------------------- 3. Scenario tool
def run_scenarios(a, lr_adopted):
    rows = []
    for s, (gm, dlr, cm, dw, cfm, om, _) in SCENARIOS.items():
        for t in GEN_TECHS:
            r = a.loc[t]; p = TECH[t]; g1, g2 = p["g1"] * gm, p["g2"] * gm
            lr0 = lr_adopted[t]; lr = 0 if lr0 == 0 else max(0, lr0 + dlr); b = np.log2(1 - lr)
            for y in SCEN_YEARS:
                cum = (1 + g1) ** (min(y, GROWTH_BREAK_YEAR) - BASE_YEAR) * (1 + g2) ** max(0, y - GROWTH_BREAK_YEAR)
                f = y > BASE_YEAR
                capex = r.capex * cum ** b * (cm if f else 1); wacc = r.wacc + (dw if f else 0)
                cf = min(.95, r.cf * (cfm if f else 1)); k = om if f else 1
                rows.append(dict(scenario=s, technology=t, year=y, cum_multiple=cum, capex=capex, wacc=wacc, cf=cf,
                                 lcoe=lcoe_crf(capex, r.fom * k, r["var"] * k, cf, wacc, r.life)))
    return pd.DataFrame(rows)

# ---------------------------------------------------------------- 4. Sensitivity
def tornado(r, rel=.20, dw=.02, dl=5):
    base = dict(capex=r.capex, fom=r.fom, var=r["var"], cf=r.cf, wacc=r.wacc, life=r.life)
    b0 = lcoe_crf(**base); rows = []
    for d, (lo, hi) in {"capex": (base["capex"] * (1 - rel), base["capex"] * (1 + rel)),
                        "cf": (base["cf"] * (1 - rel), min(.95, base["cf"] * (1 + rel))),
                        "fom": (base["fom"] * (1 - rel), base["fom"] * (1 + rel)),
                        "var": (base["var"] * (1 - rel), base["var"] * (1 + rel)),
                        "wacc": (base["wacc"] - dw, base["wacc"] + dw),
                        "life": (base["life"] - dl, base["life"] + dl)}.items():
        l, h = lcoe_crf(**{**base, d: lo}), lcoe_crf(**{**base, d: hi})
        rows.append(dict(driver=d, low_input=lo, high_input=hi, lcoe_low_input=l, lcoe_high_input=h, swing=abs(h - l)))
    return b0, pd.DataFrame(rows).sort_values("swing", ascending=False)

def two_way(r, capex_chg=(-.4, -.2, 0, .2, .4), waccs=(.04, .06, .08, .10, .12)):
    return pd.DataFrame({f"{c:+.0%}": [lcoe_crf(r.capex * (1 + c), r.fom, r["var"], r.cf, w, r.life) for w in waccs] for c in capex_chg},
                        index=[f"{w:.0%}" for w in waccs])

def monte_carlo(r, n=20000, seed=SEED):
    rng = np.random.default_rng(seed)
    s = pd.DataFrame(dict(capex=r.capex * rng.lognormal(0, .15, n), cf=np.clip(r.cf * rng.normal(1, .08, n), .05, .95),
                          fom=r.fom * rng.lognormal(0, .20, n), wacc=rng.triangular(r.wacc - .02, r.wacc, r.wacc + .03, n)))
    s["lcoe"] = lcoe_crf(s.capex, s.fom, r["var"], s.cf, s.wacc, r.life)
    rc = s.corr(method="spearman")["lcoe"].drop("lcoe")
    return s, dict(mean=s.lcoe.mean(), std=s.lcoe.std(), p5=s.lcoe.quantile(.05), p50=s.lcoe.median(), p95=s.lcoe.quantile(.95),
                   **{f"rho_{k}": v for k, v in rc.items()}, top_driver=rc.abs().idxmax())

# ---------------------------------------------------------------- 5. Project finance
FIN_DEFAULTS = dict(cap_mw=100, ppa_prem=.15, esc=0.0, infl=.02, gearing=.70, kd=.06, tenor=18, tax=.25, dep_yrs=20, ke=.10)

def irr(cfs):
    f = lambda x: sum(c / (1 + x) ** i for i, c in enumerate(cfs))
    try: return brentq(f, -.9, 10.0)
    except ValueError: return np.nan

def project_finance(r, ppa=None, **kw):
    P = {**FIN_DEFAULTS, **kw}; life = int(r.life)
    if ppa is None: ppa = lcoe_crf(r.capex, r.fom, r["var"], r.cf, r.wacc, r.life) * (1 + P["ppa_prem"])
    capex_t = P["cap_mw"] * 1000 * r.capex / 1e6; debt = P["gearing"] * capex_t; ten = min(P["tenor"], life)
    ds = debt * P["kd"] / (1 - (1 + P["kd"]) ** -ten); dep_n = min(P["dep_yrs"], life)
    bal = debt; eq, pj, rows = [-(capex_t - debt)], [-capex_t], []
    for t in range(1, life + 1):
        gen = P["cap_mw"] * r.cf * HOURS * (1 - r.degr) ** (t - 1)
        rev = gen * ppa * (1 + P["esc"]) ** (t - 1) / 1e6
        opex = (P["cap_mw"] * 1000 * r.fom + gen * r["var"]) * (1 + P["infl"]) ** (t - 1) / 1e6
        ebitda = rev - opex; dep = capex_t / dep_n if t <= dep_n else 0
        d = ds if t <= ten else 0; intr = bal * P["kd"]; prin = d - intr if d else 0; bal -= prin
        tax = max(0, ebitda - dep - intr) * P["tax"]; cfads = ebitda - tax
        eq.append(cfads - d); pj.append(ebitda - max(0, ebitda - dep) * P["tax"])
        rows.append(dict(year=t, generation_mwh=gen, revenue=rev, opex=opex, ebitda=ebitda, debt_service=d, tax=tax, cfads=cfads,
                         dscr=cfads / d if d else np.nan, equity_cf=eq[-1]))
    df = pd.DataFrame(rows); cum = np.cumsum(eq)
    npv_e = sum(c / (1 + P["ke"]) ** i for i, c in enumerate(eq))
    m = dict(ppa=ppa, capex_usd_m=capex_t, project_irr=irr(pj), equity_irr=irr(eq), equity_npv=npv_e,
             min_dscr=df.dscr.min(), avg_dscr=df.dscr.mean(), payback=int((cum < 0).sum()) if cum[-1] >= 0 else np.nan)
    return df, m

def breakeven_ppa(r, target_irr=.10, **kw):
    def f(p):
        v = project_finance(r, ppa=p, **kw)[1]["equity_irr"]
        return (-0.9 if np.isnan(v) else v) - target_irr
    return brentq(f, 20, 400)
