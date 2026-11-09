"""
IRENA-style Renewable Energy Cost Model — Streamlit dashboard.
Run: streamlit run app.py
"""
import sys
import os

# Add the current directory to sys.path so Streamlit Cloud can find local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="IRENA Renewable Cost Model",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from irena_model.config import *
from irena_model.data import (
    generate_raw, run_qa, generate_enabling, weighted,
    baseline_assumptions, learning_curves, cum_series,
)
from irena_model.models import (
    lcoe_table, run_scenarios, tornado, two_way, monte_carlo,
    project_finance, breakeven_ppa, lcoe_crf, lcoe_dcf, lcoe_components,
)

# ─────────────────────────────────────────────────────────────────────────────
# Pipeline (cached)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Running data generation, QA, and models...")
def pipeline():
    raw = generate_raw()
    clean, qlog = run_qa(raw)
    enabling = generate_enabling()
    a = baseline_assumptions(clean)
    lc = learning_curves(clean)
    lt = lcoe_table(a)
    sc = run_scenarios(a, lc.adopted_lr)
    mcs = {t: monte_carlo(a.loc[t]) for t in GEN_TECHS}
    return raw, clean, qlog, enabling, a, lc, lt, sc, mcs

raw, clean, qlog, enabling, a, lc, lt, sc, mcs = pipeline()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.title("⚡ IRENA Cost Model")
st.sidebar.caption("Cost database · LCOE · Scenarios · Sensitivity · Finance")
st.sidebar.markdown("---")
c1, c2 = st.sidebar.columns(2)
c1.metric("Raw records", f"{len(raw):,}")
c2.metric("Clean records", f"{len(clean):,}")
st.sidebar.metric("QA issues logged", f"{len(qlog):,}")
st.sidebar.markdown("---")
st.sidebar.info(
    "All data is **synthetic**, calibrated to the order of magnitude of "
    "published global averages. Not official IRENA figures."
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Sections**\n\n"
    "1. Cost Database & QA\n"
    "2. Cost Trends & Learning\n"
    "3. LCOE Methods\n"
    "4. Scenarios\n"
    "5. Interactive Drivers\n"
    "6. Sensitivity (Static)\n"
    "7. Financial Model"
)

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_ov, tab_db, tab_trend, tab_lcoe, tab_scen, tab_drivers, tab_sens, tab_fin = st.tabs([
    "📖 Overview",
    "🗄️ Cost Database & QA",
    "📈 Cost Trends & Learning",
    "🧮 LCOE Methods",
    "🔮 Scenarios",
    "🎛️ Interactive Drivers",
    "🎯 Sensitivity (Static)",
    "💰 Financial Model",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Overview
# ─────────────────────────────────────────────────────────────────────────────
with tab_ov:
    st.title("IRENA-style Renewable Energy Cost Status & Outlook Model")
    st.markdown(
        "Interactive Python + Streamlit implementation of the analytical workflow in the "
        "IRENA Associate Programme Officer (Renewable Energy Cost Status and Outlook) JD. "
        "All data is **synthetic** — calibrated to the order of magnitude of published "
        "global averages; not official IRENA data."
    )

    st.markdown("### Key results (baseline year 2024, WACC 7.5%)")
    summary = pd.DataFrame({
        "LCOE-1 (USD/MWh)": lt["lcoe_crf"].round(1),
        "LCOE-2 (DCF+degr.)": lt["lcoe_dcf_degr"].round(1),
        "LCOE-3 (IDC)": lt["lcoe_idc"].round(1),
        "Capex (USD/kW)": a["capex"].round(0),
        "CF": (a["cf"] * 100).round(1).astype(str) + "%",
        "Fitted LR": (lc["fitted_lr"] * 100).round(1).astype(str) + "%",
        "Adopted LR": (lc["adopted_lr"] * 100).round(1).astype(str) + "%",
        "R²": lc["r2"].round(2),
    })
    st.dataframe(summary, use_container_width=True)

    st.markdown("### The 5 deliverables")
    st.markdown(
        "| # | Topic | What it does |\n"
        "|---|---|---|\n"
        "| 1 | **Cost database** | ~1,000 project records, seeded errors, QA pipeline, weighted trends, learning curves |\n"
        "| 2 | **Cost modelling** | 3 LCOE methods side-by-side (CRF, DCF, IDC) + cost components |\n"
        "| 3 | **Scenario tools** | 4 scenarios to 2050 driven by learning-by-deployment + WACC/capex/CF/O&M levers |\n"
        "| 4 | **Sensitivity** | Tornado, two-way grid, 20,000-draw Monte Carlo with Spearman driver ranking |\n"
        "| 5 | **Financial model** | Debt, tax, DSCR, project/equity IRR, NPV, payback, break-even PPA |"
    )

    st.markdown("### LCOE-1 by cost component")
    comp_df = lt[["capital", "fixed_om", "variable"]].reset_index()
    fig = px.bar(
        comp_df.melt(id_vars="technology", var_name="component", value_name="usd_mwh"),
        x="technology", y="usd_mwh", color="component",
        title="LCOE-1 decomposition (USD/MWh)",
        labels={"usd_mwh": "USD/MWh", "technology": ""},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(barmode="stack", height=420)
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Cost Database & QA
# ─────────────────────────────────────────────────────────────────────────────
with tab_db:
    st.header("Cost Database & Quality Assurance")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Raw records", f"{len(raw):,}")
    col2.metric("Clean records", f"{len(clean):,}")
    col3.metric("Excluded/corrected", f"{len(qlog):,}")
    col4.metric("Acceptance rate", f"{len(clean)/len(raw)*100:.1f}%")

    st.subheader("QA log by check type")
    counts = qlog.groupby(["check", "action"]).size().reset_index(name="count")
    fig = px.bar(
        counts, x="count", y="check", color="action", orientation="h",
        title="Issues detected and actions taken",
        labels={"count": "Records", "check": ""},
    )
    fig.update_layout(height=340)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Cost distribution by technology (clean data)")
    tech_pick = st.multiselect(
        "Technologies", GEN_TECHS, default=GEN_TECHS, key="db_tech"
    )
    if tech_pick:
        d = clean[clean.technology.isin(tech_pick)]
        fig = px.box(
            d, x="technology", y="capex_usd_kw", color="technology",
            title="Capex distribution (USD/kW)",
            labels={"capex_usd_kw": "USD/kW", "technology": ""},
        )
        fig.update_layout(showlegend=False, height=420)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Clean records (first 500)")
    show_cols = ["project_id", "technology", "country", "year",
                 "capacity_mw", "capex_usd_kw", "cf", "fom_usd_kw_yr", "qa_status"]
    st.dataframe(clean[show_cols].head(500), use_container_width=True, height=400)

    st.download_button(
        "⬇️ Download clean records (CSV)",
        clean.to_csv(index=False).encode(),
        "cost_db_clean.csv", "text/csv",
    )
    st.download_button(
        "⬇️ Download QA log (CSV)",
        qlog.to_csv(index=False).encode(),
        "qa_log.csv", "text/csv",
    )

    st.subheader("Enabling technologies (BESS + electrolysers)")
    st.dataframe(enabling.head(300), use_container_width=True, height=300)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Cost Trends & Learning Curves
# ─────────────────────────────────────────────────────────────────────────────
with tab_trend:
    st.header("Cost Trends (capacity-weighted) & Learning Curves")

    metric = st.radio(
        "Metric", ["Capex (USD/kW)", "LCOE (USD/MWh)", "Capacity factor"],
        horizontal=True, key="trend_metric",
    )

    if metric == "Capex (USD/kW)":
        col, ylab = "capex_usd_kw", "USD/kW"
    elif metric == "LCOE (USD/MWh)":
        col, ylab = None, "USD/MWh"
    else:
        col, ylab = "cf", "Capacity factor"

    if col is not None:
        yr = pd.DataFrame({
            t: weighted(clean[clean.technology == t], col, "year")
            for t in GEN_TECHS
        })
    else:
        lc_series = pd.Series(
            {i: lcoe_crf(r.capex_usd_kw, r.fom_usd_kw_yr, r.var_cost_usd_mwh,
                         r.cf, WACC_BASE, r.life_yrs)
             for i, r in clean.iterrows()},
            index=clean.index,
        )
        d = clean.assign(lcoe=lc_series)
        yr = pd.DataFrame({
            t: weighted(d[d.technology == t], "lcoe", "year")
            for t in GEN_TECHS
        })

    yr.index.name = "year"
    melted_df = yr.reset_index().melt(id_vars="year", var_name="technology", value_name="value")

    fig = px.line(
        melted_df,
        x="year", y="value", color="technology", markers=True,
        title=f"{metric} — capacity-weighted average, 2010–2024",
        labels={"year": "Year", "value": ylab, "technology": ""},
    )
    fig.update_layout(height=440)
    if metric == "Capex (USD/kW)":
        fig.update_yaxes(type="log")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Learning curves — ln(capex) vs ln(cumulative GW)")
    lc_pick = st.selectbox("Technology", GEN_TECHS, index=0, key="lc_tech")
    cum = cum_series(lc_pick)
    capex_series = weighted(clean[clean.technology == lc_pick], "capex_usd_kw", "year")
    x = np.log(pd.Series(cum).loc[capex_series.index])
    y = np.log(capex_series)
    slope = np.polyfit(x, y, 1)[0]
    intercept = np.polyfit(x, y, 1)[1]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="markers+text",
                             text=capex_series.index.astype(str),
                             textposition="top center", name="observed"))
    xr = np.linspace(x.min(), x.max(), 50)
    fig.add_trace(go.Scatter(x=xr, y=intercept + slope * xr,
                             mode="lines", name=f"fit (b={slope:.3f})",
                             line=dict(dash="dash", color="crimson")))
    fig.update_layout(
        title=f"{lc_pick} — learning rate {lc.loc[lc_pick,'fitted_lr']*100:.1f}% "
              f"(R²={lc.loc[lc_pick,'r2']:.2f}, adopted {lc.loc[lc_pick,'adopted_lr']*100:.0f}%)",
        xaxis_title="ln(cumulative GW)", yaxis_title="ln(capex USD/kW)",
        height=440,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Learning rate summary")
    lr_tab = lc.copy()
    lr_tab["fitted_lr"] = (lr_tab["fitted_lr"] * 100).round(1).astype(str) + "%"
    lr_tab["adopted_lr"] = (lr_tab["adopted_lr"] * 100).round(1).astype(str) + "%"
    st.dataframe(lr_tab.round(3), use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — LCOE Methods
# ─────────────────────────────────────────────────────────────────────────────
with tab_lcoe:
    st.header("LCOE methodologies — side by side")

    st.markdown(
        "- **LCOE-1 (CRF, IRENA-style):** `[CAPEX × CRF + fixed O&M] / (CF × 8.76) + var`\n"
        "- **LCOE-2 (DCF + degradation):** discounted cash flow with annual output decay\n"
        "- **LCOE-3 (CRF + IDC):** LCOE-1 with interest during construction"
    )

    disp = lt[["lcoe_crf", "lcoe_dcf_degr", "lcoe_idc",
               "capital", "fixed_om", "variable"]].round(2)
    disp.columns = ["LCOE-1 CRF", "LCOE-2 DCF", "LCOE-3 IDC",
                    "Capital", "Fixed O&M", "Variable"]
    st.dataframe(disp, use_container_width=True)

    tech = st.selectbox("Technology", GEN_TECHS, index=0, key="lcoe_tech")
    d = lt.loc[tech]

    col1, col2, col3 = st.columns(3)
    col1.metric("LCOE-1 (CRF)", f"{d.lcoe_crf:.1f} USD/MWh")
    col2.metric("LCOE-2 (DCF)", f"{d.lcoe_dcf_degr:.1f} USD/MWh",
                f"{(d.lcoe_dcf_degr/d.lcoe_crf-1)*100:+.1f}% vs LCOE-1")
    col3.metric("LCOE-3 (IDC)", f"{d.lcoe_idc:.1f} USD/MWh",
                f"{(d.lcoe_idc/d.lcoe_crf-1)*100:+.1f}% vs LCOE-1")

    st.subheader(f"{tech} — LCOE-1 decomposition")
    fig = go.Figure(go.Bar(
        x=["Capital", "Fixed O&M", "Variable"],
        y=[d.capital, d.fixed_om, d.variable],
        marker_color=["#1f77b4", "#ff7f0e", "#2ca02c"],
        text=[f"{v:.1f}" for v in [d.capital, d.fixed_om, d.variable]],
        textposition="outside",
    ))
    fig.update_layout(yaxis_title="USD/MWh", height=380, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("All technologies — comparison across 3 methods")
    comp = lt[["lcoe_crf", "lcoe_dcf_degr", "lcoe_idc"]].reset_index()
    comp_long = comp.melt(id_vars="technology", var_name="method", value_name="lcoe")
    fig = px.bar(
        comp_long, x="technology", y="lcoe", color="method", barmode="group",
        title="LCOE-1 vs LCOE-2 vs LCOE-3 (USD/MWh)",
        labels={"lcoe": "USD/MWh", "technology": "", "method": ""},
    )
    fig.update_layout(height=440)
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — Scenarios
# ─────────────────────────────────────────────────────────────────────────────
with tab_scen:
    st.header("Scenario tool — LCOE outlook to 2050")

    col1, col2 = st.columns([2, 1])
    tech_sel = col1.multiselect(
        "Technologies", GEN_TECHS, default=["Solar PV", "Onshore Wind"], key="sc_tech"
    )
    scen_sel = col2.multiselect(
        "Scenarios", list(SCENARIOS.keys()), default=list(SCENARIOS.keys()), key="sc_scen"
    )

    if tech_sel:
        d = sc[sc.technology.isin(tech_sel) & sc.scenario.isin(scen_sel)]
        fig = px.line(
            d, x="year", y="lcoe", color="technology", line_dash="scenario",
            markers=True, title="LCOE trajectory by technology and scenario (USD/MWh)",
            labels={"lcoe": "USD/MWh", "year": "Year", "technology": "", "scenario": ""},
        )
        fig.update_layout(height=460)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("LCOE in 2050 by scenario (USD/MWh)")
    p = sc[sc.year == 2050].pivot(index="technology", columns="scenario", values="lcoe")
    fig = px.bar(
        p.reset_index().melt(id_vars="technology", var_name="scenario", value_name="lcoe"),
        x="technology", y="lcoe", color="scenario", barmode="group",
        labels={"lcoe": "USD/MWh", "technology": "", "scenario": ""},
    )
    fig.update_layout(height=440)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Scenario levers")
    lev = pd.DataFrame.from_dict(
        {k: dict(zip(["growth_mult", "lr_delta", "capex_mult",
                      "wacc_delta", "cf_mult", "om_mult"], v[:6]))
         for k, v in SCENARIOS.items()}, orient="index"
    )
    st.dataframe(lev.round(3), use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — Interactive LCOE Drivers
# ─────────────────────────────────────────────────────────────────────────────
with tab_drivers:
    st.header("Interactive LCOE Drivers")
    st.markdown("Adjust the scroll bars below to see how each driver affects the Levelized Cost of Electricity (LCOE). This mimics the core analytical work in cost modelling.")
    
    # Default values based on Onshore Wind
    default_r = a.loc["Onshore Wind"]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        capex = st.slider("CAPEX (USD/kW)", min_value=200, max_value=5000, value=int(default_r.capex), step=50)
        cf = st.slider("Capacity Factor (%)", min_value=10.0, max_value=65.0, value=float(default_r.cf * 100), step=1.0) / 100.0
        
    with col2:
        wacc = st.slider("WACC (%)", min_value=1.0, max_value=20.0, value=float(default_r.wacc * 100), step=0.5) / 100.0
        life = st.slider("Lifetime (Years)", min_value=10, max_value=50, value=int(default_r.life), step=1)
        
    with col3:
        fom = st.slider("Fixed O&M (USD/kW/yr)", min_value=0.0, max_value=200.0, value=float(default_r.fom), step=1.0)
        var = st.slider("Variable O&M (USD/MWh)", min_value=0.0, max_value=50.0, value=float(default_r['var']), step=0.5)
    
    # Calculate LCOE
    base_lcoe = lcoe_crf(capex, fom, var, cf, wacc, life)
    components = lcoe_components(capex, fom, var, cf, wacc, life)
    
    st.markdown("---")
    
    # Key Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("LCOE-1 (CRF)", f"{base_lcoe:.1f} USD/MWh")
    m2.metric("Capital Component", f"{components['capital']:.1f} USD/MWh")
    m3.metric("Fixed O&M Component", f"{components['fixed_om']:.1f} USD/MWh")
    m4.metric("Variable O&M Component", f"{components['variable']:.1f} USD/MWh")
    
    # Charts
    colA, colB = st.columns(2)
    
    with colA:
        st.subheader("Cost Component Breakdown")
        fig = go.Figure(go.Bar(
            x=["Capital", "Fixed O&M", "Variable"],
            y=[components["capital"], components["fixed_om"], components["variable"]],
            marker_color=["#1f77b4", "#ff7f0e", "#2ca02c"],
            text=[f"{v:.1f}" for v in [components["capital"], components["fixed_om"], components["variable"]]],
            textposition="outside",
        ))
        fig.update_layout(yaxis_title="USD/MWh", height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
    with colB:
        st.subheader("Sensitivity to CAPEX (current LCOE baseline)")
        capex_range = np.linspace(capex * 0.5, capex * 1.5, 20)
        lcoe_range = [lcoe_crf(c, fom, var, cf, wacc, life) for c in capex_range]
        
        fig = px.line(x=capex_range, y=lcoe_range, labels={"x": "CAPEX (USD/kW)", "y": "LCOE (USD/MWh)"})
        fig.add_vline(x=capex, line_dash="dash", line_color="red", annotation_text="Current Input")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    st.info("💡 **JD Relevance:** Understanding how a 10% change in CAPEX, WACC, or Capacity Factor impacts the final LCOE is critical for evaluating policy incentives and financing mechanisms.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — Sensitivity (Static)
# ─────────────────────────────────────────────────────────────────────────────
with tab_sens:
    st.header("Sensitivity analysis (Static)")
    st.markdown("Based on the baseline assumptions from the cost database.")

    tech = st.selectbox("Technology", GEN_TECHS, index=1, key="sens_tech")
    r = a.loc[tech]
    b0, tor = tornado(r)

    st.subheader("Tornado — Onshore Wind" if tech == "Onshore Wind" else f"Tornado — {tech}")
    col1, col2 = st.columns([2, 1])
    col1.metric("Base LCOE-1", f"{b0:.1f} USD/MWh")

    tt = tor.iloc[::-1]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=tt["driver"], x=tt["lcoe_low_input"] - b0,
        orientation="h", name="low input", marker_color="#2ca02c",
    ))
    fig.add_trace(go.Bar(
        y=tt["driver"], x=tt["lcoe_high_input"] - b0,
        orientation="h", name="high input", marker_color="#d62728",
    ))
    fig.add_vline(x=0, line_color="black", line_width=1)
    fig.update_layout(
        barmode="overlay",
        title="Change in LCOE vs base (USD/MWh)",
        xaxis_title="Δ LCOE (USD/MWh)", height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Two-way grid — WACC × Capex change")
    grid = two_way(r)
    fig = px.imshow(
        grid.values, x=grid.columns, y=grid.index,
        color_continuous_scale="RdYlGn_r", text_auto=".1f",
        title=f"{tech}: LCOE-1 (USD/MWh), rows=WACC, cols=capex change",
        labels={"x": "Capex change", "y": "WACC"},
    )
    fig.update_layout(height=440)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monte Carlo — 20,000 draws")
    _, m = mcs[tech]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Mean", f"{m['mean']:.1f}")
    c2.metric("Std", f"{m['std']:.1f}")
    c3.metric("P5", f"{m['p5']:.1f}")
    c4.metric("P50", f"{m['p50']:.1f}")
    c5.metric("P95", f"{m['p95']:.1f}")

    s, m = mcs[tech]
    fig = px.histogram(s, x="lcoe", nbins=60,
                       title=f"{tech}: Monte Carlo LCOE distribution (P5/P95 dashed)")
    fig.add_vline(x=m["p5"], line_dash="dash", line_color="red")
    fig.add_vline(x=m["p95"], line_dash="dash", line_color="red")
    fig.update_layout(height=400, xaxis_title="LCOE (USD/MWh)")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Spearman rank correlations with LCOE**")
    rho = pd.DataFrame({
        "capex": [m["rho_capex"]], "CF": [m["rho_cf"]],
        "O&M": [m["rho_fom"]], "WACC": [m["rho_wacc"]],
    }).T.round(3)
    rho.columns = ["rho"]
    st.dataframe(rho)
    st.caption(f"Top driver: **{m['top_driver']}**")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 8 — Financial Model
# ─────────────────────────────────────────────────────────────────────────────
with tab_fin:
    st.header("Project finance model (USD m, real)")

    tech = st.selectbox("Technology", GEN_TECHS, index=1, key="fin_tech")
    r = a.loc[tech]

    col1, col2, col3, col4 = st.columns(4)
    cap = col1.number_input("Capacity (MW)", 10.0, 500.0, 100.0, 10.0)
    prem = col2.slider("PPA premium over LCOE", -0.20, 0.50, 0.15, 0.01)
    gear = col3.slider("Gearing", 0.30, 0.90, 0.70, 0.05)
    kd = col4.slider("Debt rate", 0.02, 0.12, 0.06, 0.01)

    col1, col2, col3, col4 = st.columns(4)
    ten = col1.slider("Tenor (yrs)", 5, 25, 18, 1)
    tax = col2.slider("Tax rate", 0.0, 0.50, 0.25, 0.01)
    ke = col3.slider("Cost of equity", 0.05, 0.20, 0.10, 0.01)
    infl = col4.slider("Opex inflation", 0.0, 0.06, 0.02, 0.01)

    df, m = project_finance(
        r, cap_mw=cap, ppa_prem=prem, gearing=gear, kd=kd,
        tenor=ten, tax=tax, ke=ke, infl=infl,
    )

    st.markdown("#### Key outputs")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("LCOE-1 ref", f"{lt.loc[tech,'lcoe_crf']:.1f}")
    c2.metric("PPA", f"{m['ppa']:.1f} USD/MWh")
    c3.metric("Project IRR", f"{m['project_irr']*100:.2f}%")
    c4.metric("Equity IRR", f"{m['equity_irr']*100:.2f}%")
    c5.metric("Min DSCR", f"{m['min_dscr']:.2f}x")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Capex", f"{m['capex_usd_m']:.1f} USD m")
    c2.metric("Equity NPV", f"{m['equity_npv']:.1f} USD m")
    c3.metric("Avg DSCR", f"{m['avg_dscr']:.2f}x")
    c4.metric("Payback", f"{int(m['payback']) if not pd.isna(m['payback']) else 'n/a'} yr")
    be = breakeven_ppa(r)
    c5.metric("Break-even PPA", f"{be:.1f}")

    st.subheader("Cash flow profile")
    fig = go.Figure()
    for col in ["revenue", "opex", "ebitda", "cfads", "equity_cf"]:
        fig.add_trace(go.Scatter(
            x=df["year"], y=df[col], mode="lines+markers", name=col
        ))
    fig.update_layout(height=400, xaxis_title="Year", yaxis_title="USD m")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("DSCR profile")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["year"], y=df["dscr"], name="DSCR",
                         marker_color="steelblue"))
    fig.add_hline(y=1.20, line_dash="dash", line_color="red",
                  annotation_text="DSCR 1.20x covenant")
    fig.update_layout(height=340, xaxis_title="Year", yaxis_title="DSCR (x)")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Equity IRR grid — PPA premium × gearing")
    prem_grid = [-.10, 0, .10, .20, .30]
    gear_grid = [.5, .6, .7, .8]
    grid_data = np.array([
        [project_finance(r, cap_mw=cap, ppa_prem=p, gearing=g,
                         kd=kd, tenor=ten, tax=tax, ke=ke, infl=infl)[1]["equity_irr"]
         for p in prem_grid] for g in gear_grid
    ])
    fig = px.imshow(
        grid_data * 100,
        x=[f"{p:+.0%}" for p in prem_grid],
        y=[f"{g:.0%}" for g in gear_grid],
        text_auto=".1f", color_continuous_scale="RdYlGn",
        labels={"x": "PPA premium", "y": "Gearing", "color": "Equity IRR (%)"},
    )
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Cash flow table")
    st.dataframe(df.round(2), use_container_width=True, height=400)
