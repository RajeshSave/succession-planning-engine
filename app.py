import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import networkx as nx
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Succession Planning Engine", layout="wide", initial_sidebar_state="expanded")

# ─────────────────────────────────────────────────────────────────────────────
# CSS STYLING
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&display=swap');

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
  box-shadow: 0 2px 12px rgba(11,37,64,0.08);
  margin-bottom: 12px;
}

/* ── Section headers ── */
.sec-hdr {
  font-family: 'Syne', sans-serif;
  font-size: 0.95rem; font-weight: 700;
  color: var(--navy);
  margin: 18px 0 12px 0;
  padding: 8px 0;
  border-bottom: 2px solid var(--gold);
}

/* ── Small cards ── */
.scard {
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 4px solid var(--teal);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: 0 1px 8px rgba(11,37,64,0.06);
  margin-bottom: 8px;
}
.scard-rank {
  font-family: 'Syne', sans-serif;
  font-size: 0.7rem; font-weight: 700;
  text-transform: uppercase;
  color: #64748B;
  margin-bottom: 4px;
}

/* ── Band pills ── */
.band-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  font-family: 'DM Sans', sans-serif;
  margin-right: 6px;
}

/* ── LPS number ── */
.lps-num {
  font-family: 'Syne', sans-serif;
  font-size: 1.4rem;
  font-weight: 800;
}

/* ── Role label ── */
.role-label {
  font-size: 0.8rem;
  color: #64748B;
  margin-top: 3px;
}

/* ── KPI row ── */
.kpi-row {
  display: flex;
  gap: 16px;
  margin: 12px 0 16px 0;
}
.kpi {
  flex: 1;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}
.kpi-value {
  font-family: 'Syne', sans-serif;
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--teal);
  line-height: 1;
}
.kpi-label {
  font-size: 0.78rem;
  color: #64748B;
  margin-top: 6px;
  font-weight: 500;
}

/* ── Sliders ── */
.slider-row {
  margin-bottom: 10px;
  padding: 8px 0;
}
.slider-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--text);
}
.slider-track {
  height: 6px;
  background: #E2EAF0;
  border-radius: 3px;
  position: relative;
  overflow: hidden;
}
.slider-thumb {
  height: 100%;
  border-radius: 3px;
  position: absolute;
  top: 0;
  transition: left 0.1s;
}

/* ── Upload hint ── */
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

def hex_to_rgba(hex_color, alpha=0.3):
    """Convert hex color to RGBA."""
    hex_color = hex_color.lstrip("#")
    return f"rgba({int(hex_color[0:2],16)},{int(hex_color[2:4],16)},{int(hex_color[4:6],16)},{alpha})"

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — FILE UPLOAD + FILTERS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2>⬆ Upload Datasets</h2>", unsafe_allow_html=True)
    st.markdown('<div class="upload-hint">Upload all 7 CSV files to activate the engine</div>',
                unsafe_allow_html=True)

    uploaded = {
        "employees":  st.file_uploader("employees_master.csv",         type="csv", key="emp"),
        "pipeline":   None,
        "kfalp":      st.file_uploader("kf_kfalp_detail.csv",          type="csv", key="kfl"),
        "viaedge":    st.file_uploader("kf_viaedge_detail.csv",        type="csv", key="via"),
        "ref":        st.file_uploader("kf_attribute_reference.csv",   type="csv", key="ref"),
        "promos":     st.file_uploader("promotion_history.csv",        type="csv", key="prm"),
        "org":        st.file_uploader("org_structure.csv",            type="csv", key="org"),
    }

    loaded = {k: v is not None for k, v in uploaded.items()}
    n_loaded = sum(loaded.values())
    
    st.markdown(f"<div style='text-align:center;font-size:0.85rem;color:#64748B;margin:12px 0'>"
                f"<b>{n_loaded}/7</b> files loaded</div>", unsafe_allow_html=True)

# Load and process data
data = {}
if uploaded["employees"] is not None:
    data["employees"] = pd.read_csv(uploaded["employees"])
if uploaded["kfalp"] is not None:
    data["kfalp"] = pd.read_csv(uploaded["kfalp"])
