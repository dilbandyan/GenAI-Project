"""
dashboard.py — Claude Code Analytics Dashboard
Run with: streamlit run dashboard.py
"""

import json
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Claude Code Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme / CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d0d0d;
    border-right: 1px solid #1f1f1f;
}
section[data-testid="stSidebar"] * {
    color: #e8e8e8 !important;
}
section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
    background: #cc5500 !important;
}

/* Main background */
.stApp {
    background: #f7f5f2;
}

/* KPI cards */
.kpi-card {
    background: #fff;
    border: 1px solid #e8e4df;
    border-radius: 12px;
    padding: 24px 20px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    height: 100%;
}
.kpi-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 10px;
    font-family: 'DM Mono', monospace;
}
.kpi-value {
    font-size: 32px;
    font-weight: 600;
    color: #0d0d0d;
    line-height: 1;
}
.kpi-sub {
    font-size: 12px;
    color: #aaa;
    margin-top: 6px;
}

/* Section headings */
.section-title {
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: #cc5500;
    font-family: 'DM Mono', monospace;
    margin-bottom: 4px;
    margin-top: 8px;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0px;
    background: #0d0d0d;
    border-radius: 10px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #888 !important;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.05em;
    border-radius: 7px;
    padding: 8px 20px;
}
.stTabs [aria-selected="true"] {
    background: #cc5500 !important;
    color: #fff !important;
}

/* Sidebar title */
.sidebar-brand {
    font-family: 'DM Mono', monospace;
    font-size: 15px;
    font-weight: 500;
    color: #fff;
    letter-spacing: 0.05em;
    padding: 8px 0 24px 0;
    border-bottom: 1px solid #2a2a2a;
    margin-bottom: 20px;
}
.sidebar-brand span {
    color: #cc5500;
}

/* Footer */
.footer {
    text-align: center;
    color: #bbb;
    font-size: 11px;
    font-family: 'DM Mono', monospace;
    letter-spacing: 0.05em;
    padding: 40px 0 16px 0;
    border-top: 1px solid #e8e4df;
    margin-top: 48px;
}

/* Divider */
.divider {
    border: none;
    border-top: 1px solid #e8e4df;
    margin: 24px 0;
}

/* Dataframe */
.stDataFrame { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Plotly theme ──────────────────────────────────────────────────────────────
PALETTE   = ["#cc5500", "#0d0d0d", "#e87040", "#4a4a4a", "#f0a882", "#888888", "#ffd4b8"]
CHART_BG  = "rgba(0,0,0,0)"
GRID_CLR  = "#ece9e4"
FONT_CLR  = "#333333"
FONT_FAM  = "DM Sans, sans-serif"

def base_layout(fig, title="", height=380):
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=FONT_CLR, family=FONT_FAM), x=0, xanchor="left"),
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(family=FONT_FAM, color=FONT_CLR, size=12),
        height=height,
        margin=dict(l=0, r=0, t=36 if title else 10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        xaxis=dict(gridcolor=GRID_CLR, linecolor=GRID_CLR, zerolinecolor=GRID_CLR),
        yaxis=dict(gridcolor=GRID_CLR, linecolor=GRID_CLR, zerolinecolor=GRID_CLR),
    )
    return fig

# ── Load data ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data(path="analytics_results.json"):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)

data = load_data()

