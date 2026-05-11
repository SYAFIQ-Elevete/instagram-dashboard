import pandas as pd
import numpy as np


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    safe_reach = df["reach"].replace(0, np.nan)

    df["engagement"] = df["likes"] + df["comments"] + df["saves"] + df["shares"]
    df["engagement_rate"] = (df["engagement"] / safe_reach * 100).round(2)
    df["save_rate"] = (df["saves"] / safe_reach * 100).round(2)
    df["share_rate"] = (df["shares"] / safe_reach * 100).round(2)
    df["comment_rate"] = (df["comments"] / safe_reach * 100).round(2)
    df["like_rate"] = (df["likes"] / safe_reach * 100).round(2)
    df["reach_rate"] = (df["reach"] / df["impressions"].replace(0, np.nan) * 100).round(1)

    # Reel-specific
    df["completion_rate"] = np.nan
    df["avg_watch_time_sec"] = np.nan
    df["play_rate"] = np.nan

    reel_mask = df["media_type"] == "REEL"
    if reel_mask.any():
        dur_ms = df.loc[reel_mask, "duration_seconds"] * 1000
        df.loc[reel_mask, "avg_watch_time_sec"] = (df.loc[reel_mask, "avg_watch_time_ms"] / 1000).round(1)
        df.loc[reel_mask, "completion_rate"] = (
            df.loc[reel_mask, "avg_watch_time_ms"] / dur_ms.replace(0, np.nan) * 100
        ).clip(0, 100).round(1)
        df.loc[reel_mask, "play_rate"] = (
            df.loc[reel_mask, "video_views"] / df.loc[reel_mask, "reach"].replace(0, np.nan) * 100
        ).round(1)

    # Composite performance score (0–100) weighted by what matters most
    def _norm(s: pd.Series) -> pd.Series:
        lo, hi = s.min(), s.max()
        return pd.Series(50.0, index=s.index) if hi == lo else (s - lo) / (hi - lo) * 100

    df["performance_score"] = (
        _norm(df["save_rate"].fillna(0)) * 0.35
        + _norm(df["engagement_rate"].fillna(0)) * 0.30
        + _norm(df["share_rate"].fillna(0)) * 0.20
        + _norm(df["comment_rate"].fillna(0)) * 0.15
    ).round(0).astype(int)

    df["performance_tier"] = pd.cut(
        df["performance_score"],
        bins=[0, 25, 50, 75, 101],
        labels=["Low", "Average", "Good", "Excellent"],
        include_lowest=True,
    )

    df["day_of_week"] = df["timestamp"].dt.day_name()
    df["hour_posted"] = df["timestamp"].dt.hour
    df["date"] = df["timestamp"].dt.date
    df["caption_short"] = df["caption"].str[:80] + "…"

    return df
