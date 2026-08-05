"""
SARNA v4.0 — Reddit RSS Scanner
=================================
Fetches the aggregated 10-subreddit RSS feed (public, no auth),
parses entries, applies keyword filtering (60/40 intent/value split),
and deduplicates against the processed_posts.json ledger.

No Reddit API keys required. Uses feedparser + requests only.
"""

import json
import os
import re
import time
import urllib3
from datetime import datetime, timezone, timedelta
from html import unescape

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import feedparser
import requests

from config import (
    TARGET_SUBREDDITS,
    AI_SUBREDDITS,
    INTENT_REGEXES,
    AI_INTENT_REGEXES,
    COMMERCIAL_KEYWORDS,
    MAX_POSTS_PER_RUN,
    MAX_POST_AGE_DAYS,
    PROCESSED_POSTS_FILE,
    PROCESSED_POSTS_MAX,
    SCORE_WEIGHT_INTENT,
    SCORE_WEIGHT_COMMERCIAL,
    SCORE_WEIGHT_FRESHNESS,
    SCORE_WEIGHT_BODY_LENGTH,
    EXCLUDED_PHRASES,
    GROQ_MODEL,
    GROQ_API_BASE,
    GROQ_TRIAGE_PROMPT_TEMPLATE,
    GROQ_TRIAGE_PROMPT_TEMPLATE_AI,
)


# =============================================================================
# HTML stripping utility
# =============================================================================
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(html_text: str) -> str:
    """Remove HTML tags and decode entities from RSS content."""
    if not html_text:
        return ""
    text = _HTML_TAG_RE.sub(" ", html_text)
    text = unescape(text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


# =============================================================================
# State persistence (deduplication ledger)
# =============================================================================
def load_processed_posts() -> set:
    """Load the set of already-processed post IDs from the ledger file."""
    if os.path.exists(PROCESSED_POSTS_FILE):
        try:
            with open(PROCESSED_POSTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("post_ids", []))
        except (json.JSONDecodeError, KeyError):
            pass
    return set()


def save_processed_posts(post_ids: set):
    """
    Persist processed post IDs to the ledger.
    Auto-prunes to keep only the latest PROCESSED_POSTS_MAX entries.
    """
    ids_list = list(post_ids)
    if len(ids_list) > PROCESSED_POSTS_MAX:
        ids_list = ids_list[-PROCESSED_POSTS_MAX:]

    with open(PROCESSED_POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "post_ids": ids_list,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            },
            f,
            indent=2,
        )


# =============================================================================
# RSS feed fetching — Ultimate Fallback Chain
# =============================================================================
def _build_endpoint_urls(grouped_subs: str) -> list[dict]:
    """
    Build the ordered fallback chain of endpoints for a subreddit batch.
    Each entry is a dict with 'url', 'format' ('json' or 'rss'), and header flags.
    
    Priority:
      1. ScraperAPI proxy  (bypasses Cloudflare entirely)
      2. Standard RSS      (public XML feed) + cache-bust
      3. Old Reddit JSON   (legacy infra) + cache-bust
    """
    import random
    import urllib.parse

    scraper_key = os.environ.get("SCRAPER_API_KEY", "")
    cache_bust = int(time.time() * 1000) + random.randint(0, 9999)

    reddit_json_url = f"https://www.reddit.com/r/{grouped_subs}/new.json?limit=100"
    standard_rss_url = f"https://www.reddit.com/r/{grouped_subs}/new/.rss?limit=100&t={cache_bust}"
    old_reddit_json_url = f"https://old.reddit.com/r/{grouped_subs}/new.json?limit=100&t={cache_bust}"

    endpoints = []

    # Primary: ScraperAPI (only if key is configured)
    if scraper_key:
        encoded_url = urllib.parse.quote(standard_rss_url, safe="")
        proxy_url = f"https://api.scraperapi.com?api_key={scraper_key}&url={encoded_url}&premium=true"
        endpoints.append({"url": proxy_url, "format": "rss", "label": "ScraperAPI", "send_ua": False})

    # Fallback 1: Standard RSS + cache-bust
    endpoints.append({"url": standard_rss_url, "format": "rss", "label": "Standard RSS", "send_ua": True})

    # Fallback 2: Old Reddit + cache-bust
    endpoints.append({"url": old_reddit_json_url, "format": "json", "label": "Old Reddit", "send_ua": True})

    return endpoints


