"""
Instagram Graph API client.

Requirements:
  - Instagram Business or Creator account linked to a Facebook Page
  - A Meta Developer App in Live mode
  - Long-lived access token with permissions:
      instagram_basic, instagram_manage_insights, pages_read_engagement
  - The Instagram User ID (not Facebook user ID)

To get a long-lived token: exchange a short-lived token via
  GET https://graph.instagram.com/access_token
      ?grant_type=ig_exchange_token
      &client_id={app-id}
      &client_secret={app-secret}
      &access_token={short-lived-token}
"""

import requests
import pandas as pd
from datetime import datetime

BASE = "https://graph.facebook.com/v19.0"


class InstagramAPI:
    def __init__(self, access_token: str, user_id: str):
        self.token = access_token
        self.user_id = user_id

    def _get(self, path: str, params: dict = None) -> dict:
        p = dict(params or {})
        p["access_token"] = self.token
        r = requests.get(f"{BASE}/{path}", params=p, timeout=15)
        r.raise_for_status()
        return r.json()

    def get_user_info(self) -> dict:
        return self._get(
            self.user_id,
            {"fields": "id,name,username,followers_count,media_count,profile_picture_url"},
        )

    def _paginate(self, path: str, params: dict, limit: int = 100) -> list:
        items = []
        data = self._get(path, params)
        items.extend(data.get("data", []))
        while len(items) < limit:
            nxt = data.get("paging", {}).get("next")
            if not nxt:
                break
            data = requests.get(nxt, timeout=15).json()
            items.extend(data.get("data", []))
        return items[:limit]

    def get_media_list(self, limit: int = 100) -> list:
        fields = (
            "id,caption,media_type,media_url,permalink,timestamp,"
            "like_count,comments_count,thumbnail_url"
        )
        return self._paginate(
            f"{self.user_id}/media",
            {"fields": fields, "limit": 50},
            limit=limit,
        )

    def get_media_insights(self, media_id: str, media_type: str) -> dict:
        if media_type == "REEL":
            metrics = "impressions,reach,saved,shares,plays,ig_reels_avg_watch_time,ig_reels_video_view_total_time"
        elif media_type == "VIDEO":
            metrics = "impressions,reach,saved,shares,video_views"
        else:
            metrics = "impressions,reach,saved,shares"

        try:
            data = self._get(f"{media_id}/insights", {"metric": metrics})
            return {item["name"]: item["value"] for item in data.get("data", [])}
        except Exception:
            return {}

    def fetch_all_posts(self) -> pd.DataFrame:
        import streamlit as st

        media_list = self.get_media_list()
        if not media_list:
            return pd.DataFrame()

        posts = []
        bar = st.progress(0, text="Fetching post insights…")

        for i, m in enumerate(media_list):
            bar.progress((i + 1) / len(media_list), text=f"Post {i + 1}/{len(media_list)}")
            ins = self.get_media_insights(m["id"], m.get("media_type", "IMAGE"))
            caption = m.get("caption", "")
            ts_raw = m.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                ts = datetime.now()

            posts.append({
                "id": m["id"],
                "timestamp": ts,
                "media_type": m.get("media_type", "IMAGE"),
                "caption": caption,
                "permalink": m.get("permalink", ""),
                "hashtags": [w[1:] for w in caption.split() if w.startswith("#")],
                "duration_seconds": 0,  # not exposed by API
                "impressions": ins.get("impressions", 0),
                "reach": ins.get("reach", 0),
                "likes": m.get("like_count", 0),
                "comments": m.get("comments_count", 0),
                "saves": ins.get("saved", 0),
                "shares": ins.get("shares", 0),
                "video_views": ins.get("plays", ins.get("video_views", 0)),
                "avg_watch_time_ms": ins.get("ig_reels_avg_watch_time", 0),
                "total_watch_time_ms": ins.get("ig_reels_video_view_total_time", 0),
            })

        bar.empty()
        return pd.DataFrame(posts)
