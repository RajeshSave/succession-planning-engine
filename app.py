"""
Succession Planning Engine — Streamlit App
==========================================
Upload your 7 CSV files on the left sidebar and explore:
  Tab 1 — Succession Pipeline    (role selector + 3-deep pipeline cards)
  Tab 2 — Employee Profile       (full candidate deep-dive)
  Tab 3 — Compare Employees      (side-by-side multi-slider comparison)
  Tab 4 — Org Chart              (interactive hierarchy tree)
  Tab 5 — Org Readiness          (heatmap + bench strength + risk matrix)
  Tab 6 — KF Assessment Explorer (KFALP + viaEdge dimension explorer)
  Tab 7 — Career Path            (career timeline + promotion trajectory)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import networkx as nx
import io, base64, textwrap

def hex_to_rgba(hex_color, alpha=0.18):
    """Convert #RRGGBB to rgba(r,g,b,alpha) — required for Plotly 6+."""
    h = hex_color.lstrip('#')
    if len(h) == 6:
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        return f"rgba({r},{g},{b},{alpha})"
    return hex_color  # pass-through if already rgba or named


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Succession Planning Engine",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&display=swap');

/* ── Root palette ── */
:root {
  --navy:     #0B2540;
  --teal:     #0D7377;
  --teal-lt:  #14A8AE;
  --gold:     #C9A227;
  --gold-lt:  #F0C93A;
  --g5:       #1B7A3E;
  --g4:       #2563EB;
  --g3:       #D97706;
  --g2:       #EA580C;
  --g1:       #B91C1C;
  --bg:       #F0F4F8;
  --card:     #FFFFFF;
  --border:   #D1DCE8;
  --text:     #1A2535;
  --muted:    #64748B;
}

/* ── Global font ── */
html, body, [class*="css"] {
  font-family: 'DM Sans', sans-serif !important;
  background-color: var(--bg) !important;
  color: var(--text) !important;
}

/* ── Hide streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.2rem 1.8rem 2rem 1.8rem !important; max-width: 100% !important; }

/* ── App title bar ── */
.app-title {
  background: linear-gradient(135deg, var(--navy) 0%, #1a3a5c 60%, var(--teal) 100%);
  border-radius: 14px;
  padding: 18px 28px;
  margin-bottom: 18px;
  display: flex; align-items: center; gap: 16px;
}
.app-title h1 {
  font-family: 'Syne', sans-serif !important;
  font-size: 1.7rem; font-weight: 800;
  color: #fff; margin: 0; letter-spacing: -0.5px;
}
.app-title p { color: #9EC5D8; margin: 2px 0 0 0; font-size: 0.85rem; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
  background: var(--navy);
  border-radius: 12px;
  padding: 6px;
  margin-bottom: 18px;
}
.stTabs [data-baseweb="tab"] {
  font-family: 'Syne', sans-serif !important;
  font-weight: 600; font-size: 0.82rem;
  color: #9EC5D8 !important;
  border-radius: 8px;
  padding: 8px 16px;
  border: none !important;
  background: transparent !important;
  white-space: nowrap;
}
.stTabs [aria-selected="true"] {
  background: var(--teal) !important;
  color: #fff !important;
}
.stTabs [data-baseweb="tab-panel"] { padding: 0 !important; }

/* ── Cards ── */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px 22px;
  box-shadow: 0 2px 12px rgba(11,37,64,0.07);
  margin-bottom: 14px;
}
.card-navy {
  background: var(--navy);
  border-radius: 14px;
  padding: 18px 22px;
  margin-bottom: 14px;
  color: white;
}

/* ── KPI chips ── */
.kpi-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.kpi {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 18px;
  flex: 1; min-width: 130px;
  box-shadow: 0 1px 6px rgba(11,37,64,0.06);
}
.kpi-value {
  font-family: 'Syne', sans-serif;
  font-size: 1.8rem; font-weight: 800;
  color: var(--teal); line-height: 1.1;
}
.kpi-label { font-size: 0.75rem; color: var(--muted); margin-top: 2px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }

/* ── Pipeline successor card ── */
.scard {
  border-radius: 14px;
  padding: 18px 20px;
  margin-bottom: 12px;
  border-left: 5px solid var(--teal);
  background: var(--card);
  box-shadow: 0 2px 10px rgba(11,37,64,0.08);
  position: relative;
}
.scard-rank {
  position: absolute; top: 14px; right: 16px;
  font-family: 'Syne', sans-serif;
  font-size: 0.7rem; font-weight: 800;
  background: var(--navy);
  color: var(--gold-lt);
  border-radius: 20px;
  padding: 3px 10px;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.scard h3 { font-family: 'Syne', sans-serif; font-size: 1.05rem; font-weight: 700; margin: 0 0 2px 0; }
.scard .role-label { font-size: 0.78rem; color: var(--muted); margin-bottom: 8px; }
.lps-num { font-family: 'Syne', sans-serif; font-size: 2.2rem; font-weight: 800; line-height: 1; }
.band-pill {
  display: inline-block;
  border-radius: 20px;
  padding: 3px 10px;
  font-size: 0.72rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.5px;
  margin-left: 8px; vertical-align: middle;
}

/* ── Slider rows (profile) ── */
.slider-row { margin-bottom: 10px; }
.slider-label { font-size: 0.78rem; color: var(--muted); margin-bottom: 3px; display: flex; justify-content: space-between; }
.slider-track {
  height: 10px; border-radius: 6px;
  background: linear-gradient(90deg, #B91C1C 0%, #D97706 40%, #16A34A 100%);
  position: relative;
}
.slider-thumb {
  position: absolute; top: -4px;
  width: 18px; height: 18px;
  border-radius: 50%;
  border: 3px solid white;
  box-shadow: 0 2px 6px rgba(0,0,0,0.25);
  transform: translateX(-50%);
}

/* ── Section header ── */
.sec-hdr {
  font-family: 'Syne', sans-serif;
  font-size: 1.05rem; font-weight: 800;
  color: var(--navy);
  border-bottom: 2px solid var(--teal);
  padding-bottom: 6px; margin-bottom: 14px;
  display: flex; align-items: center; gap: 8px;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
  background: var(--navy) !important;
  border-right: none !important;
}
section[data-testid="stSidebar"] * { color: #C8DDE8 !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] .stFileUploader label { color: #9EC5D8 !important; font-size: 0.8rem !important; }
section[data-testid="stSidebar"] h2 {
  font-family: 'Syne', sans-serif !important;
  color: white !important; font-size: 1rem !important;
}

/* ── Metric override ── */
[data-testid="metric-container"] {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
}

/* ── Upload area ── */
.upload-hint {
  font-size: 0.78rem; color: #7A9AB8;
  text-align: center; padding: 8px;
  border: 1px dashed #3A5A78;
  border-radius: 8px; margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
BAND_COLORS = {
    "Band 5 - Ready Now":            "#1B7A3E",
    "Band 4 - Ready in 1-2 Years":   "#2563EB",
    "Band 3 - Ready in 2-3 Years":   "#D97706",
    "Band 2 - Emerging Potential":   "#EA580C",
    "Band 1 - Not Yet Ready":        "#B91C1C",
}
BAND_SHORT = {
    "Band 5 - Ready Now":            "Ready Now",
    "Band 4 - Ready in 1-2 Years":   "1-2 Yrs",
    "Band 3 - Ready in 2-3 Years":   "2-3 Yrs",
    "Band 2 - Emerging Potential":   "Emerging",
    "Band 1 - Not Yet Ready":        "Not Ready",
}
CLUSTER_COLORS = ["#0D7377","#C9A227","#2563EB","#7C3AED","#EA580C"]
CLUSTER_NAMES  = ["Performance","KF Assessment","Career Velocity","Leadership Breadth","Readiness"]

def lps_color(score):
    if score >= 80: return "#1B7A3E"
    if score >= 65: return "#2563EB"
    if score >= 50: return "#D97706"
    if score >= 35: return "#EA580C"
    return "#B91C1C"

def avatar_html(name, size=48, bg="#0D7377"):
    initials = "".join(p[0].upper() for p in name.split()[:2] if p)
    return f"""<div style="width:{size}px;height:{size}px;border-radius:50%;
        background:{bg};color:white;display:flex;align-items:center;
        justify-content:center;font-family:'Syne',sans-serif;
        font-weight:800;font-size:{size//3}px;flex-shrink:0;">{initials}</div>"""

def gauge_fig(value, title, max_val=100, color="#0D7377"):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"family": "Syne", "size": 13, "color": "#64748B"}},
        number={"font": {"family": "Syne", "size": 28, "color": color}, "suffix": ""},
        gauge={
            "axis": {"range": [0, max_val], "tickwidth": 1, "tickcolor": "#D1DCE8",
                     "tickfont": {"size": 9}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#F0F4F8",
            "borderwidth": 0,
            "steps": [
                {"range": [0, max_val*0.35], "color": "#FEE2E2"},
                {"range": [max_val*0.35, max_val*0.50], "color": "#FEF3C7"},
                {"range": [max_val*0.50, max_val*0.65], "color": "#DBEAFE"},
                {"range": [max_val*0.65, max_val*0.80], "color": "#D1FAE5"},
                {"range": [max_val*0.80, max_val],       "color": "#A7F3D0"},
            ],
            "threshold": {"line": {"color": "#0B2540", "width": 3},
                          "thickness": 0.8, "value": value},
        }
    ))
    fig.update_layout(margin=dict(l=10,r=10,t=30,b=10), height=180,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def speedometer_fig(value, title, max_val=5.0, color="#0D7377"):
    """0-5 scale speedometer for KF scores"""
    steps = [
        {"range": [0, 1.5], "color": "#FEE2E2"},
        {"range": [1.5, 2.5], "color": "#FEF3C7"},
        {"range": [2.5, 3.5], "color": "#DBEAFE"},
        {"range": [3.5, 4.5], "color": "#D1FAE5"},
        {"range": [4.5, 5.0], "color": "#6EE7B7"},
    ]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value if not np.isnan(value) else 0,
        title={"text": title, "font": {"family": "Syne", "size": 11, "color": "#64748B"}},
        number={"font": {"family": "Syne", "size": 22, "color": color},
                "valueformat": ".2f"},
        gauge={
            "axis": {"range": [0, max_val], "tickwidth": 1,
                     "tickvals": [1,2,3,4,5],
                     "ticktext": ["Limited","Developing","Effective","Strong","Exceptional"],
                     "tickfont": {"size": 8}},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "#F0F4F8", "borderwidth": 0,
            "steps": steps,
        }
    ))
    fig.update_layout(margin=dict(l=5,r=5,t=35,b=5), height=160,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def radar_fig(values, labels, name, color="#0D7377", ref_vals=None):
    fig = go.Figure()
    if ref_vals:
        fig.add_trace(go.Scatterpolar(
            r=ref_vals + [ref_vals[0]], theta=labels + [labels[0]],
            fill="toself", fillcolor="rgba(200,200,200,0.15)",
            line=dict(color="#C9A227", width=2, dash="dot"),
            name="Role Benchmark"
        ))
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]], theta=labels + [labels[0]],
        fill="toself", fillcolor=hex_to_rgba(color, 0.19),
        line=dict(color=color, width=2.5),
        name=name
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,5],
                                   tickvals=[1,2,3,4,5],
                                   tickfont={"size":8},
                                   gridcolor="#E2EAF0"),
                   angularaxis=dict(tickfont={"family":"DM Sans","size":10})),
        showlegend=True,
        legend=dict(font={"size":9}),
        margin=dict(l=40,r=40,t=30,b=30),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def slider_html(label, value, min_val, max_val, color="#0D7377", suffix="", pct=None):
    pct_pos = (value - min_val) / (max_val - min_val + 1e-9) * 100
    pct_pos = max(2, min(98, pct_pos))
    pct_str = f" ({int(pct_pos)}th pct)" if pct is None else f" ({pct}th pct)"
    return f"""
    <div class="slider-row">
      <div class="slider-label">
        <span>{label}</span>
        <span style="color:{color};font-weight:600">{value:.2f}{suffix}{pct_str}</span>
      </div>
      <div class="slider-track">
        <div class="slider-thumb" style="left:{pct_pos}%;background:{color};"></div>
      </div>
    </div>"""