def fetch_rss_feed(user_agent: str | None = None) -> list[dict]:
    """
    Fetch Reddit posts using the Ultimate Fallback Chain:
      ScraperAPI → Standard RSS → Old Reddit
    
    Each batch of subreddits tries endpoints in priority order.
    If one fails or returns a 429/403, it silently falls to the next.
    """
    import random

    # Realistic browser UA for non-proxy fallbacks (avoids Cloudflare 403s on standard requests)
    browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
    ua = user_agent or os.environ.get("REDDIT_USER_AGENT", browser_ua)

    print(f"  📡 Fetching RSS from {len(TARGET_SUBREDDITS)} subreddits in batches...")

    entries = []
    target_subs_lower = {s.lower(): s for s in TARGET_SUBREDDITS}

    # Break into batches of 5 subreddits
    batch_size = 5
    batches = [TARGET_SUBREDDITS[i:i + batch_size] for i in range(0, len(TARGET_SUBREDDITS), batch_size)]

    for batch_idx, batch in enumerate(batches):
        grouped_subs = "+".join(batch)
        endpoints = _build_endpoint_urls(grouped_subs)

        batch_success = False
        for ep in endpoints:
            if batch_success:
                break

            try:
                headers = {"User-Agent": ua} if ep.get("send_ua", True) else {}
                verify_ssl = False if ep["label"] == "ScraperAPI" else True
                timeout_val = 60 if ep["label"] == "ScraperAPI" else 35
                
                resp = requests.get(
                    ep["url"],
                    headers=headers,
                    timeout=timeout_val,
                    verify=verify_ssl
                )

                # 429 or 403 → silently fall to next endpoint
                if resp.status_code in (429, 403):
                    print(f"  ⚠️ {resp.status_code} on {ep['label']}... falling back")
                    time.sleep(random.uniform(1.5, 3.5))
                    continue

                # Any other HTTP error → fall to next endpoint
                if resp.status_code >= 400:
                    print(f"  ⚠️ {resp.status_code} on {ep['label']}... falling back")
                    continue

                resp.raise_for_status()

                # ── Parse JSON format ──
                if ep["format"] == "json":
                    data = resp.json()
                    children = data.get("data", {}).get("children", [])
                    for child in children:
                        post_data = child.get("data", {})
                        post_id = post_data.get("id")
                        if not post_id:
                            continue

                        raw_sub = post_data.get("subreddit", "unknown")
                        subreddit = target_subs_lower.get(raw_sub.lower(), raw_sub)

                        entries.append({
                            "post_id": post_id,
                            "title": post_data.get("title", "").strip(),
                            "body": strip_html(post_data.get("selftext", "")),
                            "url": f"https://reddit.com{post_data.get('permalink', '')}",
                            "subreddit": subreddit,
                            "published_utc": datetime.fromtimestamp(post_data.get("created_utc", 0), tz=timezone.utc),
                            "author": post_data.get("author", "unknown"),
                        })

                # ── Parse RSS format ──
                else:
                    feed = feedparser.parse(resp.text)
                    if feed.bozo and not feed.entries:
                        continue

                    for entry in feed.entries:
                        post_id = _extract_post_id(entry.get("link", "") or entry.get("id", ""))
                        if not post_id:
                            continue

                        raw_sub = _extract_subreddit(entry)
                        subreddit = target_subs_lower.get(raw_sub.lower(), raw_sub)
                        raw_body = entry.get("summary", "") or ""
                        body = strip_html(raw_body)
                        published_utc = _parse_published_time(entry)

                        entries.append({
                            "post_id": post_id,
                            "title": entry.get("title", "").strip(),
                            "body": body,
                            "url": entry.get("link", ""),
                            "subreddit": subreddit,
                            "published_utc": published_utc,
                            "author": _extract_author(entry),
                        })

                batch_success = True
                print(f"  ✅ Batch {batch_idx + 1}/{len(batches)} fetched via {ep['label']}")

            except requests.RequestException as e:
                print(f"  ❌ {ep['label']} error: {e}... falling back")
                continue

        if not batch_success:
            print(f"  🚨 All endpoints failed for batch: {grouped_subs}")

        # Polite inter-batch delay (Mercator principle)
        if batch_idx < len(batches) - 1:
            sleep_time = random.uniform(3.0, 6.0)
            print(f"  😴 Polite sleep {sleep_time:.1f}s before next batch...")
            time.sleep(sleep_time)

    print(f"  📥 Parsed {len(entries)} total entries across all endpoints")
    print(f"  ✅ Scanned all {len(TARGET_SUBREDDITS)} subreddits in this run")
    return entries


