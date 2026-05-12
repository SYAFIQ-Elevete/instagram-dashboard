import os
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from utils.mock_data import generate_mock_data
from utils.metrics import add_derived_metrics
from utils.instagram_api import InstagramAPI

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Instagram Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
#MainMenu {visibility: hidden;}
footer    {visibility: hidden;}
header    {visibility: hidden;}

/* Overall page */
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* Metric cards */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #ebebeb;
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
[data-testid="stMetricLabel"]       { font-size: 11px; color: #888; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; }
[data-testid="stMetricValue"]       { font-size: 28px; font-weight: 800; color: #111; line-height: 1.2; }
[data-testid="stMetricDelta"]       { font-size: 12px; }

/* Section headers */
.sec { font-size:13px; font-weight:700; color:#888; letter-spacing:0.06em;
       text-transform:uppercase; border-bottom:2px solid #E1306C;
       padding-bottom:5px; margin:24px 0 14px; display:inline-block; }

/* Tab labels */
button[data-baseweb="tab"]          { font-size:13px; font-weight:600; }

/* Account header */
.acct-name  { font-size:22px; font-weight:800; color:#111; }
.acct-sub   { font-size:13px; color:#888; margin-top:2px; }

/* Tier badges inline */
.badge-excellent { color:#00C851; font-weight:700; }
.badge-good      { color:#33b5e5; font-weight:700; }
.badge-average   { color:#ffbb33; font-weight:700; }
.badge-low       { color:#FF4444; font-weight:700; }

/* Demo banner */
.demo-banner {
    background: linear-gradient(90deg,#833AB4,#E1306C,#F77737);
    color: white; border-radius:10px; padding:12px 18px;
    font-size:13px; margin-bottom:16px;
}

/* Post detail panel */
.post-detail {
    background: #f9f9fb;
    border: 1px solid #ebebeb;
    border-radius: 14px;
    padding: 20px 24px;
    margin-top: 12px;
}

/* Dataframe tweaks */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Colour palette ─────────────────────────────────────────────────────────────
C = {
    "REEL": "#E1306C",
    "VIDEO": "#F77737",
    "CAROUSEL_ALBUM": "#405DE6",
    "IMAGE": "#833AB4",
    "good": "#00C851",
    "warn": "#FFD700",
    "bad": "#FF4444",
}
TYPE_LABEL = {"REEL": "Reels", "VIDEO": "Videos", "CAROUSEL_ALBUM": "Carousels", "IMAGE": "Images"}


# ── Auth ───────────────────────────────────────────────────────────────────────
ALLOWED_EMAILS = {
    "syafiq@elevete.com.my",
    "marketing@elevete.com.my",
    "edwin@elevete.com.my",
}

def _check_access() -> str:
    """Returns the logged-in user's email, or stops the app if not authorised."""
    try:
        user = st.experimental_user
        email = getattr(user, "email", None) or ""
    except Exception:
        email = ""

    # On Streamlit Community Cloud, email is populated after Google sign-in.
    # Locally it is empty — allow all for local dev.
    if not email:
        return "local"

    if email not in ALLOWED_EMAILS:
        st.error(
            f"⛔ Access denied.\n\n"
            f"**{email}** is not authorised to view this dashboard.\n\n"
            "Contact syafiq@elevete.com.my to request access."
        )
        st.stop()

    return email


# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def _demo_data() -> pd.DataFrame:
    return add_derived_metrics(generate_mock_data())


@st.cache_data(ttl=3600)
def _api_data(token: str, uid: str) -> tuple[pd.DataFrame, str, dict, dict, pd.DataFrame]:
    api = InstagramAPI(token, uid)
    df = add_derived_metrics(api.fetch_all_posts())
    err = getattr(api, "_last_insights_error", "")
    try:
        user_info = api.get_user_info()
    except Exception:
        user_info = {}
    try:
        demographics = api.get_audience_demographics()
    except Exception:
        demographics = {}
    try:
        follower_growth = api.get_follower_growth(90)
    except Exception:
        follower_growth = pd.DataFrame()
    return df, err, user_info, demographics, follower_growth


# ── Sidebar ────────────────────────────────────────────────────────────────────
def _sidebar(df: pd.DataFrame, user_email: str):
    with st.sidebar:
        st.markdown("## ⚙️ Filters")
        st.markdown("---")

        # Date range
        date_range = st.selectbox(
            "Date range",
            ["Last 7 days", "Last 14 days", "Last 30 days", "Last 60 days", "Last 90 days", "All time"],
            index=2,
        )

        # Content type
        available = df["media_type"].unique().tolist()
        sel_types = st.multiselect(
            "Content type",
            options=available,
            default=available,
            format_func=lambda x: TYPE_LABEL.get(x, x),
        )

        st.markdown("---")
        if st.button("🔄 Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        display = user_email if user_email != "local" else "Local dev"
        st.markdown(
            f"<p style='font-size:11px;color:#aaa;text-align:center;'>{display}</p>",
            unsafe_allow_html=True,
        )

    return date_range, sel_types or available


# ── Filter ─────────────────────────────────────────────────────────────────────
def _filter(df: pd.DataFrame, date_range: str, sel_types: list) -> pd.DataFrame:
    days = {
        "Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30,
        "Last 60 days": 60, "Last 90 days": 90, "All time": 36500,
    }[date_range]
    cutoff = datetime.now() - timedelta(days=days)
    return df[df["timestamp"].dt.tz_localize(None) >= cutoff][df["media_type"].isin(sel_types)].copy()


# ── Tab helpers ────────────────────────────────────────────────────────────────
def _sec(label: str):
    st.markdown(f'<p class="sec">{label}</p>', unsafe_allow_html=True)


def _fmt_num(n) -> str:
    try:
        n = float(n)
        if np.isnan(n):
            return "—"
    except Exception:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(int(n))


def _fmt_pct(v, decimals=2) -> str:
    try:
        if v is None or pd.isna(v) or np.isnan(float(v)):
            return "—"
        return f"{float(v):.{decimals}f}%"
    except Exception:
        return "—"


def _prev_period(df_full: pd.DataFrame, date_range: str) -> pd.DataFrame:
    days = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30, "Last 90 days": 90}.get(date_range, 30)
    curr_start = datetime.now() - timedelta(days=days)
    prev_start = curr_start - timedelta(days=days)
    ts = df_full["timestamp"].dt.tz_localize(None)
    return df_full[(ts >= prev_start) & (ts < curr_start)].copy()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview
# ══════════════════════════════════════════════════════════════════════════════
def tab_overview(df: pd.DataFrame, df_full: pd.DataFrame, date_range: str):
    if df.empty:
        st.warning("No posts match your current filters.")
        return

    prev = _prev_period(df_full, date_range)

    def _dp(curr, prev_val, mode="pct"):
        """Delta string vs previous period."""
        try:
            if prev_val is None or pd.isna(prev_val) or pd.isna(curr):
                return None
            if mode == "pct":
                if prev_val == 0:
                    return None
                return f"{(curr - prev_val) / abs(prev_val) * 100:+.0f}% vs prev period"
            return f"{curr - prev_val:+.2f}pp vs prev period"
        except Exception:
            return None

    # KPI row
    k1, k2, k3, k4, k5 = st.columns(5)
    _er   = df["engagement_rate"].mean()
    _sr   = df["save_rate"].mean()
    _reach = df["reach"].sum()
    _saves = df["saves"].sum()

    _er_p   = prev["engagement_rate"].mean() if not prev.empty else None
    _sr_p   = prev["save_rate"].mean()       if not prev.empty else None
    _reach_p = prev["reach"].sum()           if not prev.empty else None
    _saves_p = prev["saves"].sum()           if not prev.empty else None

    k1.metric("Posts", len(df),
              delta=f"{len(df) - len(prev):+d} vs prev period" if not prev.empty else None)
    k2.metric("Avg Engagement Rate", _fmt_pct(_er),
              delta=_dp(_er, _er_p, "pp"),
              help="(likes + comments + saves + shares) ÷ reach × 100")
    k3.metric("Total Reach", _fmt_num(_reach),
              delta=_dp(_reach, _reach_p))
    k4.metric("Total Saves", _fmt_num(_saves),
              delta=_dp(_saves, _saves_p),
              help="saves ÷ reach × 100 — best algorithmic signal")
    k5.metric("Avg Save Rate", _fmt_pct(_sr),
              delta=_dp(_sr, _sr_p, "pp"),
              help="saves ÷ reach × 100")

    st.markdown("<br>", unsafe_allow_html=True)

    # Trend + mix
    left, right = st.columns([2.2, 1])
    with left:
        _sec("Engagement Rate Over Time")
        df_chart = df.sort_values("timestamp").copy()
        df_chart["Content Type"] = df_chart["media_type"].map(TYPE_LABEL)
        c_map = {v: C[k] for k, v in TYPE_LABEL.items() if k in df_chart["media_type"].values}
        fig = px.line(
            df_chart,
            x="timestamp", y="engagement_rate", color="Content Type",
            color_discrete_map=c_map, markers=True,
            labels={"engagement_rate": "ER%", "timestamp": ""},
            custom_data=["caption_short", "reach", "saves", "performance_score"],
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "ER: %{y:.2f}% · Reach: %{customdata[1]:,.0f}<br>"
                "Saves: %{customdata[2]:,.0f} · Score: %{customdata[3]}/100<extra></extra>"
            )
        )
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=8, b=0), legend_title="")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        _sec("Content Mix")
        mix = df["media_type"].value_counts().reset_index()
        mix.columns = ["Type", "Count"]
        mix["Label"] = mix["Type"].map(TYPE_LABEL)
        fig = px.pie(mix, values="Count", names="Label", color="Label",
                     color_discrete_map={v: C[k] for k, v in TYPE_LABEL.items()},
                     hole=0.55)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=8, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Per-type comparison — horizontal bars, easier to read
    _sec("Average Metrics by Content Type")
    summary = (
        df.groupby("media_type")
        .agg(avg_er=("engagement_rate", "mean"),
             avg_save=("save_rate", "mean"),
             avg_reach=("reach", "mean"),
             avg_share=("share_rate", "mean"))
        .reset_index()
    )
    summary["label"] = summary["media_type"].map(TYPE_LABEL)

    c1, c2, c3, c4 = st.columns(4)
    for col, field, title, suffix in [
        (c1, "avg_er",    "Avg Engagement Rate", "%"),
        (c2, "avg_save",  "Avg Save Rate",        "%"),
        (c3, "avg_share", "Avg Share Rate",        "%"),
        (c4, "avg_reach", "Avg Reach",             ""),
    ]:
        fig = px.bar(summary, x=field, y="label", orientation="h",
                     color="media_type", color_discrete_map=C,
                     text=summary[field].apply(lambda v: _fmt_pct(v) if suffix == "%" else _fmt_num(v)),
                     title=title, labels={"label": "", field: ""})
        fig.update_traces(textposition="outside")
        fig.update_layout(height=200, showlegend=False,
                          margin=dict(l=0, r=40, t=28, b=0),
                          yaxis=dict(autorange="reversed"))
        col.plotly_chart(fig, use_container_width=True)

    # Top posts
    _sec("Top 5 Posts by Performance Score")
    top5 = df.nlargest(5, "performance_score")[
        ["media_type", "timestamp", "caption_short",
         "reach", "likes", "saves", "shares", "engagement_rate", "save_rate", "performance_score"]
    ].copy()
    top5["timestamp"]      = top5["timestamp"].dt.strftime("%b %d")
    top5["media_type"]     = top5["media_type"].map(TYPE_LABEL)
    top5["reach"]          = top5["reach"].apply(_fmt_num)
    top5["likes"]          = top5["likes"].apply(_fmt_num)
    top5["saves"]          = top5["saves"].apply(_fmt_num)
    top5["shares"]         = top5["shares"].apply(_fmt_num)
    top5["engagement_rate"] = top5["engagement_rate"].apply(_fmt_pct)
    top5["save_rate"]      = top5["save_rate"].apply(_fmt_pct)
    top5.columns = ["Type", "Date", "Caption", "Reach", "Likes", "Saves", "Shares", "ER%", "Save Rate", "Score"]
    st.dataframe(top5, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Post Explorer
# ══════════════════════════════════════════════════════════════════════════════
def tab_posts(df: pd.DataFrame):
    if df.empty:
        st.warning("No posts match your current filters.")
        return

    SORT_OPTS = {
        "performance_score": "Performance Score",
        "reach":             "Reach",
        "engagement_rate":   "Engagement Rate",
        "save_rate":         "Save Rate",
        "likes":             "Likes",
        "saves":             "Saves",
        "shares":            "Shares",
        "comments":          "Comments",
        "timestamp":         "Date Posted",
    }
    c1, c2 = st.columns([3, 1])
    sort_by = c1.selectbox("Sort by", list(SORT_OPTS.keys()),
                            format_func=lambda x: SORT_OPTS[x])
    asc = c2.radio("Order", ["Highest first", "Lowest first"],
                   horizontal=True) == "Lowest first"

    sorted_df = df.sort_values(sort_by, ascending=asc).reset_index(drop=True)

    # Build the display table
    TIER_BADGE = {"Excellent": "🟢 Excellent", "Good": "🔵 Good",
                  "Average": "🟡 Average", "Low": "🔴 Low"}
    TYPE_ICON  = {"REEL": "🎬 Reel", "VIDEO": "🎬 Video",
                  "CAROUSEL_ALBUM": "🖼️ Carousel", "IMAGE": "📸 Image"}

    tbl = pd.DataFrame({
        "Tier":      sorted_df["performance_tier"].map(TIER_BADGE),
        "Type":      sorted_df["media_type"].map(TYPE_ICON),
        "Date":      sorted_df["timestamp"].dt.strftime("%b %d, %Y"),
        "Caption":   sorted_df["caption"].str[:60] + "…",
        "Reach":     sorted_df["reach"].astype(int),
        "Likes":     sorted_df["likes"].astype(int),
        "Comments":  sorted_df["comments"].astype(int),
        "Saves":     sorted_df["saves"].astype(int),
        "Shares":    sorted_df["shares"].astype(int),
        "ER%":       sorted_df["engagement_rate"].round(2),
        "Save Rate": sorted_df["save_rate"].round(2),
        "Score":     sorted_df["performance_score"],
    })

    event = st.dataframe(
        tbl,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%d / 100"),
            "Reach":    st.column_config.NumberColumn("Reach",    format="%d"),
            "Likes":    st.column_config.NumberColumn("Likes",    format="%d"),
            "Comments": st.column_config.NumberColumn("Comments", format="%d"),
            "Saves":    st.column_config.NumberColumn("Saves",    format="%d"),
            "Shares":   st.column_config.NumberColumn("Shares",   format="%d"),
            "ER%":      st.column_config.NumberColumn("ER%",      format="%.2f%%"),
            "Save Rate":st.column_config.NumberColumn("Save Rate",format="%.2f%%"),
        },
    )

    # Drill-down panel for selected row
    sel = event.selection.rows if hasattr(event, "selection") else []
    if sel:
        r = sorted_df.iloc[sel[0]]
        st.markdown("<br>", unsafe_allow_html=True)
        _sec(f"Post Detail — {r['timestamp'].strftime('%B %d, %Y')}")

        hdr, lnk = st.columns([6, 1])
        hdr.markdown(f"**{TYPE_ICON.get(r['media_type'], r['media_type'])}** &nbsp;·&nbsp; "
                     f"{TIER_BADGE.get(str(r['performance_tier']), r['performance_tier'])}")
        lnk.markdown(f"[Open on Instagram ↗]({r['permalink']})")

        if r.get("caption"):
            st.markdown(f"> {r['caption'][:300]}")

        st.markdown("")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Reach",     _fmt_num(r["reach"]))
        m2.metric("Likes",     _fmt_num(r["likes"]))
        m3.metric("Comments",  _fmt_num(r["comments"]))
        m4.metric("Saves",     _fmt_num(r["saves"]))
        m5.metric("Shares",    _fmt_num(r["shares"]))
        m6.metric("Score",     f"{r['performance_score']}/100")

        m7, m8, m9, m10 = st.columns(4)
        m7.metric("Engagement Rate", _fmt_pct(r["engagement_rate"]),
                  help="(likes+comments+saves+shares) ÷ reach")
        m8.metric("Save Rate",       _fmt_pct(r["save_rate"]),
                  help="saves ÷ reach — best algorithmic signal")
        m9.metric("Share Rate",      _fmt_pct(r["share_rate"]))
        m10.metric("Comment Rate",   _fmt_pct(r["comment_rate"]))

        if r["media_type"] in ("REEL", "VIDEO") and r["video_views"] > 0:
            st.markdown("---")
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("Video Plays",     _fmt_num(r["video_views"]))
            v2.metric("Play Rate",       _fmt_pct(r.get("play_rate"), 0))
            v3.metric("Avg Watch Time",
                      f"{r['avg_watch_time_sec']:.1f}s"
                      if pd.notna(r.get("avg_watch_time_sec")) else "—")
            v4.metric("Completion Rate", _fmt_pct(r.get("completion_rate"), 0))
    else:
        st.caption("👆 Click any row to see full post details.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Reels
# ══════════════════════════════════════════════════════════════════════════════
def tab_reels(df: pd.DataFrame):
    reels = df[df["media_type"].isin(["REEL", "VIDEO"])].copy()
    if reels.empty:
        st.info("No reels in the selected period.")
        return

    avg_cr = reels["completion_rate"].dropna().mean()
    avg_wt = reels["avg_watch_time_sec"].dropna().mean()
    avg_pr = reels["play_rate"].dropna().mean()
    total_plays = reels["video_views"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Reels", len(reels))
    k2.metric("Avg Completion Rate", f"{avg_cr:.0f}%" if not np.isnan(avg_cr) else "N/A",
              help="Avg watch time ÷ video duration × 100")
    k3.metric("Avg Watch Time", f"{avg_wt:.1f}s" if not np.isnan(avg_wt) else "N/A")
    k4.metric("Total Plays", _fmt_num(total_plays))

    st.markdown("<br>", unsafe_allow_html=True)

    # Completion rate bar
    _sec("Completion Rate per Reel (sorted highest → lowest)")
    rs = reels.sort_values("completion_rate", ascending=False).copy()
    rs["x_label"] = rs["timestamp"].dt.strftime("%b %d") + " — " + rs["caption"].str[:35] + "…"
    fig = px.bar(
        rs, x="x_label", y="completion_rate",
        color="completion_rate",
        color_continuous_scale=["#FF4444", "#FFD700", "#00C851"],
        labels={"x_label": "", "completion_rate": "Completion %"},
        custom_data=["caption_short", "reach", "engagement_rate", "saves"],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Completion: %{y:.0f}%<br>"
            "Reach: %{customdata[1]:,.0f} · ER: %{customdata[2]:.2f}%<br>"
            "Saves: %{customdata[3]:,.0f}<extra></extra>"
        )
    )
    fig.update_layout(height=340, margin=dict(l=0, r=0, t=8, b=100),
                      coloraxis_showscale=False, xaxis_tickangle=-40)
    st.plotly_chart(fig, use_container_width=True)

    # Two scatter plots
    left, right = st.columns(2)
    with left:
        _sec("Watch Time vs Saves")
        sub = reels.dropna(subset=["completion_rate"])
        fig = px.scatter(
            sub, x="completion_rate", y="saves",
            size="reach", color="engagement_rate",
            color_continuous_scale="RdYlGn",
            labels={"completion_rate": "Completion Rate (%)",
                    "saves": "Saves", "engagement_rate": "ER%"},
            custom_data=["caption_short", "reach", "avg_watch_time_sec"],
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Completion: %{x:.0f}% · Saves: %{y:,.0f}<br>"
                "Reach: %{customdata[1]:,.0f} · Watch: %{customdata[2]:.1f}s<extra></extra>"
            )
        )
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=8, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Bubble size = reach. Color = engagement rate (green = higher).")

    with right:
        _sec("Plays vs Engagement Rate")
        fig = px.scatter(
            reels, x="video_views", y="engagement_rate",
            size="saves", color="completion_rate",
            color_continuous_scale="Viridis",
            labels={"video_views": "Video Plays",
                    "engagement_rate": "ER%",
                    "completion_rate": "Completion %"},
            custom_data=["caption_short", "reach", "saves"],
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Plays: %{x:,.0f} · ER: %{y:.2f}%<br>"
                "Saves: %{customdata[2]:,.0f}<extra></extra>"
            )
        )
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=8, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Bubble size = saves. Color = completion rate (bright = higher).")

    # Top vs bottom
    _sec("Top Performers vs Needs Improvement")
    top3 = reels.nlargest(3, "performance_score")
    bot3 = reels.nsmallest(3, "performance_score")

    col_a, col_b = st.columns(2)
    for col, rows, header in [(col_a, top3, "🚀 Top Reels"), (col_b, bot3, "📉 Needs Work")]:
        col.markdown(f"#### {header}")
        for _, r in rows.iterrows():
            with col.expander(
                f"Score {r['performance_score']} · {r['timestamp'].strftime('%b %d')} · "
                f"{r['caption'][:55]}…"
            ):
                x1, x2, x3 = st.columns(3)
                cr = r.get("completion_rate")
                x1.metric("Completion", f"{cr:.0f}%" if not pd.isna(cr) else "—")
                x2.metric("Save Rate", f"{r['save_rate']:.2f}%")
                x3.metric("Reach", _fmt_num(r["reach"]))

    with st.expander("📖 How to read Reel metrics", expanded=False):
        st.markdown("""
**Completion Rate** — What % of viewers finish the reel.
- **>60%** = strong hook + good pacing
- **30–60%** = average
- **<30%** = viewers drop off early — fix the hook or tighten the edit

**Play Rate** (plays ÷ reach) — Does the cover frame / thumbnail make people click play?
A low play rate = great reach, but the visual isn't compelling enough.

**Saves** — Clearest signal of value. Reels with high saves get pushed by the algorithm.

**Shares** — People share things that are funny, surprising, or deeply relatable.

**What to try if completion is low:**
- Lead with your most striking visual or statement in the first 2 seconds
- Add on-screen text — most people watch muted
- Cut ruthlessly: 15–25s often outperforms 60s
- End on a loop-able moment to encourage rewatches
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Carousels & Images
# ══════════════════════════════════════════════════════════════════════════════
def tab_static(df: pd.DataFrame):
    cars = df[df["media_type"] == "CAROUSEL_ALBUM"].copy()
    imgs = df[df["media_type"] == "IMAGE"].copy()

    if cars.empty and imgs.empty:
        st.info("No static content in the selected period.")
        return

    _sec("Carousel vs Image — Average Metrics")

    compare_rows = []
    for label, sub in [("Carousel", cars), ("Image", imgs)]:
        if not sub.empty:
            compare_rows.append({
                "Type": label,
                "Engagement Rate (%)": sub["engagement_rate"].mean(),
                "Save Rate (%)": sub["save_rate"].mean(),
                "Share Rate (%)": sub["share_rate"].mean(),
                "Comment Rate (%)": sub["comment_rate"].mean(),
            })

    if compare_rows:
        cmp = pd.DataFrame(compare_rows)
        metrics = ["Engagement Rate (%)", "Save Rate (%)", "Share Rate (%)", "Comment Rate (%)"]
        fig = go.Figure()
        pal = {"Carousel": C["CAROUSEL_ALBUM"], "Image": C["IMAGE"]}
        for _, row in cmp.iterrows():
            fig.add_trace(go.Bar(
                name=row["Type"],
                x=metrics,
                y=[row[m] for m in metrics],
                marker_color=pal[row["Type"]],
            ))
        fig.update_layout(barmode="group", height=300,
                          margin=dict(l=0, r=0, t=8, b=0),
                          legend_title="", yaxis_title="%")
        st.plotly_chart(fig, use_container_width=True)

    # Save-rate callout
    if not cars.empty and not imgs.empty:
        diff = cars["save_rate"].mean() - imgs["save_rate"].mean()
        winner = "Carousels" if diff > 0 else "Images"
        st.info(
            f"💾 **{winner} have a {abs(diff):.1f}pp higher save rate** "
            f"({cars['save_rate'].mean():.2f}% carousels vs {imgs['save_rate'].mean():.2f}% images)."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    def _post_list(col, subset, header):
        col.markdown(f"#### {header}")
        if subset.empty:
            col.info("No posts.")
            return
        for _, r in subset.nlargest(5, "performance_score").iterrows():
            with col.expander(
                f"Score {r['performance_score']} · {r['timestamp'].strftime('%b %d')} · "
                f"{r['caption'][:55]}…"
            ):
                x1, x2, x3 = st.columns(3)
                x1.metric("Reach", _fmt_num(r["reach"]))
                x2.metric("Save Rate", f"{r['save_rate']:.2f}%")
                x3.metric("ER", f"{r['engagement_rate']:.2f}%")
                st.markdown(
                    f"Likes {_fmt_num(r['likes'])}  ·  Comments {_fmt_num(r['comments'])}"
                    f"  ·  Saves {_fmt_num(r['saves'])}  ·  Shares {_fmt_num(r['shares'])}"
                )

    _post_list(col_a, cars, "🖼️ Top Carousels")
    _post_list(col_b, imgs, "📸 Top Images")

    with st.expander("📖 How to read Carousel & Image metrics", expanded=False):
        st.markdown("""
**Save Rate** — The headline metric for static content. High saves = reference-worthy content.
Aim for >3% for carousels, >1.5% for images.

**Comment Rate** — Driven by strong opinions, questions in captions, or surprising data.

**Share Rate** — Relatable content, quotes, or memes share well.

**Carousel tips:**
- Slide 1 = your ad creative / hook — treat it like a thumbnail
- One idea per slide, keep it scannable
- End with a clear CTA ("save this", "send to a friend who needs this")
- "How-to" and "X things about Y" reliably drive saves

**Image tips:**
- The visual stops the scroll — that's the job
- Caption does the heavy lifting: ask a question or share a hot take
- Aesthetic posts can lift profile visits even with lower direct engagement
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Strategy
# ══════════════════════════════════════════════════════════════════════════════
def tab_strategy(df: pd.DataFrame):
    if df.empty:
        st.warning("No data to analyse.")
        return

    # Posting-time heatmap
    _sec("When to Post — Engagement Rate Heatmap")
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heat = (
        df.groupby(["day_of_week", "hour_posted"])["engagement_rate"]
        .mean()
        .reset_index()
        .pivot_table(index="day_of_week", columns="hour_posted", values="engagement_rate")
        .reindex([d for d in day_order if d in df["day_of_week"].unique()])
    )
    fig = px.imshow(
        heat,
        labels=dict(x="Hour of day", y="Day", color="Avg ER%"),
        color_continuous_scale="RdYlGn",
        aspect="auto",
    )
    fig.update_layout(height=260, margin=dict(l=0, r=0, t=8, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Green = higher avg engagement rate. More posts = more reliable. Based on your publish times.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Quadrant + breakdown
    left, right = st.columns(2)
    with left:
        _sec("Content Quadrant — Value vs Virality")
        med_save = df["save_rate"].median()
        med_share = df["share_rate"].median()

        fig = px.scatter(
            df, x="share_rate", y="save_rate",
            color="media_type", color_discrete_map=C,
            size="reach",
            labels={"share_rate": "Share Rate (%) → Virality",
                    "save_rate": "Save Rate (%) → Value",
                    "media_type": ""},
            custom_data=["caption_short", "engagement_rate", "performance_score"],
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Save rate: %{y:.2f}% · Share rate: %{x:.2f}%<br>"
                "ER: %{customdata[1]:.2f}% · Score: %{customdata[2]}/100<extra></extra>"
            )
        )
        fig.add_hline(y=med_save, line_dash="dash", line_color="#ccc")
        fig.add_vline(x=med_share, line_dash="dash", line_color="#ccc")

        max_s = df["share_rate"].max()
        max_v = df["save_rate"].max()
        min_s = df["share_rate"].min()
        min_v = df["save_rate"].min()
        for txt, xp, yp in [
            ("🌟 Viral &\nValuable",   max_s * 0.80, max_v * 0.95),
            ("💎 Educational",          min_s + 0.02, max_v * 0.95),
            ("🔥 Trending",             max_s * 0.80, min_v + 0.02),
            ("🔄 Rethink",              min_s + 0.02, min_v + 0.02),
        ]:
            fig.add_annotation(x=xp, y=yp, text=txt, showarrow=False,
                                font=dict(size=10), align="center")
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=8, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Bubble size = reach. Aim to move content toward the top-right quadrant.")

    with right:
        _sec("Engagement Breakdown by Content Type")
        bd = (
            df.groupby("media_type")
            .agg(Likes=("likes","sum"), Comments=("comments","sum"),
                 Saves=("saves","sum"), Shares=("shares","sum"))
            .reset_index()
        )
        bd["label"] = bd["media_type"].map(TYPE_LABEL)
        melt = bd.melt(id_vars=["media_type","label"], var_name="Metric", value_name="Total")
        fig = px.bar(melt, x="label", y="Total", color="Metric",
                     barmode="stack",
                     color_discrete_map={
                         "Likes": "#E1306C", "Comments": "#405DE6",
                         "Saves": "#F77737", "Shares": "#833AB4"},
                     labels={"label": "", "Total": "Total interactions"})
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=8, b=0), legend_title="")
        st.plotly_chart(fig, use_container_width=True)

    # Auto insights
    _sec("Automated Insights")
    for ins in _auto_insights(df):
        with st.expander(f"{ins['icon']}  {ins['title']}", expanded=True):
            st.markdown(ins["body"])
            if ins.get("action"):
                st.markdown(f"**→ Experiment:** {ins['action']}")

    # Experiment table
    _sec("Experiment Ideas")
    st.markdown("""
| Experiment | What to test | How to measure |
|---|---|---|
| **Hook A/B** | Same content, 2 different first-3-second hooks | Completion rate + saves |
| **Caption length** | Short punchy vs long storytelling | Comment rate + saves |
| **Posting time** | Your slot vs the heatmap's best cell | Reach + ER in first 24h |
| **CTA placement** | CTA at the start vs the end | Comment rate + DM volume |
| **Format swap** | High-save carousel topic → Reel | Compare reach + saves |
| **Cover frame** | Text-first vs visual-first Reel cover | Play rate (plays ÷ reach) |
| **Reel duration** | 15-20s vs 45-60s on the same topic | Completion rate |
    """)


def _auto_insights(df: pd.DataFrame) -> list:
    out = []

    # Best content type
    if df["media_type"].nunique() > 1:
        type_er = df.groupby("media_type")["engagement_rate"].mean().dropna()
        if type_er.empty:
            best_type = None
        else:
            best_type = type_er.idxmax()
            best_er = type_er.max()
    else:
        best_type = None

    if best_type is not None:
        out.append({
            "icon": "🏆",
            "title": f"{TYPE_LABEL[best_type]} have your highest engagement",
            "body": (
                f"**{TYPE_LABEL[best_type]}** average **{best_er:.2f}% ER** — "
                "the highest of any content type in this period."
            ),
            "action": f"Post more {TYPE_LABEL[best_type]} and analyse which specific topics pull the most saves.",
        })

    # Completion rate
    reels = df[df["media_type"] == "REEL"]
    if not reels.empty:
        cr = reels["completion_rate"].dropna().mean()
        if not np.isnan(cr):
            if cr < 35:
                out.append({
                    "icon": "⚠️",
                    "title": f"Reel completion is low ({cr:.0f}%)",
                    "body": "Most viewers drop off before finishing. This signals a weak hook or mid-reel pacing issue.",
                    "action": "Lead with your most surprising line. Cut the first 2–3 seconds if they're slow.",
                })
            elif cr > 60:
                out.append({
                    "icon": "✅",
                    "title": f"Strong reel completion ({cr:.0f}%)",
                    "body": "Viewers are watching to the end — a strong signal the algorithm responds to.",
                    "action": "Keep the same pacing formula. Test slightly longer reels (45–60s) and track if it holds.",
                })

    # Save rate
    avg_save = df["save_rate"].mean()
    if pd.isna(avg_save):
        avg_save = 0.0
    if avg_save < 1.5:
        out.append({
            "icon": "💾",
            "title": f"Save rate is below average ({avg_save:.2f}%)",
            "body": "Content is engaging but not reference-worthy enough to save. Saves are the strongest algorithmic signal.",
            "action": "Add 'save this for later' CTAs. Create more checklist/how-to content that earns revisits.",
        })
    elif avg_save > 4.0:
        out.append({
            "icon": "💾",
            "title": f"Excellent save rate ({avg_save:.2f}%)",
            "body": "Your audience finds your content genuinely valuable. The algorithm rewards this consistently.",
            "action": "Double down on the content categories driving the most saves.",
        })

    # Best posting day
    day_er = df.groupby("day_of_week")["engagement_rate"].mean().dropna()
    if not day_er.empty:
        best_day = day_er.idxmax()
        best_day_er = day_er.max()
        out.append({
            "icon": "📅",
            "title": f"{best_day} is your strongest posting day",
            "body": f"Posts on **{best_day}** average **{best_day_er:.2f}% ER** — highest of any day in this period.",
            "action": f"Schedule your most important creative for {best_day}.",
        })

    # Share rate
    if df["share_rate"].mean() < 0.5:
        out.append({
            "icon": "📤",
            "title": f"Low share rate ({df['share_rate'].mean():.2f}%)",
            "body": "Very little content is being sent via DM or shared to Stories. Shares expand your reach beyond existing followers.",
            "action": "Lean into relatable, surprising, or polarising content. Memes, hot takes, and 'this is so me' posts share well.",
        })

    if not out:
        out.append({
            "icon": "📊",
            "title": "Keep collecting data",
            "body": "Post at least 15–20 pieces of content to unlock strong pattern insights.",
            "action": "",
        })

    return out


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Audience
# ══════════════════════════════════════════════════════════════════════════════
def tab_audience(demographics: dict, follower_growth: pd.DataFrame, user_info: dict):
    followers_total = user_info.get("followers_count", 0)

    # ── Follower growth ────────────────────────────────────────────────────────
    _sec("Follower Growth (Last 90 Days)")
    if not follower_growth.empty:
        start_val = follower_growth["followers"].iloc[0]
        end_val   = follower_growth["followers"].iloc[-1]
        net_gain  = end_val - start_val
        pct_gain  = (net_gain / start_val * 100) if start_val else 0

        k1, k2, k3 = st.columns(3)
        k1.metric("Current Followers", _fmt_num(followers_total))
        k2.metric("90-Day Net Growth",  f"{net_gain:+,}",
                  delta=f"{pct_gain:+.1f}%")
        k3.metric("Avg Growth / Day",
                  f"{net_gain / max(len(follower_growth), 1):+.0f}")

        st.markdown("<br>", unsafe_allow_html=True)

        fig = px.area(
            follower_growth, x="date", y="followers",
            labels={"date": "", "followers": "Followers"},
            color_discrete_sequence=["#E1306C"],
        )
        fig.update_traces(fill="tozeroy", fillcolor="rgba(225,48,108,0.08)",
                          line_color="#E1306C")
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=8, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Follower growth data is not available for this account. "
                "Make sure your token has the `instagram_manage_insights` permission.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Demographics ───────────────────────────────────────────────────────────
    if not demographics:
        st.info("Audience demographics require `instagram_manage_insights` permission "
                "and a Business/Creator account with sufficient followers.")
        return

    # Gender + Age
    gender_age = demographics.get("audience_gender_age", {})
    if gender_age:
        _sec("Audience — Age & Gender")

        rows = []
        for key, pct in gender_age.items():
            parts = key.split(".")
            if len(parts) == 2:
                rows.append({"Gender": "Male" if parts[0] == "M" else
                             "Female" if parts[0] == "F" else "Other",
                             "Age": parts[1], "Pct": round(pct * 100, 1)})
        age_df = pd.DataFrame(rows)

        left, right = st.columns(2)

        with left:
            gender_totals = age_df.groupby("Gender")["Pct"].sum().reset_index()
            fig = px.pie(gender_totals, values="Pct", names="Gender", hole=0.6,
                         color_discrete_sequence=["#E1306C", "#405DE6", "#aaa"])
            fig.update_traces(textinfo="percent+label", textposition="outside")
            fig.update_layout(height=280, showlegend=False,
                              margin=dict(l=0, r=0, t=8, b=0),
                              annotations=[dict(text="Gender", x=0.5, y=0.5,
                                               font_size=13, showarrow=False)])
            left.plotly_chart(fig, use_container_width=True)

        with right:
            age_totals = age_df.groupby("Age")["Pct"].sum().reset_index().sort_values("Age")
            fig = px.bar(age_totals, x="Age", y="Pct",
                         color_discrete_sequence=["#E1306C"],
                         labels={"Age": "Age group", "Pct": "% of audience"},
                         text=age_totals["Pct"].apply(lambda v: f"{v:.1f}%"))
            fig.update_traces(textposition="outside")
            fig.update_layout(height=280, margin=dict(l=0, r=0, t=8, b=0))
            right.plotly_chart(fig, use_container_width=True)

        # Gender × Age heatmap
        if not age_df.empty:
            pivot = age_df.pivot_table(index="Gender", columns="Age",
                                       values="Pct", aggfunc="sum").fillna(0)
            fig = px.imshow(pivot, text_auto=".1f",
                            color_continuous_scale="RdPu",
                            labels=dict(color="% audience"),
                            aspect="auto")
            fig.update_layout(height=200, margin=dict(l=0, r=0, t=8, b=0))
            st.plotly_chart(fig, use_container_width=True)

    # City breakdown
    city_data = demographics.get("audience_city", {})
    if city_data:
        _sec("Top Cities")
        city_df = (pd.DataFrame(list(city_data.items()), columns=["City", "Pct"])
                   .assign(Pct=lambda d: (d["Pct"] * 100).round(1))
                   .nlargest(10, "Pct"))
        fig = px.bar(city_df, x="Pct", y="City", orientation="h",
                     color_discrete_sequence=["#405DE6"],
                     text=city_df["Pct"].apply(lambda v: f"{v:.1f}%"),
                     labels={"Pct": "% of audience", "City": ""})
        fig.update_traces(textposition="outside")
        fig.update_layout(height=340, margin=dict(l=0, r=40, t=8, b=0),
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    # Country breakdown
    country_data = demographics.get("audience_country", {})
    if country_data:
        _sec("Top Countries")
        country_df = (pd.DataFrame(list(country_data.items()), columns=["Country", "Pct"])
                      .assign(Pct=lambda d: (d["Pct"] * 100).round(1))
                      .nlargest(10, "Pct"))
        left, right = st.columns(2)
        with left:
            fig = px.bar(country_df, x="Pct", y="Country", orientation="h",
                         color_discrete_sequence=["#833AB4"],
                         text=country_df["Pct"].apply(lambda v: f"{v:.1f}%"),
                         labels={"Pct": "% of audience", "Country": ""})
            fig.update_traces(textposition="outside")
            fig.update_layout(height=340, margin=dict(l=0, r=40, t=8, b=0),
                              yaxis=dict(autorange="reversed"))
            left.plotly_chart(fig, use_container_width=True)
        with right:
            fig = px.pie(country_df, values="Pct", names="Country", hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_traces(textinfo="percent+label", textposition="outside")
            fig.update_layout(height=340, showlegend=False,
                              margin=dict(l=0, r=0, t=8, b=0))
            right.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def _load_data() -> tuple[pd.DataFrame, bool, dict, dict, pd.DataFrame]:
    """Load real data from secrets if configured, else fall back to demo."""
    try:
        tok = st.secrets["INSTAGRAM_ACCESS_TOKEN"]
        uid = st.secrets["INSTAGRAM_USER_ID"]
    except Exception:
        return _demo_data(), False, {}, {}, pd.DataFrame()

    try:
        df, ins_err, user_info, demographics, follower_growth = _api_data(tok, uid)
        if df.empty:
            st.warning("API connected but returned no posts. Check your Instagram User ID.")
            return _demo_data(), False, {}, {}, pd.DataFrame()
        if ins_err:
            st.warning(f"Insights API error (some metrics may be 0): {ins_err}")
        return df, True, user_info, demographics, follower_growth
    except Exception as e:
        st.error(f"Instagram API error: {e}")
        return _demo_data(), False, {}, {}, pd.DataFrame()


def main():
    user_email = _check_access()

    df_raw, using_api, user_info, demographics, follower_growth = _load_data()
    date_range, sel_types = _sidebar(df_raw, user_email)
    df = _filter(df_raw, date_range, sel_types)

    # Account header
    if using_api and user_info:
        pic  = user_info.get("profile_picture_url", "")
        name = user_info.get("name", "")
        uname = user_info.get("username", "")
        followers = user_info.get("followers_count", 0)
        media_ct  = user_info.get("media_count", 0)
        h_pic, h_info = st.columns([0.06, 1])
        if pic:
            h_pic.image(pic, width=56)
        h_info.markdown(
            f"<div style='padding-top:6px'>"
            f"<span style='font-size:20px;font-weight:700;'>@{uname}</span>"
            f"&nbsp;&nbsp;<span style='color:#666;font-size:14px;'>{name}</span><br>"
            f"<span style='color:#888;font-size:13px;'>"
            f"👥 {_fmt_num(followers)} followers &nbsp;·&nbsp; 📸 {media_ct} posts total"
            f"</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.markdown(
            "<h1 style='margin-bottom:2px;'>📊 Instagram Analytics Dashboard</h1>",
            unsafe_allow_html=True,
        )

    if not using_api:
        st.markdown(
            '<div class="demo-banner">🔮  <strong>Demo mode</strong> — '
            "add your Instagram API credentials to Streamlit secrets to see real data.</div>",
            unsafe_allow_html=True,
        )

    type_names = [TYPE_LABEL.get(t, t) for t in sel_types]
    st.markdown(
        f"**{len(df)} posts** · {date_range} · {', '.join(type_names)}",
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "📈  Overview",
        "🔍  Post Explorer",
        "🎬  Reels",
        "🖼️  Carousels & Images",
        "🧠  Strategy",
        "👥  Audience",
    ])
    with t1: tab_overview(df, df_raw, date_range)
    with t2: tab_posts(df)
    with t3: tab_reels(df)
    with t4: tab_static(df)
    with t5: tab_strategy(df)
    with t6: tab_audience(demographics, follower_growth, user_info)


if __name__ == "__main__":
    main()
