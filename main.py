"""
SARNA v4.0 — Main Orchestrator
================================
Entry point for both execution loops:

  python main.py --mode ingestion      # Hourly RSS scan → Gemini → Sheets
  python main.py --mode notification   # Twice-daily email digest

  python main.py --mode ingestion --test   # Test ingestion (dry run)
  python main.py --mode notification --test # Test notification

The two loops are decoupled by design:
  - Ingestion runs every 60 minutes (captures data before RSS buffer flushes)
  - Notification runs at 9 AM & 9 PM IST (digest for human review)
"""

import argparse
import sys
import time
from datetime import datetime

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Load .env for local development (GitHub Actions uses secrets directly)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import GROQ_COMMENT_SLEEP_BETWEEN_CALLS
from reddit_rss_scanner import scan_reddit, save_processed_posts
from comment_generator import generate_comment_and_dm
from email_notifier import run_notification, send_batch_lead_alert


# =============================================================================
# Ingestion Pipeline — Direct Email Engine
# =============================================================================
def run_ingestion(test_mode: bool = False):
    """
    Full ingestion pipeline:
    1. Scan RSS feed for qualified posts (Stage 1 Regex + Stage 2 Groq Triage)
    2. For each post: generate comment + DM
    3. Send direct email alert for EVERY extracted post (no score threshold)
    4. Save processed posts ledger
    """
    start_time = time.time()
    now = datetime.now()

    print(f"\n{'🚀' * 30}")
    print(f"  SARNA v4.0 — Ingestion Loop (Direct Email)")
    print(f"  {now.strftime('%A, %B %d, %Y at %I:%M %p')}")
    if test_mode:
        print(f"  ⚠️  TEST MODE — Email alerts will be logged but NOT dispatched")
    print(f"{'🚀' * 30}\n")

    # =========================================================================
    # Step 1: Scan Reddit RSS for qualified posts
    # =========================================================================
    posts, updated_ids = scan_reddit()

    if not posts:
        print("😴 No new qualified posts found. Saving ledger and exiting.")
        save_processed_posts(updated_ids)
        _print_summary(0, 0, start_time, test_mode)
        return

    # =========================================================================
    # Step 2: Generate comment + DM & Dispatch Email for EVERY post
    # =========================================================================
    print(f"\n💬 Step 2: Generating comments & dispatching emails for {len(posts)} posts...")
    batch_data = []
    success_count = 0

    for i, post in enumerate(posts, 1):
        score_str = post.get('relevance_string', 'N/A')
        print(f"\n  [{i}/{len(posts)}] r/{post['subreddit']} (Relevance: {score_str}): {post['title'][:60]}...")

        try:
            # Generate comment and DM
            result = generate_comment_and_dm(post)
            comment = result["comment"]
            dm = result["dm"]

            print(f"    ✅ Comment: {len(comment.split())} words | DM: {len(dm.split())} words")
            
            # Store data for batch email
            if not test_mode:
                batch_data.append({
                    "post": post,
                    "comment": comment,
                    "dm": dm
                })
            else:
                print(f"    🧪 TEST MODE — Email alert generation verified for r/{post['subreddit']}")

            success_count += 1

        except Exception as e:
            # If ONE post fails, log and continue — never crash the pipeline
            print(f"    ❌ Failed to process post: {e}")
            continue

        # Rate limit: sleep between Groq calls
        if i < len(posts):
            print(f"    ⏳ Rate limit sleep ({GROQ_COMMENT_SLEEP_BETWEEN_CALLS}s)...")
            time.sleep(GROQ_COMMENT_SLEEP_BETWEEN_CALLS)

    # Send batch email alert if there are leads
    if batch_data:
        print(f"\n📧 Sending batch email for {len(batch_data)} leads...")
        send_batch_lead_alert(batch_data)

    # =========================================================================
    # Step 3: Save processed posts ledger
    # =========================================================================
    print(f"\n💾 Step 3: Saving processed posts ledger...")
    save_processed_posts(updated_ids)
    print(f"  ✅ Ledger updated: {len(updated_ids)} total tracked IDs")

    # =========================================================================
    # Summary
    # =========================================================================
    _print_summary(success_count, len(posts), start_time, test_mode)


def _print_summary(success: int, total: int, start_time: float, test_mode: bool):
    """Print the run summary."""
    elapsed = round(time.time() - start_time, 1)
    print(f"\n{'='*60}")
    print(f"✅ Ingestion run complete in {elapsed}s")
    print(f"   📋 Posts scanned: {total}")
    print(f"   💬 Comments generated: {success}")
    if test_mode:
        print(f"   📊 Sheet writes: SKIPPED (test mode)")
    print(f"{'='*60}\n")


# =============================================================================
# CLI entry point
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="SARNA v4.0 — Sahajta AI Reddit Networking Agent"
    )
    parser.add_argument(
        "--mode",
        choices=["ingestion", "notification"],
        required=True,
        help="Execution mode: 'ingestion' (RSS scan + Gemini + Sheets) or 'notification' (email digest)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: runs pipeline but skips external writes (Sheets, email)",
    )

    args = parser.parse_args()

    if args.mode == "ingestion":
        run_ingestion(test_mode=args.test)

    elif args.mode == "notification":
        if args.test:
            print("🧪 Notification test mode — will attempt real Sheet read + email send")
        run_notification()


if __name__ == "__main__":
    main()
