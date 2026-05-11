import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random


CAPTIONS = {
    "REEL": [
        "3 content mistakes killing your engagement (and what actually works) #contentcreator #socialmediatips",
        "POV: you finally crack the algorithm 👀 #reels #viral #growyourinstagram",
        "Day in the life of a social media manager 🎥 #dayinthelife #smm #behindthescenes",
        "The hook formula that grew our client by 2k in 7 days #instagramtips #growth",
        "Stop making this mistake in your reels → link in bio for the full breakdown",
        "Client expectations vs reality 😂 #agencylife #contentcreator #relatable",
        "How I batch a full month of content in one day ✨ #productivity #contentbatch",
        "The reel format that gets 10x more saves 🔖 #reelstips #savethis",
        "Before vs After: full account audit results (shocking) #socialmediamarketing",
        "Unpopular opinion: posting time matters less than THIS 👇 #algorithm",
        "I tested 30 different hooks so you don't have to. Here's what worked #experiment",
        "The only content calendar template you'll ever need 📅 #contentplanning",
        "Why your reach dropped and exactly how to fix it #instagramalgorithm",
        "Watch time hack that no one talks about 👇 #reelstrategy #engagement",
        "How we took this account from 1k to 10k in 60 days #casestudy",
    ],
    "CAROUSEL_ALBUM": [
        "5 things your analytics are telling you (that you're ignoring) → save this",
        "The content pillars framework that tripled our client's engagement ↓",
        "Complete guide: Instagram algorithm 2024 — what actually works now",
        "10 caption formulas that drive comments 💬 (save for later)",
        "Our exact process for 30 days of content in 3 hours → swipe →",
        "Why your reels aren't growing and the exact fix (6 slides) →",
        "Engagement rate calculator + what's actually good in your niche",
        "The creative brief we use for every single client project",
        "Instagram audit checklist: 15 things to fix right now",
        "How to repurpose 1 idea into 10 pieces of content →",
        "The save-worthy content formula (swipe to see all 8 types)",
        "Brand voice guide: how to sound consistent across every post",
    ],
    "IMAGE": [
        "Grateful for another month helping brands show up authentically ✨",
        "New brand collab dropping this week — so excited to share this 🎉",
        "Quote of the week: 'Content is king but consistency is the kingdom'",
        "Studio setup tour 📸 where all the magic happens",
        "Team photo from yesterday's content shoot 🎬 #teamwork",
        "New service offering live now — DM 'INFO' to learn more",
        "Behind the scenes from today's shoot 📷 #bts",
        "Throwback to our first client campaign 🙏 how far we've come",
    ],
}


def generate_mock_data(days: int = 90, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    random.seed(seed)

    media_types = ["REEL"] * 14 + ["CAROUSEL_ALBUM"] * 11 + ["IMAGE"] * 8
    random.shuffle(media_types)
    n = len(media_types)

    now = datetime.now()
    timestamps = sorted(
        [now - timedelta(days=random.uniform(1, days)) for _ in range(n)],
        reverse=True,
    )

    cap_counters = {k: 0 for k in CAPTIONS}
    posts = []

    for i, (ts, media_type) in enumerate(zip(timestamps, media_types)):
        cap_list = CAPTIONS[media_type]
        caption = cap_list[cap_counters[media_type] % len(cap_list)]
        cap_counters[media_type] += 1

        # More recent posts had slightly higher reach (account growing)
        growth_factor = 1 + (0.4 * (1 - i / n))

        if media_type == "REEL":
            base_reach = int(np.random.lognormal(8.5, 0.75) * growth_factor)
            impressions = int(base_reach * np.random.uniform(1.15, 1.9))
            likes = int(base_reach * np.random.uniform(0.035, 0.13))
            comments = int(base_reach * np.random.uniform(0.004, 0.020))
            saves = int(base_reach * np.random.uniform(0.018, 0.09))
            shares = int(base_reach * np.random.uniform(0.010, 0.065))
            video_views = int(base_reach * np.random.uniform(0.55, 1.15))
            duration_s = random.choice([15, 20, 25, 30, 45, 60])
            avg_watch_ms = int(duration_s * 1000 * np.random.uniform(0.22, 0.88))
            total_watch_ms = avg_watch_ms * video_views

        elif media_type == "CAROUSEL_ALBUM":
            base_reach = int(np.random.lognormal(8.1, 0.55) * growth_factor)
            impressions = int(base_reach * np.random.uniform(1.08, 1.55))
            likes = int(base_reach * np.random.uniform(0.030, 0.095))
            comments = int(base_reach * np.random.uniform(0.006, 0.028))
            saves = int(base_reach * np.random.uniform(0.030, 0.130))  # carousels save more
            shares = int(base_reach * np.random.uniform(0.007, 0.045))
            video_views = 0
            duration_s = 0
            avg_watch_ms = 0
            total_watch_ms = 0

        else:  # IMAGE
            base_reach = int(np.random.lognormal(7.6, 0.50) * growth_factor)
            impressions = int(base_reach * np.random.uniform(1.04, 1.35))
            likes = int(base_reach * np.random.uniform(0.025, 0.075))
            comments = int(base_reach * np.random.uniform(0.003, 0.013))
            saves = int(base_reach * np.random.uniform(0.007, 0.042))
            shares = int(base_reach * np.random.uniform(0.003, 0.022))
            video_views = 0
            duration_s = 0
            avg_watch_ms = 0
            total_watch_ms = 0

        hashtags = [w[1:] for w in caption.split() if w.startswith("#")]

        posts.append({
            "id": f"post_{i + 1:03d}",
            "timestamp": ts,
            "media_type": media_type,
            "caption": caption,
            "hashtags": hashtags,
            "permalink": f"https://www.instagram.com/p/demo{i + 1}/",
            "duration_seconds": duration_s,
            "impressions": max(0, impressions),
            "reach": max(1, int(base_reach)),
            "likes": max(0, likes),
            "comments": max(0, comments),
            "saves": max(0, saves),
            "shares": max(0, shares),
            "video_views": max(0, video_views),
            "avg_watch_time_ms": max(0, avg_watch_ms),
            "total_watch_time_ms": max(0, total_watch_ms),
        })

    return pd.DataFrame(posts)