def df(key, required_cols=None):
    """Return a DataFrame for a result key, or empty DataFrame."""
    rows = data.get(key, [])
    if not rows:
        return pd.DataFrame()
    d = pd.DataFrame(rows)
    if required_cols:
        for c in required_cols:
            if c not in d.columns:
                return pd.DataFrame()
    return d

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">⚡ Claude Code<br><span>Analytics</span></div>
    """, unsafe_allow_html=True)

    st.markdown("**Filters**")

    all_practices = ["Backend Engineering", "Data Engineering",
                     "Frontend Engineering", "ML Engineering", "Platform Engineering"]
    sel_practices = st.multiselect(
        "Practice",
        options=all_practices,
        default=all_practices,
        placeholder="All practices",
    )

    all_models = []
    cbm = df("cost_by_model")
    if not cbm.empty and "model" in cbm.columns:
        all_models = cbm["model"].tolist()
    sel_models = st.multiselect(
        "Model",
        options=all_models,
        default=all_models,
        placeholder="All models",
    )

    st.markdown("---")
    st.markdown(
        "<span style='font-size:11px;color:#555;font-family:DM Mono,monospace'>"
        "Filters apply where data<br>includes practice or model.</span>",
        unsafe_allow_html=True,
    )

# ── Filter helpers ────────────────────────────────────────────────────────────
def filter_practice(d, col="practice"):
    if d.empty or col not in d.columns:
        return d
    return d[d[col].isin(sel_practices)] if sel_practices else d

def filter_model(d, col="model"):
    if d.empty or col not in d.columns:
        return d
    return d[d[col].isin(sel_models)] if sel_models else d

# ── KPI helpers ───────────────────────────────────────────────────────────────
def kpi(label, value, sub=""):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {"<div class='kpi-sub'>"+sub+"</div>" if sub else ""}
    </div>
    """, unsafe_allow_html=True)

def section(title):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

def no_data():
    st.info("No data available for the current filter selection.", icon="📭")

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊  Overview",
    "🤖  Model Analysis",
    "👩‍💻  Developer Behavior",
    "🏢  Team Insights",
    "📈  Predictive Analytics",
])

# ═══════════════════════════════════════════════════════════════════
# PAGE 1 — OVERVIEW
# ═══════════════════════════════════════════════════════════════════
with tab1:

    # — KPIs ——————————————————————————————————————————————————————
    section("Key Metrics")
    k1, k2, k3, k4 = st.columns(4)

    # Total Cost
    dc = df("daily_cost")
    total_cost = 0.0
    if not dc.empty and "total_cost_usd" in dc.columns:
        total_cost = dc["total_cost_usd"].sum()
    with k1:
        kpi("Total Cost", f"${total_cost:,.2f}", "60-day period")

    # Total Sessions
    sbp = filter_practice(df("sessions_by_practice"))
    total_sessions = 0
    if not sbp.empty and "session_count" in sbp.columns:
        total_sessions = int(sbp["session_count"].sum())
    with k2:
        kpi("Total Sessions", f"{total_sessions:,}")

    # Total API Requests
    cbm_f = filter_model(df("cost_by_model"))
    total_reqs = 0
    if not cbm_f.empty and "request_count" in cbm_f.columns:
        total_reqs = int(cbm_f["request_count"].sum())
    with k3:
        kpi("API Requests", f"{total_reqs:,}")

    # Avg Session Length
    asl = df("avg_session_length")
    avg_len = "—"
    if not asl.empty and "avg_prompts_per_session" in asl.columns:
        avg_len = f"{asl['avg_prompts_per_session'].iloc[0]:.1f}"
    with k4:
        kpi("Avg Session Length", avg_len, "prompts / session")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # — Daily Cost ——————————————————————————————————————————————————
    col_a, col_b = st.columns([3, 2])

    with col_a:
        section("Daily Cost Over Time")
        if not dc.empty and "day" in dc.columns:
            fig = px.line(dc, x="day", y="total_cost_usd",
                          color_discrete_sequence=[PALETTE[0]])
            fig.update_traces(line_width=2.5,
                              fill="tozeroy",
                              fillcolor="rgba(204,85,0,0.08)")
            fig.update_xaxes(title="")
            fig.update_yaxes(title="USD", tickprefix="$")
            base_layout(fig, height=340)
            st.plotly_chart(fig, use_container_width=True)
        else:
            no_data()

    # — Cost by Practice ————————————————————————————————————————————
    with col_b:
        section("Cost by Engineering Practice")
        cbp = filter_practice(df("cost_by_practice"))
        if not cbp.empty and "practice" in cbp.columns:
            cbp_s = cbp.sort_values("total_cost_usd", ascending=True)
            # Shorten labels
            cbp_s["practice_short"] = cbp_s["practice"].str.replace(" Engineering","", regex=False)
            fig = px.bar(cbp_s, x="total_cost_usd", y="practice_short",
                         orientation="h",
                         color_discrete_sequence=[PALETTE[0]])
            fig.update_xaxes(title="Total Cost (USD)", tickprefix="$")
            fig.update_yaxes(title="")
            base_layout(fig, height=340)
            st.plotly_chart(fig, use_container_width=True)
        else:
            no_data()