if uploaded["viaedge"] is not None:
    data["viaedge"] = pd.read_csv(uploaded["viaedge"])
if uploaded["ref"] is not None:
    data["ref"] = pd.read_csv(uploaded["ref"])
if uploaded["promos"] is not None:
    data["promos"] = pd.read_csv(uploaded["promos"])
if uploaded["org"] is not None:
    data["org"] = pd.read_csv(uploaded["org"])

# Check if minimum required data exists
if len(data) < 1:
    st.markdown("""
    <div class="card" style="text-align:center;padding:40px">
      <h2 style="color:#0B2540">📊 Succession Planning Engine</h2>
      <p style="color:#64748B;font-size:1.05rem">Upload CSV files to get started</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Process employees data
df_emp = data.get("employees", pd.DataFrame())
if len(df_emp) == 0:
    st.error("❌ employees_master.csv is required")
    st.stop()

df_emp.columns = [c.replace("–","-").replace("—","-") for c in df_emp.columns]
all_names = sorted(df_emp["Employee Full Name"].unique())

# ─────────────────────────────────────────────────────────────────────────────
# APP HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-title">
  <span style="font-size:2.2rem">🎯</span>
  <div>
    <h1>Succession Planning Engine</h1>
    <p>Strategic talent assessment & pipeline development</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "1️⃣ Succession Pipeline",
    "2️⃣ Employee Profile",
    "3️⃣ Compare Employees",
    "4️⃣ Org Structure",
    "5️⃣ Readiness Matrix",
    "6️⃣ KF Assessments",
    "7️⃣ Career Paths"
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — SUCCESSION PIPELINE
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="sec-hdr">🔍 Role Pipeline Explorer</div>', unsafe_allow_html=True)
    
    roles = sorted(df_emp["Current Job Title"].unique())
    selected_role = st.selectbox("Select Role", roles, key="role_sel")
    
    eligible = df_emp[df_emp["Current Job Title"] == selected_role]
    
    if len(eligible) == 0:
        st.info(f"No employees found in role: {selected_role}")
    else:
        # Pipeline metrics
        st.markdown('<div class="sec-hdr">📈 Pipeline Snapshot</div>', unsafe_allow_html=True)
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Current Incumbents", len(eligible))
        with m2:
            ready_now = (eligible["LPS Band"] == "Band 5 - Ready Now").sum()
            st.metric("Ready Now", ready_now)
        with m3:
            ready_12 = (eligible["LPS Band"].isin(["Band 4 - Ready in 1-2 Years", "Band 5 - Ready Now"])).sum()
            st.metric("Ready 1-2 Yrs", ready_12)
        with m4:
            avg_lps = eligible["LPS"].mean()
            st.metric("Avg LPS", f"{avg_lps:.0f}")
        
        # Top 3 successors
        st.markdown('<div class="sec-hdr">🌟 Top Succession Candidates</div>', unsafe_allow_html=True)
        
        top3 = eligible.nlargest(3, "LPS")
        
        for i, (_, row) in enumerate(top3.iterrows()):
            name = row["Employee Full Name"]
            title = row["Current Job Title"]
            grade = int(row["Job Grade (1-9)"])
            ee = row["EE Number"]
            lps = row["LPS"]
            bs = row["LPS Band"]
            bc = lps_color(lps)
            
            # Cluster scores
            c1v = row.get("C1", 0)
            c2v = row.get("C2", 0)
            c3v = row.get("C3", 0)
            c4v = row.get("C4", 0)
            c5v = row.get("C5", 0)
            
            cluster_bar = go.Figure(go.Bar(
                x=[c1v,c2v,c3v,c4v,c5v],
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
            
            rank_colors = ["#1B7A3E", "#2563EB", "#D97706"]
            rank_labels = ["🥇 1st Choice", "🥈 2nd Choice", "🥉 3rd Choice"]
            
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
                    <span class="band-pill" style="background:{bc}20;color:{bc}">{BAND_SHORT.get(bs,bs)}</span>
                  </div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)
            st.plotly_chart(cluster_bar, use_container_width=True,
                            config={"displayModeBar":False}, key=f"cb_{i}_{selected_role}")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — EMPLOYEE PROFILE
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    search_col, _ = st.columns([2, 3])
    with search_col:
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
                        use_container_width=True, config={"displayModeBar":False},
                        key=f"gauge_lps_{sel_emp}")

    with h3:
        kfalp_comp = emp.get("KF KFALP - Composite Score (1-5)", np.nan)
        ve_comp    = emp.get("KF viaEdge - Learning Agility Composite (1-5)", np.nan)
        if not np.isnan(kfalp_comp):
            st.plotly_chart(speedometer_fig(kfalp_comp, "KFALP Composite", color="#C9A227"),
                            use_container_width=True, config={"displayModeBar":False},
                            key=f"speedometer_kfalp_{sel_emp}")
        if not np.isnan(ve_comp):
            st.plotly_chart(speedometer_fig(ve_comp, "viaEdge Composite", color="#7C3AED"),
                            use_container_width=True, config={"displayModeBar":False},
                            key=f"speedometer_viaedge_{sel_emp}")

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
                        use_container_width=True, config={"displayModeBar":False},
                        key=f"radar_kfalp_{sel_emp}")
        st.plotly_chart(radar_fig(ve_vals, ve_labels, "viaEdge", "#7C3AED", ref_ve),
                        use_container_width=True, config={"displayModeBar":False},
                        key=f"radar_viaedge_{sel_emp}")

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
                                use_container_width=True, config={"displayModeBar":False},
                                key=f"gauge_cmp_{i}_{name}")
                st.markdown(f"<div style='text-align:center;font-size:0.8rem;color:#64748B'>"
                            f"{row['Current Job Title']}</div>", unsafe_allow_html=True)

        # ── Assessment comparison ────────────────────────────────────────────
        st.markdown('<div class="sec-hdr" style="margin-top:12px">📊 Assessment Comparison</div>',
                    unsafe_allow_html=True)
        
        kf_cmp_cols = [
            "KF KFALP - Composite Score (1-5)",
            "KF viaEdge - Learning Agility Composite (1-5)"
        ]
        
        html_cmp = "<div style='display:flex;flex-direction:column;gap:8px'>"
        for col_clean in kf_cmp_cols:
            if col_clean in df_emp.columns:
                name = col_clean.replace("KF ","").replace(" (1-5)","").replace(" - Composite Score","")
                html_cmp += f"<div style='font-size:0.82rem;font-weight:600;color:#0B2540'>{name}</div>"
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
        st.plotly_chart(fig_ov, use_container_width=True, config={"displayModeBar":False},
                        key="overlay_radar_compare")

# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — ORG STRUCTURE
# ═════════════════════════════════════════════════════════════════════════════
with tab4:
    if "org" not in data:
        st.info("Upload **org_structure.csv** to visualize organizational structure.")
    else:
        df_org = data["org"].copy()
        df_org.columns = [c.replace("–","-").replace("—","-") for c in df_org.columns]

        st.markdown('<div class="sec-hdr">🏛️ Organizational Structure Network</div>', unsafe_allow_html=True)
        
        # Build network graph
        G = nx.DiGraph()
        grade_colors = {}
        node_size = {}
        node_color = []
        node_text = []
        node_x = []
        node_y = []
        edge_x = []
        edge_y = []
        node_hover = []

        for _, row in df_org.iterrows():
            emp_name = row.get("Employee Full Name", "Unknown")
            mgr_name = row.get("Manager Name", None)
            grade = int(row.get("Job Grade (1-9)", 5))
            
            G.add_node(emp_name, grade=grade, manager=mgr_name)
            if mgr_name and mgr_name != emp_name:
                G.add_edge(mgr_name, emp_name)

        # Layout
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

        # Node styling
        grade_color_map = {
            9: "#1B7A3E", 8: "#2563EB", 7: "#0D7377",
            6: "#D97706", 5: "#EA580C", 4: "#C9A227",
            3: "#7C3AED", 2: "#64748B", 1: "#94A3B8"
        }

        for node in G.nodes():
            grade = G.nodes[node].get("grade", 5)
            clr = grade_color_map.get(grade, "#888")
            grade_colors[grade] = clr
            
            node_color.append(clr)
            node_size[node] = max(300, min(2000, 300 + grade * 100))
            node_text.append(node.split()[-1][:6])
            node_x.append(pos[node][0])
            node_y.append(pos[node][1])

            emp_row = df_org[df_org["Employee Full Name"] == node]
            if len(emp_row) > 0:
                lps_val = emp_row.iloc[0].get("LPS", 0)
                is_cr = emp_row.iloc[0].get("Critical Role", False)
                _lps_str = f"LPS: {lps_val:.0f}" if lps_val == lps_val else "N/A"
                _cr_str  = "★ Critical Role" if is_cr else ""
                node_hover.append(f"<b>{node}</b><br>Grade: {grade}<br>{_lps_str}<br>{_cr_str}")
            else:
                node_hover.append(f"<b>{node}</b><br>Grade: {grade}")

        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.append(x0)
            edge_x.append(x1)
            edge_x.append(None)
            edge_y.append(y0)
            edge_y.append(y1)
            edge_y.append(None)

        fig_org = go.Figure()
        fig_org.add_trace(go.Scatter(
            x=edge_x, y=edge_y, mode="lines",
            line=dict(width=1.2, color="#CBD5E1"), hoverinfo="none"
        ))
        fig_org.add_trace(go.Scatter(
            x=node_x, y=node_y, mode="markers+text",
            marker=dict(size=[node_size.get(n, 500) / 50 for n in G.nodes()],
                        color=node_color,
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
        st.plotly_chart(fig_org, use_container_width=True, config={"displayModeBar": True},
                        key="org_network_graph")

        # Legend
        leg_cols = st.columns(len(grade_colors))
        for i, (g, c) in enumerate(sorted(grade_colors.items(), reverse=True)):
            with leg_cols[i]:
                st.markdown(f"<div style='display:flex;align-items:center;gap:4px;font-size:0.72rem'>"
                            f"<div style='width:12px;height:12px;border-radius:50%;background:{c}'></div>"
                            f"Grade {g}</div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — ORG READINESS
# ═════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="sec-hdr">🎯 Organizational Readiness Assessment</div>', unsafe_allow_html=True)
    
    roles = sorted(df_emp["Current Job Title"].unique())
    selected_role = st.selectbox("Select Role for Deep Dive", roles, key="readiness_role_sel")
    
    df_eligible = df_emp[df_emp["Current Job Title"] == selected_role]
    
    if len(df_eligible) == 0:
        st.info(f"No employees in role: {selected_role}")
    else:
        # Current incumbent
        inc_name = df_eligible.iloc[0]["Employee Full Name"]
        inc_ee = df_eligible.iloc[0]["EE Number"]
        inc_lps = df_eligible.iloc[0]["LPS"]
        inc_color = lps_color(inc_lps)

        st.markdown(f"""
        <div class="card" style="background:linear-gradient(135deg,{inc_color}15 0%,{inc_color}05 100%);
                      border-left:4px solid {inc_color}">
          <div style="display:flex;gap:12px;align-items:center">
            {avatar_html(inc_name, 48, inc_color)}
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
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar":False},
                        key=f"donut_readiness_{selected_role}")

        # Band distribution
        st.markdown('<div class="sec-hdr">Readiness Band Distribution</div>', unsafe_allow_html=True)
        band_dist = pool["LPS Band"].value_counts()
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
        st.plotly_chart(fig_bands, use_container_width=True, config={"displayModeBar":False},
                        key=f"bands_readiness_{selected_role}")

        # 9-box distribution
        st.markdown('<div class="sec-hdr">9-Box Distribution</div>', unsafe_allow_html=True)
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
        st.plotly_chart(fig_nb, use_container_width=True, config={"displayModeBar":False},
                        key=f"nineboy_readiness_{selected_role}")

        # ─────────────────────────────────────────────────────────────────────
        # GRAPHICAL 9-BOX MATRIX
        # ─────────────────────────────────────────────────────────────────────
        st.markdown('<div class="sec-hdr">🧩 Graphical 9-Box Talent Matrix</div>',
                    unsafe_allow_html=True)

        plot_df = df_eligible.copy()

        plot_df["Performance Axis"] = (
            plot_df["Average Performance Rating - Last 3 Years (1-5)"]
            .fillna(3)
            .clip(1, 5)
        )
        plot_df["Potential Axis"] = (
            plot_df["LPS"]
            .fillna(50)
            .clip(0, 100)
            / 20
        )

        fig_9box = px.scatter(
            plot_df,
            x="Performance Axis",
            y="Potential Axis",
            hover_name="Employee Full Name",
            hover_data={
                "Current Job Title": True,
                "LPS": ":.0f",
                "Performance Axis": False,
                "Potential Axis": False,
            },
            color="LPS Band",
            color_discrete_map=BAND_COLORS,
            size="Number of Direct Reports",
            size_max=30,
            title="9-Box: Performance vs. Potential",
        )

        fig_9box.add_vline(x=3, line_dash="dash", line_color="#CBD5E1", opacity=0.5)
        fig_9box.add_hline(y=2.5, line_dash="dash", line_color="#CBD5E1", opacity=0.5)

        fig_9box.update_xaxes(
            range=[0.5, 5.5],
            tickvals=[1, 2, 3, 4, 5],
            ticktext=["Low", "", "Medium", "", "High"],
            title="Performance Rating"
        )

        fig_9box.update_yaxes(
            range=[1, 5],
            title="Potential"
        )

        fig_9box.update_layout(
            xaxis=dict(range=[0.5, 5.5], title="Performance"),
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
            config={"displayModeBar":False},
            key=f"nineboxplot_readiness_{selected_role}"
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
                        title=f"{sel_dim} — Distribution"
                    )
                    fig_kf_dist.update_layout(
                        margin=dict(l=0,r=0,t=30,b=0), height=220,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        title_font=dict(family="Syne",size=12),
                        xaxis_title=None, yaxis_title=None,
                    )
                    st.plotly_chart(fig_kf_dist, use_container_width=True,
                                    config={"displayModeBar":False},
                                    key=f"kf_dist_{sel_dim}")

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
                                    config={"displayModeBar":False},
                                    key=f"kf_band_{sel_dim}")

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
                                    config={"displayModeBar":False},
                                    key="kf_heatmap")

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
                        xaxis_title=None, yaxis_title=None,
                    )
                    st.plotly_chart(fig_ve_dist, use_container_width=True,
                                    config={"displayModeBar":False},
                                    key=f"ve_dist_{sel_ve_dim}")

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
                                    config={"displayModeBar":False},
                                    key="ve_heatmap")

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
                      <div style="font-size:0.8rem;color:#64748B;margin:8px 0">{rd_sub.iloc[0].get('Description','')}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    for _, row in rd_sub.iterrows():
                        score = row.get("Score", "")
                        band_name = row.get("Band", "")
                        desc = row.get("Behavioral Indicators", "")
                        
                        kf_band_color_map = {
                            "Exceptional": "#065F46",
                            "Strong": "#1B7A3E",
                            "Effective": "#2563EB",
                            "Developing": "#D97706",
                            "Limited": "#B91C1C"
                        }
                        kf_band_c = kf_band_color_map.get(band_name, "#888")
                        
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
                                    use_container_width=True, config={"displayModeBar":False},
                                    key=f"speedometer_kfalp_{sel_cp}")
                if not pd.isna(k2v):
                    st.plotly_chart(speedometer_fig(k2v,"viaEdge Composite", color="#7C3AED"),
                                    use_container_width=True, config={"displayModeBar":False},
                                    key=f"speedometer_viaedge_{sel_cp}")

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
                    mode="lines+markers",
                    line=dict(color="#0D7377", width=3),
                    marker=dict(size=10, color="#C9A227", symbol="diamond"),
                    name="Grade Progression",
                ))

                # Career entry marker
                if len(emp_promos) > 0:
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
                    curr_year  = 2025
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
                    margin=dict(l=0,r=60,t=30,b=0),
                    height=350,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="white",
                )
                st.plotly_chart(fig_timeline, use_container_width=True, config={"displayModeBar":False},
                                key=f"timeline_{sel_cp}")
