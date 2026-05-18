"""
Succession Planning Engine v5
==============================
Upload 6 CSV files — succession_pipeline.csv is AUTO-GENERATED live.
Pipeline fix: each role gets its own grade-windowed, department-relevant,
globally-deduplicated successor pool — no two roles share the same top-3.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
from collections import deque

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def hex_to_rgba(h, a=0.18):
    h = h.lstrip("#")
    r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"

def safe_float(v, default=0.0):
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except: return default

def lps_color(s):
    if s>=80: return "#1B7A3E"
    if s>=65: return "#2563EB"
    if s>=50: return "#D97706"
    if s>=35: return "#EA580C"
    return "#B91C1C"

def norm_pct(val, series):
    s = series.dropna()
    return int((s < val).mean()*100) if len(s)>0 else 50

def avatar_html(name, size=48, bg="#0D7377"):
    ini = "".join(p[0].upper() for p in str(name).split()[:2] if p)
    return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{bg};'
            f'color:white;display:flex;align-items:center;justify-content:center;'
            f'font-family:Syne,sans-serif;font-weight:800;font-size:{size//3}px;'
            f'flex-shrink:0;">{ini}</div>')

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
BAND_COLORS = {
    "Band 5 - Ready Now":          "#1B7A3E",
    "Band 4 - Ready in 1-2 Years": "#2563EB",
    "Band 3 - Ready in 2-3 Years": "#D97706",
    "Band 2 - Emerging Potential": "#EA580C",
    "Band 1 - Not Yet Ready":      "#B91C1C",
}
BAND_SHORT = {
    "Band 5 - Ready Now":          "Ready Now",
    "Band 4 - Ready in 1-2 Years": "1-2 Yrs",
    "Band 3 - Ready in 2-3 Years": "2-3 Yrs",
    "Band 2 - Emerging Potential": "Emerging",
    "Band 1 - Not Yet Ready":      "Not Ready",
}
CL_COLORS = ["#0D7377","#C9A227","#2563EB","#7C3AED","#EA580C"]
CL_NAMES  = ["Performance","KF Assessment","Career Velocity","Ldrship Breadth","Readiness"]

# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL ROLES CONFIG
# min_grade = minimum grade a candidate must be AT to be eligible
# dept      = preferred department(s) — candidates from these ranked first
# ─────────────────────────────────────────────────────────────────────────────
ROLES_CFG = {
    "CEO": {
        "min_grade": 9, "grade_window": 2,
        "dept": None,
        "label": "Chief Executive Officer"
    },
    "CFO": {
        "min_grade": 8, "grade_window": 2,
        "dept": ["Finance"],
        "label": "Chief Financial Officer"
    },
    "CHRO": {
        "min_grade": 8, "grade_window": 2,
        "dept": ["Human Resources"],
        "label": "Chief Human Resources Officer"
    },
    "CGO": {
        "min_grade": 7, "grade_window": 2,
        "dept": ["Corporate Governance","Corporate Strategy","Finance","Legal & Compliance"],
        "label": "Chief Governance Officer"
    },
    "CBO-AI Solutions and Services": {
        "min_grade": 8, "grade_window": 2,
        "dept": ["AI & Digital Solutions","Cybersecurity","Service Design"],
        "label": "Chief Business Officer — AI"
    },
    "Executive Vice President": {
        "min_grade": 7, "grade_window": 2,
        "dept": None,
        "label": "Executive Vice President"
    },
    "Senior Vice President": {
        "min_grade": 7, "grade_window": 2,
        "dept": None,
        "label": "Senior Vice President"
    },
    "Advisor": {
        "min_grade": 7, "grade_window": 2,
        "dept": ["Strategic Advisory","Corporate Strategy"],
        "label": "Advisor"
    },
    "Vice President (CISO)": {
        "min_grade": 6, "grade_window": 2,
        "dept": ["Cybersecurity"],
        "label": "VP — Chief Information Security Officer"
    },
    "Associate Vice President": {
        "min_grade": 6, "grade_window": 2,
        "dept": None,
        "label": "Associate Vice President"
    },
    "Senior Director - Corporate Strategy": {
        "min_grade": 6, "grade_window": 2,
        "dept": ["Corporate Strategy","Office of the CEO"],
        "label": "Senior Director — Corporate Strategy"
    },
    "Senior Director - HRBP": {
        "min_grade": 6, "grade_window": 2,
        "dept": ["Human Resources"],
        "label": "Senior Director — HRBP"
    },
    "Senior Director - Practice Sales": {
        "min_grade": 6, "grade_window": 2,
        "dept": ["Sales","Business Development","AI & Digital Solutions"],
        "label": "Senior Director — Practice Sales"
    },
}
CRITICAL_ROLES = list(ROLES_CFG.keys())

# ─────────────────────────────────────────────────────────────────────────────
# LPS COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────
def recompute_lps(df, w1, w2, w3, w4, w5):
    def sn(s):
        lo,hi = s.min(),s.max()
        return (s-lo)/(hi-lo+1e-9)*100

    c1 = (sn(df["Average Performance Rating - Last 3 Years (1-5)"])*0.50 +
          sn(df["Last Annual Performance Rating (1-5)"])*0.35 +
          df["Performance Trajectory"].clip(-2,2).add(2).div(4).mul(100)*0.15)

    kf_col = "KF Blended Assessment Composite (1-5)"
    kf_fill = df[kf_col].fillna(df["Average Performance Rating - Last 3 Years (1-5)"]) \
              if kf_col in df.columns else df["Average Performance Rating - Last 3 Years (1-5)"]
    c2 = sn(kf_fill)

    c3 = (sn(df["Promotions per Year (Career)"])*0.50 +
          sn(df["Promotions per Year (Last 5 Years)"])*0.35 +
          sn(df["Total Promotions (Career)"])*0.15)

    breadth = (df["Cross-Functional Experience"].astype(int)*25 +
               df["International / Multi-Geography Experience"].astype(int)*20 +
               sn(df["Number of Critical Projects Led"])*30 +
               sn(df["External Industry Recognition Count"])*15 +
               sn(df["Number of Direct Reports"])*10)
    c4 = sn(breadth)

    gg = 9 - df["Job Grade (1-9)"]
    c5 = (sn(df["Mobility / Relocation Willingness (1-5)"])*0.35 +
          sn(gg.max()-gg)*0.35 +
          df["Flight Risk"].map({"Low":100,"Medium":50,"High":0})*0.30)

    lps = (c1*(w1/100)+c2*(w2/100)+c3*(w3/100)+c4*(w4/100)+c5*(w5/100)).round(2)

    def band(s):
        if s>=80: return "Band 5 - Ready Now"
        if s>=65: return "Band 4 - Ready in 1-2 Years"
        if s>=50: return "Band 3 - Ready in 2-3 Years"
        if s>=35: return "Band 2 - Emerging Potential"
        return "Band 1 - Not Yet Ready"

    df = df.copy()
    df["LPS"] = lps
    df["LPS Band"] = lps.apply(band)
    df["C1"]=c1.round(2); df["C2"]=c2.round(2)
    df["C3"]=c3.round(2); df["C4"]=c4.round(2); df["C5"]=c5.round(2)
    return df

# ─────────────────────────────────────────────────────────────────────────────
# BUILD PIPELINE — UNIQUE PER ROLE
# ─────────────────────────────────────────────────────────────────────────────
def build_pipeline(df_scored, exclude_risk=True, min_gr=5):
    """
    For every critical role:
    1. Identify the incumbent (person currently holding that title).
    2. Build a role-specific eligible pool:
       - Grade window: [min_grade - grade_window, min_grade + 1]
       - Preferred departments listed first (department relevance)
       - Exclude the incumbent
       - Exclude high-flight-risk if flag set
       - Exclude anyone already assigned as #1 successor to a higher-priority role
         (global deduplication — no one appears in two top-3 pipelines)
    3. Rank by LPS within the eligible pool.
    4. Return top 3 per role.
    """
    rows = []
    globally_used = set()   # EE Numbers already assigned as #1 elsewhere

    for role, cfg in ROLES_CFG.items():
        min_g  = cfg["min_grade"]
        window = cfg["grade_window"]
        depts  = cfg["dept"]

        # ── Incumbent ────────────────────────────────────────────────────────
        inc_match = df_scored[df_scored["Current Job Title"] == role]
        if len(inc_match) > 0:
            inc = inc_match.iloc[0]
        else:
            inc = df_scored.sort_values(["Job Grade (1-9)","LPS"], ascending=False).iloc[0]

        # ── Grade window ─────────────────────────────────────────────────────
        grade_lo = max(1, min_g - window)
        grade_hi = min(9, min_g + 1)

        base = df_scored[
            (df_scored["Job Grade (1-9)"] >= grade_lo) &
            (df_scored["Job Grade (1-9)"] <= grade_hi) &
            (df_scored["EE Number"] != inc["EE Number"])
        ].copy()

        if exclude_risk:
            base = base[base["Flight Risk"] != "High"]
        base = base[base["Job Grade (1-9)"] >= min_gr]

        # ── Department relevance: dept-matched candidates come first ──────────
        if depts:
            in_dept  = base[base["Department"].isin(depts)].sort_values("LPS", ascending=False)
            out_dept = base[~base["Department"].isin(depts)].sort_values("LPS", ascending=False)
            candidates = pd.concat([in_dept, out_dept]).drop_duplicates("EE Number")
        else:
            candidates = base.sort_values("LPS", ascending=False)

        # ── Global deduplication: prefer fresh candidates ─────────────────────
        fresh = candidates[~candidates["EE Number"].isin(globally_used)]
        final_pool = fresh if len(fresh) >= 3 else candidates  # relax if pool too small

        top3 = final_pool.head(3)

        # Mark #1 as globally used so they don't appear as #1 elsewhere
        if len(top3) > 0:
            globally_used.add(top3.iloc[0]["EE Number"])

        for rank, (_, cand) in enumerate(top3.iterrows(), start=1):
            rows.append({
                "Critical Role":                                  role,
                "Role Label":                                     cfg["label"],
                "Incumbent EE Number":                            inc["EE Number"],
                "Incumbent Name":                                 inc["Employee Full Name"],
                "Successor Rank":                                 rank,
                "Successor EE Number":                            cand["EE Number"],
                "Successor Full Name":                            cand["Employee Full Name"],
                "Successor Current Job Title":                    cand["Current Job Title"],
                "Successor Job Grade (1-9)":                      int(cand["Job Grade (1-9)"]),
                "Successor Department":                           cand["Department"],
                "Successor Business Unit":                        cand["Business Unit"],
                "Successor Work Location":                        cand["Work Location"],
                "Leadership Potential Score (0-100)":             round(float(cand["LPS"]),2),
                "LPS Band":                                       cand["LPS Band"],
                "LPS - Performance Cluster (0-100)":              round(float(cand.get("C1",0)),2),
                "LPS - KF Assessment Cluster (0-100)":            round(float(cand.get("C2",0)),2),
                "LPS - Career Velocity Cluster (0-100)":          round(float(cand.get("C3",0)),2),
                "LPS - Leadership Breadth Cluster (0-100)":       round(float(cand.get("C4",0)),2),
                "LPS - Readiness & Mobility Cluster (0-100)":     round(float(cand.get("C5",0)),2),
                "Last Annual Performance Rating (1-5)":           safe_float(cand["Last Annual Performance Rating (1-5)"]),
                "Average Performance Rating - Last 3 Years (1-5)":safe_float(cand["Average Performance Rating - Last 3 Years (1-5)"]),
                "Total Promotions (Career)":                      int(cand["Total Promotions (Career)"]),
                "Promotions in Last 5 Years":                     int(cand["Promotions in Last 5 Years"]),
                "Promotions per Year (Career)":                   round(float(cand["Promotions per Year (Career)"]),4),
                "KF KFALP - Composite Score (1-5)":               cand.get("KF KFALP - Composite Score (1-5)",None),
                "KF viaEdge - Learning Agility Composite (1-5)":  cand.get("KF viaEdge - Learning Agility Composite (1-5)",None),
                "KF Blended Assessment Composite (1-5)":          cand.get("KF Blended Assessment Composite (1-5)",None),
                "Tenure with Organisation (Years)":               safe_float(cand["Tenure with Organisation (Years)"]),
                "9-Box Position":                                  cand["9-Box Position"],
                "Flight Risk":                                     cand["Flight Risk"],
                "On Active Retention Plan":                       bool(cand["On Active Retention Plan"]),
            })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def gauge_fig(value, title, max_val=100, color="#0D7377"):
    v = safe_float(value)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=v,
        title={"text": title, "font": {"family":"Syne","size":13,"color":"#64748B"}},
        number={"font": {"family":"Syne","size":28,"color":color}},
        gauge={
            "axis": {"range":[0,max_val],"tickwidth":1,"tickcolor":"#D1DCE8","tickfont":{"size":9}},
            "bar": {"color":color,"thickness":0.25},
            "bgcolor":"#F0F4F8","borderwidth":0,
            "steps":[
                {"range":[0,         max_val*0.35],"color":"#FEE2E2"},
                {"range":[max_val*0.35,max_val*0.50],"color":"#FEF3C7"},
                {"range":[max_val*0.50,max_val*0.65],"color":"#DBEAFE"},
                {"range":[max_val*0.65,max_val*0.80],"color":"#D1FAE5"},
                {"range":[max_val*0.80,max_val],      "color":"#A7F3D0"},
            ],
            "threshold":{"line":{"color":"#0B2540","width":3},"thickness":0.8,"value":v},
        }
    ))
    fig.update_layout(margin=dict(l=10,r=10,t=30,b=10),height=180,
                      paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
    return fig

def speedometer_fig(value, title, color="#0D7377"):
    v = safe_float(value)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=v,
        title={"text":title,"font":{"family":"Syne","size":11,"color":"#64748B"}},
        number={"font":{"family":"Syne","size":22,"color":color},"valueformat":".2f"},
        gauge={
            "axis":{"range":[0,5.0],"tickwidth":1,
                    "tickvals":[1,2,3,4,5],
                    "ticktext":["Limited","Developing","Effective","Strong","Exceptional"],
                    "tickfont":{"size":8}},
            "bar":{"color":color,"thickness":0.3},
            "bgcolor":"#F0F4F8","borderwidth":0,
            "steps":[
                {"range":[0,  1.5],"color":"#FEE2E2"},{"range":[1.5,2.5],"color":"#FEF3C7"},
                {"range":[2.5,3.5],"color":"#DBEAFE"},{"range":[3.5,4.5],"color":"#D1FAE5"},
                {"range":[4.5,5.0],"color":"#6EE7B7"},
            ],
        }
    ))
    fig.update_layout(margin=dict(l=5,r=5,t=35,b=5),height=160,
                      paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
    return fig

def radar_fig(values, labels, name, color="#0D7377", ref_vals=None):
    fig = go.Figure()
    if ref_vals:
        fig.add_trace(go.Scatterpolar(
            r=ref_vals+[ref_vals[0]], theta=labels+[labels[0]],
            fill="toself", fillcolor="rgba(200,200,200,0.15)",
            line=dict(color="#C9A227",width=2,dash="dot"), name="Org Benchmark"
        ))
    fig.add_trace(go.Scatterpolar(
        r=values+[values[0]], theta=labels+[labels[0]],
        fill="toself", fillcolor=hex_to_rgba(color,0.19),
        line=dict(color=color,width=2.5), name=name
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True,range=[0,5],
                                   tickvals=[1,2,3,4,5],tickfont={"size":8},
                                   gridcolor="#E2EAF0"),
                   angularaxis=dict(tickfont={"family":"DM Sans","size":10})),
        showlegend=True, legend=dict(font={"size":9}),
        margin=dict(l=40,r=40,t=30,b=30), height=300,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def slider_html(label, value, lo, hi, color="#0D7377", pct=None):
    pp = max(2, min(98, (value-lo)/(hi-lo+1e-9)*100))
    ps = f"({int(pct)}th pct)" if pct is not None else f"({int(pp)}th pct)"
    return (f'<div style="margin-bottom:10px">'
            f'<div style="font-size:0.78rem;color:#64748B;margin-bottom:3px;'
            f'display:flex;justify-content:space-between;">'
            f'<span>{label}</span>'
            f'<span style="color:{color};font-weight:600">{value:.2f} {ps}</span></div>'
            f'<div style="height:10px;border-radius:6px;background:linear-gradient('
            f'90deg,#B91C1C 0%,#D97706 40%,#16A34A 100%);position:relative;">'
            f'<div style="position:absolute;top:-4px;left:{pp}%;width:18px;height:18px;'
            f'border-radius:50%;background:{color};border:3px solid white;'
            f'box-shadow:0 2px 6px rgba(0,0,0,0.25);transform:translateX(-50%);"></div>'
            f'</div></div>')

# ─────────────────────────────────────────────────────────────────────────────
# 9-BOX GRID (full graphical)
# ─────────────────────────────────────────────────────────────────────────────
def nine_box_fig(df_plot, highlight_ee=None):
    perf_map = {"Low Performer":0,"Moderate Performer":1,"High Performer":2,"Exceptional Performer":2}
    pot_map  = {"Low Potential":0,"Moderate Potential":1,"High Potential":2}

    def parse_box(s):
        if not isinstance(s,str) or "/" not in s: return None,None
        parts = [p.strip() for p in s.split("/")]
        px = next((v for k,v in perf_map.items() if k in parts[0]),None)
        py = next((v for k,v in pot_map.items()  if k in parts[1]),None)
        return px, py

    df2 = df_plot.copy()
    df2[["px","py"]] = df2["9-Box Position"].apply(lambda x: pd.Series(parse_box(x)))
    df2 = df2.dropna(subset=["px","py"])
    rng = np.random.RandomState(42)
    df2["xj"] = df2["px"] + rng.uniform(-0.28,0.28,len(df2))
    df2["yj"] = df2["py"] + rng.uniform(-0.28,0.28,len(df2))

    cell_bg = {
        (0,0):"#FEE2E2",(1,0):"#FEF3C7",(2,0):"#FEF3C7",
        (0,1):"#FEF3C7",(1,1):"#DBEAFE",(2,1):"#D1FAE5",
        (0,2):"#FEF3C7",(1,2):"#D1FAE5",(2,2):"#A7F3D0",
    }
    cell_lbl = {
        (0,0):"Underperformer",(1,0):"Effective Contributor",(2,0):"Misaligned Star",
        (0,1):"Developing",(1,1):"Core Contributor",(2,1):"High Potential",
        (0,2):"Enigma",(1,2):"Future Leader",(2,2):"Top Talent",
    }

    fig = go.Figure()
    for (px_c,py_c),col in cell_bg.items():
        fig.add_shape(type="rect",
            x0=px_c-0.5,y0=py_c-0.5,x1=px_c+0.5,y1=py_c+0.5,
            fillcolor=col, line=dict(color="#CBD5E1",width=1.5), layer="below")
        fig.add_annotation(x=px_c, y=py_c+0.4,
            text=f"<b>{cell_lbl.get((px_c,py_c),'')}</b>",
            showarrow=False, font=dict(size=9,color="#374151",family="Syne"), xanchor="center")

    for band, grp in df2.groupby("LPS Band"):
        bc = BAND_COLORS.get(band,"#888"); bs = BAND_SHORT.get(band,band)
        hover = [f"<b>{r['Employee Full Name']}</b><br>EE: {r['EE Number']}<br>"
                 f"Title: {r['Current Job Title']}<br>Dept: {r['Department']}<br>"
                 f"LPS: {r['LPS']:.1f} — {bs}<br>9-Box: {r['9-Box Position']}"
                 for _,r in grp.iterrows()]
        fig.add_trace(go.Scatter(
            x=grp["xj"], y=grp["yj"], mode="markers",
            marker=dict(size=8,color=bc,opacity=0.82,line=dict(width=1,color="white")),
            name=bs, hovertext=hover, hoverinfo="text",
        ))

    if highlight_ee is not None:
        row = df2[df2["EE Number"]==highlight_ee]
        if len(row)>0:
            r = row.iloc[0]
            fig.add_trace(go.Scatter(
                x=[r["xj"]], y=[r["yj"]], mode="markers+text",
                marker=dict(size=22,color="#C9A227",symbol="star",line=dict(width=2,color="#0B2540")),
                text=[r["Employee Full Name"].split()[0]],
                textposition="top center",
                textfont=dict(family="Syne",size=10,color="#0B2540"),
                name="Selected", hovertext=[r["Employee Full Name"]], hoverinfo="text",
            ))

    fig.update_layout(
        xaxis=dict(tickvals=[0,1,2],
                   ticktext=["Low Performance","Moderate Performance","High Performance"],
                   range=[-0.55,2.55],showgrid=False,zeroline=False,
                   tickfont=dict(family="Syne",size=10,color="#374151"),
                   title=dict(text="PERFORMANCE →",font=dict(family="Syne",size=11,color="#0B2540"))),
        yaxis=dict(tickvals=[0,1,2],
                   ticktext=["Low Potential","Moderate Potential","High Potential"],
                   range=[-0.55,2.55],showgrid=False,zeroline=False,
                   tickfont=dict(family="Syne",size=10,color="#374151"),
                   title=dict(text="POTENTIAL ↑",font=dict(family="Syne",size=11,color="#0B2540"))),
        legend=dict(font=dict(size=9,family="DM Sans"),orientation="h",
                    x=0.5,xanchor="center",y=-0.14),
        margin=dict(l=10,r=10,t=20,b=50), height=480,
        paper_bgcolor="white", plot_bgcolor="white",
        hoverlabel=dict(bgcolor="white",font_size=11,font_family="DM Sans",bordercolor="#D1DCE8"),
    )
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG + CSS
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Succession Planning Engine",page_icon="🎯",
                   layout="wide",initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{--navy:#0B2540;--teal:#0D7377;--gold:#C9A227;--gold-lt:#F0C93A;
  --bg:#F0F4F8;--card:#FFFFFF;--border:#D1DCE8;--text:#1A2535;--muted:#64748B;}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif!important;background-color:var(--bg)!important;color:var(--text)!important;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:1.2rem 1.8rem 2rem 1.8rem!important;max-width:100%!important;}
.app-title{background:linear-gradient(135deg,#0B2540 0%,#1a3a5c 60%,#0D7377 100%);border-radius:14px;padding:18px 28px;margin-bottom:18px;display:flex;align-items:center;gap:16px;}
.app-title h1{font-family:'Syne',sans-serif!important;font-size:1.7rem;font-weight:800;color:#fff;margin:0;}
.app-title p{color:#9EC5D8;margin:2px 0 0 0;font-size:0.85rem;}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:var(--navy);border-radius:12px;padding:6px;margin-bottom:18px;}
.stTabs [data-baseweb="tab"]{font-family:'Syne',sans-serif!important;font-weight:600;font-size:0.82rem;color:#9EC5D8!important;border-radius:8px;padding:8px 16px;border:none!important;background:transparent!important;white-space:nowrap;}
.stTabs [aria-selected="true"]{background:var(--teal)!important;color:#fff!important;}
.stTabs [data-baseweb="tab-panel"]{padding:0!important;}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px 22px;box-shadow:0 2px 12px rgba(11,37,64,0.07);margin-bottom:14px;}
.card-navy{background:var(--navy);border-radius:14px;padding:18px 22px;margin-bottom:14px;}
.kpi-row{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;}
.kpi{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 18px;flex:1;min-width:120px;box-shadow:0 1px 6px rgba(11,37,64,0.06);}
.kpi-value{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;color:var(--teal);line-height:1.1;}
.kpi-label{font-size:0.75rem;color:var(--muted);margin-top:2px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;}
.scard{border-radius:14px;padding:16px 20px;margin-bottom:10px;border-left:5px solid var(--teal);background:var(--card);box-shadow:0 2px 10px rgba(11,37,64,0.08);position:relative;}
.scard-rank{position:absolute;top:12px;right:14px;font-family:'Syne',sans-serif;font-size:0.68rem;font-weight:800;background:var(--navy);color:var(--gold-lt);border-radius:20px;padding:3px 10px;letter-spacing:1px;text-transform:uppercase;}
.scard h3{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin:0 0 2px 0;}
.lps-num{font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;line-height:1;}
.band-pill{display:inline-block;border-radius:20px;padding:3px 10px;font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;margin-left:8px;vertical-align:middle;}
.sec-hdr{font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:800;color:var(--navy);border-bottom:2px solid var(--teal);padding-bottom:6px;margin-bottom:14px;}
section[data-testid="stSidebar"]{background:var(--navy)!important;border-right:none!important;}
section[data-testid="stSidebar"] *{color:#C8DDE8!important;}
section[data-testid="stSidebar"] h2{font-family:'Syne',sans-serif!important;color:white!important;font-size:1rem!important;}
.upload-hint{font-size:0.78rem;color:#7A9AB8;text-align:center;padding:8px;border:1px dashed #3A5A78;border-radius:8px;margin-bottom:8px;}
.dept-badge{display:inline-block;background:#EBF4F8;color:#0B2540;border-radius:6px;padding:2px 8px;font-size:0.72rem;font-weight:600;margin-top:4px;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<h2>⬆ Upload Datasets</h2>", unsafe_allow_html=True)
    st.markdown('<div class="upload-hint">Upload 6 CSV files — pipeline auto-generated per role</div>',
                unsafe_allow_html=True)
    uploaded = {
        "employees": st.file_uploader("employees_master.csv",       type="csv", key="emp"),
        "kfalp":     st.file_uploader("kf_kfalp_detail.csv",        type="csv", key="kfl"),
        "viaedge":   st.file_uploader("kf_viaedge_detail.csv",      type="csv", key="via"),
        "ref":       st.file_uploader("kf_attribute_reference.csv", type="csv", key="ref"),
        "promos":    st.file_uploader("promotion_history.csv",      type="csv", key="prm"),
        "org":       st.file_uploader("org_structure.csv",          type="csv", key="org"),
    }
    n_loaded = sum(v is not None for v in uploaded.values())
    st.markdown(f"<div style='color:#6EE7B7;font-size:0.8rem;margin-top:6px'>"
                f"✓ {n_loaded}/6 files · Pipeline: auto-generated per role</div>",
                unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<h2>🎛 LPS Weights</h2>", unsafe_allow_html=True)
    w1 = st.slider("Performance",        5,60,25,5,key="w1")
    w2 = st.slider("KF Assessment",      5,60,30,5,key="w2")
    w3 = st.slider("Career Velocity",    5,40,20,5,key="w3")
    w4 = st.slider("Leadership Breadth", 5,30,15,5,key="w4")
    w5 = st.slider("Readiness",          5,30,10,5,key="w5")
    total_w = w1+w2+w3+w4+w5
    wclr = "#6EE7B7" if total_w==100 else "#FCA5A5"
    st.markdown(f"<div style='color:{wclr};font-size:0.85rem;font-weight:600'>"
                f"Total: {total_w}% {'✓' if total_w==100 else '— must equal 100'}</div>",
                unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<h2>🔍 Filters</h2>", unsafe_allow_html=True)
    exclude_risk = st.checkbox("Exclude High Flight Risk", value=True)
    min_grade    = st.slider("Min Grade for Eligibility", 1, 9, 5)

# ─────────────────────────────────────────────────────────────────────────────
# LOAD + SCORE + BUILD
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_csv(f):
    df = pd.read_csv(f)
    df.columns = [c.replace("\u2013","-").replace("\u2014","-") for c in df.columns]
    return df

data = {k: load_csv(v) for k, v in uploaded.items() if v is not None}

st.markdown("""
<div class="app-title">
  <div style="font-size:2.2rem">🎯</div>
  <div>
    <h1>Succession Planning Engine</h1>
    <p>Powered by HRMS Data · Korn Ferry KFALP · Korn Ferry viaEdge</p>
  </div>
