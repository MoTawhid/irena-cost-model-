"""Run the full pipeline: data -> QA -> models -> Excel -> recalculation -> reconciliation -> figures."""
import sys, os, json, subprocess, numpy as np, pandas as pd
from openpyxl import load_workbook
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from irena_model.config import *
from irena_model.data import *
from irena_model.models import *
from irena_model.build_workbook import build

OUT = "outputs"; os.makedirs(f"{OUT}/data", exist_ok=True); os.makedirs(f"{OUT}/figures", exist_ok=True)
XLSX = f"{OUT}/IRENA_Cost_Model.xlsx"

raw = generate_raw(); clean, log = run_qa(raw); enabling = generate_enabling()
raw.to_csv(f"{OUT}/data/cost_db_raw.csv", index=False); clean.to_csv(f"{OUT}/data/cost_db_clean.csv", index=False)
log.to_csv(f"{OUT}/data/qa_log.csv", index=False); enabling.to_csv(f"{OUT}/data/enabling_db.csv", index=False)
a = baseline_assumptions(clean); lc = learning_curves(clean); lt = lcoe_table(a)
sc = run_scenarios(a, lc.adopted_lr)
mc, mcs = {}, {}
for t in GEN_TECHS: mcs[t], mc[t] = monte_carlo(a.loc[t])
rows = {}
for t in GEN_TECHS:
    r = a.loc[t]; _, m = project_finance(r)
    rows[t] = dict(lcoe=lt.loc[t, "lcoe_crf"], ppa=m["ppa"], project_irr=m["project_irr"], equity_irr=m["equity_irr"], equity_npv=m["equity_npv"],
                   min_dscr=m["min_dscr"], be_ppa=breakeven_ppa(r), be_ratio=breakeven_ppa(r) / lt.loc[t, "lcoe_crf"])
fin_tab = pd.DataFrame(rows).T
ow = a.loc["Onshore Wind"]; prem = [-.10, 0, .10, .20, .30]; gear = [.5, .6, .7, .8]
fin_grid = pd.DataFrame({f"{p:+.0%}": [project_finance(ow, ppa_prem=p, gearing=g)[1]["equity_irr"] for g in gear] for p in prem}, index=[f"{g:.0%}" for g in gear])
for n, d in dict(baseline_assumptions=a, learning_curves=lc, lcoe_methods=lt, scenarios=sc, finance_summary=fin_tab).items(): d.to_csv(f"{OUT}/data/{n}.csv")

build(XLSX, clean, log, enabling, a, lc, mc, fin_tab, fin_grid, len(raw))
res = subprocess.run(["python", "/mnt/skills/public/xlsx/scripts/recalc.py", XLSX, "120"], capture_output=True, text=True); print(res.stdout[-600:], res.stderr[-300:])

# ---------------- reconciliation: recalculated Excel vs independent Python ----------------
wb = load_workbook(XLSX, data_only=True); chk = []
def cmp(name, xl, py, tol=1e-6): chk.append((name, abs(xl - py) <= tol * max(1, abs(py)), xl, py))
for i, t in enumerate(GEN_TECHS):
    ws = wb["Assumptions"]
    for col, k in zip("BCDE", ["capex", "cf", "fom", "var"]): cmp(f"Assump {t} {k}", ws[f"{col}{7+i}"].value, a.loc[t, k])
    ws = wb["LCOE_Model"]
    for col, k in zip("KOP", ["lcoe_crf", "lcoe_dcf_degr", "lcoe_idc"]): cmp(f"LCOE {t} {k}", ws[f"{col}{6+i}"].value, lt.loc[t, k])
    cmp(f"LR {t}", wb["Assumptions"][f"J{7+i}"].value, lc.loc[t, "adopted_lr"])
ws = wb["Scen_Calc"]; r = 5
for s in SCENARIOS:
    for t in GEN_TECHS:
        for y in SCEN_YEARS:
            cmp(f"Scen {s}/{t}/{y}", ws[f"P{r}"].value, sc[(sc.scenario == s) & (sc.technology == t) & (sc.year == y)].lcoe.iloc[0]); r += 1