# ═══════════════════════════════════════════════════════════════════
# PAGE 2 — MODEL ANALYSIS
# ═══════════════════════════════════════════════════════════════════
with tab2:

    # — Cost by Model ———————————————————————————————————————————————
    section("Cost by Model")
    cbm_f = filter_model(df("cost_by_model"))
    if not cbm_f.empty:
        cbm_s = cbm_f.sort_values("total_cost_usd", ascending=False)
        cbm_s["model_short"] = cbm_s["model"].str.replace("claude-","", regex=False)
        fig = px.bar(cbm_s, x="model_short", y="total_cost_usd",
                     color="model_short",
                     color_discrete_sequence=PALETTE,
                     text="request_count")
        fig.update_traces(texttemplate="<b>%{text:,}</b> reqs", textposition="outside",
                          textfont_size=10)
        fig.update_xaxes(title="")
        fig.update_yaxes(title="Total Cost (USD)", tickprefix="$")
        fig.update_layout(showlegend=False)
        base_layout(fig, height=360)
        st.plotly_chart(fig, use_container_width=True)
    else:
        no_data()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    col_a, col_b = st.columns([3, 2])

    # — Avg Tokens by Model ————————————————————————————————————————
    with col_a:
        section("Avg Tokens by Model")
        tbm = filter_model(df("tokens_by_model"))
        if not tbm.empty:
            tbm["model_short"] = tbm["model"].str.replace("claude-","", regex=False)
            token_cols = {
                "avg_input_tokens":      "Input",
                "avg_output_tokens":     "Output",
                "avg_cache_read_tokens": "Cache Read",
            }
            melted = tbm.melt(
                id_vars="model_short",
                value_vars=[c for c in token_cols if c in tbm.columns],
                var_name="token_type",
                value_name="avg_tokens",
            )
            melted["token_type"] = melted["token_type"].map(token_cols)
            fig = px.bar(melted, x="model_short", y="avg_tokens",
                         color="token_type",
                         barmode="group",
                         color_discrete_sequence=PALETTE)
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Avg Tokens")
            base_layout(fig, height=360)
            st.plotly_chart(fig, use_container_width=True)
        else:
            no_data()

    # — Error Rate Table ————————————————————————————————————————————
    with col_b:
        section("Error Rate by Model")
        erb = filter_model(df("error_rate_by_model"))
        if not erb.empty:
            display = erb.copy()
            display["model"] = display["model"].str.replace("claude-","", regex=False)
            if "error_rate_pct" in display.columns:
                display["error_rate_pct"] = display["error_rate_pct"].apply(lambda x: f"{x:.2f}%")
            display = display.rename(columns={
                "model":           "Model",
                "total_requests":  "Requests",
                "total_errors":    "Errors",
                "error_rate_pct":  "Error Rate",
            })
            st.dataframe(display, use_container_width=True, hide_index=True, height=340)
        else:
            no_data()