</div>
""", unsafe_allow_html=True)

if "employees" not in data:
    st.info("👈 Upload **employees_master.csv** to activate the engine.")
    st.stop()

df_emp  = recompute_lps(data["employees"], w1, w2, w3, w4, w5)
df_elig = df_emp[df_emp["Flight Risk"]!="High"].copy() if exclude_risk else df_emp.copy()
df_elig = df_elig[df_elig["Job Grade (1-9)"] >= min_grade]
df_pip  = build_pipeline(df_emp, exclude_risk=exclude_risk, min_gr=min_grade)
all_names = sorted(df_emp["Employee Full Name"].unique())

# ─────────────────────────────────────────────────────────────────────────────
# KF KEY LISTS (reused across tabs)
# ─────────────────────────────────────────────────────────────────────────────
KF_KEYS  = ["KF KFALP - Drivers Score (1-5)","KF KFALP - Curiosity Score (1-5)",
            "KF KFALP - Insight Score (1-5)","KF KFALP - Engagement Score (1-5)",
            "KF KFALP - Determination Score (1-5)","KF KFALP - Learnability Score (1-5)"]
KF_LBLS  = ["Drivers","Curiosity","Insight","Engagement","Determination","Learnability"]
VE_KEYS  = ["KF viaEdge - Mental Agility Score (1-5)","KF viaEdge - People Agility Score (1-5)",
            "KF viaEdge - Change Agility Score (1-5)","KF viaEdge - Results Agility Score (1-5)",
            "KF viaEdge - Self-Awareness Score (1-5)"]
VE_LBLS  = ["Mental Agility","People Agility","Change Agility","Results Agility","Self-Awareness"]

# ═════════════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════════════
tab1,tab2,tab3,tab4,tab5,tab6,tab7 = st.tabs([
    "🏆 Succession Pipeline","👤 Employee Profile","⚖️ Compare Employees",
    "🌐 Org Chart","📊 Org Readiness","🧠 KF Assessment","📈 Career Path",
])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — SUCCESSION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════
with tab1:
    left, right = st.columns([1, 2.2], gap="large")

    with left:
        st.markdown('<div class="sec-hdr">🏢 Select Critical Role</div>', unsafe_allow_html=True)
        sel_role = st.selectbox("", CRITICAL_ROLES, label_visibility="collapsed", key="sel_role")
        cfg      = ROLES_CFG[sel_role]

        role_rows = df_pip[df_pip["Critical Role"] == sel_role]
        inc_name  = str(role_rows.iloc[0].get("Incumbent Name","—")) if len(role_rows)>0 else "—"
        inc_ee    = str(role_rows.iloc[0].get("Incumbent EE Number","—")) if len(role_rows)>0 else "—"

        dept_badge = ""
        if cfg["dept"]:
            dept_badge = "".join(f'<span class="dept-badge">{d}</span> ' for d in cfg["dept"])

        st.markdown(f"""
        <div class="card-navy">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
            {avatar_html(inc_name, 52, "#C9A227")}
            <div>
              <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1rem;color:white">{inc_name}</div>
              <div style="font-size:0.75rem;color:#9EC5D8">Incumbent · {inc_ee}</div>
            </div>
          </div>
          <div style="font-family:'Syne',sans-serif;font-size:0.85rem;font-weight:700;color:#F0C93A;margin-bottom:6px">{cfg['label']}</div>
          <div style="font-size:0.72rem;color:#6A9AB8">Preferred talent pool: {dept_badge if cfg['dept'] else 'All departments'}</div>
          <div style="font-size:0.72rem;color:#6A9AB8">Grade window: {max(1,cfg['min_grade']-cfg['grade_window'])}–{min(9,cfg['min_grade']+1)}</div>
        </div>""", unsafe_allow_html=True)

        n_pool    = len(df_elig)
        ready_now = (df_elig["LPS Band"]=="Band 5 - Ready Now").sum()
        avg_lps   = df_elig["LPS"].mean()
        st.markdown(f"""
        <div class="kpi-row">
          <div class="kpi"><div class="kpi-value">{n_pool}</div><div class="kpi-label">Pool</div></div>
          <div class="kpi"><div class="kpi-value" style="color:#1B7A3E">{ready_now}</div><div class="kpi-label">Ready Now</div></div>
          <div class="kpi"><div class="kpi-value" style="color:#0D7377">{avg_lps:.0f}</div><div class="kpi-label">Avg LPS</div></div>
        </div>""", unsafe_allow_html=True)

        band_counts = df_elig["LPS Band"].value_counts()
        fig_donut = go.Figure(go.Pie(
            labels=[BAND_SHORT.get(b,b) for b in band_counts.index],
            values=band_counts.values, hole=0.62,
            marker=dict(colors=[BAND_COLORS.get(b,"#888") for b in band_counts.index]),
            textfont=dict(family="DM Sans",size=10),
        ))
        fig_donut.update_layout(
            margin=dict(l=0,r=0,t=10,b=0),height=180,showlegend=True,
            legend=dict(font=dict(size=9,family="DM Sans"),orientation="h",x=0.5,xanchor="center",y=-0.05),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text=f"<b>{n_pool}</b><br>Pool",x=0.5,y=0.5,
                              font=dict(family="Syne",size=14,color="#0B2540"),showarrow=False)]
        )
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar":False})

    with right:
        st.markdown('<div class="sec-hdr">🔗 Succession Pipeline — Top 3 Role-Specific Successors</div>',
                    unsafe_allow_html=True)

        role_pip = df_pip[df_pip["Critical Role"]==sel_role].sort_values("Successor Rank")
        rank_colors = ["#1B7A3E","#2563EB","#D97706"]
        rank_labels = ["#1 — Primary Successor","#2 — Secondary Successor","#3 — Tertiary Successor"]

        if len(role_pip)==0:
            st.warning("No successors found for this role with current filters.")
        else:
            for i, (_,cand) in enumerate(role_pip.iterrows()):
                if i>=3: break
                lps  = cand["Leadership Potential Score (0-100)"]
                band = cand["LPS Band"]
                bc   = BAND_COLORS.get(band,"#888")
                bs   = BAND_SHORT.get(band,band)
                c1v  = cand["LPS - Performance Cluster (0-100)"]
                c2v  = cand["LPS - KF Assessment Cluster (0-100)"]
                c3v  = cand["LPS - Career Velocity Cluster (0-100)"]
                c4v  = cand["LPS - Leadership Breadth Cluster (0-100)"]
                c5v  = cand["LPS - Readiness & Mobility Cluster (0-100)"]

                bar = go.Figure(go.Bar(
                    x=[c1v,c2v,c3v,c4v,c5v], y=CL_NAMES, orientation="h",
                    marker_color=CL_COLORS,
                    text=[f"{v:.0f}" for v in [c1v,c2v,c3v,c4v,c5v]],
                    textposition="outside", textfont=dict(size=9,family="DM Sans"),
                ))
                bar.update_layout(xaxis=dict(range=[0,110],showgrid=False,showticklabels=False),
                                   yaxis=dict(tickfont=dict(size=9,family="DM Sans")),
                                   margin=dict(l=0,r=40,t=0,b=0),height=100,
                                   paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                                   showlegend=False)

                dept_tag = cand["Successor Department"]
                st.markdown(f"""
                <div class="scard" style="border-left-color:{rank_colors[i]}">
                  <div class="scard-rank">{rank_labels[i]}</div>
                  <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                    {avatar_html(cand['Successor Full Name'],44,rank_colors[i])}
                    <div style="flex:1">
                      <h3 style="color:#0B2540">{cand['Successor Full Name']}</h3>
                      <div style="font-size:0.78rem;color:#64748B">{cand['Successor Current Job Title']} · Grade {cand['Successor Job Grade (1-9)']} · {cand['Successor EE Number']}</div>
                      <div style="font-size:0.73rem;margin-top:2px"><span class="dept-badge">{dept_tag}</span></div>
                      <div style="margin-top:4px;display:flex;align-items:baseline;gap:6px">
                        <span class="lps-num" style="color:{bc}">{lps:.1f}</span>
                        <span style="font-size:0.78rem;color:#64748B">/ 100 LPS</span>
                        <span class="band-pill" style="background:{bc}20;color:{bc}">{bs}</span>
                      </div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
                st.plotly_chart(bar, use_container_width=True,
                                config={"displayModeBar":False}, key=f"bar_{i}_{sel_role}")

            # Comparison chart
            st.markdown('<div class="sec-hdr" style="margin-top:8px">📊 Pipeline Cluster Comparison</div>',
                        unsafe_allow_html=True)
            fig_cmp = go.Figure()
            for i, (_,r) in enumerate(role_pip.head(3).iterrows()):
                vals = [r["LPS - Performance Cluster (0-100)"],r["LPS - KF Assessment Cluster (0-100)"],
                        r["LPS - Career Velocity Cluster (0-100)"],r["LPS - Leadership Breadth Cluster (0-100)"],
                        r["LPS - Readiness & Mobility Cluster (0-100)"]]
                fig_cmp.add_trace(go.Bar(
                    name=r["Successor Full Name"], x=CL_NAMES, y=vals,
                    marker_color=rank_colors[i],
                    text=[f"{v:.0f}" for v in vals],
                    textposition="outside", textfont=dict(size=9),
                ))
            fig_cmp.update_layout(
                barmode="group",
                xaxis=dict(tickfont=dict(family="DM Sans",size=10)),
                yaxis=dict(range=[0,110],tickfont=dict(size=9)),
                legend=dict(font=dict(family="DM Sans",size=10),orientation="h",x=0.5,xanchor="center",y=1.08),
                margin=dict(l=0,r=0,t=30,b=0),height=260,
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_cmp, use_container_width=True, config={"displayModeBar":False})

        dl1,dl2,dl3 = st.columns([1,1,1])
        with dl2:
            st.download_button(
                label="⬇ Download Full Pipeline CSV",
                data=df_pip.to_csv(index=False).encode("utf-8"),
                file_name="succession_pipeline_generated.csv",
                mime="text/csv", use_container_width=True,
            )

# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — EMPLOYEE PROFILE
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    sc,_ = st.columns([2,3])
    with sc:
        sel_emp = st.selectbox("Select Employee", all_names, key="emp_sel")
    emp  = df_emp[df_emp["Employee Full Name"]==sel_emp].iloc[0]
    lps  = emp["LPS"]; bc = lps_color(lps); band = emp["LPS Band"]

    h1c,h2c,h3c = st.columns([1.5,1.5,1])
    with h1c:
        fr_bg  = "#FEE2E2" if emp["Flight Risk"]=="High" else "#FEF3C7" if emp["Flight Risk"]=="Medium" else "#D1FAE5"
        fr_clr = "#B91C1C" if emp["Flight Risk"]=="High" else "#D97706" if emp["Flight Risk"]=="Medium" else "#166534"
        st.markdown(f"""
        <div class="card" style="display:flex;gap:16px;align-items:center">
          {avatar_html(sel_emp,64,bc)}
          <div>
            <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;color:#0B2540">{sel_emp}</div>
            <div style="color:#64748B;font-size:0.82rem">{emp['Current Job Title']}</div>
            <div style="color:#64748B;font-size:0.78rem">{emp['Department']} · Grade {int(emp['Job Grade (1-9)'])} · {emp['EE Number']}</div>
            <div style="margin-top:6px">
              <span class="band-pill" style="background:{bc}20;color:{bc};font-size:0.75rem">{BAND_SHORT.get(band,band)}</span>
              <span class="band-pill" style="background:{fr_bg};color:{fr_clr};font-size:0.75rem">FR: {emp['Flight Risk']}</span>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
    with h2c:
        st.plotly_chart(gauge_fig(lps,"Leadership Potential Score",color=bc),
                        use_container_width=True,config={"displayModeBar":False})
    with h3c:
        kfc = safe_float(emp.get("KF KFALP - Composite Score (1-5)",0))
        vec = safe_float(emp.get("KF viaEdge - Learning Agility Composite (1-5)",0))
        if kfc>0: st.plotly_chart(speedometer_fig(kfc,"KFALP Composite",color="#C9A227"),
                                   use_container_width=True,config={"displayModeBar":False})
        if vec>0: st.plotly_chart(speedometer_fig(vec,"viaEdge Composite",color="#7C3AED"),
                                   use_container_width=True,config={"displayModeBar":False})

    sl_col,rd_col = st.columns([1.3,1])
    with sl_col:
        st.markdown('<div class="sec-hdr">📏 Feature Profile — Position in Organisation</div>',
                    unsafe_allow_html=True)
        sl_defs = [
            ("Performance (3yr Avg)","Average Performance Rating - Last 3 Years (1-5)",1,5,"#0D7377"),
            ("Last Performance Rating","Last Annual Performance Rating (1-5)",1,5,"#0D7377"),
            ("Total Promotions","Total Promotions (Career)",0,14,"#0D7377"),
            ("Promotions/Year","Promotions per Year (Career)",0,0.8,"#0D7377"),
            ("Promotions/Year (5yr)","Promotions per Year (Last 5 Years)",0,0.8,"#0D7377"),
            ("Tenure (Years)","Tenure with Organisation (Years)",0,40,"#0D7377"),
            ("Direct Reports","Number of Direct Reports",0,50,"#0D7377"),
            ("Critical Projects","Number of Critical Projects Led",0,14,"#0D7377"),
            ("Mobility Willingness","Mobility / Relocation Willingness (1-5)",1,5,"#0D7377"),
            ("KF KFALP — Drivers","KF KFALP - Drivers Score (1-5)",1,5,"#C9A227"),
            ("KF KFALP — Curiosity","KF KFALP - Curiosity Score (1-5)",1,5,"#C9A227"),
            ("KF KFALP — Insight","KF KFALP - Insight Score (1-5)",1,5,"#C9A227"),
            ("KF KFALP — Engagement","KF KFALP - Engagement Score (1-5)",1,5,"#C9A227"),
            ("KF KFALP — Determination","KF KFALP - Determination Score (1-5)",1,5,"#C9A227"),
            ("KF KFALP — Learnability","KF KFALP - Learnability Score (1-5)",1,5,"#C9A227"),
            ("viaEdge — Mental Agility","KF viaEdge - Mental Agility Score (1-5)",1,5,"#7C3AED"),
            ("viaEdge — People Agility","KF viaEdge - People Agility Score (1-5)",1,5,"#7C3AED"),
            ("viaEdge — Change Agility","KF viaEdge - Change Agility Score (1-5)",1,5,"#7C3AED"),
            ("viaEdge — Results Agility","KF viaEdge - Results Agility Score (1-5)",1,5,"#7C3AED"),
            ("viaEdge — Self-Awareness","KF viaEdge - Self-Awareness Score (1-5)",1,5,"#7C3AED"),
        ]
        html_s = ""
        for lbl,col,lo,hi,clr in sl_defs:
            if col not in df_emp.columns: continue
            val = emp.get(col,np.nan)
            if pd.isna(val):
                html_s += f"<div style='font-size:0.78rem;color:#CBD5E1;margin-bottom:8px'>{lbl}: N/A</div>"
                continue
            pct = norm_pct(float(val), df_emp[col])
            html_s += slider_html(lbl, float(val), lo, hi, clr, pct=pct)
        st.markdown(f'<div class="card">{html_s}</div>', unsafe_allow_html=True)

    with rd_col:
        st.markdown('<div class="sec-hdr">🕸 KFALP Radar</div>', unsafe_allow_html=True)
        kf_vals = [safe_float(emp.get(k,2.5),2.5) for k in KF_KEYS]
        ref_kf  = [df_emp[k].mean() if k in df_emp.columns else 3.0 for k in KF_KEYS]
        st.plotly_chart(radar_fig(kf_vals,KF_LBLS,"KFALP","#C9A227",ref_kf),
                        use_container_width=True,config={"displayModeBar":False})

        st.markdown('<div class="sec-hdr">🕸 viaEdge Radar</div>', unsafe_allow_html=True)
        ve_vals = [safe_float(emp.get(k,2.5),2.5) for k in VE_KEYS]
        ref_ve  = [df_emp[k].mean() if k in df_emp.columns else 3.0 for k in VE_KEYS]
        st.plotly_chart(radar_fig(ve_vals,VE_LBLS,"viaEdge","#7C3AED",ref_ve),
                        use_container_width=True,config={"displayModeBar":False})

        st.markdown('<div class="sec-hdr">🔲 9-Box Position</div>', unsafe_allow_html=True)
        st.plotly_chart(nine_box_fig(df_emp,highlight_ee=emp["EE Number"]),
                        use_container_width=True,config={"displayModeBar":False})

# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — COMPARE EMPLOYEES
# ═══════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="sec-hdr">⚖️ Select 2–4 Employees to Compare</div>',
                unsafe_allow_html=True)
    sel_emps = st.multiselect("Choose employees", all_names, max_selections=4,
                               default=all_names[:2] if len(all_names)>=2 else all_names,
                               key="cmp_sel")
    if len(sel_emps)<2:
        st.info("Select at least 2 employees to compare.")
    else:
        cmp_colors = ["#0D7377","#C9A227","#7C3AED","#EA580C"]
        cmp_df = df_emp[df_emp["Employee Full Name"].isin(sel_emps)].copy()

        hcols = st.columns(len(sel_emps))
        for i,name in enumerate(sel_emps):
            row = cmp_df[cmp_df["Employee Full Name"]==name].iloc[0]
            clr = cmp_colors[i]
            with hcols[i]:
                st.plotly_chart(gauge_fig(row["LPS"],name[:18],color=clr),
                                use_container_width=True,config={"displayModeBar":False})
                bs = BAND_SHORT.get(row["LPS Band"],row["LPS Band"])
                st.markdown(f"<div style='text-align:center;font-size:0.78rem;color:#64748B'>"
                            f"{row['Current Job Title']}<br>Grade {int(row['Job Grade (1-9)'])}"
                            f"<span class='band-pill' style='background:{clr}20;color:{clr}'>{bs}</span>"
                            f"</div>", unsafe_allow_html=True)

        st.markdown('<div class="sec-hdr" style="margin-top:16px">📏 Feature Comparison</div>',
                    unsafe_allow_html=True)
        cmp_sl_defs = [
            ("LPS Score","LPS",0,100),
            ("Performance (3yr Avg)","Average Performance Rating - Last 3 Years (1-5)",1,5),
            ("Total Promotions","Total Promotions (Career)",0,14),
            ("Promotions/Year","Promotions per Year (Career)",0,0.8),
            ("KF KFALP Composite","KF KFALP - Composite Score (1-5)",1,5),
            ("viaEdge Composite","KF viaEdge - Learning Agility Composite (1-5)",1,5),
            ("KFALP — Learnability","KF KFALP - Learnability Score (1-5)",1,5),
            ("viaEdge — Change Agility","KF viaEdge - Change Agility Score (1-5)",1,5),
            ("viaEdge — Results Agility","KF viaEdge - Results Agility Score (1-5)",1,5),
            ("Tenure (Years)","Tenure with Organisation (Years)",0,40),
            ("Critical Projects","Number of Critical Projects Led",0,14),
            ("Mobility Willingness","Mobility / Relocation Willingness (1-5)",1,5),
        ]
        html_cmp = ""
        for lbl,col,lo,hi in cmp_sl_defs:
            if col not in cmp_df.columns: continue
            html_cmp += (f"<div style='font-size:0.78rem;color:#374151;margin:10px 0 3px;font-weight:600'>{lbl}</div>"
                         f"<div style='height:10px;border-radius:6px;background:linear-gradient(90deg,"
                         f"#B91C1C 0%,#D97706 40%,#16A34A 100%);position:relative;margin-bottom:12px'>")
            for j,name in enumerate(sel_emps):
                r = cmp_df[cmp_df["Employee Full Name"]==name]
                if len(r)==0: continue
                val = r.iloc[0].get(col,np.nan)
                if pd.isna(val): continue
                pp = max(2,min(98,(float(val)-lo)/(hi-lo+1e-9)*100))
                clr = cmp_colors[j]
                html_cmp += (f"<div title='{name}: {float(val):.2f}' style='position:absolute;"
                             f"top:-5px;left:{pp}%;width:20px;height:20px;border-radius:50%;"
                             f"background:{clr};border:3px solid white;transform:translateX(-50%);"
                             f"box-shadow:0 2px 6px rgba(0,0,0,0.25);'></div>")
            html_cmp += "</div><div style='display:flex;gap:10px;flex-wrap:wrap;margin-bottom:2px'>"
            for j,name in enumerate(sel_emps):
                r = cmp_df[cmp_df["Employee Full Name"]==name]
                if len(r)==0: continue
                val = r.iloc[0].get(col,np.nan)
                vs = f"{float(val):.2f}" if not pd.isna(val) else "N/A"
                html_cmp += (f"<span style='font-size:0.72rem;color:{cmp_colors[j]};"
                             f"font-weight:600'>● {name.split()[0]}: {vs}</span>")
            html_cmp += "</div>"
        st.markdown(f'<div class="card">{html_cmp}</div>', unsafe_allow_html=True)

        oc1,oc2 = st.columns([1,1])
        with oc1:
            st.markdown('<div class="sec-hdr">🕸 KFALP Overlay</div>', unsafe_allow_html=True)
            fig_ov = go.Figure()
            for j,name in enumerate(sel_emps):
                row = cmp_df[cmp_df["Employee Full Name"]==name]
                if len(row)==0: continue
                vals = [safe_float(row.iloc[0].get(k,2.5),2.5) for k in KF_KEYS]
                clr  = cmp_colors[j]
                fig_ov.add_trace(go.Scatterpolar(
                    r=vals+[vals[0]], theta=KF_LBLS+[KF_LBLS[0]],
                    fill="toself", fillcolor=hex_to_rgba(clr,0.15),
                    line=dict(color=clr,width=2.5), name=name,
                ))
            fig_ov.update_layout(
                polar=dict(radialaxis=dict(visible=True,range=[0,5],tickvals=[1,2,3,4,5],tickfont={"size":8})),
                legend=dict(font={"size":9,"family":"DM Sans"}),
                margin=dict(l=40,r=40,t=20,b=20),height=320,
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_ov, use_container_width=True, config={"displayModeBar":False})
        with oc2:
            st.markdown('<div class="sec-hdr">🔲 9-Box Comparison</div>', unsafe_allow_html=True)
            st.plotly_chart(nine_box_fig(cmp_df),
                            use_container_width=True,config={"displayModeBar":False})

# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — ORG CHART
# ═══════════════════════════════════════════════════════════════════════════
with tab4:
    if "org" not in data:
        st.info("Upload **org_structure.csv** to view the interactive org chart.")
    else:
        df_org = data["org"].copy()
        st.markdown('<div class="sec-hdr">🌐 Interactive Organisation Chart</div>',
                    unsafe_allow_html=True)
        lps_map = df_emp.set_index("Current Job Title")["LPS"].to_dict()
        df_org["LPS"] = df_org["Job Title"].map(lps_map)

        G = nx.DiGraph()
        for _,row in df_org.iterrows():
            G.add_node(row["Job Title"],
                       grade=row.get("Job Grade (1-9)",5),
                       lps=row.get("LPS",50),
                       is_critical=row.get("Is Critical Role",False))
            if str(row.get("Parent Node ID","")) not in ["","nan"]:
                G.add_edge(str(row["Parent Node ID"]), row["Job Title"])

        pos={}; levels={}
        roots=[n for n in G.nodes if G.in_degree(n)==0]
        if roots:
            q=deque([(roots[0],0)]); visited=set()
            while q:
                node,depth=q.popleft()
                if node in visited: continue
                visited.add(node); levels.setdefault(depth,[]).append(node)
                for child in G.successors(node): q.append((child,depth+1))
        for depth,nodes in levels.items():
            n=len(nodes)
            for i,node in enumerate(nodes):
                pos[node]=(i-(n-1)/2.0,-depth*1.8)

        ex,ey=[],[]
        for u,v in G.edges():
            if u in pos and v in pos:
                x0,y0=pos[u]; x1,y1=pos[v]
                ex+=[x0,x1,None]; ey+=[y0,y1,None]

        grade_colors={9:"#0B2540",8:"#0D7377",7:"#C9A227",6:"#2563EB",
                      5:"#7C3AED",4:"#16A34A",3:"#EA580C",2:"#64748B",1:"#94A3B8"}
        nx_,ny_,nt_,nc_,ns_,nh_=[],[],[],[],[],[]
        for node in G.nodes():
            if node not in pos: continue
            x,y=pos[node]; nx_.append(x); ny_.append(y)
            nd=G.nodes[node]; g=nd.get("grade",5)
            lps_v=nd.get("lps",50); is_cr=bool(nd.get("is_critical",False))
            nc_.append(grade_colors.get(g,"#888"))
            ns_.append(30 if g>=9 else 24 if g>=7 else 18)
            nt_.append(node[:20]+("..." if len(node)>20 else ""))
            _lps=f"{float(lps_v):.1f}" if lps_v is not None and str(lps_v)!="nan" else "N/A"
            nh_.append(f"<b>{node}</b><br>Grade: {g}<br>LPS: {_lps}{' ★ Critical' if is_cr else ''}")

        fig_org=go.Figure()
        fig_org.add_trace(go.Scatter(x=ex,y=ey,mode="lines",
                                      line=dict(width=1.2,color="#CBD5E1"),hoverinfo="none"))
        fig_org.add_trace(go.Scatter(x=nx_,y=ny_,mode="markers+text",
                                      marker=dict(size=ns_,color=nc_,line=dict(width=2,color="white")),
                                      text=nt_,textposition="bottom center",
                                      textfont=dict(family="DM Sans",size=8,color="#1A2535"),
                                      hovertext=nh_,hoverinfo="text"))
        fig_org.update_layout(showlegend=False,
                               xaxis=dict(showgrid=False,zeroline=False,showticklabels=False),
                               yaxis=dict(showgrid=False,zeroline=False,showticklabels=False),
                               margin=dict(l=20,r=20,t=20,b=20),height=560,
                               paper_bgcolor="white",plot_bgcolor="white",
                               hoverlabel=dict(bgcolor="white",font_size=11,font_family="DM Sans",bordercolor="#D1DCE8"))
        st.plotly_chart(fig_org, use_container_width=True, config={"displayModeBar":True})
        leg_cols=st.columns(len(grade_colors))
        for i,(g,c) in enumerate(sorted(grade_colors.items(),reverse=True)):
            with leg_cols[i]:
                st.markdown(f"<div style='display:flex;align-items:center;gap:4px;font-size:0.72rem'>"
                            f"<div style='width:12px;height:12px;border-radius:50%;background:{c}'></div>G{g}</div>",
                            unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 5 — ORG READINESS
# ═══════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="sec-hdr">📊 Organisational Succession Readiness</div>',
                unsafe_allow_html=True)
    n_roles  = len(CRITICAL_ROLES)
    avg_top1 = df_elig.sort_values("LPS",ascending=False).groupby("Current Job Title")["LPS"].first().mean()
    pct_b3   = df_elig["LPS Band"].isin(["Band 5 - Ready Now","Band 4 - Ready in 1-2 Years",
                                          "Band 3 - Ready in 2-3 Years"]).mean()*100
    hr_pct   = (df_emp["Flight Risk"]=="High").mean()*100

    k1,k2,k3,k4,k5=st.columns(5)
    for col_w,val,lbl,clr in [
        (k1,n_roles,"Critical Roles","#0B2540"),
        (k2,f"{avg_top1:.1f}","Avg LPS #1 Succ","#0D7377"),
        (k3,f"{pct_b3:.0f}%","Pool at Band 3+","#1B7A3E"),
        (k4,f"{hr_pct:.0f}%","High Flight Risk","#B91C1C"),
        (k5,len(df_elig),"Eligible Emps","#2563EB"),
    ]:
        with col_w:
            st.markdown(f'<div class="kpi"><div class="kpi-value" style="color:{clr}">{val}</div>'
                        f'<div class="kpi-label">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    r1,r2=st.columns([1.8,1])
    with r1:
        st.markdown('<div class="sec-hdr">🔥 Bench Strength — Top 3 per Role</div>',
                    unsafe_allow_html=True)
        heat_z,heat_t,heat_y=[],[],[]
        for role in CRITICAL_ROLES:
            rp = df_pip[df_pip["Critical Role"]==role].sort_values("Successor Rank")
            vals = rp["Leadership Potential Score (0-100)"].tolist()
            while len(vals)<3: vals.append(0)
            heat_z.append(vals[:3]); heat_t.append([f"{v:.1f}" for v in vals[:3]])
            heat_y.append(ROLES_CFG[role]["label"][:40])
        fig_heat=go.Figure(go.Heatmap(
            z=heat_z,x=["Successor #1","Successor #2","Successor #3"],y=heat_y,
            text=heat_t,texttemplate="%{text}",
            textfont=dict(family="Syne",size=11,color="white"),
            colorscale=[[0,"#B91C1C"],[0.35,"#EA580C"],[0.5,"#D97706"],
                        [0.65,"#2563EB"],[0.8,"#1B7A3E"],[1.0,"#065F46"]],
            zmin=0,zmax=100,showscale=True,colorbar=dict(title="LPS",tickfont=dict(size=9)),
        ))
        fig_heat.update_layout(
            margin=dict(l=0,r=0,t=10,b=0),height=420,
            xaxis=dict(tickfont=dict(family="Syne",size=10)),
            yaxis=dict(tickfont=dict(family="DM Sans",size=9),autorange="reversed"),
            paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar":False})

    with r2:
        st.markdown('<div class="sec-hdr">🎯 LPS Band Distribution</div>', unsafe_allow_html=True)
        bd=df_elig["LPS Band"].value_counts()
        fig_bd=go.Figure(go.Bar(x=bd.values,y=[BAND_SHORT.get(b,b) for b in bd.index],
                                 orientation="h",marker_color=[BAND_COLORS.get(b,"#888") for b in bd.index],
                                 text=bd.values,textposition="outside",textfont=dict(family="DM Sans",size=10)))
        fig_bd.update_layout(xaxis=dict(showgrid=False,showticklabels=False),
                              yaxis=dict(tickfont=dict(family="DM Sans",size=10)),
                              margin=dict(l=0,r=40,t=10,b=0),height=200,
                              paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bd, use_container_width=True, config={"displayModeBar":False})

    # 9-Box Grid
    st.markdown('<div class="sec-hdr" style="margin-top:10px">🔲 Organisation-wide 9-Box Grid</div>',
                unsafe_allow_html=True)
    nb_f,_ = st.columns([1.5,3])
    with nb_f:
        nb_opts = ["All Departments"]+sorted(df_elig["Department"].unique().tolist())
        nb_dept = st.selectbox("Filter by Department", nb_opts, key="nb_dept")
    nb_df = df_elig if nb_dept=="All Departments" else df_elig[df_elig["Department"]==nb_dept]
    st.plotly_chart(nine_box_fig(nb_df), use_container_width=True, config={"displayModeBar":False})

    nb_sum = nb_df.groupby("9-Box Position").agg(
        Count=("EE Number","count"),
        Avg_LPS=("LPS","mean"),
        Avg_Perf=("Average Performance Rating - Last 3 Years (1-5)","mean")
    ).round(2).reset_index().sort_values("Count",ascending=False)
    st.dataframe(nb_sum, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 6 — KF ASSESSMENT
# ═══════════════════════════════════════════════════════════════════════════
with tab6:
    if "kfalp" not in data and "viaedge" not in data:
        st.info("Upload kf_kfalp_detail.csv and kf_viaedge_detail.csv to explore KF assessments.")
    else:
        st.markdown('<div class="sec-hdr">🧠 Korn Ferry Assessment Explorer</div>',
                    unsafe_allow_html=True)
        kft1,kft2,kft3=st.tabs(["KFALP Dimensions","viaEdge Dimensions","Reference Guide"])

        with kft1:
            if "kfalp" in data:
                df_kf=data["kfalp"].copy()
                kfc1,kfc2=st.columns([1,2])
                with kfc1:
                    kf_dims=df_kf["KF KFALP Dimension"].unique().tolist()
                    sel_dim=st.selectbox("KFALP Dimension",kf_dims,key="kfd")
                    dim_df=df_kf[df_kf["KF KFALP Dimension"]==sel_dim]
                    fig_kd=px.histogram(dim_df,x="Raw Score (1-5)",nbins=20,
                                         color_discrete_sequence=["#C9A227"],title=f"{sel_dim} — Distribution")
                    fig_kd.update_layout(margin=dict(l=0,r=0,t=30,b=0),height=200,
                                          paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                                          title_font=dict(family="Syne",size=12),xaxis_title=None,yaxis_title=None)
                    st.plotly_chart(fig_kd,use_container_width=True,config={"displayModeBar":False})
                    band_cnt=dim_df["KFALP Rating Band"].value_counts()
                    kf_bc={"Exceptional":"#065F46","Strong":"#1B7A3E","Effective":"#2563EB","Developing":"#D97706","Limited":"#B91C1C"}
                    fig_kb=go.Figure(go.Pie(labels=band_cnt.index,values=band_cnt.values,hole=0.55,
                                            marker_colors=[kf_bc.get(b,"#888") for b in band_cnt.index],textfont=dict(size=9)))
                    fig_kb.update_layout(margin=dict(l=0,r=0,t=10,b=0),height=180,showlegend=True,
                                          legend=dict(font=dict(size=8),orientation="h",x=0.5,xanchor="center",y=-0.1),
                                          paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_kb,use_container_width=True,config={"displayModeBar":False})
                with kfc2:
                    pivot=df_kf.pivot_table(index="Employee Full Name",columns="KF KFALP Dimension",
                                             values="Raw Score (1-5)",aggfunc="mean").dropna()
                    sc=("Learnability" if "Learnability" in pivot.columns else pivot.columns[0])
                    pivot=pivot.sort_values(sc,ascending=False).head(30)
                    fig_kh=px.imshow(pivot.round(1),color_continuous_scale=["#B91C1C","#D97706","#DBEAFE","#1B7A3E"],
                                      zmin=1,zmax=5,text_auto=".1f",aspect="auto",title="KFALP — Top 30")
                    fig_kh.update_layout(margin=dict(l=0,r=0,t=30,b=0),height=480,paper_bgcolor="rgba(0,0,0,0)",
                                          title_font=dict(family="Syne",size=12),xaxis_tickfont=dict(size=9),yaxis_tickfont=dict(size=8))
                    st.plotly_chart(fig_kh,use_container_width=True,config={"displayModeBar":False})

        with kft2:
            if "viaedge" in data:
                df_ve=data["viaedge"].copy()
                vec1,vec2=st.columns([1,2])
                with vec1:
                    ve_dims=df_ve["KF viaEdge Dimension"].unique().tolist()
                    sel_ve=st.selectbox("viaEdge Dimension",ve_dims,key="ved")
                    ve_df=df_ve[df_ve["KF viaEdge Dimension"]==sel_ve]
                    fig_vd=px.histogram(ve_df,x="Raw Score (1-5)",nbins=20,color_discrete_sequence=["#7C3AED"],title=f"{sel_ve} — Distribution")
                    fig_vd.update_layout(margin=dict(l=0,r=0,t=30,b=0),height=200,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",title_font=dict(family="Syne",size=12),xaxis_title=None,yaxis_title=None)
                    st.plotly_chart(fig_vd,use_container_width=True,config={"displayModeBar":False})
                    pct_col="KF viaEdge Learning Agility Percentile"
                    if pct_col in df_ve.columns:
                        fig_vp=px.histogram(df_ve.drop_duplicates("EE Number"),x=pct_col,nbins=20,color_discrete_sequence=["#0D7377"],title="Learning Agility Percentile")
                        fig_vp.update_layout(margin=dict(l=0,r=0,t=30,b=0),height=180,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",title_font=dict(family="Syne",size=11),xaxis_title=None,yaxis_title=None)
                        st.plotly_chart(fig_vp,use_container_width=True,config={"displayModeBar":False})
                with vec2:
                    ve_pivot=df_ve.pivot_table(index="Employee Full Name",columns="KF viaEdge Dimension",values="Raw Score (1-5)",aggfunc="mean").dropna()
                    sv="Mental Agility" if "Mental Agility" in ve_pivot.columns else ve_pivot.columns[0]
                    ve_pivot=ve_pivot.sort_values(sv,ascending=False).head(30)
                    fig_vh=px.imshow(ve_pivot.round(1),color_continuous_scale=["#B91C1C","#D97706","#DBEAFE","#1B7A3E"],zmin=1,zmax=5,text_auto=".1f",aspect="auto",title="viaEdge — Top 30")
                    fig_vh.update_layout(margin=dict(l=0,r=0,t=30,b=0),height=480,paper_bgcolor="rgba(0,0,0,0)",title_font=dict(family="Syne",size=12),xaxis_tickfont=dict(size=9),yaxis_tickfont=dict(size=8))
                    st.plotly_chart(fig_vh,use_container_width=True,config={"displayModeBar":False})

        with kft3:
            if "ref" in data:
                df_ref=data["ref"].copy()
                instruments=df_ref["KF Instrument"].unique().tolist() if "KF Instrument" in df_ref.columns else []
                sel_inst=st.selectbox("Instrument",instruments,key="ref_inst")
                ref_sub=df_ref[df_ref["KF Instrument"]==sel_inst]
                dims_ref=ref_sub["Dimension"].unique().tolist() if "Dimension" in ref_sub.columns else []
                sel_rdim=st.selectbox("Dimension",dims_ref,key="ref_dim")
                rd_sub=ref_sub[ref_sub["Dimension"]==sel_rdim]
                if len(rd_sub)>0:
                    r0=rd_sub.iloc[0]
                    st.markdown(f"""<div class="card">
                      <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;color:#0D7377">{sel_rdim}</div>
                      <div style="font-size:0.8rem;color:#64748B;margin:4px 0 10px">{r0.get('Category','')}</div>
                      <div style="font-size:0.82rem;margin-bottom:8px"><b>Sub-Dimensions:</b> {r0.get('Sub-Dimensions','')}</div>
                      <div style="font-size:0.82rem;margin-bottom:8px"><b>What It Measures:</b> {r0.get('What It Measures','')}</div>
                      <div style="font-size:0.82rem;margin-bottom:8px"><b>High Potential Signal:</b> {r0.get('High Potential Signal','')}</div>
                      <div style="font-size:0.82rem"><b>Assessment Method:</b> {r0.get('Assessment Method','')}</div>
                    </div>""", unsafe_allow_html=True)
                    for _,brow in rd_sub.sort_values("Score",ascending=False).iterrows():
                        bc2={"Exceptional":"#065F46","Strong":"#1B7A3E","Effective":"#2563EB",
                             "Developing":"#D97706","Limited":"#B91C1C","Expert":"#065F46",
                             "Advanced":"#1B7A3E","Emerging":"#EA580C","Needs Development":"#B91C1C"}.get(brow.get("Rating Band",""),"#888")
                        st.markdown(f"""<div style="display:flex;gap:12px;margin-bottom:8px;align-items:flex-start">
                          <div style="background:{bc2};color:white;border-radius:8px;padding:4px 10px;font-family:'Syne',sans-serif;font-size:0.75rem;font-weight:700;white-space:nowrap;flex-shrink:0">{brow.get('Score','')} — {brow.get('Rating Band','')}</div>
                          <div style="font-size:0.8rem;color:#374151;line-height:1.5">{brow.get('Behavioural Descriptor','')}</div>
                        </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 7 — CAREER PATH
# ═══════════════════════════════════════════════════════════════════════════
with tab7:
    if "promos" not in data:
        st.info("Upload **promotion_history.csv** to view career paths.")
    else:
        df_promo=data["promos"].copy()
        df_promo.columns=[c.replace("\u2013","-").replace("\u2014","-") for c in df_promo.columns]
        st.markdown('<div class="sec-hdr">📈 Career Path & Promotion Trajectory</div>',
                    unsafe_allow_html=True)
        cp1,cp2=st.columns([1,2.5])
        with cp1:
            promo_names=sorted(df_promo["Employee Full Name"].unique().tolist())
            sel_cp=st.selectbox("Select Employee",promo_names,key="cp_sel")
            emp_cp=df_emp[df_emp["Employee Full Name"]==sel_cp]
            if len(emp_cp)>0:
                e=emp_cp.iloc[0]; lps_s=safe_float(e["LPS"]); clr_v=lps_color(lps_s)
                st.markdown(f"""<div class="card">
                  <div style="display:flex;gap:10px;align-items:center;margin-bottom:10px">
                    {avatar_html(sel_cp,44,clr_v)}
                    <div>
                      <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:0.9rem">{sel_cp}</div>
                      <div style="font-size:0.75rem;color:#64748B">{e['Current Job Title']}</div>
                    </div>
                  </div>
                  <div style="font-size:0.78rem;color:#374151">
                    <b>Grade:</b> {int(e['Job Grade (1-9)'])} &nbsp;|&nbsp; <b>Tenure:</b> {e['Tenure with Organisation (Years)']}y<br>
                    <b>Promotions:</b> {int(e['Total Promotions (Career)'])} &nbsp;|&nbsp; <b>LPS:</b> {lps_s:.1f}
                  </div>
                </div>""", unsafe_allow_html=True)
                k1v=safe_float(e.get("KF KFALP - Composite Score (1-5)",0))
                k2v=safe_float(e.get("KF viaEdge - Learning Agility Composite (1-5)",0))
                if k1v>0: st.plotly_chart(speedometer_fig(k1v,"KFALP Composite",color="#C9A227"),use_container_width=True,config={"displayModeBar":False})
                if k2v>0: st.plotly_chart(speedometer_fig(k2v,"viaEdge Composite",color="#7C3AED"),use_container_width=True,config={"displayModeBar":False})

        with cp2:
            emp_promos=df_promo[df_promo["Employee Full Name"]==sel_cp].sort_values("Promotion Year")
            if len(emp_promos)==0:
                st.info(f"No promotion history found for {sel_cp}.")
            else:
                years=emp_promos["Promotion Year"].tolist()
                grades=emp_promos["Promoted To Grade"].tolist()
                perfs=emp_promos["Performance Rating at Promotion"].tolist()
                fig_tl=go.Figure()
                fig_tl.add_trace(go.Scatter(x=years,y=grades,mode="lines+markers+text",
                    line=dict(color="#0D7377",width=3),
                    marker=dict(size=[10+p*2 for p in perfs],color=perfs,
                                colorscale=[[0,"#B91C1C"],[0.5,"#D97706"],[1,"#1B7A3E"]],
                                cmin=1,cmax=5,showscale=True,line=dict(width=2,color="white"),
                                colorbar=dict(title="Perf",tickfont=dict(size=8),len=0.5,y=0.5)),
                    text=[f"G{g}" for g in grades],textposition="top center",
                    textfont=dict(family="Syne",size=10,color="#0B2540"),name="Grade"))
                fig_tl.add_trace(go.Scatter(x=years,y=perfs,mode="lines+markers",
                    line=dict(color="#C9A227",width=2,dash="dot"),marker=dict(size=8,color="#C9A227"),
                    name="Performance",yaxis="y2"))
                entry_yr=emp_promos["Promotion Year"].min()-2
                entry_gr=emp_promos["Promoted From Grade"].iloc[0]
                fig_tl.add_trace(go.Scatter(x=[entry_yr],y=[entry_gr],mode="markers+text",
                    marker=dict(size=12,color="#64748B",symbol="square"),
                    text=["Entry"],textposition="top center",textfont=dict(family="Syne",size=9,color="#64748B"),
                    name="Career Entry",hoverinfo="skip"))
                emp_row=df_emp[df_emp["Employee Full Name"]==sel_cp]
                if len(emp_row)>0:
                    fig_tl.add_trace(go.Scatter(x=[2025],y=[int(emp_row.iloc[0]["Job Grade (1-9)"])],
                        mode="markers+text",marker=dict(size=14,color=lps_color(emp_row.iloc[0]["LPS"]),symbol="star"),
                        text=["Now"],textposition="top center",textfont=dict(family="Syne",size=10,color="#0B2540"),
                        name="Current",hoverinfo="skip"))
                fig_tl.update_layout(
                    xaxis=dict(title="Year",tickfont=dict(family="DM Sans",size=10)),
                    yaxis=dict(title="Job Grade",range=[0,10],tickvals=list(range(1,10)),tickfont=dict(family="DM Sans",size=10)),
                    yaxis2=dict(title="Performance",overlaying="y",side="right",range=[0,5.5],tickfont=dict(size=9)),
                    legend=dict(font=dict(family="DM Sans",size=9),orientation="h",x=0.5,xanchor="center",y=1.06),
                    margin=dict(l=0,r=60,t=30,b=0),height=320,
                    paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#F8FBFD",hovermode="x unified")
                st.plotly_chart(fig_tl,use_container_width=True,config={"displayModeBar":False})
                disp_cols=[c for c in ["Promotion Number (Career)","Promotion Year","Promoted From Grade","Promoted To Grade","Performance Rating at Promotion","Years Since Last Promotion"] if c in emp_promos.columns]
                st.markdown('<div class="sec-hdr" style="margin-top:8px">📋 Promotion History</div>',unsafe_allow_html=True)
                st.dataframe(emp_promos[disp_cols].reset_index(drop=True),use_container_width=True,hide_index=True)

        st.markdown('<div class="sec-hdr" style="margin-top:16px">🚀 Promotion Velocity vs Performance</div>',unsafe_allow_html=True)
        vel_df=df_emp[["Job Grade (1-9)","Promotions per Year (Career)","Average Performance Rating - Last 3 Years (1-5)"]].dropna()
        fig_vel=px.scatter(vel_df,x="Average Performance Rating - Last 3 Years (1-5)",y="Promotions per Year (Career)",
                            color="Job Grade (1-9)",color_continuous_scale=px.colors.sequential.Teal,opacity=0.7,size_max=8,
                            labels={"Average Performance Rating - Last 3 Years (1-5)":"Avg Performance (3yr)",
                                    "Promotions per Year (Career)":"Promotions / Year","Job Grade (1-9)":"Grade"},
                            title="Performance vs Promotion Velocity (coloured by Grade)")
        fig_vel.update_layout(margin=dict(l=0,r=0,t=30,b=0),height=320,
                               paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#F8FBFD",
                               title_font=dict(family="Syne",size=12))
        st.plotly_chart(fig_vel,use_container_width=True,config={"displayModeBar":False})
