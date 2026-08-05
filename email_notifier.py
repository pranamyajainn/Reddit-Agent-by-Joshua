"""
SARNA v4.0 — Email Notifier (Decoupled Alert Engine)
=====================================================
Runs independently from the ingestion loop (twice daily: 9 AM & 9 PM IST).

1. Authenticates to Google Sheet to read current row count
2. Compares against notification_state.json to compute new-row delta
3. Composes a plain-text digest email with Sheet hyperlink
4. Sends via Gmail SMTP from joshua.us333@gmail.com → pranamyajeet@gmail.com
5. Updates notification_state.json for next cycle

Zero attachments. Hyperlink only.
"""

import json
import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from config import (
    EMAIL_RECIPIENT,
    EMAIL_SUBJECT_TEMPLATE,
    GOOGLE_SHEET_URL_TEMPLATE,
    NOTIFICATION_STATE_FILE,
)
from google_sheets_writer import authenticate_sheets, get_row_count


# =============================================================================
# Notification state persistence
# =============================================================================
def load_notification_state() -> dict:
    """Load the last notification state (row count + timestamp)."""
    if os.path.exists(NOTIFICATION_STATE_FILE):
        try:
            with open(NOTIFICATION_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass
    return {"last_notified_row_count": 1, "last_notification_time": None}


def save_notification_state(row_count: int):
    """Save the current notification state."""
    with open(NOTIFICATION_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "last_notified_row_count": row_count,
                "last_notification_time": datetime.now().isoformat(),
            },
            f,
            indent=2,
        )


# =============================================================================
# Email composition
# =============================================================================
def compose_digest(new_rows: int, total_rows: int, sheet_url: str) -> str:
    """Compose the plain-text email body with lead summary and Sheet link."""

    if new_rows > 0:
        body = (
            f"Hey Pranamya,\n\n"
            f"🚀 SARNA found {new_rows} new lead{'s' if new_rows != 1 else ''} since your last alert.\n\n"
            f"📊 Quick stats:\n"
            f"  • New rows added: {new_rows}\n"
            f"  • Total rows in Sheet: {total_rows}\n\n"
            f"👉 Open the Sheet to review and post:\n"
            f"   {sheet_url}\n\n"
            f"Remember:\n"
            f"  ✅ Review each comment for tone before posting\n"
            f"  ✅ Check the 'Subreddit Guidelines' column\n"
            f"  ✅ Tweak the language to match your voice\n"
            f"  ❌ Never copy-paste DMs without reading the thread first\n\n"
            f"Happy hunting! 🎯\n"
            f"— SARNA v4.0"
        )
    else:
        body = (
            f"Hey Pranamya,\n\n"
            f"😴 No new Reddit leads found since your last alert.\n\n"
            f"This can happen during quiet periods — the agent will keep "
            f"scanning every hour and will catch new posts as they appear.\n\n"
            f"📊 Total rows in Sheet: {total_rows}\n\n"
            f"👉 Sheet link: {sheet_url}\n\n"
            f"— SARNA v4.0"
        )

    return body


