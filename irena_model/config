"""Central configuration: technology parameters (synthetic, calibrated to the
order of magnitude of published global weighted averages -- NOT official IRENA data)."""
SEED = 42
YEARS = list(range(2010, 2025))
BASE_YEAR = 2024
HOURS = 8760
GEN_TECHS = ["Solar PV", "Onshore Wind", "Offshore Wind", "CSP", "Hydropower", "Bioenergy"]

# capex: USD/kW (2024, global weighted avg), lr: learning rate, cf: capacity factor,
# fom: USD/kW/yr, var: USD/MWh (fuel + variable O&M), cum: global cumulative GW,
# g1/g2: reference deployment CAGR 2024-30 / 2030-50, drift: real capex drift for mature techs
TECH = {
 "Solar PV":      dict(capex=700,  lr=.24, cf10=.15, cf24=.17, fom=17, var=0,  life=30, degr=.005, constr=1, cum10=40,   cum24=1800, g1=.17,  g2=.06,  drift=0,     size=80),
 "Onshore Wind":  dict(capex=1300, lr=.12, cf10=.27, cf24=.36, fom=38, var=0,  life=25, degr=.002, constr=1, cum10=200,  cum24=1100, g1=.08,  g2=.04,  drift=0,     size=100),
 "Offshore Wind": dict(capex=3400, lr=.10, cf10=.38, cf24=.42, fom=95, var=0,  life=25, degr=.002, constr=3, cum10=3,    cum24=80,   g1=.22,  g2=.09,  drift=0,     size=450),
 "CSP":           dict(capex=4500, lr=.15, cf10=.30, cf24=.35, fom=80, var=2,  life=30, degr=0,    constr=3, cum10=1.1,  cum24=8.5,  g1=.15,  g2=.08,  drift=0,     size=150),
 "Hydropower":    dict(capex=2800, lr=0,   cf10=.48, cf24=.46, fom=56, var=1,  life=40, degr=0,    constr=5, cum10=1000, cum24=1400, g1=.018, g2=.012, drift=.008, size=300),
 "Bioenergy":     dict(capex=2400, lr=0,   cf10=.70, cf24=.68, fom=120,var=25, life=30, degr=0,    constr=2, cum10=60,   cum24=160,  g1=.03,  g2=.02,  drift=.005, size=40),
}
ENABLING = {  # capex in native unit
 "BESS (4h, utility)": dict(unit="USD/kWh", capex=275,  lr=.20, cum10=0.3, cum24=400, eff=(.84, .88)),
 "Electrolyser (PEM/Alk)": dict(unit="USD/kW", capex=1700, lr=.15, cum10=0.05, cum24=5, eff=(50, 55)),  # kWh/kgH2 (system)
}
COUNTRIES = {  # country: (region, capex multiplier)
 "China": ("Asia", .78), "India": ("Asia", .82), "Vietnam": ("Asia", .92), "Japan": ("Asia", 1.30),
 "Germany": ("Europe", 1.10), "UK": ("Europe", 1.12), "Spain": ("Europe", 1.00), "Netherlands": ("Europe", 1.12),
 "Denmark": ("Europe", 1.10), "USA": ("North America", 1.18), "Mexico": ("Latin America", 1.00),
 "Brazil": ("Latin America", .95), "South Africa": ("Africa", 1.02), "Egypt": ("Africa", .98), "Australia": ("Oceania", 1.15),
}
TECH_COUNTRIES = {
 "Solar PV": ["China","India","USA","Germany","Spain","Brazil","Mexico","Australia","Vietnam","South Africa","Egypt","Japan"],
 "Onshore Wind": ["China","India","USA","Germany","Spain","Brazil","Mexico","Australia","South Africa","Egypt","Denmark","UK"],
 "Offshore Wind": ["China","UK","Germany","Netherlands","Denmark","USA","Japan","Vietnam"],
 "CSP": ["China","Spain","USA","South Africa","Egypt","Australia","India"],
 "Hydropower": ["China","India","Brazil","Vietnam","Egypt","Mexico","South Africa","Spain"],
 "Bioenergy": ["China","India","Brazil","USA","Germany","UK","Denmark","Spain"],
}
BOUNDS = {  # plausibility ranges for QA: (capex_min, capex_max, cf_min, cf_max)
 "Solar PV": (250, 7000, .08, .35), "Onshore Wind": (700, 3500, .12, .60), "Offshore Wind": (2000, 9000, .25, .65),
 "CSP": (2500, 12000, .15, .60), "Hydropower": (800, 8000, .20, .90), "Bioenergy": (1000, 6000, .30, .90),
}
# Scenario levers: growth multiplier on CAGR, learning-rate delta, capex mult, WACC delta, CF mult, O&M mult, description
SCENARIOS = {
 "Reference":            (1.00, 0.00, 1.00, 0.000, 1.00, 1.00, "Current policies; learning continues at historical rates"),
 "Accelerated":          (1.25, 0.02, 1.00, -0.010, 1.03, 0.97, "1.5C-aligned: faster deployment, cheaper capital, better CF"),
 "Conservative":         (0.70, -0.02, 1.00, 0.015, 1.00, 1.03, "Slow policy support, tighter financing"),
 "Supply-chain shock":   (0.90, 0.00, 1.20, 0.010, 1.00, 1.05, "Persistent +20% equipment/logistics cost, higher rates"),
}
SCEN_YEARS = [2024, 2030, 2035, 2040, 2050]
GROWTH_BREAK_YEAR = 2030
WACC_BASE = 0.075
LR_MIN_R2 = 0.5