def _extract_post_id(url: str) -> str | None:
    """Extract the Reddit post ID from a URL like /r/sub/comments/ID/..."""
    match = re.search(r"/comments/([a-z0-9]+)", url)
    if match:
        return match.group(1)
    # Fallback: try t3_ format
    match = re.search(r"t3_([a-z0-9]+)", url)
    if match:
        return match.group(1)
    return None


def _extract_subreddit(entry) -> str:
    """Extract subreddit name from RSS entry tags or URL."""
    # Try category tags first
    tags = entry.get("tags", [])
    if tags:
        for tag in tags:
            term = tag.get("term", "")
            if term:
                return term

    # Fallback: parse from URL
    url = entry.get("link", "")
    match = re.search(r"/r/([^/]+)/", url)
    if match:
        return match.group(1)
    return "unknown"


def _extract_author(entry) -> str:
    """Extract author name from RSS entry."""
    author = entry.get("author", "") or entry.get("author_detail", {}).get("name", "")
    if author and author.startswith("/u/"):
        return author[3:]
    return author or "unknown"


def _parse_published_time(entry) -> datetime | None:
    """Parse the published/updated timestamp from an RSS entry."""
    time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if time_struct:
        try:
            return datetime(*time_struct[:6], tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
    return None


# =============================================================================
# =============================================================================
# Keyword tagging & Scoring
# =============================================================================
def stage1_regex_fuzzy_filter(entries: list[dict], track: str = "ecom") -> list[dict]:
    """
    Stage 1: Broad Regex Net to catch obvious SEEKER posts.
    track='ecom'  → uses INTENT_REGEXES (Shopify/merchant signals)
    track='ai'    → uses AI_INTENT_REGEXES (agency/automation buyer signals)
    """
    SHARER_PREFIXES = [
        "i built", "i made", "i ran ", "i created", "i wrote", "i launched",
        "i released", "i published", "how i ", "here's what i ", "here's how i",
        "what i've learned", "what i learned", "til ", "psa:", "[psa]",
        "sharing my", "just shipped", "just released", "just launched",
        "replaced a few", "replaced my", "swapped my", "switched from",
        "show hn:", "show reddit:", "i open sourced",
    ]

    patterns = AI_INTENT_REGEXES if track == "ai" else INTENT_REGEXES
    label = "[AI TRACK]" if track == "ai" else "[ECOM TRACK]"

    tagged = []
    sharer_dropped = 0

    for entry in entries:
        title_lower = entry.get("title", "").lower().strip()

        if any(title_lower.startswith(prefix) for prefix in SHARER_PREFIXES):
            sharer_dropped += 1
            continue

        searchable = f"{entry['title']} {entry['body']}".lower()
        intent_hits = sum(1 for pattern in patterns if re.search(pattern, searchable))

        if intent_hits == 0:
            continue

        commercial_hits = sum(1 for kw in COMMERCIAL_KEYWORDS if kw in searchable)

        entry["regex_intent_hits"] = intent_hits
        entry["commercial_score"] = commercial_hits
        entry["match_type"] = f"stage1_regex_{track}"
        entry["keyword_tier"] = "regex_pass"
        entry["track"] = track

        tagged.append(entry)

    if sharer_dropped > 0:
        print(f"  🚫 {label} Sharer pre-check: dropped {sharer_dropped} posts")
    print(f"  🎯 {label} Stage 1: {len(tagged)} posts passed to Stage 2")
    return tagged


def stage2_groq_triage(entries: list[dict], track: str = "ecom") -> list[dict]:
    """
    Stage 2: B2B Triage using Groq LLM.
    track='ecom' → uses Shopify/merchant triage prompt
    track='ai'   → uses Agency/Automation buyer triage prompt
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("  ⚠️  GROQ_API_KEY not set. Falling back to Stage 1 scores.")
        for e in entries:
            e["intent_score"] = e.get("regex_intent_hits", 0) * 20
        return entries

    try:
        with open("pranamya_guidelines.txt", "r", encoding="utf-8") as f:
            guidelines = "\n\nCRITICAL EDGE-CASE GUIDELINES FROM FOUNDER:\n" + f.read()
    except FileNotFoundError:
        guidelines = ""

    label = "[AI TRACK]" if track == "ai" else "[ECOM TRACK]"
    base_prompt = GROQ_TRIAGE_PROMPT_TEMPLATE_AI if track == "ai" else GROQ_TRIAGE_PROMPT_TEMPLATE
    
    # Inject guidelines if the prompt template supports it (only ECOM supports it currently)
    try:
        prompt = base_prompt.format(PRANAMYA_GUIDELINES=guidelines)
    except KeyError:
        prompt = base_prompt

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    scored_entries = []

    for entry in entries:
        title = entry.get("title", "")
        body = entry.get("body", "")[:800]

        user_prompt = f"POST TITLE: {title}\n\nPOST BODY: {body}\n\nScore this post."

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0
        }

        try:
            resp = requests.post(GROQ_API_BASE, json=payload, headers=headers, timeout=15)
            if resp.status_code == 429:
                print(f"  ⚠️ {label} Groq rate limited. Returning current scored entries.")
                break
            resp.raise_for_status()

            raw_text = resp.json()["choices"][0]["message"]["content"].strip()
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text).strip()

            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                match = re.search(r"\{[^{}]*\}", raw_text, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(0))
                    except:
                        data = {"intent_score": 0, "reason": "Parse failed"}
                else:
                    data = {"intent_score": 0, "reason": "Parse failed"}

            intent_score = data.get("intent_score", 0)

            if intent_score >= 0:  # Feedback Loop: Allow everything through!
                entry["intent_score"] = intent_score
                entry["groq_reason"] = data.get("reason", "")
                scored_entries.append(entry)

            time.sleep(1.0)

        except Exception as e:
            print(f"  ❌ {label} Groq Triage Error: {e}")

    print(f"  🧠 {label} Stage 2 Groq Triage: {len(scored_entries)} posts qualified")
    return scored_entries


def score_post(post: dict) -> float:
    """Calculate the base relevance score based on Intent + Commercial Context."""
    # Groq gives an intent_score from 0-100
    raw_intent = post.get("intent_score", 0)
    intent_pts = (raw_intent / 100.0) * SCORE_WEIGHT_INTENT
    
    commercial_pts = min(post.get("commercial_score", 0) * 5, SCORE_WEIGHT_COMMERCIAL)
    
    # Freshness (linear decay over MAX_POST_AGE_DAYS)
    age_hours = post.get("age_hours", 0)
    max_age_hours = MAX_POST_AGE_DAYS * 24
    freshness_pts = max(0, SCORE_WEIGHT_FRESHNESS * (1 - (age_hours / max_age_hours)))
    
    # Body length bonus
    body_len = len(post.get("body", ""))
    length_pts = min(body_len / 200.0, SCORE_WEIGHT_BODY_LENGTH)
    
    base_score = intent_pts + commercial_pts + freshness_pts + length_pts
    return base_score


def rank_and_select(posts: list[dict], max_posts: int = 20) -> list[dict]:
    """
    Apply subreddit quality weighting to BASE SCORE without diversity bonus.
    Pure merit & quality ranking.
    """
    for p in posts:
        p["base_score"] = score_post(p)
        
    subreddit_counts = {}
    for p in posts:
        sub = p["subreddit"]
        subreddit_counts[sub] = subreddit_counts.get(sub, 0) + 1
        
        total_score = min(100.0, p["base_score"])
        
        p["total_score"] = round(total_score, 1)
        
        intent = p.get('intent_score', 0)
        comm = p.get('commercial_score', 0)
        age = p.get('age_hours', 0)
        tier = p.get('keyword_tier', 'unknown')
        p["relevance_string"] = f"{p['total_score']}/100 [{tier}] — {intent} intent, {comm} commercial, {int(age)}h old"

    posts.sort(key=lambda x: x["total_score"], reverse=True)
    
    selected = posts[:max_posts]
    if selected:
        print(f"  🏆 Ranked and selected {len(selected)} posts (top score: {selected[0]['total_score']}/100)")
        print(f"  📊 Subreddit distribution: {dict(subreddit_counts)}")
    
    return selected


# =============================================================================
# Freshness filter
# =============================================================================
def filter_by_freshness(entries: list[dict]) -> list[dict]:
    """
    Filter out:
    1. Posts older than MAX_POST_AGE_DAYS
    2. Posts with body length < MIN_BODY_LENGTH (noise filter)
    3. Posts containing EXCLUDED_PHRASES (anti-pattern filter)
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_POST_AGE_DAYS)
    fresh = []
    length_filtered = 0
    pattern_filtered = 0

    for entry in entries:
        # Age filter
        pub_time = entry.get("published_utc")
        if pub_time is None:
            fresh.append(entry)
            age_hours = 0
        elif pub_time >= cutoff:
            age_hours = (now - pub_time).total_seconds() / 3600
            entry["age_hours"] = round(age_hours, 1)
            
            # Excluded phrases filter
            body = entry.get("body", "")
            searchable = f"{entry.get('title', '')} {body}".lower()
            if any(phrase in searchable for phrase in EXCLUDED_PHRASES):
                pattern_filtered += 1
                continue
            
            fresh.append(entry)
        else:
            # Post too old, skip
            pass

    filtered_count = len(entries) - len(fresh)
    if filtered_count > 0:
        print(f"  ⏰ Freshness filter: dropped {filtered_count} posts older than {MAX_POST_AGE_DAYS} days")
    if pattern_filtered > 0:
        print(f"  ⚠️  Anti-pattern filter: dropped {pattern_filtered} low-signal posts")

    return fresh


