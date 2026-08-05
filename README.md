# 🤖 SARNA v4.0 — Sahajta AI Reddit Networking Agent

A fully autonomous, $0/month Reddit prospecting engine that scans 10 e-commerce subreddits every hour, generates AI-powered engagement copy (public comment + private DM), and routes everything to a live Google Sheet for human review.

**Architecture**: Two decoupled loops running on GitHub Actions (free tier).

```
⚙️ Every 60 Minutes: Ingestion Loop
    ├── RSS feed fetch (10 subreddits, 1 HTTP request)
    ├── Keyword filter (60% intent / 40% value)
    ├── Gemini 2.0 Flash (comment + DM generation)
    └── Google Sheets append (5-column row)

⏰ 9 AM & 9 PM IST: Notification Loop
    └── Email digest with Sheet link → pranamyajeet@gmail.com
```

## 📊 What You Get

A live Google Sheet that grows continuously:

| Subreddit | Post Title & Link | AI Comment | Guidelines | AI DM |
|-----------|-------------------|------------|------------|-------|
| r/shopify | [Struggling with conversions](url) | "yeah i've seen this exact thing..." | No promo, no links | "hey, re: my comment..." |

You review → tweak tone → manually post the best ones.

## 🔑 Setup Guide (Complete Beginner)

### Phase 0: Get Your 5 API Credentials (~15 min)

| # | Secret Name | Where to Get |
|---|-------------|-------------|
| 1 | `REDDIT_USER_AGENT` | Set to: `python:sarna_monitor:v4.0 (by /u/YOUR_USERNAME)` |
| 2 | `GEMINI_API_KEY` | https://aistudio.google.com/apikey → Create key (free) |
| 3 | `GMAIL_ADDRESS` | `joshua.us333@gmail.com` |
| 4 | `GMAIL_APP_PASSWORD` | https://myaccount.google.com/security → 2-Step Verification ON → App passwords → Create |
| 5 | `GOOGLE_SHEETS_CREDENTIALS` | Google Cloud Console → New project → Enable Sheets API → Service Account → JSON key (see below) |
| 6 | `GOOGLE_SHEET_ID` | From your Google Sheet URL (see below) |

### Phase 1: Google Service Account Setup (5 min)

1. Go to https://console.cloud.google.com
2. Create project → name it `sarna`
3. Go to **APIs & Services → Library** → Search "Google Sheets API" → **Enable**
4. Go to **APIs & Services → Credentials** → **Create Credentials → Service Account**
5. Name: `sarna-bot` → click through
6. Click into the service account → **Keys** tab → **Add Key → JSON**
7. A `.json` file downloads — its **entire contents** become `GOOGLE_SHEETS_CREDENTIALS`

### Phase 2: Create Google Sheet (2 min)