b0, tor = tornado(a.loc["Onshore Wind"]); ws = wb["Sensitivity"]; names = {"capex": 17, "cf": 18, "fom": 19, "var": 20, "wacc": 21, "life": 22}
cmp("Tornado base", ws["B11"].value, b0)
for d, row in tor.set_index("driver").iterrows(): cmp(f"Tornado {d}", ws[f"D{names[d]}"].value + ws[f"E{names[d]}"].value, row.lcoe_low_input + row.lcoe_high_input)
ws = wb["Fin_Model"]; _, m = project_finance(a.loc["Onshore Wind"])
for k, c in [("project_irr", "E8"), ("equity_irr", "E9"), ("equity_npv", "E10"), ("min_dscr", "E11"), ("capex_usd_m", "E4"), ("ppa", "B14")]: cmp(f"Fin {k}", ws[c].value, m[k], 1e-5)
cmp("DCF tie-out", wb["LCOE_DCF"]["B14"].value, 0, 1e-6); cmp("Scenario baseline check", wb["Scenarios"]["B50"].value, 0, 1e-6); cmp("Debt repaid", ws["E14"].value, 0, 1e-6)
bad = [c for c in chk if not c[1]]; print(f"Reconciliation: {len(chk)-len(bad)}/{len(chk)} checks passed"); [print("  FAIL", c) for c in bad]

# ---------------- figures ----------------
yr = pd.DataFrame({t: weighted(clean[clean.technology == t], "capex_usd_kw", "year") for t in GEN_TECHS})
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
yr.plot(ax=ax[0], logy=True, title="Weighted-avg total installed cost (USD/kW, log)"); ax[0].grid(alpha=.3)
lcy = pd.DataFrame({t: weighted(clean.assign(l=clean.apply(lambda x: lcoe_crf(x.capex_usd_kw, x.fom_usd_kw_yr, x.var_cost_usd_mwh, x.cf, WACC_BASE, x.life_yrs), axis=1)).loc[lambda d: d.technology == t], "l", "year") for t in GEN_TECHS})
lcy.plot(ax=ax[1], title="Weighted-avg LCOE (USD/MWh, 7.5% WACC)"); ax[1].grid(alpha=.3); plt.tight_layout(); plt.savefig(f"{OUT}/figures/1_cost_trends.png", dpi=130); plt.close()
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
for s in SCENARIOS:
    d = sc[(sc.scenario == s) & (sc.technology == "Solar PV")]; ax[0].plot(d.year, d.lcoe, marker="o", label=s)
ax[0].set_title("Solar PV LCOE by scenario (USD/MWh)"); ax[0].legend(); ax[0].grid(alpha=.3)
p = sc[(sc.year == 2050)].pivot(index="technology", columns="scenario", values="lcoe"); p.plot.bar(ax=ax[1], title="LCOE in 2050 by scenario"); plt.tight_layout(); plt.savefig(f"{OUT}/figures/2_scenarios.png", dpi=130); plt.close()
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5)); tt = tor.iloc[::-1]
ax[0].barh(tt.driver, tt.lcoe_low_input - b0, label="low input"); ax[0].barh(tt.driver, tt.lcoe_high_input - b0, label="high input"); ax[0].axvline(0, c="k"); ax[0].legend(); ax[0].set_title("Onshore Wind tornado: LCOE change (USD/MWh)")
ax[1].hist(mcs["Onshore Wind"].lcoe, bins=60, alpha=.8); ax[1].axvline(mc["Onshore Wind"]["p5"], c="r", ls="--"); ax[1].axvline(mc["Onshore Wind"]["p95"], c="r", ls="--"); ax[1].set_title("Onshore Wind Monte Carlo LCOE (P5/P95 dashed)")
plt.tight_layout(); plt.savefig(f"{OUT}/figures/3_sensitivity.png", dpi=130); plt.close()
print(lt.round(1)); print(fin_tab.round(3)); print(pd.DataFrame(mc).T[["mean", "p5", "p95", "top_driver"]])
