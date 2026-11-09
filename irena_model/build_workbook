"""Builds the Excel deliverable. All calculations are LIVE formulas; Python-only results (QA log, Monte Carlo,
break-even PPAs) are written as clearly labelled static values."""
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.chart import LineChart, BarChart, Reference
from .config import *
from .data import cum_series

FN = "Arial"
def font(**k): return Font(name=FN, size=10, **k)
FILL_H = PatternFill("solid", start_color="1F3864"); FILL_Y = PatternFill("solid", start_color="FFFF00"); FILL_G = PatternFill("solid", start_color="E7EEF7")
KIND = {"input": font(color="0000FF"), "link": font(color="008000"), "calc": font(), "label": font(), "bold": font(bold=True),
        "hdr": font(bold=True, color="FFFFFF"), "title": Font(name=FN, size=14, bold=True, color="1F3864"), "note": font(italic=True, color="595959")}
F_USD, F_PCT, F_1, F_2, F_INT = '#,##0;(#,##0);-', '0.0%;(0.0%);-', '#,##0.0;(#,##0.0);-', '#,##0.00;(#,##0.00);-', '0'
HRS = "Assumptions!$B$15"

def put(ws, ref, v, kind="calc", fmt=None, fill=None, wrap=False):
    c = ws[ref]; c.value = v; c.font = KIND[kind]
    if fmt: c.number_format = fmt
    if kind == "hdr": c.fill = FILL_H; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    if fill: c.fill = fill
    if wrap: c.alignment = Alignment(wrap_text=True, vertical="top")
    return c
def hdr(ws, row, labels, col0=1):
    for i, t in enumerate(labels): put(ws, f"{L(col0+i)}{row}", t, "hdr")
def widths(ws, d):
    for k, v in d.items(): ws.column_dimensions[k].width = v
def title(ws, t, sub=None):
    put(ws, "A1", t, "title")
    if sub: put(ws, "A2", sub, "note")
def dd(ws, ref, formula):
    v = DataValidation(type="list", formula1=formula, allow_blank=False); ws.add_data_validation(v); v.add(ref)
def AI(col, cell): return f"INDEX(Assumptions!${col}$7:${col}$12,MATCH({cell},Assumptions!$A$7:$A$12,0))"
def crf_f(w, n): return f"({w}*(1+{w})^{n}/((1+{w})^{n}-1))"
def lcoe_f(capex, cf, fom, var, life, wacc):
    return f"(({capex})*{crf_f('('+str(wacc)+')','('+str(life)+')')}+({fom}))/(({cf})*{HRS}/1000)+({var})"

