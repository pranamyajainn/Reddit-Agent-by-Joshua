"""
SARNA v4.0 — Google Sheets Writer
===================================
Authenticates via Service Account JSON (from env var) and appends
5-column rows to the target Google Sheet.

Schema:
  A: Subreddit
  B: Post Title & Link (hyperlink formula)
  C: AI Suggested Comment
  D: Subreddit Guidelines
  E: AI Suggested DM
  F: Relevance Score

Append-only: rows persist indefinitely as a historical log.
"""

import json
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import SUBREDDIT_COMPLIANCE, SHEET_RANGE


# =============================================================================
# Google Sheets authentication
# =============================================================================
def authenticate_sheets():
    """
    Authenticate to Google Sheets API using Service Account credentials
    from the GOOGLE_SHEETS_CREDENTIALS environment variable.

    Returns:
        Tuple of (sheets_service, sheet_id) or (None, None) on failure.
    """
    creds_json_str = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")

    if not creds_json_str:
        print("  ❌ GOOGLE_SHEETS_CREDENTIALS not set")
        return None, None

    if not sheet_id:
        print("  ❌ GOOGLE_SHEET_ID not set")
        return None, None

    try:
        creds_data = json.loads(creds_json_str)
        credentials = Credentials.from_service_account_info(
            creds_data,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        service = build("sheets", "v4", credentials=credentials)
        print("  ✅ Google Sheets authenticated")
        return service, sheet_id

    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid GOOGLE_SHEETS_CREDENTIALS JSON: {e}")
        return None, None
    except Exception as e:
        print(f"  ❌ Sheets auth error: {e}")
        return None, None


# =============================================================================
# Row building
# =============================================================================
def build_row(post: dict, comment: str, dm: str) -> list:
    """
    Build a single 6-column row for the Sheet.

    Columns:
      A: Subreddit (e.g., "r/shopify")
      B: Post Title & Link (clickable hyperlink formula)
      C: AI Suggested Comment
      D: Subreddit Guidelines (Layer 1 + Layer 2 from config)
      E: AI Suggested DM
      F: Relevance Score
    """
    subreddit = post.get("subreddit", "unknown")
    title = post.get("title", "Untitled")
    url = post.get("url", "")

    # Column A: Subreddit
    col_a = f"r/{subreddit}"

    # Wrap URL with Apps Script if available
    web_app_url = os.environ.get("APPS_SCRIPT_WEB_APP_URL")
    target_url = url
    if web_app_url and url:
        import urllib.parse
        target_url = f"{web_app_url}?url={urllib.parse.quote(url)}"

    # Column B: Post Title as clickable hyperlink
    # Use HYPERLINK formula so it's clickable in Google Sheets
    col_b = f'=HYPERLINK("{target_url}", "{title.replace(chr(34), chr(39))}")'

    # Column C: AI Comment
    col_c = comment

    # Column D: Subreddit Guidelines (both layers concatenated)
    compliance = SUBREDDIT_COMPLIANCE.get(subreddit, {})
    rules = compliance.get("layer_1_rules", "No specific rules.")
    culture = compliance.get("layer_2_culture", "Be helpful and genuine.")
    col_d = f"RULES: {rules}\nCULTURE: {culture}"

    # Column E: AI DM
    col_e = dm

    # Column F: Relevance Score
    col_f = post.get("relevance_string", "N/A")

    return [col_a, col_b, col_c, col_d, col_e, col_f]


# =============================================================================
# Sheet operations
# =============================================================================
def append_rows(
    service,
    sheet_id: str,
    rows: list[list],
    max_retries: int = 2,
) -> bool:
    """
    Append multiple rows to the Google Sheet.

    Args:
        service: Authenticated Sheets API service object
        sheet_id: The Google Sheet ID
        rows: List of row arrays to append
        max_retries: Number of retries on transient errors

    Returns:
        True if successful, False otherwise
    """
    if not rows:
        print("  ⚠️  No rows to append")
        return True

    body = {
        "values": rows,
    }

    for attempt in range(1, max_retries + 2):
        try:
            result = (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=sheet_id,
                    range=f"{SHEET_RANGE}!A:F",
                    valueInputOption="USER_ENTERED",  # Allows HYPERLINK formulas
                    insertDataOption="INSERT_ROWS",
                    body=body,
                )
                .execute()
            )

            updated = result.get("updates", {}).get("updatedRows", 0)
            print(f"  ✅ Appended {updated} rows to Google Sheet")
            return True

        except HttpError as e:
            print(f"  ❌ Sheets API error (attempt {attempt}): {e}")
            if attempt <= max_retries and e.resp.status in (429, 500, 503):
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            return False

        except Exception as e:
            print(f"  ❌ Unexpected Sheets error (attempt {attempt}): {e}")
            if attempt <= max_retries:
                import time
                time.sleep(2 ** attempt)
                continue
            return False

    return False


def get_row_count(service, sheet_id: str) -> int:
    """
    Get the current number of data rows in the Sheet (excluding header).
    Used by the notification loop to compute new row delta.
    """
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range=f"{SHEET_RANGE}!A:A",
            )
            .execute()
        )
        values = result.get("values", [])
        # Subtract 1 for header row (if present)
        return max(0, len(values) - 1) if values else 0

    except Exception as e:
        print(f"  ⚠️  Could not read Sheet row count: {e}")
        return -1  # Sentinel: unknown


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
        print("🧪 Running Google Sheets writer test...\n")

        service, sheet_id = authenticate_sheets()
        if service and sheet_id:
            test_row = build_row(
                post={
                    "subreddit": "shopify",
                    "title": "Test Post — SARNA v4.0 Verification",
                    "url": "https://reddit.com/r/shopify/comments/test/test_post/",
                },
                comment="this is a test comment from sarna v4.0. ignore this row.",
                dm="test dm — ignore this row.",
            )
            success = append_rows(service, sheet_id, [test_row])
            if success:
                print("✅ Test row appended successfully!")

                row_count = get_row_count(service, sheet_id)
                print(f"📊 Current data rows in Sheet: {row_count}")
            else:
                print("❌ Test row append failed")
        else:
            print("❌ Authentication failed — check your env vars")