1. Go to https://sheets.google.com → New blank sheet
2. Name it: **"SARNA — Reddit Opportunities"**
3. In Row 1, add headers: `Subreddit | Post Title & Link | AI Suggested Comment | Subreddit Guidelines | AI Suggested DM`
4. **Share** the sheet with your service account email (e.g., `sarna-bot@sarna-xxxxx.iam.gserviceaccount.com`) → **Editor** access
5. Copy the **Sheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/COPY_THIS_PART/edit
   ```

### Phase 3: Deploy to GitHub (10 min)

1. Create a **private** repo on GitHub (e.g., `sarna-agent`)
2. Push all code files to the repo
3. Go to **Settings → Secrets and variables → Actions**
4. Add these 6 repository secrets:

   | Secret Name | Value |
   |-------------|-------|
   | `REDDIT_USER_AGENT` | `python:sarna_monitor:v4.0 (by /u/your_username)` |
   | `GEMINI_API_KEY` | Your Gemini API key |
   | `GMAIL_ADDRESS` | `joshua.us333@gmail.com` |
   | `GMAIL_APP_PASSWORD` | 16-char app password |
   | `GOOGLE_SHEETS_CREDENTIALS` | Full JSON content of service account key |
   | `GOOGLE_SHEET_ID` | Your Sheet ID string |

### Phase 4: Test (2 min)

1. Go to **Actions** tab in your repo
2. Click **"SARNA Ingestion Loop"** → **"Run workflow"** → Run
3. Wait 2-3 minutes for completion
4. Check your Google Sheet — new rows should appear
5. Then run **"SARNA Notification Loop"** → check email

### Phase 5: It's Autonomous! 🎉

- **Ingestion**: Runs every 60 minutes automatically (24x/day)
- **Notification**: Fires at 9 AM & 9 PM IST automatically
- **No PC needed** — runs in GitHub's cloud for free

## 📁 File Structure

```
reddit-agent/
├── .github/workflows/
│   ├── ingestion_loop.yml       # Hourly cron (0 * * * *)
│   └── notification_loop.yml    # Twice-daily cron (9 AM & 9 PM IST)
├── .env.example                 # Local dev env template
├── .gitignore                   # Protects .env
├── requirements.txt             # Python dependencies
├── config.py                    # Keywords, subreddit rules, prompts, templates
├── reddit_rss_scanner.py        # RSS fetch + keyword filter + dedup
├── comment_generator.py         # Gemini dual-layer prompting + fallbacks
├── google_sheets_writer.py      # Sheets API authentication + append
├── email_notifier.py            # Gmail SMTP digest sender
├── main.py                      # CLI orchestrator (--mode ingestion|notification)
├── processed_posts.json         # Dedup ledger (auto-committed by bot)
└── notification_state.json      # Row count tracker (auto-committed by bot)
```

## 🔧 Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Copy env template and fill in your keys
cp .env.example .env
# Edit .env with your actual credentials

# Test RSS scanning (no external writes)
python reddit_rss_scanner.py --test

# Test comment generation
python comment_generator.py --test

# Test Sheets write (appends a test row)
python google_sheets_writer.py --test

# Test email notification
python email_notifier.py --test

# Full ingestion dry run (scans + generates, no Sheet writes)
python main.py --mode ingestion --test

# Full ingestion live run
python main.py --mode ingestion

# Notification run
python main.py --mode notification
```

## 🛡️ Safety Guardrails

| Protection | How |
|------------|-----|
| **Zero Reddit writes** | No Reddit API auth. RSS is public read-only. |
| **No auto-posting** | Sheet drafts only. Joshua posts manually. |
| **Banned word scanning** | Gemini output scanned for corporate jargon; regenerated or replaced. |
| **Dual-layer compliance** | Layer 1 (rules) + Layer 2 (culture) injected per subreddit. |
| **Fallback templates** | Pre-written human copy if Gemini fails after 2 retries. |
| **Per-post error isolation** | One post failing doesn't crash the pipeline. |
| **Rate limiting** | 4.5s sleep between Gemini calls (protects 15 RPM free tier). |

## 💰 Cost

| Service | Free Tier | Our Usage | Cost |
|---------|-----------|-----------|------|
| GitHub Actions | 2,000 min/month | ~720 min/month | **$0** |
| Gemini 2.0 Flash | 15 RPM, 1M tokens/day | ~10 calls/hour | **$0** |
| Google Sheets API | Unlimited reads/writes | ~24 writes/day | **$0** |
| Gmail SMTP | 500 emails/day | 2 emails/day | **$0** |
| **Total** | | | **$0/month** |

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| RSS returns 403 | Check `REDDIT_USER_AGENT` is set and includes `/u/username` |
| Gemini rate limited | Verify 4.5s sleep is in config.py; check API key is valid |
| Sheet append fails | Verify service account has Editor access to the Sheet |
| Email not received | Check spam folder; verify `GMAIL_APP_PASSWORD` (16-char, not regular password) |
| No new posts found | Normal during quiet periods; agent runs hourly and will catch new posts |
| Duplicate rows | Check `processed_posts.json` is being committed back to repo |

## 📈 Growth Strategy

1. **Week 1**: Let SARNA populate the Sheet. Post 5-8 best comments daily. Build karma.
2. **Week 2-3**: Notice which comment styles get upvotes. Refine keywords in `config.py`.
3. **Month 2+**: Profile visitors start messaging you. Track DM-to-audit conversions.
4. **Ongoing**: Add keywords based on what works. The Sheet is your historical playbook.

---

**Owner**: Joshua, Sahajta AI  
**Version**: 4.0  
**Cost**: $0/month  
**Status**: Production-ready
