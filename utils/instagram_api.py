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
from datetime import datetime, timedelta

BASE = "https://graph.facebook.com/v19.0"


class InstagramAPI:
    def __init__(self, access_token: str, user_id: str):
        self.token = access_token
        self.user_id = user_id

    def _get(self, path: str, params: dict = None) -> dict:
        p = dict(params or {})
        p["access_token"] = self.token
        r = requests.get(f"{BASE}/{path}", params=p, timeout=15)
        if not r.ok:
            try:
                detail = r.json()
            except Exception:
                detail = r.text
            raise requests.HTTPError(
                f"{r.status_code} {r.reason} — {detail}", response=r
            )
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
            "id,caption,media_type,permalink,timestamp,"
            "like_count,comments_count"
        )
        return self._paginate(
            f"{self.user_id}/media",
            {"fields": fields, "limit": 50},
            limit=limit,
        )

    def get_media_insights(self, media_id: str, media_type: str) -> dict:
        # impressions deprecated from v22+; request lifetime period for correct totals
        if media_type == "REEL":
            metrics = "reach,saved,shares,plays,ig_reels_avg_watch_time,ig_reels_video_view_total_time"
        elif media_type == "VIDEO":
            # VIDEO may actually be a Reel served in old format — try plays too
            metrics = "reach,saved,shares,plays"
        else:
            metrics = "reach,saved,shares"

        try:
            data = self._get(f"{media_id}/insights", {"metric": metrics, "period": "lifetime"})
            result = {}
            for item in data.get("data", []):
                name = item.get("name")
                if "value" in item:
                    result[name] = item["value"]
                elif "values" in item and item["values"]:
                    # sum all values to get the lifetime total across all periods
                    result[name] = sum(v.get("value", 0) for v in item["values"])
            return result
        except Exception as e:
            # some metrics may not be supported — retry with minimal set
            try:
                data = self._get(f"{media_id}/insights", {"metric": "reach,saved,shares", "period": "lifetime"})
                result = {}
                for item in data.get("data", []):
                    name = item.get("name")
                    if "value" in item:
                        result[name] = item["value"]
                    elif "values" in item and item["values"]:
                        result[name] = sum(v.get("value", 0) for v in item["values"])
                return result
            except Exception as e2:
                self._last_insights_error = str(e2)
                return {}

    def get_follower_growth(self, days: int = 90) -> pd.DataFrame:
        since = int((datetime.now() - timedelta(days=days)).timestamp())
        until = int(datetime.now().timestamp())
        try:
            data = self._get(f"{self.user_id}/insights", {
                "metric": "follower_count",
                "period": "day",
                "since": since,
                "until": until,
            })
            rows = []
            for item in data.get("data", []):
                for v in item.get("values", []):
                    rows.append({
                        "date": pd.to_datetime(v["end_time"]).tz_localize(None).normalize(),
                        "followers": v["value"],
                    })
            return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        except Exception:
            return pd.DataFrame()

    def get_audience_demographics(self) -> dict:
        try:
            data = self._get(f"{self.user_id}/insights", {
                "metric": "audience_gender_age,audience_city,audience_country",
                "period": "lifetime",
            })
            result = {}
            for item in data.get("data", []):
                name = item.get("name")
                val = item.get("value") or (item.get("values") or [{}])[-1].get("value", {})
                result[name] = val
            return result
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
                "duration_seconds": 0,
                "impressions": ins.get("reach", 0),
                "reach": ins.get("reach", 0),
                "likes": m.get("like_count", 0),
                "comments": m.get("comments_count", 0),
                "saves": ins.get("saved", 0),
                "shares": ins.get("shares", 0),
                "video_views": ins.get("plays", ins.get("video_views", 0)),
                "avg_watch_time_ms": ins.get("ig_reels_avg_watch_time", 0),
                "total_watch_time_ms": ins.get("ig_reels_video_view_total_time", 0),
                "media_url": m.get("media_url", ""),
                "thumbnail_url": m.get("thumbnail_url", ""),
            })

        bar.empty()
        return pd.DataFrame(posts)