# =============================================================================
# Email sending
# =============================================================================
def send_notification_email(
    new_rows: int,
    total_rows: int,
    sheet_url: str,
) -> bool:
    """
    Send the digest notification email via Gmail SMTP.

    Args:
        new_rows: Number of new rows since last notification
        total_rows: Total rows currently in the Sheet
        sheet_url: Direct URL to the Google Sheet

    Returns:
        True if sent successfully, False otherwise
    """
    sender = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender or not app_password:
        print("  ❌ GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set")
        return False

    # Build email
    now = datetime.now()
    period = "Morning ☀️" if now.hour < 12 else "Evening 🌙"
    date_str = now.strftime("%B %d, %Y")

    msg = EmailMessage()
    msg["Subject"] = EMAIL_SUBJECT_TEMPLATE.format(date=date_str, period=period)
    msg["From"] = sender
    msg["To"] = EMAIL_RECIPIENT
    msg.set_content(compose_digest(new_rows, total_rows, sheet_url))

    # Send via Gmail SMTP SSL
    try:
        print(f"  📧 Sending notification to {EMAIL_RECIPIENT}...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(msg)
        print(f"  ✅ Email sent successfully")
        return True

    except smtplib.SMTPAuthenticationError:
        print("  ❌ Gmail auth failed — check GMAIL_APP_PASSWORD")
        print("     Must be the 16-char App Password, not your regular password")
        return False

    except Exception as e:
        print(f"  ❌ SMTP error: {e}")
        return False


def send_lead_alert(post: dict, comment: str, dm: str) -> bool:
    """Send an instant email alert for any extracted lead (no score threshold)."""
    sender = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender or not app_password:
        print("    ⚠️ GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — skipping email dispatch")
        return False
        
    score = post.get('total_score', 0)
    title = post.get('title', 'Unknown')
    sub = post.get('subreddit', 'unknown')
    url = post.get('url', '')
    track = post.get('track', 'ecom').upper()
    
    msg = EmailMessage()
    msg["Subject"] = f"🎯 [{track}] NEW REDDIT LEAD: [{score}/100] r/{sub} - {title[:50]}"
    msg["From"] = sender
    msg["To"] = EMAIL_RECIPIENT
    
    import urllib.parse
    encoded_title = urllib.parse.quote(title)
    
    # Pre-filled Google Form Links for Autonomous Feedback
    form_base = "https://docs.google.com/forms/d/e/1FAIpQLSfSU2-BodgTamTgmegi6lnLZs-N0612WJKIvLvJoCJjnRKi7g/viewform?usp=pp_url"
    good_link = f"{form_base}&entry.1636857333={encoded_title}&entry.1036755291=GOOD"
    bad_link = f"{form_base}&entry.1636857333={encoded_title}&entry.1036755291=BAD"
    
    msg.add_alternative(f"""\
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #2c3e50;">🎯 NEW {track} REDDIT LEAD DETECTED 🎯</h2>
        <p><strong>Score:</strong> {score}/100<br>
        <strong>Subreddit:</strong> r/{sub}<br>
        <strong>Title:</strong> {title}<br>
        <strong>URL:</strong> <a href="{url}">{url}</a></p>
        
        <h3 style="color: #2980b9; border-bottom: 1px solid #eee; padding-bottom: 5px;">--- AI COMMENT DRAFT ---</h3>
        <p style="white-space: pre-wrap;">{comment}</p>
        
        <h3 style="color: #27ae60; border-bottom: 1px solid #eee; padding-bottom: 5px;">--- AI DM DRAFT ---</h3>
        <p style="white-space: pre-wrap;">{dm}</p>
        
        <hr style="border: none; border-top: 1px solid #ccc; margin: 20px 0;">
        <h3 style="color: #8e44ad;">🤖 AUTONOMOUS FEEDBACK LOOP</h3>
        <p>Help the AI learn by grading this lead. This takes 5 seconds:</p>
        <p>
          <a href="{good_link}" style="background-color: #2ecc71; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-right: 15px;">🟢 MARK AS GOOD LEAD</a>
          <a href="{bad_link}" style="background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">🔴 MARK AS BAD LEAD</a>
        </p>
      </body>
    </html>
    """, subtype='html')
    
    try:
        print(f"    📧 Dispatching email alert to {EMAIL_RECIPIENT}...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(msg)
        print(f"    ✅ Email sent successfully for r/{sub} post!")
        return True
    except Exception as e:
        print(f"    ❌ Failed to send lead alert email: {e}")
        return False

def send_batch_lead_alert(batch_data: list) -> bool:
    """Send an instant email alert containing multiple leads."""
    sender = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender or not app_password:
        print("    ⚠️ GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set — skipping batch email dispatch")
        return False
        
    if not batch_data:
        return True
        
    msg = EmailMessage()
    msg["Subject"] = f"🎯 {len(batch_data)} NEW REDDIT LEADS FOUND!"
    msg["From"] = sender
    msg["To"] = EMAIL_RECIPIENT
    
    import urllib.parse
    form_base = "https://docs.google.com/forms/d/e/1FAIpQLSfSU2-BodgTamTgmegi6lnLZs-N0612WJKIvLvJoCJjnRKi7g/viewform?usp=pp_url"
    
    html_content = f"""\
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #2c3e50;">🎯 {len(batch_data)} NEW REDDIT LEADS DETECTED 🎯</h2>
        <p>The agent found multiple leads in this run. Review them below:</p>
    """
    
    for item in batch_data:
        post = item["post"]
        comment = item["comment"]
        dm = item["dm"]
        
        score = post.get('total_score', 0)
        title = post.get('title', 'Unknown')
        sub = post.get('subreddit', 'unknown')
        url = post.get('url', '')
        track = post.get('track', 'ecom').upper()
        
        encoded_title = urllib.parse.quote(title)
        good_link = f"{form_base}&entry.1636857333={encoded_title}&entry.1036755291=GOOD"
        bad_link = f"{form_base}&entry.1636857333={encoded_title}&entry.1036755291=BAD"
        
        html_content += f"""\
        <div style="border: 1px solid #ccc; padding: 15px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color: #2980b9; margin-top: 0; border-bottom: 2px solid #3498db; padding-bottom: 5px;">[{track}] r/{sub} - Score: {score}/100</h3>
            <p><strong>Title:</strong> {title}<br>
            <strong>URL:</strong> <a href="{url}">{url}</a></p>
            
            <h4 style="color: #27ae60; margin-bottom: 5px;">💬 AI COMMENT DRAFT</h4>
            <div style="background-color: #f8fcf9; border-left: 4px solid #2ecc71; padding: 10px; white-space: pre-wrap; font-size: 0.9em;">{comment}</div>
            
            <h4 style="color: #8e44ad; margin-bottom: 5px;">✉️ AI DM DRAFT</h4>
            <div style="background-color: #fbf8fc; border-left: 4px solid #9b59b6; padding: 10px; white-space: pre-wrap; font-size: 0.9em;">{dm}</div>
            
            <div style="margin-top: 20px; text-align: center; background: #ecf0f1; padding: 15px; border-radius: 5px;">
                <strong style="display: block; margin-bottom: 10px;">🤖 AUTONOMOUS FEEDBACK: GRADE THIS LEAD</strong>
                <a href="{good_link}" style="display: inline-block; background-color: #2ecc71; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-right: 15px;">🟢 GOOD LEAD</a>
                <a href="{bad_link}" style="display: inline-block; background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">🔴 BAD LEAD</a>
            </div>
        </div>
        """
        
    html_content += """
      </body>
    </html>
    """
    
    msg.add_alternative(html_content, subtype='html')
    
    try:
        print(f"    📧 Dispatching batch email alert to {EMAIL_RECIPIENT}...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(msg)
        print(f"    ✅ Batch email sent successfully for {len(batch_data)} leads!")
        return True
    except Exception as e:
        print(f"    ❌ Failed to send batch lead alert email: {e}")
        return False

# =============================================================================
# Main notification pipeline
# =============================================================================
def run_notification():
    """
    Full notification pipeline:
    1. Auth to Google Sheets
    2. Read current row count
    3. Compare to last notification state
    4. Send digest email
    5. Update notification state
    """
    print(f"\n{'='*60}")
    print(f"📧 SARNA Notification Loop — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    # Step 1: Authenticate to Sheets
    service, sheet_id = authenticate_sheets()
    if not service or not sheet_id:
        print("  ❌ Cannot read Sheet — skipping notification")
        return False

    # Step 2: Get current row count
    current_rows = get_row_count(service, sheet_id)
    if current_rows < 0:
        print("  ❌ Could not determine row count — skipping notification")
        return False

    # Step 3: Load last notification state
    state = load_notification_state()
    last_count = state.get("last_notified_row_count", 1)
    last_time = state.get("last_notification_time", "never")

    new_rows = max(0, current_rows - last_count)
    print(f"  📊 Sheet rows: {current_rows} total, {new_rows} new since last alert")
    print(f"  🕐 Last notification: {last_time}")

    # Step 4: Build Sheet URL and send email
    sheet_url = GOOGLE_SHEET_URL_TEMPLATE.format(sheet_id=sheet_id)
    email_sent = send_notification_email(new_rows, current_rows, sheet_url)

    # Step 5: Update state (even if email failed, to prevent re-alerting)
    if email_sent:
        save_notification_state(current_rows)
        print(f"  💾 Notification state updated: {current_rows} rows")

    print(f"{'='*60}\n")
    return email_sent


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
        print("🧪 Running email notifier test...\n")
        print("  (Will attempt to read Sheet and send a real email)\n")

    run_notification()