# =============================================================================
# Deduplication
# =============================================================================
def deduplicate(entries: list[dict], processed_ids: set) -> list[dict]:
    """Remove entries that have already been processed in previous runs."""
    unique = [e for e in entries if e["post_id"] not in processed_ids]
    dupes = len(entries) - len(unique)
    if dupes > 0:
        print(f"  🔄 Dedup: skipped {dupes} already-processed posts")
    return unique


# =============================================================================
# Main scan orchestrator
# =============================================================================
def scan_reddit() -> tuple[list[dict], set]:
    """
    Two-Track scan pipeline:
      Track A (ECOM): Shopify/E-commerce subreddits → merchant pain signals
      Track B (AI):   AI/Automation subreddits → agency/buyer signals

    Returns:
        - Combined list of qualified post dicts (max MAX_POSTS_PER_RUN total)
        - Updated set of all processed post IDs (old + new)
    """
    print(f"\n{'='*60}")
    print(f"🔍 SARNA RSS Scanner — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    # Load existing dedup ledger
    processed_ids = load_processed_posts()
    print(f"  📦 Ledger: {len(processed_ids)} previously processed posts")

    # Step 1: Fetch all RSS entries (both track subreddits together)
    raw_entries = fetch_rss_feed()
    if not raw_entries:
        print("  😴 No entries from RSS feed. Exiting scan.")
        return [], processed_ids

    # Step 2: Freshness filter + dedup (shared across both tracks)
    fresh_entries = filter_by_freshness(raw_entries)
    new_entries = deduplicate(fresh_entries, processed_ids)
    if not new_entries:
        print("  😴 All entries already processed. No new posts this run.")
        return [], processed_ids

    # Step 3: Split entries into Track A (ecom) and Track B (ai) buckets
    ai_sub_lower = {s.lower() for s in AI_SUBREDDITS}
    track_a = [e for e in new_entries if e.get("subreddit", "").lower() not in ai_sub_lower]
    track_b = [e for e in new_entries if e.get("subreddit", "").lower() in ai_sub_lower]

    print(f"\n  📊 Track split: {len(track_a)} ECOM posts | {len(track_b)} AI posts")

    qualified_all = []

    # ── TRACK A: Ecom/Shopify Pipeline ──────────────────────────────────────
    if track_a:
        print(f"\n  🛒 [ECOM TRACK] Running {len(track_a)} posts through ecom pipeline...")
        a1 = stage1_regex_fuzzy_filter(track_a, track="ecom")
        if a1:
            a2 = stage2_groq_triage(a1, track="ecom")
            qualified_all.extend(a2)

    # ── TRACK B: AI/Automation Pipeline ─────────────────────────────────────
    if track_b:
        print(f"\n  🤖 [AI TRACK] Running {len(track_b)} posts through AI/agency pipeline...")
        b1 = stage1_regex_fuzzy_filter(track_b, track="ai")
        if b1:
            b2 = stage2_groq_triage(b1, track="ai")
            qualified_all.extend(b2)

    # Step 4: Rank and select combined results
    qualified = rank_and_select(qualified_all, max_posts=MAX_POSTS_PER_RUN)

    # Update ledger with ALL processed post IDs (so we don't re-process rejected posts)
    new_ids = {e["post_id"] for e in new_entries}
    updated_ids = processed_ids | new_ids

    print(f"\n✅ Scan complete: {len(qualified)} qualified posts ready for processing")
    print(f"{'='*60}\n")

    return qualified, updated_ids


# =============================================================================
# CLI test
# =============================================================================
if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    import sys
    if "--test" in sys.argv:
        print("🧪 Running RSS scanner test...\n")

    posts, ids = scan_reddit()
    for i, p in enumerate(posts[:5], 1):
        print(f"\n--- Post {i} ---")
        print(f"  Title:     {p['title'][:80]}")
        print(f"  Subreddit: r/{p['subreddit']}")
        print(f"  Type:      {p.get('match_type', 'n/a')}")
        print(f"  Score:     {p.get('total_score', 0)}/100")
        print(f"  Relevance: {p.get('relevance_string', '')}")
        print(f"  URL:       {p['url']}")
    print(f"\nTotal qualified: {len(posts)}")