def build(path, clean, log, enabling, a, lc, mc, fin_tab, fin_grid, raw_n):
    wb = Workbook(); N = 4 + len(clean); T = GEN_TECHS
    R = lambda c: f"Cost_DB!${c}$5:${c}${N}"
    # ============================================================ README
    ws = wb.active; ws.title = "README"; title(ws, "IRENA-style Renewable Energy Cost Status & Outlook Model", "SYNTHETIC DATA - calibrated to the order of magnitude of published global averages; not official IRENA figures.")
    lines = [("Sheet map", "bold"),
     ("Assumptions - baseline inputs (capacity-weighted from Cost_DB) + WACC, lifetime, degradation, construction time", "label"),
     ("1. COST DATABASE: Cost_DB (cleaned projects, row-level LCOE), DB_Enabling (BESS, electrolysers), QA_Log (verification log), Cost_Trends (weighted-average capex/CF/LCOE 2010-24), Learning_Curves (log-log regression)", "label"),
     ("2. COST MODELLING: LCOE_Model (3 methods side-by-side + cost components), LCOE_DCF (transparent year-by-year DCF with tie-out)", "label"),
     ("3. SCENARIO TOOL: Scenarios (dashboard, selector, comparison) driven by Scen_Calc (long-form engine)", "label"),
     ("4. SENSITIVITY: Sensitivity (tornado, 2-way WACC x capex grid), MC_Results (Monte Carlo from Python)", "label"),
     ("5. FINANCIAL MODEL: Fin_Model (project finance cash flow, debt sculpting-free annuity, DSCR, IRR/NPV), Fin_Results (Python batch results)", "label"),
     ("", "label"), ("Colour code", "bold"),
     ("Blue = hard-coded input / lever  |  Black = formula  |  Green = link to another sheet  |  Yellow fill = key assumption to edit", "label"),
     ("", "label"), ("Method notes", "bold"),
     ("LCOE-1 (IRENA-style): [CAPEX x CRF + fixed O&M] / (CF x 8.76) + variable cost, USD/MWh, real terms, CRF = r(1+r)^n/((1+r)^n-1).", "label"),
     ("LCOE-2: year-by-year discounted costs / discounted energy, with annual output degradation.", "label"),
     ("LCOE-3: LCOE-1 with interest during construction approximated as capex x (1 + WACC x construction years / 2).", "label"),
     ("Learning curve: capex = capex0 x (cumulative capacity ratio)^b, b = log2(1 - LR); LR fitted by log-log regression (adopted only if R2 >= threshold, else 0).", "label"),
     ("Scenarios: cumulative capacity grows at CAGR x scenario multiplier (2024-30, then 2030-50); levers apply from years after the baseline year.", "label"),
     ("Financial model simplifications: single drawdown at t=0, annuity debt, straight-line depreciation, no tax-loss carry-forward, no DSRA/working capital, real PPA escalation input.", "label"),
     ("Python-generated static sheets (QA_Log, MC_Results, Fin_Results) will not update when Excel inputs change; re-run run_all.py to refresh.", "label")]
    for i, (t, k) in enumerate(lines): put(ws, f"A{4+i}", t, k)
    ws.column_dimensions["A"].width = 170

    # ============================================================ Assumptions
    ws = wb.create_sheet("Assumptions"); title(ws, "Baseline Assumptions", "Capex, CF, O&M, variable cost = capacity-weighted averages of Cost_DB for the baseline year (formulas).")
    put(ws, "A3", "Baseline year", "bold"); put(ws, "B3", BASE_YEAR, "input", F_INT, FILL_Y)
    hdr(ws, 6, ["Technology", "Capex (USD/kW)", "Capacity factor", "Fixed O&M (USD/kW/yr)", "Variable cost (USD/MWh)", "Lifetime (yrs)", "WACC (real)", "Degradation (%/yr)", "Construction (yrs)", "Adopted learning rate", "Source / note"])
    ws.row_dimensions[6].height = 42
    for i, t in enumerate(T):
        r = 7 + i; put(ws, f"A{r}", t, "bold")
        for col, src, fmt in [("B", "G", F_USD), ("C", "H", F_PCT), ("D", "I", F_1), ("E", "J", F_1)]:
            put(ws, f"{col}{r}", f"=SUMPRODUCT(({R('B')}=$A{r})*({R('E')}=$B$3)*{R('F')}*{R(src)})/SUMIFS({R('F')},{R('B')},$A{r},{R('E')},$B$3)", "calc", fmt)
        p = TECH[t]
        put(ws, f"F{r}", p["life"], "input", F_INT); put(ws, f"G{r}", WACC_BASE, "input", F_PCT, FILL_Y); put(ws, f"H{r}", p["degr"], "input", '0.00%;(0.00%);-')
        put(ws, f"I{r}", p["constr"], "input", F_INT); put(ws, f"J{r}", f"=Learning_Curves!{L(2+4*i)}25", "link", F_PCT)
        put(ws, f"K{r}", "Cost_DB (synthetic); life/degr/constr: analyst assumption; WACC: uniform real 7.5% placeholder; LR: Learning_Curves", "note")
    put(ws, "A14", "Global constants", "bold"); put(ws, "A15", "Hours per year", "label"); put(ws, "B15", HOURS, "input", '#,##0')
    widths(ws, {"A": 22, "B": 15, "C": 13, "D": 16, "E": 16, "F": 12, "G": 12, "H": 14, "I": 14, "J": 14, "K": 90}); ws.freeze_panes = "B7"

    # ============================================================ Cost_DB
    ws = wb.create_sheet("Cost_DB"); title(ws, "Cost Database - verified project records (synthetic)", f"{len(clean)} records after QA (from {raw_n} raw). Columns M-O are formulas (row-level LCOE at the technology WACC).")
    cols = ["Project ID", "Technology", "Country", "Region", "Year", "Capacity (MW)", "Capex (USD/kW)", "Capacity factor", "Fixed O&M (USD/kW/yr)", "Variable cost (USD/MWh)", "Lifetime (yrs)", "QA status", "WACC", "CRF", "LCOE (USD/MWh)"]
    hdr(ws, 4, cols); ws.row_dimensions[4].height = 32
    for i, r in enumerate(clean.itertuples()):
        x = 5 + i
        vals = [r.project_id, r.technology, r.country, r.region, int(r.year), r.capacity_mw, float(r.capex_usd_kw), float(r.cf), r.fom_usd_kw_yr, r.var_cost_usd_mwh, int(r.life_yrs), r.qa_status]
        for j, v in enumerate(vals): ws.cell(x, 1 + j, v).font = KIND["input"] if j >= 5 and j <= 10 else font()
        ws.cell(x, 13, f"={AI('G', f'$B{x}')}"); ws.cell(x, 14, f"=M{x}*(1+M{x})^K{x}/((1+M{x})^K{x}-1)")
        ws.cell(x, 15, f"=(G{x}*N{x}+I{x})/(H{x}*{HRS}/1000)+J{x}")
        for j, f in [(6, F_1), (7, F_USD), (8, F_PCT), (9, F_1), (10, F_1), (13, F_PCT), (14, '0.0000'), (15, F_1)]: ws.cell(x, j).number_format = f
        for j in (13, 14, 15): ws.cell(x, j).font = KIND["calc"] if j > 13 else KIND["link"]
    widths(ws, {L(i + 1): w for i, w in enumerate([11, 15, 14, 14, 7, 12, 13, 11, 14, 14, 10, 20, 9, 9, 13])}); ws.freeze_panes = "C5"; ws.auto_filter.ref = f"A4:O{N}"

    # ============================================================ DB_Enabling
    ws = wb.create_sheet("DB_Enabling"); title(ws, "Enabling technologies - BESS & electrolysers (synthetic)", "Capex in native unit (USD/kWh for BESS, USD/kW for electrolysers). Efficiency: BESS round-trip; electrolyser system kWh/kgH2.")
    hdr(ws, 4, ["Project ID", "Technology", "Country", "Year", "Size (MW)", "Capex", "Unit", "Efficiency", "QA status"])
    for i, r in enumerate(enabling.itertuples()):
        for j, v in enumerate([r.project_id, r.technology, r.country, int(r.year), r.size_mw, float(r.capex), r.unit, float(r.efficiency), r.qa_status]): ws.cell(5 + i, 1 + j, v).font = font()
    NE = 4 + len(enabling)
    put(ws, "K4", "Average capex by year", "bold"); hdr(ws, 5, ["Year"] + list(ENABLING), 11)
    for k, y in enumerate([2010, 2015, 2020, 2024]):
        put(ws, f"K{6+k}", y, "input", F_INT)
        for j, t in enumerate(ENABLING): put(ws, f"{L(12+j)}{6+k}", f'=AVERAGEIFS($F$5:$F${NE},$B$5:$B${NE},{L(12+j)}$5,$D$5:$D${NE},$K{6+k})', "calc", F_USD)
    put(ws, "K11", "Change 2010-24", "bold")
    for j in range(2): put(ws, f"{L(12+j)}11", f"={L(12+j)}9/{L(12+j)}6-1", "calc", F_PCT)
    put(ws, "K13", "Fitted learning rate (Python, log-log, unweighted yearly mean)", "bold")
    for j, t in enumerate(ENABLING):
        d = enabling[enabling.technology == t].groupby("year").capex.mean(); cum = pd.Series(cum_series(t))
        lr = 1 - 2 ** np.polyfit(np.log(cum.loc[d.index]), np.log(d), 1)[0]
        put(ws, f"{L(12+j)}14", float(lr), "input", F_PCT)
    widths(ws, {"A": 11, "B": 24, "C": 14, "D": 7, "E": 10, "F": 10, "G": 10, "H": 11, "I": 11, "K": 16, "L": 22, "M": 24})

    # ============================================================ QA_Log
    ws = wb.create_sheet("QA_Log"); title(ws, "Data verification & quality-assurance log (Python pipeline)", "Order: duplicates -> missing -> unit fixes -> plausibility ranges -> robust (MAD) outliers. Static values.")
    put(ws, "A3", f"Raw records: {raw_n}   |   Accepted: {len(clean)}   |   Issues logged: {len(log)}", "bold")
    hdr(ws, 5, ["Check", "Action", "Count"]); s = log.groupby(["check", "action"]).size().reset_index()
    for i, r in enumerate(s.itertuples()): put(ws, f"A{6+i}", r.check); put(ws, f"B{6+i}", r.action); put(ws, f"C{6+i}", int(r[3]), "calc", F_INT)
    r0 = 8 + len(s); hdr(ws, r0, ["Project ID", "Technology", "Year", "Check", "Action", "Field", "Original", "Corrected"])
    for i, r in enumerate(log.itertuples()):
        for j, v in enumerate([r.project_id, r.technology, int(r.year), r.check, r.action, r.field, r.original, r.corrected]):
            c = ws.cell(r0 + 1 + i, 1 + j, v if not isinstance(v, (np.floating,)) else float(v)); c.font = font()
    widths(ws, {"A": 28, "B": 16, "C": 8, "D": 28, "E": 11, "F": 15, "G": 12, "H": 12})

    # ============================================================ Cost_Trends
    ws = wb.create_sheet("Cost_Trends"); title(ws, "Capacity-weighted cost trends 2010-2024", "All cells are SUMPRODUCT/SUMIFS formulas over Cost_DB.")
    blocks = [(4, "Total installed cost (USD/kW)", "G", F_USD), (23, "Capacity factor", "H", F_PCT), (42, "LCOE (USD/MWh)", "O", F_1)]
    for r0, name, col, fmt in blocks:
        put(ws, f"A{r0}", name, "bold"); hdr(ws, r0 + 1, ["Year"] + T)
        for k, y in enumerate(YEARS):
            x = r0 + 2 + k; put(ws, f"A{x}", y, "input", F_INT)
            for j in range(6):
                c = L(2 + j)
                put(ws, f"{c}{x}", f"=SUMPRODUCT(({R('B')}={c}${r0+1})*({R('E')}=$A{x})*{R('F')}*{R(col)})/SUMIFS({R('F')},{R('B')},{c}${r0+1},{R('E')},$A{x})", "calc", fmt)
        x = r0 + 2 + len(YEARS); put(ws, f"A{x}", "Change 2010-24", "bold")
        for j in range(6): c = L(2 + j); put(ws, f"{c}{x}", f"={c}{x-1}/{c}{r0+2}-1", "calc", F_PCT)
    widths(ws, {"A": 16, **{L(i): 14 for i in range(2, 8)}})
    for r0, name, _, _ in blocks:
        ch = LineChart(); ch.title = name; ch.height, ch.width = 7.5, 15
        ch.add_data(Reference(ws, min_col=2, max_col=7, min_row=r0 + 1, max_row=r0 + 1 + len(YEARS)), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=r0 + 2, max_row=r0 + 1 + len(YEARS))); ws.add_chart(ch, f"I{r0}")

    # ============================================================ Learning_Curves
    ws = wb.create_sheet("Learning_Curves"); title(ws, "Experience (learning) curves: ln(capex) = a + b ln(cumulative GW)", "Learning rate LR = 1 - 2^b. Cumulative capacity is a synthetic input series (blue).")
    for i, t in enumerate(T):
        c0 = 2 + 4 * i; put(ws, f"{L(c0)}4", t, "bold"); hdr(ws, 5, ["Cum. GW", "Capex USD/kW", "ln(cum)", "ln(capex)"], c0)
        cum = cum_series(t)
        for k, y in enumerate(YEARS):
            x = 6 + k
            if i == 0: put(ws, f"A{x}", y, "input", F_INT)
            put(ws, f"{L(c0)}{x}", cum[y], "input", F_1); put(ws, f"{L(c0+1)}{x}", f"=Cost_Trends!{L(2+i)}{6+k}", "link", F_USD)
            put(ws, f"{L(c0+2)}{x}", f"=LN({L(c0)}{x})", "calc", '0.000'); put(ws, f"{L(c0+3)}{x}", f"=LN({L(c0+1)}{x})", "calc", '0.000')
        xr, yr = f"{L(c0+2)}6:{L(c0+2)}20", f"{L(c0+3)}6:{L(c0+3)}20"
        put(ws, f"{L(c0)}22", f"=SLOPE({yr},{xr})", "calc", '0.000'); put(ws, f"{L(c0)}23", f"=1-2^{L(c0)}22", "calc", F_PCT)
        put(ws, f"{L(c0)}24", f"=RSQ({yr},{xr})", "calc", '0.000'); put(ws, f"{L(c0)}25", f"=IF({L(c0)}24>=$B$28,MAX(0,{L(c0)}23),0)", "calc", F_PCT)
    for r, t in zip(range(22, 26), ["Slope b", "Fitted learning rate", "R-squared", "Adopted learning rate"]): put(ws, f"A{r}", t, "bold")
    put(ws, "A28", "Minimum R2 to adopt LR", "bold"); put(ws, "B28", LR_MIN_R2, "input", '0.00', FILL_Y)
    put(ws, "A29", "Mature technologies (hydro, bio) show no statistically meaningful learning -> LR set to 0.", "note")
    widths(ws, {"A": 22, **{L(i): 11 for i in range(2, 26)}}); ws.freeze_panes = "B6"

    # ============================================================ LCOE_Model
    ws = wb.create_sheet("LCOE_Model"); title(ws, "LCOE methodologies side-by-side (USD/MWh, real)", "K = Method 1 (CRF, IRENA-style); O = Method 2 (DCF with degradation, closed form); P = Method 3 (CRF + interest during construction).")
    hdr(ws, 5, ["Technology", "Capex", "CF", "Fixed O&M", "Var. cost", "Life", "WACC", "Degr.", "Constr. yrs", "CRF", "LCOE-1 CRF", "of which capital", "of which fixed O&M", "of which variable", "LCOE-2 DCF+degr.", "LCOE-3 CRF+IDC", "LCOE-2 vs 1", "LCOE-3 vs 1"]); ws.row_dimensions[5].height = 42
    for i, t in enumerate(T):
        r = 6 + i; ar = 7 + i
        put(ws, f"A{r}", f"=Assumptions!A{ar}", "link")
        for c, ac, fmt in [("B", "B", F_USD), ("C", "C", F_PCT), ("D", "D", F_1), ("E", "E", F_1), ("F", "F", F_INT), ("G", "G", F_PCT), ("H", "H", '0.00%;(0.00%);-'), ("I", "I", F_INT)]: put(ws, f"{c}{r}", f"=Assumptions!{ac}{ar}", "link", fmt)
        put(ws, f"J{r}", f"=G{r}*(1+G{r})^F{r}/((1+G{r})^F{r}-1)", "calc", '0.0000')
        e = f"(C{r}*{HRS}/1000)"
        put(ws, f"K{r}", f"=(B{r}*J{r}+D{r})/{e}+E{r}", "calc", F_1); put(ws, f"L{r}", f"=B{r}*J{r}/{e}", "calc", F_1)
        put(ws, f"M{r}", f"=D{r}/{e}", "calc", F_1); put(ws, f"N{r}", f"=E{r}", "calc", F_1)
        q = f"((1-H{r})/(1+G{r}))"
        put(ws, f"O{r}", f"=(B{r}+D{r}*(1-(1+G{r})^(-F{r}))/G{r})/({e}/(1+G{r})*(1-{q}^F{r})/(1-{q}))+E{r}", "calc", F_1)
        put(ws, f"P{r}", f"=(B{r}*(1+G{r}*I{r}/2)*J{r}+D{r})/{e}+E{r}", "calc", F_1)
        put(ws, f"Q{r}", f"=O{r}/K{r}-1", "calc", F_PCT); put(ws, f"R{r}", f"=P{r}/K{r}-1", "calc", F_PCT)
    widths(ws, {"A": 18, **{L(i): 12 for i in range(2, 19)}})
    ch = BarChart(); ch.type = "col"; ch.grouping = "stacked"; ch.overlap = 100; ch.title = "LCOE-1 by cost component (USD/MWh)"; ch.height, ch.width = 8, 16
    ch.add_data(Reference(ws, min_col=12, max_col=14, min_row=5, max_row=11), titles_from_data=True); ch.set_categories(Reference(ws, min_col=1, min_row=6, max_row=11)); ws.add_chart(ch, "A14")

    # ============================================================ LCOE_DCF
    ws = wb.create_sheet("LCOE_DCF"); title(ws, "Transparent year-by-year DCF LCOE", "Select a technology; the sheet discounts costs and energy explicitly and ties out to LCOE_Model (closed form).")
    put(ws, "A3", "Technology", "bold"); put(ws, "B3", "Solar PV", "input", None, FILL_Y); dd(ws, "B3", "=Assumptions!$A$7:$A$12")
    for r, (lab, col, fmt) in zip(range(5, 12), [("Capex (USD/kW)", "B", F_USD), ("Capacity factor", "C", F_PCT), ("Fixed O&M (USD/kW/yr)", "D", F_1), ("Variable cost (USD/MWh)", "E", F_1), ("Lifetime (yrs)", "F", F_INT), ("WACC", "G", F_PCT), ("Degradation (%/yr)", "H", '0.00%;(0.00%);-')]):
        put(ws, f"A{r}", lab); put(ws, f"B{r}", f"={AI(col, '$B$3')}", "link", fmt)
    put(ws, "A12", "LCOE - explicit DCF (USD/MWh)", "bold"); put(ws, "B12", "=I59/J59", "calc", F_2)
    put(ws, "A13", "LCOE-2 closed form (LCOE_Model)"); put(ws, "B13", "=INDEX(LCOE_Model!$O$6:$O$11,MATCH($B$3,LCOE_Model!$A$6:$A$11,0))", "link", F_2)
    put(ws, "A14", "Tie-out difference (should be ~0)"); put(ws, "B14", "=B12-B13", "calc", '0.0000')
    hdr(ws, 17, ["Year", "Operating", "Energy (MWh/kW)", "Capex (USD/kW)", "Fixed O&M (USD/kW)", "Variable (USD/kW)", "Total cost (USD/kW)", "Discount factor", "PV cost", "PV energy"])
    for t in range(41):
        r = 18 + t
        put(ws, f"A{r}", t if t == 0 else f"=A{r-1}+1", "input" if t == 0 else "calc", F_INT)
        put(ws, f"B{r}", f"=IF(AND(A{r}>=1,A{r}<=$B$9),1,0)", "calc", F_INT)
        put(ws, f"C{r}", f"=B{r}*$B$6*{HRS}/1000*(1-$B$11)^(A{r}-1)" if t else "=0", "calc", '0.000')
        put(ws, f"D{r}", "=$B$5" if t == 0 else "=0", "calc", F_USD); put(ws, f"E{r}", f"=$B$7*B{r}", "calc", F_1); put(ws, f"F{r}", f"=$B$8*C{r}", "calc", F_1)
        put(ws, f"G{r}", f"=D{r}+E{r}+F{r}", "calc", F_1); put(ws, f"H{r}", f"=1/(1+$B$10)^A{r}", "calc", '0.0000')
        put(ws, f"I{r}", f"=G{r}*H{r}", "calc", F_1); put(ws, f"J{r}", f"=C{r}*H{r}", "calc", '0.000')
    put(ws, "A59", "Total", "bold"); put(ws, "I59", "=SUM(I18:I58)", "calc", F_1); put(ws, "J59", "=SUM(J18:J58)", "calc", '0.000')
    widths(ws, {"A": 34, **{L(i): 16 for i in range(2, 11)}})

    # ============================================================ Scenarios + Scen_Calc
    ws = wb.create_sheet("Scenarios"); title(ws, "Scenario tool: LCOE outlook to 2050", "Levers (blue) feed Scen_Calc. Learning: capex = capex0 x (cum. capacity multiple)^log2(1-LR). Levers apply to years after the baseline year.")
    put(ws, "A3", "Baseline year", "bold"); put(ws, "B3", "=Assumptions!B3", "link", F_INT); put(ws, "D3", "Growth break year", "bold"); put(ws, "E3", GROWTH_BREAK_YEAR, "input", F_INT, FILL_Y)
    hdr(ws, 5, ["Scenario", "Growth multiplier (x CAGR)", "Learning-rate delta", "Capex multiplier", "WACC delta", "CF multiplier", "O&M / var. cost multiplier", "Narrative"]); ws.row_dimensions[5].height = 42
    for i, (s, v) in enumerate(SCENARIOS.items()):
        r = 6 + i; put(ws, f"A{r}", s, "bold")
        for c, x, fmt in zip("BCDEFG", v[:6], ['0.00', '0.0%;(0.0%);-', '0.00', '0.0%;(0.0%);-', '0.00', '0.00']): put(ws, f"{c}{r}", x, "input", fmt, FILL_Y if c in "BE" else None)
        put(ws, f"H{r}", v[6], "note")
    hdr(ws, 12, ["Technology", "Deployment CAGR to break year", "Deployment CAGR after break year"]); ws.row_dimensions[12].height = 32
    for i, t in enumerate(T): put(ws, f"A{13+i}", t, "bold"); put(ws, f"B{13+i}", TECH[t]["g1"], "input", F_PCT); put(ws, f"C{13+i}", TECH[t]["g2"], "input", F_PCT)
    put(ws, "A21", "Selected scenario", "bold"); put(ws, "B21", "Reference", "input", None, FILL_Y); dd(ws, "B21", "=$A$6:$A$9")
    put(ws, "A22", "LCOE by technology (USD/MWh) - selected scenario", "bold"); hdr(ws, 23, ["Technology"] + SCEN_YEARS)
    SC = "Scen_Calc!"; rg = lambda c: f"{SC}${c}$5:${c}$124"
    for i, t in enumerate(T):
        r = 24 + i; put(ws, f"A{r}", t, "bold")
        for j, y in enumerate(SCEN_YEARS): put(ws, f"{L(2+j)}{r}", f"=SUMIFS({rg('P')},{rg('A')},$B$21,{rg('B')},$A{r},{rg('C')},{L(2+j)}$23)", "calc", F_1)
    for blk, (r0, yr) in enumerate([(32, 2030), (42, 2050)]):
        put(ws, f"A{r0-1}", f"LCOE in {yr} by scenario (USD/MWh)", "bold"); hdr(ws, r0, ["Technology"] + list(SCENARIOS))
        for i, t in enumerate(T):
            r = r0 + 1 + i; put(ws, f"A{r}", t, "bold")
            for j in range(4): put(ws, f"{L(2+j)}{r}", f"=SUMIFS({rg('P')},{rg('A')},{L(2+j)}${r0},{rg('B')},$A{r},{rg('C')},{yr})", "calc", F_1)
    put(ws, "A50", "Check: baseline-year LCOE equals LCOE-1 (max abs diff, should be 0)", "note")
    put(ws, "B50", "=MAX(ABS(B24-LCOE_Model!K6),ABS(B25-LCOE_Model!K7),ABS(B26-LCOE_Model!K8),ABS(B27-LCOE_Model!K9),ABS(B28-LCOE_Model!K10),ABS(B29-LCOE_Model!K11))", "calc", '0.0000')
    widths(ws, {"A": 26, "B": 17, "C": 17, "D": 17, "E": 14, "F": 14, "G": 18, "H": 60})
    ch = LineChart(); ch.title = "LCOE outlook - selected scenario (USD/MWh)"; ch.height, ch.width = 8, 16
    ch.add_data(Reference(ws, min_col=1, max_col=6, min_row=24, max_row=29), from_rows=True, titles_from_data=True); ch.set_categories(Reference(ws, min_col=2, max_col=6, min_row=23)); ws.add_chart(ch, "J3")
    ws2 = wb.create_sheet("Scen_Calc"); title(ws2, "Scenario engine (long form: scenario x technology x year)", "Do not edit; driven by Assumptions and Scenarios.")
    hdr(ws2, 4, ["Scenario", "Technology", "Year", "CAGR to break", "CAGR after break", "Cum. capacity multiple", "Adopted LR", "Learning exponent b", "Capex (USD/kW)", "WACC", "CF", "Fixed O&M", "Var. cost", "Life", "CRF", "LCOE (USD/MWh)"]); ws2.row_dimensions[4].height = 32
    SM = lambda c, r: f"INDEX(Scenarios!${c}$6:${c}$9,MATCH($A{r},Scenarios!$A$6:$A$9,0))"; GM = lambda c, r: f"INDEX(Scenarios!${c}$13:${c}$18,MATCH($B{r},Scenarios!$A$13:$A$18,0))"
    r = 5
    for s in SCENARIOS:
        for t in T:
            for y in SCEN_YEARS:
                put(ws2, f"A{r}", s, "input"); put(ws2, f"B{r}", t, "input"); put(ws2, f"C{r}", y, "input", F_INT)
                fut = f"($C{r}>Scenarios!$B$3)"
                put(ws2, f"D{r}", f"={GM('B', r)}*{SM('B', r)}", "calc", F_PCT); put(ws2, f"E{r}", f"={GM('C', r)}*{SM('B', r)}", "calc", F_PCT)
                put(ws2, f"F{r}", f"=(1+D{r})^(MIN($C{r},Scenarios!$E$3)-Scenarios!$B$3)*(1+E{r})^MAX(0,$C{r}-Scenarios!$E$3)", "calc", '0.00')
                put(ws2, f"G{r}", f"=IF({AI('J', f'$B{r}')}=0,0,MAX(0,{AI('J', f'$B{r}')}+{SM('C', r)}))", "calc", F_PCT)
                put(ws2, f"H{r}", f"=LOG(1-G{r},2)", "calc", '0.000')
                put(ws2, f"I{r}", f"={AI('B', f'$B{r}')}*F{r}^H{r}*IF({fut},{SM('D', r)},1)", "calc", F_USD)
                put(ws2, f"J{r}", f"={AI('G', f'$B{r}')}+IF({fut},{SM('E', r)},0)", "calc", F_PCT)
                put(ws2, f"K{r}", f"=MIN(0.95,{AI('C', f'$B{r}')}*IF({fut},{SM('F', r)},1))", "calc", F_PCT)
                put(ws2, f"L{r}", f"={AI('D', f'$B{r}')}*IF({fut},{SM('G', r)},1)", "calc", F_1)
                put(ws2, f"M{r}", f"={AI('E', f'$B{r}')}*IF({fut},{SM('G', r)},1)", "calc", F_1)
                put(ws2, f"N{r}", f"={AI('F', f'$B{r}')}", "calc", F_INT)
                put(ws2, f"O{r}", f"=J{r}*(1+J{r})^N{r}/((1+J{r})^N{r}-1)", "calc", '0.0000')
                put(ws2, f"P{r}", f"=(I{r}*O{r}+L{r})/(K{r}*{HRS}/1000)+M{r}", "calc", F_1); r += 1
    widths(ws2, {"A": 20, "B": 16, **{L(i): 13 for i in range(3, 17)}}); ws2.freeze_panes = "D5"

    # ============================================================ Sensitivity
    ws = wb.create_sheet("Sensitivity"); title(ws, "Sensitivity analysis (LCOE-1, USD/MWh)", "One-at-a-time tornado and two-way WACC x capex grid for the selected technology.")
    put(ws, "A3", "Technology", "bold"); put(ws, "B3", "Onshore Wind", "input", None, FILL_Y); dd(ws, "B3", "=Assumptions!$A$7:$A$12")
    for r, (lab, col, fmt) in zip(range(5, 11), [("Capex (USD/kW)", "B", F_USD), ("Capacity factor", "C", F_PCT), ("Fixed O&M (USD/kW/yr)", "D", F_1), ("Variable cost (USD/MWh)", "E", F_1), ("Lifetime (yrs)", "F", F_INT), ("WACC", "G", F_PCT)]):
        put(ws, f"A{r}", lab); put(ws, f"B{r}", f"={AI(col, '$B$3')}", "link", fmt)
    base = dict(capex="$B$5", cf="$B$6", fom="$B$7", var="$B$8", life="$B$9", wacc="$B$10")
    put(ws, "A11", "Base LCOE (USD/MWh)", "bold"); put(ws, "B11", "=" + lcoe_f(**base), "calc", F_2)
    put(ws, "A12", "Relative variation (+/-) for capex, CF, O&M, var. cost"); put(ws, "B12", .20, "input", F_PCT, FILL_Y)
    put(ws, "A13", "WACC variation (+/- absolute)"); put(ws, "B13", .02, "input", F_PCT, FILL_Y)
    put(ws, "A14", "Lifetime variation (+/- years)"); put(ws, "B14", 5, "input", F_INT, FILL_Y)
    hdr(ws, 16, ["Driver", "Low input", "High input", "LCOE @ low input", "LCOE @ high input", "Swing (abs)", "Low input vs base", "High input vs base"]); ws.row_dimensions[16].height = 32
    drv = [("Capex", "capex", "=$B$5*(1-$B$12)", "=$B$5*(1+$B$12)", F_USD), ("Capacity factor", "cf", "=$B$6*(1-$B$12)", "=MIN(0.95,$B$6*(1+$B$12))", F_PCT),
           ("Fixed O&M", "fom", "=$B$7*(1-$B$12)", "=$B$7*(1+$B$12)", F_1), ("Variable cost", "var", "=$B$8*(1-$B$12)", "=$B$8*(1+$B$12)", F_1),
           ("WACC", "wacc", "=$B$10-$B$13", "=$B$10+$B$13", F_PCT), ("Lifetime", "life", "=$B$9-$B$14", "=$B$9+$B$14", F_INT)]
    for i, (lab, key, lo, hi, fmt) in enumerate(drv):
        r = 17 + i; put(ws, f"A{r}", lab, "bold"); put(ws, f"B{r}", lo, "calc", fmt); put(ws, f"C{r}", hi, "calc", fmt)
        put(ws, f"D{r}", "=" + lcoe_f(**{**base, key: f"$B{r}"}), "calc", F_1); put(ws, f"E{r}", "=" + lcoe_f(**{**base, key: f"$C{r}"}), "calc", F_1)
        put(ws, f"F{r}", f"=ABS(E{r}-D{r})", "calc", F_1); put(ws, f"G{r}", f"=D{r}/$B$11-1", "calc", F_PCT); put(ws, f"H{r}", f"=E{r}/$B$11-1", "calc", F_PCT)
    put(ws, "A24", "Two-way grid: LCOE vs WACC (rows) and capex change (columns)", "bold")
    put(ws, "A25", "WACC \\ Capex change", "hdr")
    for j, c in enumerate([-.4, -.2, 0, .2, .4]): put(ws, f"{L(2+j)}25", c, "input", '+0%;-0%;0%')
    for i, w in enumerate([.04, .06, .08, .10, .12]):
        r = 26 + i; put(ws, f"A{r}", w, "input", F_PCT)
        for j in range(5): put(ws, f"{L(2+j)}{r}", "=" + lcoe_f(**{**base, "capex": f"$B$5*(1+{L(2+j)}$25)", "wacc": f"$A{r}"}), "calc", F_1)
    widths(ws, {"A": 46, **{L(i): 16 for i in range(2, 9)}})
    ch = BarChart(); ch.type = "bar"; ch.grouping = "clustered"; ch.overlap = 100; ch.title = "Tornado: LCOE change vs base"; ch.height, ch.width = 9, 16
    ch.add_data(Reference(ws, min_col=7, max_col=8, min_row=16, max_row=22), titles_from_data=True); ch.set_categories(Reference(ws, min_col=1, min_row=17, max_row=22)); ws.add_chart(ch, "J3")

    # ============================================================ MC_Results
    ws = wb.create_sheet("MC_Results"); title(ws, "Monte Carlo LCOE (Python, 20,000 draws; static values)", "Capex lognormal s=15%; CF normal 8% rel.; fixed O&M lognormal s=20%; WACC triangular (-2pp, base, +3pp). Spearman rank correlations with LCOE.")
    hdr(ws, 4, ["Technology", "Mean", "Std", "P5", "P50", "P95", "rho capex", "rho CF", "rho O&M", "rho WACC", "Top driver"])
    for i, t in enumerate(T):
        m = mc[t]; r = 5 + i; put(ws, f"A{r}", t, "bold")
        for j, k in enumerate(["mean", "std", "p5", "p50", "p95"]): put(ws, f"{L(2+j)}{r}", float(m[k]), "input", F_1)
        for j, k in enumerate(["capex", "cf", "fom", "wacc"]): put(ws, f"{L(7+j)}{r}", float(m[f"rho_{k}"]), "input", '0.00')
        put(ws, f"K{r}", m["top_driver"], "input")
    widths(ws, {"A": 18, **{L(i): 12 for i in range(2, 12)}})

    # ============================================================ Fin_Model
    ws = wb.create_sheet("Fin_Model"); title(ws, "Project finance model (USD m, real) - single project", "Select technology; technical inputs link to Assumptions. PPA = LCOE-1 x (1 + premium) unless overridden.")
    put(ws, "A3", "Technology", "bold"); put(ws, "B3", "Onshore Wind", "input", None, FILL_Y); dd(ws, "B3", "=Assumptions!$A$7:$A$12")
    spec = [(4, "Project capacity (MW)", FIN_CAP := 100, "input", '#,##0'), (5, "Capex (USD/kW)", "B", "link", F_USD), (6, "Capacity factor", "C", "link", F_PCT), (7, "Fixed O&M (USD/kW/yr)", "D", "link", F_1),
            (8, "Variable cost (USD/MWh)", "E", "link", F_1), (9, "Operating life (yrs, max 40)", "F", "link", F_INT), (10, "Degradation (%/yr)", "H", "link", '0.00%;(0.00%);-')]
    for r, lab, v, k, fmt in spec:
        put(ws, f"A{r}", lab); put(ws, f"B{r}", v if k == "input" else f"={AI(v, '$B$3')}", k, fmt, FILL_Y if k == "input" else None)
    put(ws, "A11", "Reference LCOE-1 (USD/MWh)"); put(ws, "B11", "=INDEX(LCOE_Model!$K$6:$K$11,MATCH($B$3,LCOE_Model!$A$6:$A$11,0))", "link", F_1)
    P = [(12, "PPA premium over LCOE", .15, F_PCT), (13, "PPA price override (USD/MWh; blank = use premium)", None, F_1), (14, "PPA price (USD/MWh)", '=IF(B13="",B11*(1+B12),B13)', F_1),
         (15, "PPA real escalation (%/yr)", 0.0, F_PCT), (16, "Opex inflation (%/yr)", .02, F_PCT), (17, "Gearing (debt/capex)", .70, F_PCT), (18, "Interest rate on debt", .06, F_PCT),
         (19, "Debt tenor (yrs)", 18, F_INT), (20, "Tax rate", .25, F_PCT), (21, "Depreciation period (yrs)", 20, F_INT), (22, "Cost of equity", .10, F_PCT)]
    for r, lab, v, fmt in P:
        put(ws, f"A{r}", lab); put(ws, f"B{r}", v, "calc" if r == 14 else "input", fmt, None if r == 14 else FILL_Y)
    put(ws, "D3", "Key outputs", "bold")
    outs = [(4, "Total capex (USD m)", "=B4*1000*B5/10^6", F_1), (5, "Debt (USD m)", "=B17*E4", F_1), (6, "Equity (USD m)", "=E4-E5", F_1), (7, "Annual debt service (USD m)", "=PMT(B18,MIN(B19,B9),-E5)", F_2),
            (8, "Project IRR (post-tax, unlevered)", "=IRR(T26:T66)", F_PCT), (9, "Equity IRR", "=IRR(S26:S66)", F_PCT), (10, "Equity NPV @ cost of equity (USD m)", "=S26+NPV(B22,S27:S66)", F_2),
            (11, "Minimum DSCR", "=MIN(R27:R66)", '0.00"x"'), (12, "Average DSCR", '=IFERROR(AVERAGE(R27:R66),"n/a")', '0.00"x"'), (13, "Equity payback (year)", '=IF(U66<0,"n/a",COUNTIF(U26:U66,"<0"))', F_INT),
            (14, "Debt balance at tenor end (check = 0)", "=INDEX(M26:M66,MIN(B19,B9)+1)", '0.000')]
    for r, lab, f, fmt in outs: put(ws, f"D{r}", lab); put(ws, f"E{r}", f, "calc", fmt)
    hdr(ws, 25, ["Year", "Operating", "Generation (MWh)", "PPA price (USD/MWh)", "Revenue", "Opex", "EBITDA", "Capex", "Depreciation", "Debt opening", "Interest", "Principal", "Debt closing", "Debt service", "Taxable income", "Tax", "CFADS", "DSCR", "Equity cash flow", "Project cash flow (unlevered)", "Cumulative equity CF"]); ws.row_dimensions[25].height = 42
    for t in range(41):
        r = 26 + t; p = r - 1
        put(ws, f"A{r}", 0 if t == 0 else f"=A{p}+1", "input" if t == 0 else "calc", F_INT)
        put(ws, f"B{r}", f"=IF(AND($A{r}>=1,$A{r}<=$B$9),1,0)", "calc", F_INT)
        put(ws, f"C{r}", f"=IF($B{r}=1,$B$4*$B$6*{HRS}*(1-$B$10)^($A{r}-1),0)", "calc", F_USD)
        put(ws, f"D{r}", f"=IF($B{r}=1,$B$14*(1+$B$15)^($A{r}-1),0)", "calc", F_1)
        put(ws, f"E{r}", f"=C{r}*D{r}/10^6", "calc", F_2); put(ws, f"F{r}", f"=IF($B{r}=1,($B$4*1000*$B$7+C{r}*$B$8)*(1+$B$16)^($A{r}-1)/10^6,0)", "calc", F_2)
        put(ws, f"G{r}", f"=E{r}-F{r}", "calc", F_2); put(ws, f"H{r}", "=$E$4" if t == 0 else "=0", "calc", F_2)
        put(ws, f"I{r}", f"=IF(AND($A{r}>=1,$A{r}<=MIN($B$21,$B$9)),$E$4/MIN($B$21,$B$9),0)", "calc", F_2)
        if t == 0:
            for c in "JKLNOPQ": put(ws, f"{c}{r}", "=0", "calc", F_2)
            put(ws, f"M{r}", "=$E$5", "calc", F_2); put(ws, f"S{r}", f"=-(H{r}-$E$5)", "calc", F_2); put(ws, f"T{r}", f"=-H{r}", "calc", F_2); put(ws, f"U{r}", f"=S{r}", "calc", F_2)
        else:
            put(ws, f"J{r}", f"=M{p}", "calc", F_2); put(ws, f"K{r}", f"=J{r}*$B$18", "calc", F_2)
            put(ws, f"N{r}", f"=IF(AND($A{r}>=1,$A{r}<=MIN($B$19,$B$9)),$E$7,0)", "calc", F_2); put(ws, f"L{r}", f"=IF(N{r}>0,N{r}-K{r},0)", "calc", F_2)
            put(ws, f"M{r}", f"=J{r}-L{r}", "calc", F_2); put(ws, f"O{r}", f"=G{r}-I{r}-K{r}", "calc", F_2); put(ws, f"P{r}", f"=MAX(0,O{r})*$B$20", "calc", F_2)
            put(ws, f"Q{r}", f"=G{r}-P{r}", "calc", F_2); put(ws, f"R{r}", f'=IF(N{r}>0,Q{r}/N{r},"")', "calc", '0.00"x"')
            put(ws, f"S{r}", f"=Q{r}-N{r}", "calc", F_2); put(ws, f"T{r}", f"=G{r}-MAX(0,G{r}-I{r})*$B$20", "calc", F_2); put(ws, f"U{r}", f"=U{p}+S{r}", "calc", F_2)
    widths(ws, {"A": 46, "B": 14, "C": 16, "D": 36, "E": 14, **{L(i): 14 for i in range(6, 22)}}); ws.freeze_panes = "B26"
    ch = LineChart(); ch.title = "Cumulative equity cash flow (USD m)"; ch.height, ch.width = 7.5, 15
    ch.add_data(Reference(ws, min_col=21, min_row=25, max_row=66), titles_from_data=True); ch.set_categories(Reference(ws, min_col=1, min_row=26, max_row=66)); ws.add_chart(ch, "G3")

    # ============================================================ Fin_Results
    ws = wb.create_sheet("Fin_Results"); title(ws, "Financial model batch results (Python; static)", "Same logic as Fin_Model with default financing terms (100 MW, 70% gearing, 6% debt, 18y tenor, 25% tax, PPA = LCOE x 1.15).")
    hdr(ws, 4, ["Technology", "LCOE-1 (USD/MWh)", "PPA (USD/MWh)", "Project IRR", "Equity IRR", "Equity NPV @10% (USD m)", "Min DSCR", "Break-even PPA @10% equity IRR", "Break-even PPA / LCOE"]); ws.row_dimensions[4].height = 42
    for i, r in enumerate(fin_tab.itertuples()):
        x = 5 + i; put(ws, f"A{x}", r.Index, "bold")
        for j, (k, fmt) in enumerate([("lcoe", F_1), ("ppa", F_1), ("project_irr", F_PCT), ("equity_irr", F_PCT), ("equity_npv", F_2), ("min_dscr", '0.00"x"'), ("be_ppa", F_1), ("be_ratio", '0.00"x"')]): put(ws, f"{L(2+j)}{x}", float(getattr(r, k)), "input", fmt)
    put(ws, "A13", "Onshore Wind: equity IRR by PPA premium (columns) and gearing (rows)", "bold"); put(ws, "A14", "Gearing \\ PPA premium", "hdr")
    for j, c in enumerate(fin_grid.columns): put(ws, f"{L(2+j)}14", c, "hdr")
    for i, (g, row) in enumerate(fin_grid.iterrows()):
        put(ws, f"A{15+i}", g, "bold")
        for j, v in enumerate(row): put(ws, f"{L(2+j)}{15+i}", float(v), "input", F_PCT)
    widths(ws, {"A": 26, **{L(i): 16 for i in range(2, 10)}})
    wb.save(path)