# ═══════════════════════════════════════════════════════════════════
# PAGE 3 — DEVELOPER BEHAVIOR
# ═══════════════════════════════════════════════════════════════════
with tab3:

    col_a, col_b = st.columns([3, 2])

    # — Hourly Activity ————————————————————————————————————————————
    with col_a:
        section("Hourly Activity (UTC)")
        ha = df("hourly_activity")
        if not ha.empty and "hour" in ha.columns:
            ha["hour_label"] = ha["hour"].apply(lambda h: f"{h:02d}:00")
            fig = px.bar(ha, x="hour_label", y="request_count",
                         color_discrete_sequence=[PALETTE[0]])
            fig.update_xaxes(title="Hour of Day", tickangle=-45)
            fig.update_yaxes(title="Requests")
            base_layout(fig, height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            no_data()

    # — Tool Usage Frequency ————————————————————————————————————————
    with col_b:
        section("Tool Usage Frequency (Top 10)")
        tuf = df("tool_usage_frequency")
        if not tuf.empty and "tool_name" in tuf.columns:
            top10 = tuf.head(10).sort_values("decision_count", ascending=True)
            fig = px.bar(top10, x="decision_count", y="tool_name",
                         orientation="h",
                         color_discrete_sequence=[PALETTE[2]])
            fig.update_xaxes(title="Decisions")
            fig.update_yaxes(title="")
            base_layout(fig, height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            no_data()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    col_c, col_d = st.columns([2, 3])

    # — Tool Success Rate ——————————————————————————————————————————
    with col_c:
        section("Tool Success Rate")
        tsr = df("tool_success_rate")
        if not tsr.empty and "success_rate_pct" in tsr.columns:
            tsr_s = tsr.sort_values("success_rate_pct", ascending=True)
            fig = px.bar(tsr_s, x="success_rate_pct", y="tool_name",
                         orientation="h",
                         color="success_rate_pct",
                         color_continuous_scale=["#e87040", "#cc5500", "#0d0d0d"],
                         range_color=[90, 100])
            fig.update_xaxes(title="Success Rate (%)", range=[88, 101])
            fig.update_yaxes(title="")
            fig.update_coloraxes(showscale=False)
            base_layout(fig, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            no_data()

    # — Top 10 Users ————————————————————————————————————————————————
    with col_d:
        section("Top 10 Users by Cost")
        tuc = filter_practice(df("top_users_by_cost"), col="practice")
        if not tuc.empty:
            display = tuc.copy()
            if "total_cost_usd" in display.columns:
                display["total_cost_usd"] = display["total_cost_usd"].apply(lambda x: f"${x:,.2f}")
            if "request_count" in display.columns:
                display["request_count"] = display["request_count"].apply(lambda x: f"{x:,}")
            cols_map = {
                "full_name":      "Name",
                "practice":       "Practice",
                "level":          "Level",
                "total_cost_usd": "Total Cost",
                "request_count":  "Requests",
            }
            display = display[[c for c in cols_map if c in display.columns]]
            display = display.rename(columns=cols_map)
            st.dataframe(display, use_container_width=True, hide_index=True, height=400)
        else:
            no_data()

# ═══════════════════════════════════════════════════════════════════
# PAGE 4 — TEAM INSIGHTS
# ═══════════════════════════════════════════════════════════════════
with tab4:

    col_a, col_b = st.columns(2)

    # — Cost by Level ——————————————————————————————————————————————
    with col_a:
        section("Cost by Seniority Level")
        cbl = df("cost_by_level")
        if not cbl.empty and "level" in cbl.columns:
            fig = px.bar(cbl, x="level", y="total_cost_usd",
                         color="level",
                         color_discrete_sequence=PALETTE)
            fig.update_xaxes(title="Seniority Level",
                             categoryorder="array",
                             categoryarray=[f"L{i}" for i in range(1, 11)])
            fig.update_yaxes(title="Total Cost (USD)", tickprefix="$")
            fig.update_layout(showlegend=False)
            base_layout(fig, height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            no_data()

    # — Sessions by Practice ————————————————————————————————————————
    with col_b:
        section("Sessions by Practice")
        sbp = filter_practice(df("sessions_by_practice"))
        if not sbp.empty and "practice" in sbp.columns:
            sbp_s = sbp.sort_values("session_count", ascending=False)
            sbp_s["practice_short"] = sbp_s["practice"].str.replace(" Engineering","", regex=False)
            fig = px.bar(sbp_s, x="practice_short", y="session_count",
                         color="practice_short",
                         color_discrete_sequence=PALETTE)
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Sessions")
            fig.update_layout(showlegend=False)
            base_layout(fig, height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            no_data()

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # — Practice summary table —————————————————————————————————————
    section("Practice Summary")
    cbp  = filter_practice(df("cost_by_practice"))
    sbp2 = filter_practice(df("sessions_by_practice"))

    if not cbp.empty and not sbp2.empty:
        merged = cbp.merge(sbp2, on="practice", how="outer")
        if "total_cost_usd" in merged.columns:
            merged["Cost per Session"] = (
                merged["total_cost_usd"] / merged["session_count"]
            ).apply(lambda x: f"${x:.2f}" if pd.notna(x) else "—")
            merged["total_cost_usd"] = merged["total_cost_usd"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
            merged["session_count"]  = merged["session_count"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
        merged = merged.rename(columns={
            "practice":       "Practice",
            "total_cost_usd": "Total Cost",
            "session_count":  "Sessions",
        })
        st.dataframe(merged, use_container_width=True, hide_index=True)
    else:
        no_data()

# ═══════════════════════════════════════════════════════════════════
# PAGE 5 — PREDICTIVE ANALYTICS
# ═══════════════════════════════════════════════════════════════════

with tab5:

    # ── lazy imports ──────────────────────────────────────────────
    try:
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.ensemble import RandomForestClassifier, IsolationForest
        from sklearn.preprocessing import LabelEncoder
        _sklearn_ok = True
    except ImportError:
        st.error(
            "scikit-learn is required for this tab.  "
            "Run: `pip install scikit-learn`"
        )
        _sklearn_ok = False

    if _sklearn_ok:

        # ── shared data ───────────────────────────────────────────
        dc_raw = data.get("daily_cost", [])
        ha_raw = data.get("hourly_activity", [])
        tu_raw = data.get("top_users_by_cost", [])

        # ══════════════════════════════════════════════════════════
        # 1 · COST FORECASTING
        # ══════════════════════════════════════════════════════════
        section("Cost Forecasting — Next 14 Days")
        st.markdown(
            """
            A **Linear Regression** model is trained on historical daily cost, using the
            sequential day index as the sole feature.  The dashed segment shows the
            extrapolated trend for the next 14 days.  Use this to anticipate budget
            consumption and spot acceleration or deceleration in AI spend.
            """
        )

        if len(dc_raw) < 7:
            st.warning("Not enough daily cost data to train a forecast (need ≥ 7 days).")
        else:
            dc_df = pd.DataFrame(dc_raw)
            dc_df["day"] = pd.to_datetime(dc_df["day"])
            dc_df = dc_df.sort_values("day").reset_index(drop=True)
            dc_df["day_idx"] = np.arange(len(dc_df))

            X_hist = dc_df[["day_idx"]].values
            y_hist = dc_df["total_cost_usd"].values

            lr = LinearRegression().fit(X_hist, y_hist)

            # ── anomaly detection (2-σ) ───────────────────────────
            mu, sigma = y_hist.mean(), y_hist.std()
            dc_df["anomaly"] = (np.abs(y_hist - mu) > 2 * sigma)
            n_anomalies = dc_df["anomaly"].sum()

            # ── future dates ──────────────────────────────────────
            last_idx  = dc_df["day_idx"].max()
            last_day  = dc_df["day"].max()
            future_idx   = np.arange(last_idx + 1, last_idx + 15).reshape(-1, 1)
            future_days  = [last_day + pd.Timedelta(days=i) for i in range(1, 15)]
            future_cost  = lr.predict(future_idx)

            future_df = pd.DataFrame({
                "day":          future_days,
                "total_cost_usd": future_cost,
                "day_idx":      future_idx.flatten(),
                "anomaly":      False,
            })

            # ── chart ─────────────────────────────────────────────
            fig = go.Figure()

            # historical line
            fig.add_trace(go.Scatter(
                x=dc_df["day"], y=dc_df["total_cost_usd"],
                mode="lines",
                name="Actual",
                line=dict(color=PALETTE[0], width=2.5),
                fill="tozeroy",
                fillcolor="rgba(204,85,0,0.07)",
            ))

            # anomaly markers
            anom = dc_df[dc_df["anomaly"]]
            if not anom.empty:
                fig.add_trace(go.Scatter(
                    x=anom["day"], y=anom["total_cost_usd"],
                    mode="markers",
                    name="Anomaly (±2σ)",
                    marker=dict(color="#e03030", size=10, symbol="circle",
                                line=dict(color="#fff", width=1.5)),
                ))

            # forecast line
            fig.add_trace(go.Scatter(
                x=future_df["day"], y=future_df["total_cost_usd"],
                mode="lines+markers",
                name="Forecast",
                line=dict(color=PALETTE[1], width=2, dash="dash"),
                marker=dict(size=5),
            ))

            # ±1σ band on forecast
            slope_unc = sigma * 0.3          # simple heuristic uncertainty
            fig.add_trace(go.Scatter(
                x=list(future_df["day"]) + list(future_df["day"])[::-1],
                y=list(future_cost + slope_unc) + list(future_cost - slope_unc)[::-1],
                fill="toself",
                fillcolor="rgba(13,13,13,0.07)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Forecast ±1σ",
                hoverinfo="skip",
            ))

            base_layout(fig, height=400)
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Daily Cost (USD)", tickprefix="$")
            st.plotly_chart(fig, use_container_width=True)

            # ── anomaly summary ───────────────────────────────────
            section("Anomaly Detection — Unusual Cost Days")
            st.markdown(
                f"""
                Days whose cost deviates more than **2 standard deviations** from the
                60-day mean (μ = **${mu:.2f}**, σ = **${sigma:.2f}**) are flagged as
                anomalies and shown as red dots above.
                **{n_anomalies} anomalous day(s)** were detected.
                These may correspond to large batch jobs, end-of-sprint pushes, or
                sudden changes in team usage patterns.
                """
            )

            if n_anomalies > 0:
                anom_display = anom[["day", "total_cost_usd"]].copy()
                anom_display["deviation_σ"] = (
                    (anom["total_cost_usd"] - mu) / sigma
                ).apply(lambda x: f"{x:+.2f}σ")
                anom_display["total_cost_usd"] = anom_display["total_cost_usd"].apply(
                    lambda x: f"${x:.2f}"
                )
                anom_display["day"] = anom_display["day"].dt.strftime("%Y-%m-%d")
                anom_display = anom_display.rename(columns={
                    "day": "Date",
                    "total_cost_usd": "Cost",
                    "deviation_σ": "Deviation",
                })
                st.dataframe(anom_display, use_container_width=False, hide_index=True)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════
        # 3 · HIGH-COST USER PREDICTION
        # ══════════════════════════════════════════════════════════
        section("High-Cost User Prediction — Feature Importance")
        st.markdown(
            """
            A **Random Forest classifier** is trained to predict whether a developer
            falls above or below the median spend, using three features:
            *request count*, *engineering practice* (label-encoded), and
            *seniority level* (L1–L10 mapped to 1–10).
            The chart below shows which features the model weighted most heavily —
            higher importance means that feature is more predictive of high spend.
            """
        )

        if len(tu_raw) < 6:
            st.warning("Not enough user data to train classifier (need ≥ 6 users).")
        else:
            tu_df = pd.DataFrame(tu_raw)

            # feature engineering
            le_practice = LabelEncoder()
            tu_df["practice_enc"] = le_practice.fit_transform(
                tu_df["practice"].fillna("Unknown")
            )
            tu_df["level_num"] = (
                tu_df["level"]
                .str.extract(r"(\d+)")[0]
                .astype(float)
                .fillna(5)
            )

            median_cost = tu_df["total_cost_usd"].median()
            tu_df["high_cost"] = (tu_df["total_cost_usd"] > median_cost).astype(int)

            feature_names = ["request_count", "practice_enc", "level_num"]
            X = tu_df[feature_names].values
            y = tu_df["high_cost"].values

            rf = RandomForestClassifier(n_estimators=200, random_state=42)
            rf.fit(X, y)

            importance_df = pd.DataFrame({
                "Feature":   ["Request Count", "Practice", "Seniority Level"],
                "Importance": rf.feature_importances_,
            }).sort_values("Importance", ascending=True)

            col_imp, col_stats = st.columns([3, 2])

            with col_imp:
                fig = px.bar(
                    importance_df,
                    x="Importance", y="Feature",
                    orientation="h",
                    color="Importance",
                    color_continuous_scale=["#f0a882", PALETTE[0], PALETTE[1]],
                )
                fig.update_coloraxes(showscale=False)
                fig.update_xaxes(title="Feature Importance", tickformat=".0%")
                fig.update_yaxes(title="")
                base_layout(fig, height=280)
                st.plotly_chart(fig, use_container_width=True)

            with col_stats:
                st.markdown("**Model summary**")
                st.markdown(f"""
                | | |
                |---|---|
                | Training samples | {len(tu_df)} |
                | Median cost threshold | ${median_cost:.2f} |
                | High-cost users | {int(y.sum())} |
                | Low-cost users | {int((y == 0).sum())} |
                | Estimators | 200 |
                | Top feature | {importance_df.iloc[-1]['Feature']} |
                """)

        st.markdown('<hr class="divider">', unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════
        # 4 · USAGE SPIKE DETECTION (HOURLY)
        # ══════════════════════════════════════════════════════════
        section("Hourly Usage Spike Detection — Isolation Forest")
        st.markdown(
            """
            An **Isolation Forest** model scans the 24-hour activity distribution and
            flags hours whose request volume is anomalously high or low relative to the
            overall pattern.  Anomalous hours are highlighted in red.
            These spikes may indicate scheduled batch jobs, timezone-driven demand
            surges, or unusual overnight activity worth investigating.
            """
        )

        if len(ha_raw) < 8:
            st.warning("Not enough hourly data to run Isolation Forest (need ≥ 8 hours).")
        else:
            ha_df = pd.DataFrame(ha_raw).sort_values("hour").reset_index(drop=True)
            X_hourly = ha_df[["request_count"]].values

            iso = IsolationForest(contamination=0.15, random_state=42)
            ha_df["anomaly"] = iso.fit_predict(X_hourly) == -1

            normal_df = ha_df[~ha_df["anomaly"]]
            spike_df  = ha_df[ ha_df["anomaly"]]

            ha_df["hour_label"] = ha_df["hour"].apply(lambda h: f"{h:02d}:00")

            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=normal_df["hour"].apply(lambda h: f"{h:02d}:00"),
                y=normal_df["request_count"],
                name="Normal",
                marker_color=PALETTE[0],
            ))

            if not spike_df.empty:
                fig.add_trace(go.Bar(
                    x=spike_df["hour"].apply(lambda h: f"{h:02d}:00"),
                    y=spike_df["request_count"],
                    name="Anomalous",
                    marker_color="#e03030",
                ))

            base_layout(fig, height=340)
            fig.update_layout(barmode="overlay")
            fig.update_xaxes(title="Hour of Day (UTC)", categoryorder="array",
                             categoryarray=ha_df["hour_label"].tolist())
            fig.update_yaxes(title="Request Count")
            st.plotly_chart(fig, use_container_width=True)

            n_spikes = ha_df["anomaly"].sum()
            spike_hours = spike_df["hour"].apply(lambda h: f"{h:02d}:00").tolist()
            if spike_hours:
                st.markdown(
                    f"**{n_spikes} anomalous hour(s) detected:** "
                    + ", ".join(f"`{h}`" for h in spike_hours)
                )

    # ── footer (repeat or leave to parent file) ───────────────────
    st.markdown(
        '<div class="footer">Data generated synthetically for demonstration purposes</div>',
        unsafe_allow_html=True,
    )