def norm_pct(val, series):
    """Return percentile rank 0-100 of val within series (ignoring NaN)."""
    s = series.dropna()
    if len(s) == 0: return 50
    return int((s < val).mean() * 100)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — FILE UPLOAD + FILTERS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2>⬆ Upload Datasets</h2>", unsafe_allow_html=True)
    st.markdown('<div class="upload-hint">Upload all 7 CSV files to activate the engine</div>',
                unsafe_allow_html=True)

    uploaded = {
        "employees":  st.file_uploader("employees_master.csv",         type="csv", key="emp"),
        # "pipeline" will now be auto-generated
        "pipeline":   None,
        "kfalp":      st.file_uploader("kf_kfalp_detail.csv",          type="csv", key="kfl"),
        "viaedge":    st.file_uploader("kf_viaedge_detail.csv",        type="csv", key="via"),
        "ref":        st.file_uploader("kf_attribute_reference.csv",   type="csv", key="ref"),
        "promos":     st.file_uploader("promotion_history.csv",        type="csv", key="prm"),
        "org":        st.file_uploader("org_structure.csv",            type="csv", key="org"),
    }

    loaded = {k: v is not None for k, v in uploaded.items()}
    n_loaded = sum(loaded.values())
    TOTAL_REQUIRED_FILES = 6

    st.markdown(
        f"<div style='color:#6EE7B7;font-size:0.8rem;margin-top:6px'>✓ {n_loaded}/{TOTAL_REQUIRED_FILES} files loaded</div>",
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("<h2>🎛 LPS Weights</h2>", unsafe_allow_html=True)
    w1 = st.slider("Performance",        5, 60, 25, 5, key="w1")
    w2 = st.slider("KF Assessment",      5, 60, 30, 5, key="w2")
    w3 = st.slider("Career Velocity",    5, 40, 20, 5, key="w3")
    w4 = st.slider("Leadership Breadth", 5, 30, 15, 5, key="w4")
    w5 = st.slider("Readiness",          5, 30, 10, 5, key="w5")
    total_w = w1+w2+w3+w4+w5
    wcolor = "#6EE7B7" if total_w == 100 else "#FCA5A5"
    st.markdown(f"<div style='color:{wcolor};font-size:0.85rem;font-weight:600'>Total: {total_w}% {'✓' if total_w==100 else '— must equal 100%'}</div>",
                unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<h2>🔍 Filters</h2>", unsafe_allow_html=True)
    exclude_high_risk = st.checkbox("Exclude High Flight Risk", value=True)
    min_grade = st.slider("Min Grade for Eligibility", 1, 9, 5)

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_csv(file_obj):
    return pd.read_csv(file_obj)

data = {}
for key, uf in uploaded.items():
    if uf is not None:
        data[key] = load_csv(uf)

# ─────────────────────────────────────────────────────────────────────────────
# RECOMPUTE LPS with sidebar weights
# ─────────────────────────────────────────────────────────────────────────────
def recompute_lps(df, w1, w2, w3, w4, w5):
    def sn(s):
        lo, hi = s.min(), s.max()
        return ((s - lo) / (hi - lo + 1e-9) * 100)

    c1 = (sn(df["Average Performance Rating - Last 3 Years (1-5)"]) * 0.50 +
          sn(df["Last Annual Performance Rating (1-5)"])             * 0.35 +
          df["Performance Trajectory"].clip(-2,2).add(2).div(4).mul(100) * 0.15)

    kf_col = "KF Blended Assessment Composite (1-5)"
    perf_col = "Average Performance Rating - Last 3 Years (1-5)"
    kf_fill = df[kf_col].fillna(df[perf_col]) if kf_col in df.columns else df[perf_col]
    c2 = sn(kf_fill)

    c3 = (sn(df["Promotions per Year (Career)"])       * 0.50 +
          sn(df["Promotions per Year (Last 5 Years)"]) * 0.35 +
          sn(df["Total Promotions (Career)"])           * 0.15)

    breadth = (df["Cross-Functional Experience"].astype(int)*25 +
               df["International / Multi-Geography Experience"].astype(int)*20 +
               sn(df["Number of Critical Projects Led"])*30 +
               sn(df["External Industry Recognition Count"])*15 +
               sn(df["Number of Direct Reports"])*10)
    c4 = sn(breadth)

    fr_map  = {"Low":100,"Medium":50,"High":0}
    gg      = 9 - df["Job Grade (1-9)"]
    c5 = (sn(df["Mobility / Relocation Willingness (1-5)"]) * 0.35 +
          sn(gg.max() - gg)                                  * 0.35 +
          df["Flight Risk"].map(fr_map)                      * 0.30)

    lps = (c1*(w1/100) + c2*(w2/100) + c3*(w3/100) +
           c4*(w4/100) + c5*(w5/100)).round(2)

    def band(s):
        if s>=80: return "Band 5 - Ready Now"
        if s>=65: return "Band 4 - Ready in 1-2 Years"
        if s>=50: return "Band 3 - Ready in 2-3 Years"
        if s>=35: return "Band 2 - Emerging Potential"
        return "Band 1 - Not Yet Ready"

    df = df.copy()
    df["LPS"] = lps
    df["LPS Band"] = lps.apply(band)
    df["C1"] = c1.round(2); df["C2"] = c2.round(2)
    df["C3"] = c3.round(2); df["C4"] = c4.round(2); df["C5"] = c5.round(2)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# AUTO GENERATE SUCCESSION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def generate_succession_pipeline(df_emp, df_org=None):
    """
    Automatically generate succession pipeline from employee data.
    """

    critical_roles = []

    # Use org structure critical roles if available
    if df_org is not None and "Is Critical Role" in df_org.columns:
        critical_roles = (
            df_org[df_org["Is Critical Role"] == True]["Job Title"]
            .dropna()
            .unique()
            .tolist()
        )

    # Fallback: use higher grades
    if len(critical_roles) == 0:
        critical_roles = (
            df_emp[df_emp["Job Grade (1-9)"] >= 7]["Current Job Title"]
            .dropna()
            .unique()
            .tolist()
        )

    pipeline_rows = []

    for role in critical_roles:

        incumbents = df_emp[df_emp["Current Job Title"] == role]

        incumbent_name = (
            incumbents.iloc[0]["Employee Full Name"]
            if len(incumbents) > 0 else "Vacant"
        )

        incumbent_ee = (
            incumbents.iloc[0]["EE Number"]
            if len(incumbents) > 0 else "NA"
        )

        successors = (
            df_emp[df_emp["Current Job Title"] != role]
            .sort_values("LPS", ascending=False)
            .head(3)
        )

        row = {
            "Critical Role": role,
            "Incumbent Name": incumbent_name,
            "Incumbent EE Number": incumbent_ee,
        }

        for idx, (_, s) in enumerate(successors.iterrows(), start=1):
            row[f"Successor {idx} Name"] = s["Employee Full Name"]
            row[f"Successor {idx} EE"] = s["EE Number"]
            row[f"Successor {idx} LPS"] = round(s["LPS"], 2)
            row[f"Successor {idx} Band"] = s["LPS Band"]

        pipeline_rows.append(row)

    return pd.DataFrame(pipeline_rows)


# ─────────────────────────────────────────────────────────────────────────────
# TITLE BAR
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-title">
  <div style="font-size:2.2rem">🎯</div>
  <div>
    <h1>Succession Planning Engine</h1>
    <p>Powered by HRMS Data · Korn Ferry KFALP · Korn Ferry viaEdge</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# GATE: need at least employees + pipeline
# ─────────────────────────────────────────────────────────────────────────────
if "employees" not in data:
    st.info("👈 Upload **employees_master.csv** to get started. All other datasets unlock advanced features.")
    st.stop()

df_emp = recompute_lps(data["employees"], w1, w2, w3, w4, w5)
# Normalise column names (dashes may differ)
df_emp.columns = [c.replace("–","-").replace("—","-") for c in df_emp.columns]

if exclude_high_risk:
    df_eligible = df_emp[df_emp["Flight Risk"] != "High"].copy()
else:
    df_eligible = df_emp.copy()
df_eligible = df_eligible[df_eligible["Job Grade (1-9)"] >= min_grade]

# Auto-generate succession pipeline
if "org" in data:
    df_pip = generate_succession_pipeline(df_eligible, data["org"])
else:
    df_pip = generate_succession_pipeline(df_eligible)

df_pip.columns = [c.replace("–","-").replace("—","-") for c in df_pip.columns]

CRITICAL_ROLES = sorted(df_pip["Critical Role"].unique().tolist())

# ═════════════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏆 Succession Pipeline",
    "👤 Employee Profile",
    "⚖️ Compare Employees",
    "🌐 Org Chart",
    "📊 Org Readiness",
    "🧠 KF Assessment",
    "📈 Career Path",
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — SUCCESSION PIPELINE
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    col_left, col_right = st.columns([1, 2.2], gap="large")

    with col_left:
        st.markdown('<div class="sec-hdr">🏢 Select Critical Role</div>', unsafe_allow_html=True)
        selected_role = st.selectbox("", CRITICAL_ROLES, label_visibility="collapsed", key="sel_role")

        # Incumbent info
        inc_rows = df_pip[df_pip["Critical Role"] == selected_role]
        if len(inc_rows) > 0:
            inc_name = inc_rows.iloc[0].get("Incumbent Name", "—")
            inc_ee   = inc_rows.iloc[0].get("Incumbent EE Number", "—")
        else:
            inc_name, inc_ee = "—", "—"

        st.markdown(f"""
        <div class="card-navy">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
            {avatar_html(inc_name if inc_name != '—' else 'X', 52, '#C9A227')}
            <div>
              <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1rem;color:white">{inc_name}</div>
              <div style="font-size:0.75rem;color:#9EC5D8">Current Incumbent</div>
              <div style="font-size:0.72rem;color:#6A9AB8">{inc_ee}</div>
            </div>
          </div>
          <div style="font-family:'Syne',sans-serif;font-size:0.85rem;font-weight:700;color:#F0C93A;line-height:1.3">{selected_role}</div>
        </div>""", unsafe_allow_html=True)

        # Talent pool stats
        pool = df_eligible.copy()
        n_pool = len(pool)
        ready_now = (pool["LPS Band"] == "Band 5 - Ready Now").sum()
        avg_lps   = pool["LPS"].mean()

        st.markdown(f"""
        <div class="kpi-row">
          <div class="kpi"><div class="kpi-value">{n_pool}</div><div class="kpi-label">Eligible Pool</div></div>
          <div class="kpi"><div class="kpi-value" style="color:#1B7A3E">{ready_now}</div><div class="kpi-label">Ready Now</div></div>
          <div class="kpi"><div class="kpi-value" style="color:#0D7377">{avg_lps:.0f}</div><div class="kpi-label">Avg LPS</div></div>
        </div>""", unsafe_allow_html=True)

        # LPS distribution donut
        band_counts = pool["LPS Band"].value_counts()
        fig_donut = go.Figure(go.Pie(
            labels=[BAND_SHORT.get(b, b) for b in band_counts.index],
            values=band_counts.values,
            hole=0.62,
            marker=dict(colors=[BAND_COLORS.get(b,"#888") for b in band_counts.index]),
            textfont=dict(family="DM Sans", size=10),
        ))
        fig_donut.update_layout(
            margin=dict(l=0,r=0,t=10,b=0), height=180,
            showlegend=True,
            legend=dict(font=dict(size=9, family="DM Sans"), orientation="h",
                        x=0.5, xanchor="center", y=-0.05),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text=f"<b>{n_pool}</b><br>Pool", x=0.5, y=0.5,
                              font=dict(family="Syne",size=14,color="#0B2540"),
                              showarrow=False)]
        )
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar":False}
)

    with col_right:
        st.markdown('<div class="sec-hdr">🔗 Succession Pipeline — Top 3 Successors</div>',
                    unsafe_allow_html=True
)

        # Get top 3 from recomputed LPS for this role
        # Use eligible pool filtered by role's min grade
        top3 = df_eligible.sort_values("LPS", ascending=False).head(3)

        if len(top3) == 0:
            st.warning("No eligible successors found with current filters.")
        else:
            rank_labels = ["#1 — Primary Successor", "#2 — Secondary Successor", "#3 — Tertiary Successor"]
            rank_colors = ["#1B7A3E", "#2563EB", "#D97706"]

            for i, (_, cand) in enumerate(top3.iterrows()):
                lps   = cand["LPS"]
                band  = cand["LPS Band"]
                bc    = BAND_COLORS.get(band, "#888")
                bs    = BAND_SHORT.get(band, band)
                name  = cand["Employee Full Name"]
                title = cand["Current Job Title"]
                ee    = cand["EE Number"]
                grade = int(cand["Job Grade (1-9)"])
                c1v, c2v, c3v, c4v, c5v = (
                    cand.get("C1",0), cand.get("C2",0),
                    cand.get("C3",0), cand.get("C4",0), cand.get("C5",0)
                )

                # Cluster mini-bar
                cluster_bar = go.Figure(go.Bar(
                    x=[c1v, c2v, c3v, c4v, c5v],
                    y=CLUSTER_NAMES,
                    orientation="h",
                    marker_color=CLUSTER_COLORS,
                    text=[f"{v:.0f}" for v in [c1v,c2v,c3v,c4v,c5v]],
                    textposition="outside",
                    textfont=dict(size=9, family="DM Sans"),
                ))
                cluster_bar.update_layout(
                    xaxis=dict(range=[0,105], showgrid=False, showticklabels=False),
                    yaxis=dict(tickfont=dict(size=9, family="DM Sans")),
                    margin=dict(l=0,r=40,t=0,b=0), height=100,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                )

                st.markdown(f"""
                <div class="scard" style="border-left-color:{rank_colors[i]}">
                  <div class="scard-rank">{rank_labels[i]}</div>
                  <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
                    {avatar_html(name, 44, rank_colors[i])}
                    <div style="flex:1">
                      <h3 style="color:#0B2540">{name}</h3>
                      <div class="role-label">{title} · Grade {grade} · {ee}</div>
                      <div style="display:flex;align-items:baseline;gap:6px;margin-top:4px">
                        <span class="lps-num" style="color:{bc}">{lps:.1f}</span>
                        <span style="font-size:0.78rem;color:#64748B">/ 100 LPS</span>
                        <span class="band-pill" style="background:{bc}20;color:{bc}">{bs}</span>
                      </div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
                st.plotly_chart(cluster_bar, use_container_width=True,
                                config={"displayModeBar":False}, key=f"cb_{i}_{selected_role}")
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        # Grouped comparison bar
        if len(top3) > 0:
            st.markdown('<div class="sec-hdr" style="margin-top:10px">📊 Pipeline Cluster Comparison</div>',
                        unsafe_allow_html=True)
            fig_cmp = go.Figure()
            names_top3 = top3["Employee Full Name"].tolist()
            cluster_vals = [[r.get("C1",0), r.get("C2",0), r.get("C3",0),
                             r.get("C4",0), r.get("C5",0)] for _, r in top3.iterrows()]
            bar_colors = ["#1B7A3E","#2563EB","#D97706"]
            for idx, (cname, cvals) in enumerate(zip(names_top3, cluster_vals)):
                fig_cmp.add_trace(go.Bar(
                    name=cname, x=CLUSTER_NAMES, y=cvals,
                    marker_color=bar_colors[idx],
                    text=[f"{v:.0f}" for v in cvals],
                    textposition="outside", textfont=dict(size=9),
                ))
            fig_cmp.update_layout(
                barmode="group",
                xaxis=dict(tickfont=dict(family="DM Sans", size=10)),
                yaxis=dict(range=[0,110], tickfont=dict(size=9)),
                legend=dict(font=dict(family="DM Sans",size=10), orientation="h",
                            x=0.5, xanchor="center", y=1.08),
                margin=dict(l=0,r=0,t=30,b=0), height=260,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_cmp, use_container_width=True,
                            config={"displayModeBar":False}
)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — EMPLOYEE PROFILE
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    search_col, _ = st.columns([2, 3])
    with search_col:
        all_names = sorted(df_emp["Employee Full Name"].unique())
        sel_emp = st.selectbox("Select Employee", all_names, key="emp_sel")

    emp = df_emp[df_emp["Employee Full Name"] == sel_emp].iloc[0]
    lps = emp["LPS"]
    bc  = lps_color(lps)
    band = emp["LPS Band"]

    # ── Header row ──────────────────────────────────────────────────────────
    h1, h2, h3 = st.columns([1.5, 1.5, 1])
    with h1:
        st.markdown(f"""
        <div class="card" style="display:flex;gap:16px;align-items:center">
          {avatar_html(sel_emp, 64, bc)}
          <div>
            <div style="font-family:'Syne',sans-serif;font-size:1.15rem;font-weight:800;color:#0B2540">{sel_emp}</div>
            <div style="color:#64748B;font-size:0.82rem">{emp['Current Job Title']}</div>
            <div style="color:#64748B;font-size:0.78rem">{emp['Department']} · Grade {int(emp['Job Grade (1-9)'])} · {emp['EE Number']}</div>
            <div style="margin-top:6px">
              <span class="band-pill" style="background:{bc}20;color:{bc};font-size:0.75rem">{BAND_SHORT.get(band,band)}</span>
              <span class="band-pill" style="background:#0D737720;color:#0D7377;font-size:0.75rem">{emp['9-Box Position']}</span>
              <span class="band-pill" style="background:{'#FEE2E2' if emp['Flight Risk']=='High' else '#FEF3C7' if emp['Flight Risk']=='Medium' else '#D1FAE5'};
                color:{'#B91C1C' if emp['Flight Risk']=='High' else '#D97706' if emp['Flight Risk']=='Medium' else '#166534'};font-size:0.75rem">
                Flight Risk: {emp['Flight Risk']}</span>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

    with h2:
        st.plotly_chart(gauge_fig(lps, "Leadership Potential Score", color=bc),
                        use_container_width=True, config={"displayModeBar":False}
)

    with h3:
        kfalp_comp = emp.get("KF KFALP - Composite Score (1-5)", np.nan)
        ve_comp    = emp.get("KF viaEdge - Learning Agility Composite (1-5)", np.nan)
        if not np.isnan(kfalp_comp):
            st.plotly_chart(speedometer_fig(kfalp_comp, "KFALP Composite", color="#C9A227"),
                            use_container_width=True, config={"displayModeBar":False}
)
        if not np.isnan(ve_comp):
            st.plotly_chart(speedometer_fig(ve_comp, "viaEdge Composite", color="#7C3AED"),
                            use_container_width=True, config={"displayModeBar":False}
)

    # ── Feature sliders + radar ──────────────────────────────────────────────
    sc1, sc2 = st.columns([1.3, 1])
    with sc1:
        st.markdown('<div class="sec-hdr">📏 Feature Profile — Position in Organisation</div>',
                    unsafe_allow_html=True)

        slider_defs = [
            ("Performance Rating (3yr Avg)",   "Average Performance Rating - Last 3 Years (1-5)", 1, 5),
            ("Last Performance Rating",         "Last Annual Performance Rating (1-5)", 1, 5),
            ("Total Promotions (Career)",       "Total Promotions (Career)", 0, 14),
            ("Promotions per Year (Career)",    "Promotions per Year (Career)", 0, 0.8),
            ("Promotions per Year (Last 5Yr)",  "Promotions per Year (Last 5 Years)", 0, 0.8),
            ("Tenure (Years)",                  "Tenure with Organisation (Years)", 0, 40),
            ("Direct Reports",                  "Number of Direct Reports", 0, 50),
            ("Critical Projects Led",           "Number of Critical Projects Led", 0, 14),
            ("Mobility Willingness",            "Mobility / Relocation Willingness (1-5)", 1, 5),
        ]
        kf_slider_defs = [
            ("KF KFALP — Drivers",              "KF KFALP - Drivers Score (1-5)", 1, 5, "#C9A227"),
            ("KF KFALP — Curiosity",            "KF KFALP - Curiosity Score (1-5)", 1, 5, "#C9A227"),
            ("KF KFALP — Insight",              "KF KFALP - Insight Score (1-5)", 1, 5, "#C9A227"),
            ("KF KFALP — Engagement",           "KF KFALP - Engagement Score (1-5)", 1, 5, "#C9A227"),
            ("KF KFALP — Determination",        "KF KFALP - Determination Score (1-5)", 1, 5, "#C9A227"),
            ("KF KFALP — Learnability",         "KF KFALP - Learnability Score (1-5)", 1, 5, "#C9A227"),
            ("KF viaEdge — Mental Agility",     "KF viaEdge - Mental Agility Score (1-5)", 1, 5, "#7C3AED"),
            ("KF viaEdge — People Agility",     "KF viaEdge - People Agility Score (1-5)", 1, 5, "#7C3AED"),
            ("KF viaEdge — Change Agility",     "KF viaEdge - Change Agility Score (1-5)", 1, 5, "#7C3AED"),
            ("KF viaEdge — Results Agility",    "KF viaEdge - Results Agility Score (1-5)", 1, 5, "#7C3AED"),
            ("KF viaEdge — Self-Awareness",     "KF viaEdge - Self-Awareness Score (1-5)", 1, 5, "#7C3AED"),
        ]

        html_sliders = ""
        for lbl, col, lo, hi in slider_defs:
            col_clean = col.replace("–","-").replace("—","-")
            if col_clean in df_emp.columns:
                val = emp.get(col_clean, lo)
                if pd.isna(val): val = lo
                pct = norm_pct(val, df_emp[col_clean])
                html_sliders += slider_html(lbl, float(val), lo, hi, "#0D7377", pct=pct)

        html_sliders += "<div style='margin-top:12px;font-family:Syne,sans-serif;font-size:0.85rem;font-weight:700;color:#C9A227;border-top:1px solid #E2EAF0;padding-top:10px'>Korn Ferry Assessment Scores</div>"
        for lbl, col, lo, hi, color in kf_slider_defs:
            col_clean = col.replace("–","-").replace("—","-")
            if col_clean in df_emp.columns:
                val = emp.get(col_clean, np.nan)
                if pd.isna(val):
                    html_sliders += f"<div class='slider-row'><div class='slider-label'><span>{lbl}</span><span style='color:#CBD5E1'>N/A</span></div></div>"
                    continue
                pct = norm_pct(val, df_emp[col_clean].dropna())
                html_sliders += slider_html(lbl, float(val), lo, hi, color, pct=pct)

        st.markdown(f'<div class="card">{html_sliders}</div>', unsafe_allow_html=True)

    with sc2:
        st.markdown('<div class="sec-hdr">🕸 Leadership Potential Radar</div>',
                    unsafe_allow_html=True)

        kf_keys = [
            "KF KFALP - Drivers Score (1-5)",
            "KF KFALP - Curiosity Score (1-5)",
            "KF KFALP - Insight Score (1-5)",
            "KF KFALP - Engagement Score (1-5)",
            "KF KFALP - Determination Score (1-5)",
            "KF KFALP - Learnability Score (1-5)",
        ]
        kf_labels = ["Drivers","Curiosity","Insight","Engagement","Determination","Learnability"]
        kf_vals   = [float(emp.get(k, 2.5)) if not pd.isna(emp.get(k, np.nan)) else 2.5 for k in kf_keys]

        ve_keys = [
            "KF viaEdge - Mental Agility Score (1-5)",
            "KF viaEdge - People Agility Score (1-5)",
            "KF viaEdge - Change Agility Score (1-5)",
            "KF viaEdge - Results Agility Score (1-5)",
            "KF viaEdge - Self-Awareness Score (1-5)",
        ]
        ve_labels = ["Mental Agility","People Agility","Change Agility","Results Agility","Self-Awareness"]
        ve_vals   = [float(emp.get(k, 2.5)) if not pd.isna(emp.get(k, np.nan)) else 2.5 for k in ve_keys]

        ref_kf = [df_emp[k].mean() if k in df_emp.columns else 3.0 for k in kf_keys]
        ref_ve = [df_emp[k].mean() if k in df_emp.columns else 3.0 for k in ve_keys]

        st.plotly_chart(radar_fig(kf_vals, kf_labels, "KFALP", "#C9A227", ref_kf),
                        use_container_width=True, config={"displayModeBar":False}
)
        st.plotly_chart(radar_fig(ve_vals, ve_labels, "viaEdge", "#7C3AED", ref_ve),
                        use_container_width=True, config={"displayModeBar":False}
)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPARE EMPLOYEES
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="sec-hdr">⚖️ Select 2–4 Employees to Compare</div>',
                unsafe_allow_html=True)
    sel_emps = st.multiselect("Choose employees", all_names, max_selections=4,
                               default=all_names[:2] if len(all_names) >= 2 else all_names,
                               key="cmp_sel")

    if len(sel_emps) < 2:
        st.info("Select at least 2 employees to compare.")
    else:
        cmp_colors = ["#0D7377","#C9A227","#7C3AED","#EA580C"]
        cmp_df     = df_emp[df_emp["Employee Full Name"].isin(sel_emps)].copy()

        # ── Header cards ──────────────────────────────────────────────────
        hcols = st.columns(len(sel_emps))
        for i, name in enumerate(sel_emps):
            row = cmp_df[cmp_df["Employee Full Name"] == name].iloc[0]
            clr = cmp_colors[i]
            lps = row["LPS"]
            with hcols[i]:
                st.plotly_chart(gauge_fig(lps, name[:20], color=clr),
                                use_container_width=True, config={"displayModeBar":False}
)
                st.markdown(f"""
                <div style="text-align:center;font-size:0.78rem;color:#64748B">
                  {row['Current Job Title']}<br>Grade {int(row['Job Grade (1-9)'])}
                  <span class="band-pill" style="background:{clr}20;color:{clr}">{BAND_SHORT.get(row['LPS Band'],row['LPS Band'])}</span>
                </div>""", unsafe_allow_html=True)

        # ── Multi-slider comparison ────────────────────────────────────────
        st.markdown('<div class="sec-hdr" style="margin-top:16px">📏 Feature Comparison Sliders</div>',
                    unsafe_allow_html=True)

        all_slider_defs = [
            ("Leadership Potential Score",      "LPS", 0, 100),
            ("Performance Rating (3yr Avg)",    "Average Performance Rating - Last 3 Years (1-5)", 1, 5),
            ("Total Promotions (Career)",       "Total Promotions (Career)", 0, 14),
            ("Promotions per Year",             "Promotions per Year (Career)", 0, 0.8),
            ("KF KFALP — Composite",            "KF KFALP - Composite Score (1-5)", 1, 5),
            ("KF viaEdge — Composite",          "KF viaEdge - Learning Agility Composite (1-5)", 1, 5),
            ("KF KFALP — Learnability",         "KF KFALP - Learnability Score (1-5)", 1, 5),
            ("KF viaEdge — Change Agility",     "KF viaEdge - Change Agility Score (1-5)", 1, 5),
            ("KF viaEdge — Results Agility",    "KF viaEdge - Results Agility Score (1-5)", 1, 5),
            ("Tenure (Years)",                  "Tenure with Organisation (Years)", 0, 40),
            ("Critical Projects Led",           "Number of Critical Projects Led", 0, 14),
            ("Direct Reports",                  "Number of Direct Reports", 0, 50),
            ("Mobility Willingness",            "Mobility / Relocation Willingness (1-5)", 1, 5),
        ]

        html_cmp = ""
        for lbl, col, lo, hi in all_slider_defs:
            col_clean = col.replace("–","-").replace("—","-")
            if col_clean not in cmp_df.columns:
                continue
            html_cmp += f"<div style='font-size:0.78rem;color:#64748B;margin:10px 0 4px 0;font-weight:600'>{lbl}</div>"
            html_cmp += f"<div style='height:10px;border-radius:6px;background:linear-gradient(90deg,#B91C1C 0%,#D97706 40%,#16A34A 100%);position:relative;margin-bottom:14px'>"
            for j, name in enumerate(sel_emps):
                row = cmp_df[cmp_df["Employee Full Name"] == name]
                if len(row) == 0: continue
                val = row.iloc[0].get(col_clean, np.nan)
                if pd.isna(val): continue
                pct_pos = (float(val) - lo) / (hi - lo + 1e-9) * 100
                pct_pos = max(2, min(98, pct_pos))
                clr = cmp_colors[j]
                html_cmp += f"<div title='{name}: {val:.2f}' style='position:absolute;top:-5px;left:{pct_pos}%;width:20px;height:20px;border-radius:50%;background:{clr};border:3px solid white;transform:translateX(-50%);box-shadow:0 2px 6px rgba(0,0,0,0.25);cursor:pointer'></div>"
            html_cmp += "</div>"
            # Legend row
            html_cmp += "<div style='display:flex;gap:12px;flex-wrap:wrap;margin-bottom:2px'>"
            for j, name in enumerate(sel_emps):
                row = cmp_df[cmp_df["Employee Full Name"] == name]
                if len(row) == 0: continue
                val = row.iloc[0].get(col_clean, np.nan)
                clr = cmp_colors[j]
                val_str = f"{val:.2f}" if not pd.isna(val) else "N/A"
                html_cmp += f"<span style='font-size:0.72rem;color:{clr};font-weight:600'>⬤ {name.split()[0]}: {val_str}</span>"
            html_cmp += "</div>"

        st.markdown(f'<div class="card">{html_cmp}</div>', unsafe_allow_html=True)

        # ── Overlay radar ─────────────────────────────────────────────────
        st.markdown('<div class="sec-hdr" style="margin-top:12px">🕸 KF Assessment Overlay Radar</div>',
                    unsafe_allow_html=True)
        fig_ov = go.Figure()
        kf_radar_keys = ["KF KFALP - Drivers Score (1-5)","KF KFALP - Curiosity Score (1-5)",
                         "KF KFALP - Insight Score (1-5)","KF KFALP - Engagement Score (1-5)",
                         "KF KFALP - Determination Score (1-5)","KF KFALP - Learnability Score (1-5)"]
        kf_radar_lbls = ["Drivers","Curiosity","Insight","Engagement","Determination","Learnability"]
        for j, name in enumerate(sel_emps):
            row = cmp_df[cmp_df["Employee Full Name"] == name]
            if len(row) == 0: continue
            vals = [float(row.iloc[0].get(k,2.5)) if not pd.isna(row.iloc[0].get(k,np.nan)) else 2.5
                    for k in kf_radar_keys]
            clr = cmp_colors[j]
            fig_ov.add_trace(go.Scatterpolar(
                r=vals+[vals[0]], theta=kf_radar_lbls+[kf_radar_lbls[0]],
                fill="toself", fillcolor=hex_to_rgba(clr, 0.15),
                line=dict(color=clr, width=2.5), name=name
            ))
        fig_ov.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,5],
                                       tickvals=[1,2,3,4,5],
                                       tickfont={"size":8})),
            legend=dict(font={"size":9,"family":"DM Sans"}),
            margin=dict(l=40,r=40,t=20,b=20), height=380,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_ov, use_container_width=True, config={"displayModeBar":False}
)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — ORG CHART
# ═════════════════════════════════════════════════════════════════════════════
with tab4:
    if "org" not in data:
        st.info("Upload **org_structure.csv** to view the interactive org chart."
)
    else:
        df_org = data["org"].copy()
        df_org.columns = [c.replace("–","-").replace("—","-") for c in df_org.columns]

        st.markdown('<div class="sec-hdr">🌐 Interactive Organisation Chart</div>',
                    unsafe_allow_html=True)

        # Merge LPS from employees
        lps_map = df_emp.set_index("Current Job Title")["LPS"].to_dict()
        df_org["LPS"] = df_org["Job Title"].map(lps_map)

        # Build networkx graph for layout
        G = nx.DiGraph()
        for _, row in df_org.iterrows():
            G.add_node(row["Job Title"],
                       grade=row.get("Job Grade (1-9)", 5),
                       dept=row.get("Department",""),
                       level=row.get("Org Level",2),
                       lps=row.get("LPS", 50),
                       is_critical=row.get("Is Critical Role", False))
            if row["Parent Node ID"] and str(row["Parent Node ID"]) != "nan":
                G.add_edge(row["Parent Node ID"], row["Job Title"])

        # Hierarchical layout using BFS levels
        pos = {}
        levels = {}
        root = [n for n in G.nodes if G.in_degree(n) == 0]
        if root:
            from collections import deque
            q = deque([(root[0], 0)])
            visited = set()
            while q:
                node, depth = q.popleft()
                if node in visited: continue
                visited.add(node)
                levels.setdefault(depth, []).append(node)
                for child in G.successors(node):
                    q.append((child, depth+1))

        for depth, nodes_at_level in levels.items():
            n = len(nodes_at_level)
            for i, node in enumerate(nodes_at_level):
                pos[node] = (i - (n-1)/2.0, -depth * 1.8)

        # Build plotly figure
        edge_x, edge_y = [], []
        for u, v in G.edges():
            if u in pos and v in pos:
                x0, y0 = pos[u]; x1, y1 = pos[v]
                edge_x += [x0, x1, None]; edge_y += [y0, y1, None]

        grade_colors = {9:"#0B2540",8:"#0D7377",7:"#C9A227",6:"#2563EB",
                        5:"#7C3AED",4:"#16A34A",3:"#EA580C",2:"#64748B",1:"#94A3B8"}

        node_x, node_y, node_text, node_color, node_size, node_hover = [],[],[],[],[],[]
        for node in G.nodes():
            if node not in pos: continue
            x, y = pos[node]
            node_x.append(x); node_y.append(y)
            nd = G.nodes[node]
            g  = nd.get("grade", 5)
            lps_v = nd.get("lps", 50)
            is_cr = nd.get("is_critical", False)
            node_color.append(grade_colors.get(g,"#888"))
            node_size.append(30 if g >= 9 else 24 if g >= 7 else 18)
            short = node[:22] + ("..." if len(node) > 22 else "")
            node_text.append(short)
            _lps_str = f"{lps_v:.1f}" if (lps_v is not None and not (isinstance(lps_v, float) and lps_v != lps_v)) else "N/A"
            _cr_str  = "★ Critical Role" if is_cr else ""
            node_hover.append(f"<b>{node}</b><br>Grade: {g}<br>LPS: {_lps_str}<br>{_cr_str}")

        fig_org = go.Figure()
        fig_org.add_trace(go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(width=1.2, color="#CBD5E1"), hoverinfo="none"
        ))
        fig_org.add_trace(go.Scatter(
            x=node_x, y=node_y, mode="markers+text",
            marker=dict(size=node_size, color=node_color,
                        line=dict(width=2, color="white"),
                        symbol="circle"),
            text=node_text,
            textposition="bottom center",
            textfont=dict(family="DM Sans", size=8, color="#1A2535"),
            hovertext=node_hover,
            hoverinfo="text",
        ))
        fig_org.update_layout(
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=20,r=20,t=20,b=20),
            height=560,
            paper_bgcolor="white",
            plot_bgcolor="white",
            hoverlabel=dict(bgcolor="white", font_size=11,
                            font_family="DM Sans", bordercolor="#D1DCE8"),
        )
        st.plotly_chart(fig_org, use_container_width=True, config={"displayModeBar": True}
)

        # Legend
        leg_cols = st.columns(len(grade_colors)
)
        for i, (g, c) in enumerate(sorted(grade_colors.items(), reverse=True)):
            with leg_cols[i]:
                st.markdown(f"<div style='display:flex;align-items:center;gap:4px;font-size:0.72rem'>"
                            f"<div style='width:12px;height:12px;border-radius:50%;background:{c}'></div>"
                            f"Grade {g}</div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — ORG READINESS
# ═════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="sec-hdr">📊 Organisational Succession Readiness</div>',
                unsafe_allow_html=True)

    # KPI Banner
    n_roles    = len(CRITICAL_ROLES)
    top1_lps   = df_eligible.sort_values("LPS",ascending=False).groupby("Current Job Title")["LPS"].first()
    avg_top1   = top1_lps.mean() if len(top1_lps) > 0 else 0
    pct_band3  = (df_eligible["LPS Band"].isin(
                  ["Band 5 - Ready Now","Band 4 - Ready in 1-2 Years","Band 3 - Ready in 2-3 Years"])
                 ).mean() * 100
    high_risk_in_pool = (df_emp["Flight Risk"]=="High").mean()*100

    k1,k2,k3,k4,k5 = st.columns(5)
    for col_w, val, lbl, clr in [
        (k1, n_roles, "Critical Roles", "#0B2540"),
        (k2, f"{avg_top1:.1f}", "Avg LPS — #1 Successor", "#0D7377"),
        (k3, f"{pct_band3:.0f}%", "Pool at Band 3+", "#1B7A3E"),
        (k4, f"{high_risk_in_pool:.0f}%", "High Flight Risk", "#B91C1C"),
        (k5, len(df_eligible), "Eligible Employees", "#2563EB"),
    ]:
        with col_w:
            st.markdown(f"""
            <div class="kpi">
              <div class="kpi-value" style="color:{clr}">{val}</div>
              <div class="kpi-label">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    r1c1, r1c2 = st.columns([1.8, 1])

    with r1c1:
        # Bench strength heatmap
        st.markdown('<div class="sec-hdr">🔥 Bench Strength Heatmap — Top 3 Successors per Role</div>',
                    unsafe_allow_html=True)

        heat_data = []
        role_labels = []
        for role in CRITICAL_ROLES:
            top3 = df_eligible.sort_values("LPS", ascending=False).head(3)
            lps_vals = top3["LPS"].tolist()
            while len(lps_vals) < 3: lps_vals.append(None)
            heat_data.append(lps_vals[:3])
            role_labels.append(role[:35])

        heat_z = [[v if v is not None else 0 for v in row] for row in heat_data]
        heat_text = [[f"{v:.1f}" if v is not None else "—" for v in row] for row in heat_data]

        fig_heat = go.Figure(go.Heatmap(
            z=heat_z,
            x=["Successor #1","Successor #2","Successor #3"],
            y=role_labels,
            text=heat_text,
            texttemplate="%{text}",
            textfont=dict(family="Syne", size=11, color="white"),
            colorscale=[
                [0.0,  "#B91C1C"], [0.35, "#EA580C"],
                [0.50, "#D97706"], [0.65, "#2563EB"],
                [0.80, "#1B7A3E"], [1.0,  "#065F46"],
            ],
            zmin=0, zmax=100,
            showscale=True,
            colorbar=dict(title="LPS", tickfont=dict(size=9)),
        ))
        fig_heat.update_layout(
            margin=dict(l=0,r=0,t=10,b=0), height=420,
            xaxis=dict(tickfont=dict(family="Syne",size=10)),
            yaxis=dict(tickfont=dict(family="DM Sans",size=9), autorange="reversed"),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar":False}
)

    with r1c2:
        # LPS distribution
        st.markdown('<div class="sec-hdr">🎯 LPS Band Distribution</div>',
                    unsafe_allow_html=True
)
        band_dist = df_eligible["LPS Band"].value_counts()
        fig_bands = go.Figure(go.Bar(
            x=band_dist.values,
            y=[BAND_SHORT.get(b,b) for b in band_dist.index],
            orientation="h",
            marker_color=[BAND_COLORS.get(b,"#888") for b in band_dist.index],
            text=band_dist.values, textposition="outside",
            textfont=dict(family="DM Sans",size=10),
        ))
        fig_bands.update_layout(
            xaxis=dict(showgrid=False,showticklabels=False),
            yaxis=dict(tickfont=dict(family="DM Sans",size=10)),
            margin=dict(l=0,r=40,t=10,b=0), height=220,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_bands, use_container_width=True, config={"displayModeBar":False}
)

        # 9-box distribution
        st.markdown('<div class="sec-hdr">9-Box Distribution</div>', unsafe_allow_html=True
)
        nb = df_eligible["9-Box Position"].value_counts().head(6)
        fig_nb = go.Figure(go.Bar(
            x=nb.values, y=nb.index.str[:28],
            orientation="h",
            marker_color="#0D7377",
            text=nb.values, textposition="outside",
            textfont=dict(size=9),
        ))
        fig_nb.update_layout(
            xaxis=dict(showgrid=False,showticklabels=False),
            yaxis=dict(tickfont=dict(family="DM Sans",size=8)),
            margin=dict(l=0,r=40,t=10,b=0), height=230,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_nb, use_container_width=True, config={"displayModeBar":False}
)

        # ─────────────────────────────────────────────────────────────────────
        # GRAPHICAL 9-BOX MATRIX
        # ─────────────────────────────────────────────────────────────────────
        st.markdown('<div class="sec-hdr">🧩 Graphical 9-Box Talent Matrix</div>',
                    unsafe_allow_html=True
)

        plot_df = df_eligible.copy()

        plot_df["Performance Axis"] = (
            plot_df["Average Performance Rating - Last 3 Years (1-5)"]
        )

        plot_df["Potential Axis"] = plot_df["LPS"] / 20

        plot_df["Category"] = plot_df["LPS Band"]

        fig_9box = px.scatter(
            plot_df,
            x="Performance Axis",
            y="Potential Axis",
            color="Category",
            hover_data=[
                "Employee Full Name",
                "Current Job Title",
                "Department",
                "LPS"
            ],
            color_discrete_map={
                "Band 5 - Ready Now": "#1B7A3E",
                "Band 4 - Ready in 1-2 Years": "#2563EB",
                "Band 3 - Ready in 2-3 Years": "#D97706",
                "Band 2 - Emerging Potential": "#EA580C",
                "Band 1 - Not Yet Ready": "#B91C1C",
            },
        )

        for x in [2.33, 3.66]:
            fig_9box.add_vline(
                x=x,
                line_width=2,
                line_dash="dash",
                line_color="#CBD5E1"
            )

        for y in [2.33, 3.66]:
            fig_9box.add_hline(
                y=y,
                line_width=2,
                line_dash="dash",
                line_color="#CBD5E1"
            )

        fig_9box.update_traces(
            marker=dict(
                size=14,
                line=dict(width=1, color="white")
            )
        )

        fig_9box.update_layout(
            height=650,
            title="Performance vs Potential — 9 Box Matrix",
            xaxis=dict(range=[1,5], title="Performance"),
            yaxis=dict(range=[1,5], title="Potential"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="white",
            legend=dict(
                orientation="h",
                y=1.05,
                x=0.5,
                xanchor="center"
            ),
        )

        st.plotly_chart(
            fig_9box,
            use_container_width=True,
            config={"displayModeBar":False}

        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 6 — KF ASSESSMENT EXPLORER
# ═════════════════════════════════════════════════════════════════════════════
with tab6:
    if "kfalp" not in data and "viaedge" not in data:
        st.info("Upload **kf_kfalp_detail.csv** and **kf_viaedge_detail.csv** to explore KF assessments.")
    else:
        st.markdown('<div class="sec-hdr">🧠 Korn Ferry Assessment Explorer</div>',
                    unsafe_allow_html=True)
        kf_tab1, kf_tab2, kf_tab3 = st.tabs(["KFALP Dimensions","viaEdge Dimensions","Reference Guide"])

        with kf_tab1:
            if "kfalp" in data:
                df_kf = data["kfalp"].copy()
                df_kf.columns = [c.replace("–","-").replace("—","-") for c in df_kf.columns]

                kfc1, kfc2 = st.columns([1,2])
                with kfc1:
                    kf_dims = df_kf["KF KFALP Dimension"].unique().tolist()
                    sel_dim = st.selectbox("KFALP Dimension", kf_dims, key="kfd")
                    dim_df  = df_kf[df_kf["KF KFALP Dimension"]==sel_dim]
                    # Score distribution
                    fig_kf_dist = px.histogram(
                        dim_df, x="Raw Score (1-5)", nbins=20,
                        color_discrete_sequence=["#C9A227"],
                        title=f"{sel_dim} — Score Distribution"
                    )
                    fig_kf_dist.update_layout(
                        margin=dict(l=0,r=0,t=30,b=0), height=220,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        title_font=dict(family="Syne",size=12),
                        xaxis_title=None, yaxis_title=None,
                    )
                    st.plotly_chart(fig_kf_dist, use_container_width=True,
                                    config={"displayModeBar":False}
)

                    # Band breakdown donut
                    band_cnt = dim_df["KFALP Rating Band"].value_counts()
                    kf_band_colors = {"Exceptional":"#065F46","Strong":"#1B7A3E",
                                      "Effective":"#2563EB","Developing":"#D97706","Limited":"#B91C1C"}
                    fig_kf_band = go.Figure(go.Pie(
                        labels=band_cnt.index, values=band_cnt.values, hole=0.55,
                        marker_colors=[kf_band_colors.get(b,"#888") for b in band_cnt.index],
                        textfont=dict(size=9),
                    ))
                    fig_kf_band.update_layout(
                        margin=dict(l=0,r=0,t=10,b=0), height=180,
                        showlegend=True,
                        legend=dict(font=dict(size=8),orientation="h",x=0.5,xanchor="center",y=-0.1),
                        paper_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_kf_band, use_container_width=True,
                                    config={"displayModeBar":False}
)

                with kfc2:
                    # Heatmap: employee × dimension
                    pivot = df_kf.pivot_table(
                        index="Employee Full Name", columns="KF KFALP Dimension",
                        values="Raw Score (1-5)", aggfunc="mean"
                    ).dropna()
                    pivot = pivot.sort_values("Learnability" if "Learnability" in pivot.columns
                                             else pivot.columns[0], ascending=False).head(30)
                    fig_kf_heat = px.imshow(
                        pivot.round(1),
                        color_continuous_scale=["#B91C1C","#D97706","#DBEAFE","#1B7A3E"],
                        zmin=1, zmax=5,
                        text_auto=".1f",
                        aspect="auto",
                        title="KFALP Scores — Top 30 Employees"
                    )
                    fig_kf_heat.update_layout(
                        margin=dict(l=0,r=0,t=30,b=0), height=480,
                        paper_bgcolor="rgba(0,0,0,0)",
                        title_font=dict(family="Syne",size=12),
                        xaxis_tickfont=dict(size=9),
                        yaxis_tickfont=dict(size=8),
                    )
                    st.plotly_chart(fig_kf_heat, use_container_width=True,
                                    config={"displayModeBar":False}
)

        with kf_tab2:
            if "viaedge" in data:
                df_ve = data["viaedge"].copy()
                df_ve.columns = [c.replace("–","-").replace("—","-") for c in df_ve.columns]

                vec1, vec2 = st.columns([1,2])
                with vec1:
                    ve_dims = df_ve["KF viaEdge Dimension"].unique().tolist()
                    sel_ve_dim = st.selectbox("viaEdge Dimension", ve_dims, key="ved")
                    ve_dim_df = df_ve[df_ve["KF viaEdge Dimension"]==sel_ve_dim]

                    fig_ve_dist = px.histogram(
                        ve_dim_df, x="Raw Score (1-5)", nbins=20,
                        color_discrete_sequence=["#7C3AED"],
                        title=f"{sel_ve_dim} — Distribution"
                    )
                    fig_ve_dist.update_layout(
                        margin=dict(l=0,r=0,t=30,b=0), height=220,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        title_font=dict(family="Syne",size=12),
                    )
                    st.plotly_chart(fig_ve_dist, use_container_width=True,
                                    config={"displayModeBar":False}
)

                    pct_col = "KF viaEdge Learning Agility Percentile"
                    if pct_col in df_ve.columns:
                        fig_pct = px.histogram(
                            df_ve.drop_duplicates("EE Number"),
                            x=pct_col, nbins=20,
                            color_discrete_sequence=["#0D7377"],
                            title="Learning Agility Percentile Distribution"
                        )
                        fig_pct.update_layout(
                            margin=dict(l=0,r=0,t=30,b=0), height=200,
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            title_font=dict(family="Syne",size=11),
                        )
                        st.plotly_chart(fig_pct, use_container_width=True,
                                        config={"displayModeBar":False}
)

                with vec2:
                    ve_pivot = df_ve.pivot_table(
                        index="Employee Full Name", columns="KF viaEdge Dimension",
                        values="Raw Score (1-5)", aggfunc="mean"
                    ).dropna()
                    ve_pivot = ve_pivot.sort_values(
                        "Mental Agility" if "Mental Agility" in ve_pivot.columns
                        else ve_pivot.columns[0], ascending=False).head(30)
                    fig_ve_heat = px.imshow(
                        ve_pivot.round(1),
                        color_continuous_scale=["#B91C1C","#D97706","#DBEAFE","#1B7A3E"],
                        zmin=1, zmax=5, text_auto=".1f", aspect="auto",
                        title="viaEdge Scores — Top 30 Employees"
                    )
                    fig_ve_heat.update_layout(
                        margin=dict(l=0,r=0,t=30,b=0), height=480,
                        paper_bgcolor="rgba(0,0,0,0)",
                        title_font=dict(family="Syne",size=12),
                        xaxis_tickfont=dict(size=9), yaxis_tickfont=dict(size=8),
                    )
                    st.plotly_chart(fig_ve_heat, use_container_width=True,
                                    config={"displayModeBar":False}
)

        with kf_tab3:
            if "ref" in data:
                df_ref = data["ref"].copy()
                df_ref.columns = [c.replace("–","-").replace("—","-") for c in df_ref.columns]
                instruments = df_ref["KF Instrument"].unique().tolist() if "KF Instrument" in df_ref.columns else []
                sel_inst = st.selectbox("Instrument", instruments, key="ref_inst")
                ref_sub  = df_ref[df_ref["KF Instrument"]==sel_inst]
                dims_ref = ref_sub["Dimension"].unique().tolist() if "Dimension" in ref_sub.columns else []
                sel_rdim = st.selectbox("Dimension", dims_ref, key="ref_dim")
                rd_sub   = ref_sub[ref_sub["Dimension"]==sel_rdim]
                if len(rd_sub) > 0:
                    st.markdown(f"""
                    <div class="card">
                      <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;color:#0D7377">{sel_rdim}</div>
                      <div style="font-size:0.8rem;color:#64748B;margin:4px 0 10px 0">{rd_sub.iloc[0].get('Category','')}</div>
                      <div style="font-size:0.82rem;margin-bottom:8px"><b>Sub-Dimensions:</b> {rd_sub.iloc[0].get('Sub-Dimensions','')}</div>
                      <div style="font-size:0.82rem;margin-bottom:8px"><b>What It Measures:</b> {rd_sub.iloc[0].get('What It Measures','')}</div>
                      <div style="font-size:0.82rem;margin-bottom:8px"><b>High Potential Signal:</b> {rd_sub.iloc[0].get('High Potential Signal','')}</div>
                      <div style="font-size:0.82rem;margin-bottom:8px"><b>Assessment Method:</b> {rd_sub.iloc[0].get('Assessment Method','')}</div>
                    </div>""", unsafe_allow_html=True)
                    st.markdown('<div class="sec-hdr" style="margin-top:8px">Band Descriptors</div>', unsafe_allow_html=True)
                    for _, brow in rd_sub.sort_values("Score", ascending=False).iterrows():
                        score = brow.get("Score", "")
                        band_name = brow.get("Rating Band","")
                        desc = brow.get("Behavioural Descriptor","")
                        kf_band_c = {"Exceptional":"#065F46","Strong":"#1B7A3E","Effective":"#2563EB",
                                     "Developing":"#D97706","Limited":"#B91C1C",
                                     "Expert":"#065F46","Advanced":"#1B7A3E",
                                     "Emerging":"#EA580C","Needs Development":"#B91C1C"}.get(band_name,"#888")
                        st.markdown(f"""
                        <div style="display:flex;gap:12px;margin-bottom:8px;align-items:flex-start">
                          <div style="background:{kf_band_c};color:white;border-radius:8px;
                            padding:4px 10px;font-family:'Syne',sans-serif;
                            font-size:0.75rem;font-weight:700;white-space:nowrap;flex-shrink:0">
                            {score} — {band_name}
                          </div>
                          <div style="font-size:0.8rem;color:#374151;line-height:1.5">{desc}</div>
                        </div>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 7 — CAREER PATH
# ═════════════════════════════════════════════════════════════════════════════
with tab7:
    if "promos" not in data:
        st.info("Upload **promotion_history.csv** to view career paths and trajectories.")
    else:
        df_promo = data["promos"].copy()
        df_promo.columns = [c.replace("–","-").replace("—","-") for c in df_promo.columns]

        st.markdown('<div class="sec-hdr">📈 Career Path & Promotion Trajectory</div>',
                    unsafe_allow_html=True)

        cp1, cp2 = st.columns([1, 2.5])
        with cp1:
            promo_names = sorted(df_promo["Employee Full Name"].unique().tolist())
            sel_cp = st.selectbox("Select Employee", promo_names, key="cp_sel")
            emp_cp = df_emp[df_emp["Employee Full Name"]==sel_cp]
            if len(emp_cp) > 0:
                e = emp_cp.iloc[0]
                lps_v = e["LPS"]
                lps_v_safe = float(lps_v) if lps_v == lps_v else 0.0
                clr_v = lps_color(lps_v_safe)
                st.markdown(f"""
                <div class="card">
                  <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px">
                    {avatar_html(sel_cp, 44, clr_v)}
                    <div>
                      <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:0.9rem">{sel_cp}</div>
                      <div style="font-size:0.75rem;color:#64748B">{e['Current Job Title']}</div>
                    </div>
                  </div>
                  <div style="font-size:0.78rem;color:#374151">
                    <b>Grade:</b> {int(e['Job Grade (1-9)'])} &nbsp;|&nbsp; <b>Tenure:</b> {e['Tenure with Organisation (Years)']}y<br>
                    <b>Total Promos:</b> {int(e['Total Promotions (Career)'])} &nbsp;|&nbsp; <b>LPS:</b> {lps_v_safe:.1f}
                  </div>
                </div>""", unsafe_allow_html=True)

                # KF speedometers for this employee
                k1v = e.get("KF KFALP - Composite Score (1-5)", np.nan)
                k2v = e.get("KF viaEdge - Learning Agility Composite (1-5)", np.nan)
                if not pd.isna(k1v):
                    st.plotly_chart(speedometer_fig(k1v,"KFALP Composite", color="#C9A227"),
                                    use_container_width=True, config={"displayModeBar":False}
)
                if not pd.isna(k2v):
                    st.plotly_chart(speedometer_fig(k2v,"viaEdge Composite", color="#7C3AED"),
                                    use_container_width=True, config={"displayModeBar":False}
)

        with cp2:
            emp_promos = df_promo[df_promo["Employee Full Name"]==sel_cp].sort_values("Promotion Year")
            if len(emp_promos) == 0:
                st.info(f"No promotion history found for {sel_cp}.")
            else:
                # Timeline / Gantt-style chart
                fig_timeline = go.Figure()
                years  = emp_promos["Promotion Year"].tolist()
                grades = emp_promos["Promoted To Grade"].tolist()
                perfs  = emp_promos["Performance Rating at Promotion"].tolist()

                # Grade progression line
                fig_timeline.add_trace(go.Scatter(
                    x=years, y=grades,
                    mode="lines+markers+text",
                    line=dict(color="#0D7377", width=3),
                    marker=dict(
                        size=[10 + p*2 for p in perfs],
                        color=perfs,
                        colorscale=[[0,"#B91C1C"],[0.5,"#D97706"],[1,"#1B7A3E"]],
                        cmin=1, cmax=5,
                        line=dict(width=2, color="white"),
                        showscale=True,
                        colorbar=dict(title="Perf@Promo",tickfont=dict(size=8),len=0.5,y=0.5),
                    ),
                    text=[f"G{g}" for g in grades],
                    textposition="top center",
                    textfont=dict(family="Syne",size=10,color="#0B2540"),
                    name="Grade",
                    hovertemplate="<b>%{x}</b><br>Promoted to Grade %{y}<br>Performance: %{marker.color:.1f}<extra></extra>",
                ))

                # Performance line (secondary axis)
                fig_timeline.add_trace(go.Scatter(
                    x=years, y=perfs,
                    mode="lines+markers",
                    line=dict(color="#C9A227", width=2, dash="dot"),
                    marker=dict(size=8, color="#C9A227"),
                    name="Performance",
                    yaxis="y2",
                    hovertemplate="<b>%{x}</b><br>Performance: %{y:.1f}<extra></extra>",
                ))

                # Add career start point
                career_sy = emp_promos["Promotion Year"].min() - 2
                entry_grade = emp_promos["Promoted From Grade"].iloc[0]
                fig_timeline.add_trace(go.Scatter(
                    x=[career_sy], y=[entry_grade],
                    mode="markers+text",
                    marker=dict(size=12, color="#64748B", symbol="square"),
                    text=["Entry"], textposition="top center",
                    textfont=dict(family="Syne",size=9,color="#64748B"),
                    name="Career Entry", hoverinfo="skip",
                ))

                emp_data = df_emp[df_emp["Employee Full Name"]==sel_cp]
                if len(emp_data) > 0:
                    curr_year  = YEAR if 'YEAR' in dir() else 2025
                    curr_grade = int(emp_data.iloc[0]["Job Grade (1-9)"])
                    fig_timeline.add_trace(go.Scatter(
                        x=[curr_year], y=[curr_grade],
                        mode="markers+text",
                        marker=dict(size=14, color=lps_color(emp_data.iloc[0]["LPS"]),
                                    symbol="star"),
                        text=["Now"], textposition="top center",
                        textfont=dict(family="Syne",size=10,color="#0B2540"),
                        name="Current Position", hoverinfo="skip",
                    ))

                fig_timeline.update_layout(
                    xaxis=dict(title="Year", tickfont=dict(family="DM Sans",size=10)),
                    yaxis=dict(title="Job Grade", range=[0, 10],
                               tickvals=list(range(1,10)),
                               tickfont=dict(family="DM Sans",size=10)),
                    yaxis2=dict(title="Performance Rating", overlaying="y", side="right",
                                range=[0,5.5], tickfont=dict(size=9)),
                    legend=dict(font=dict(family="DM Sans",size=9),
                                orientation="h", x=0.5, xanchor="center", y=1.06),
                    margin=dict(l=0,r=60,t=30,b=0), height=320,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8FBFD",
                    hovermode="x unified",
                )
                st.plotly_chart(fig_timeline, use_container_width=True,
                                config={"displayModeBar":False}
)

                # Promotion detail table
                st.markdown('<div class="sec-hdr" style="margin-top:8px">📋 Promotion History Detail</div>',
                            unsafe_allow_html=True)
                display_cols = ["Promotion Number (Career)","Promotion Year",
                                "Promoted From Grade","Promoted To Grade",
                                "Performance Rating at Promotion","Years Since Last Promotion"]
                display_cols = [c for c in display_cols if c in emp_promos.columns]
                st.dataframe(
                    emp_promos[display_cols].reset_index(drop=True),
                    use_container_width=True, hide_index=True,
                )

        # ── Organisation-wide promotion velocity ──────────────────────────
        st.markdown('<div class="sec-hdr" style="margin-top:16px">🚀 Organisation-wide Promotion Velocity by Grade</div>',
                    unsafe_allow_html=True)

        vel_df = df_emp[["Job Grade (1-9)","Promotions per Year (Career)",
                         "Average Performance Rating - Last 3 Years (1-5)"]].dropna()
        fig_vel = px.scatter(
            vel_df,
            x="Average Performance Rating - Last 3 Years (1-5)",
            y="Promotions per Year (Career)",
            color="Job Grade (1-9)",
            color_continuous_scale=px.colors.sequential.Teal,
            opacity=0.7,
            size_max=8,
            labels={"Average Performance Rating - Last 3 Years (1-5)": "Avg Performance (3yr)",
                    "Promotions per Year (Career)": "Promotions / Year",
                    "Job Grade (1-9)": "Grade"},
            title="Performance vs Promotion Velocity (coloured by Grade)",
        )
        fig_vel.update_layout(
            margin=dict(l=0,r=0,t=30,b=0), height=320,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F8FBFD",
            title_font=dict(family="Syne",size=12),
        )
