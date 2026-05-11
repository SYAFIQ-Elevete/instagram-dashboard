# Instagram Analytics Dashboard

A Streamlit dashboard for your content team to analyse Instagram post performance.

## What's inside

| Tab | What you'll find |
|---|---|
| **Overview** | KPI cards, engagement trend, content mix, top 5 posts |
| **Post Explorer** | Sortable, searchable list of every post with full metrics |
| **Reels** | Completion rate, watch time, play rate, top vs bottom performers |
| **Carousels & Images** | Side-by-side comparison, save rate analysis, top posts |
| **Strategy** | Posting-time heatmap, content quadrant, auto-generated insights, experiment ideas |

---

## Quick start (local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your team password
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml and set DASHBOARD_PASSWORD

# 3. Run
streamlit run app.py
```

Default password (if you skip step 2): `instagram2024`

---

## Connect real Instagram data

### Step 1 — Create a Meta Developer App
1. Go to https://developers.facebook.com and create an app (type: Business)
2. Add the **Instagram Graph API** product
3. Set app to **Live mode**

### Step 2 — Link your Instagram Business/Creator account
Your Instagram account must be a **Business** or **Creator** account linked to a Facebook Page.

### Step 3 — Get a long-lived access token
```
GET https://graph.instagram.com/access_token
    ?grant_type=ig_exchange_token
    &client_id={YOUR_APP_ID}
    &client_secret={YOUR_APP_SECRET}
    &access_token={SHORT_LIVED_TOKEN}
```
Long-lived tokens last ~60 days. Refresh before expiry.

### Step 4 — Find your Instagram User ID
```
GET https://graph.instagram.com/me?fields=id,username&access_token={TOKEN}
```

### Step 5 — Connect
Enter the token and user ID in the **Instagram API** section of the sidebar, then click **Connect**.

### Required permissions
- `instagram_basic`
- `instagram_manage_insights`
- `pages_read_engagement`

---

## Deploy to Streamlit Community Cloud (share with team)

1. Push this folder to a GitHub repository (private is fine)
2. Go to https://share.streamlit.io and connect your repo
3. Set `DASHBOARD_PASSWORD` in the app's Secrets section (Settings → Secrets)
4. Share the Streamlit URL with your team — they log in with the password

---

## What the Instagram API actually provides

| Metric | Available? |
|---|---|
| Reach, Impressions | ✅ |
| Likes, Comments | ✅ |
| Saves | ✅ |
| Shares | ✅ (most accounts) |
| Video Plays | ✅ |
| Avg Watch Time | ✅ (Reels only) |
| Frame-by-frame retention | ❌ Not exposed by Instagram |
| Per-slide carousel data | ❌ Not exposed by Instagram |
| Audience age / gender | ✅ Account-level only |

---

## Metrics glossary

| Metric | Formula | What it signals |
|---|---|---|
| Engagement Rate | (likes+comments+saves+shares) ÷ reach × 100 | Overall content performance |
| Save Rate | saves ÷ reach × 100 | Content value / reference-worthiness |
| Share Rate | shares ÷ reach × 100 | Viral / relatability potential |
| Comment Rate | comments ÷ reach × 100 | Conversation / community building |
| Play Rate | plays ÷ reach × 100 | Reel thumbnail effectiveness |
| Completion Rate | avg watch time ÷ duration × 100 | Hook + pacing quality |
| Performance Score | Weighted composite (0–100) | Quick ranking across all posts |

**Performance Score weights:** Save Rate 35% · Engagement Rate 30% · Share Rate 20% · Comment Rate 15%
