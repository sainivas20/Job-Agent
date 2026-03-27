"""
Job Link Screenshot Agent
=========================
Reads job URLs from an Excel file, takes screenshots of each page,
and sends all results via email.

Requirements (install once):
    pip install pandas openpyxl playwright
    playwright install chromium
"""

import os
import time
import smtplib
import base64
import pandas as pd
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─────────────────────────────────────────────
# CONFIGURATION — fill these in before running
# ─────────────────────────────────────────────
EMAIL_SENDER   = "sainivasmiryanam3118@gmail.com"       # Your Gmail address
EMAIL_PASSWORD = "[Enter your password]"     # Gmail App Password (not your login password)
EMAIL_RECEIVER = "sainivasmiryanam3118@gmail.com"      # Who receives the results

EXCEL_FILE     = "option1_job_links.xlsx"     # Path to your Excel file
SCREENSHOTS_DIR = "screenshots"               # Folder where screenshots are saved

PAGE_TIMEOUT_MS = 15_000    # 15 seconds to load a page before giving up
SCROLL_PAUSE_S  = 1.5       # Seconds to pause after scrolling (lets lazy images load)


# ─────────────────────────────────────────────
# STEP 1 — Read the Excel file
# ─────────────────────────────────────────────
def load_jobs(excel_path: str) -> list[dict]:
    """
    Reads the Excel file and returns a list of job dicts.
    Each dict has keys: number, title, company, url
    Only the first 5 data rows are used; legend rows are ignored.
    """
    df = pd.read_excel(excel_path)

    # Keep only rows that have a valid URL
    df = df[df["URL"].notna() & df["URL"].astype(str).str.startswith("http")]

    jobs = []
    for _, row in df.iterrows():
        jobs.append({
            "number":  str(row["#"]).strip(),
            "title":   str(row["Job Title"]).strip(),
            "company": str(row["Company"]).strip(),
            "url":     str(row["URL"]).strip(),
        })

    print(f"✅ Loaded {len(jobs)} job URLs from '{excel_path}'")
    return jobs


# ─────────────────────────────────────────────
# STEP 2 — Take screenshots
# ─────────────────────────────────────────────
def take_screenshots(jobs: list[dict], output_dir: str) -> list[dict]:
    """
    Visits each URL with a headless browser and saves a full-page screenshot.
    Returns a results list — one entry per job — with screenshot path or error info.
    """
    Path(output_dir).mkdir(exist_ok=True)
    results = []

    with sync_playwright() as pw:
        # Launch a headless (invisible) Chrome browser
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        for job in jobs:
            print(f"\n🔗 Processing #{job['number']}: {job['title']} @ {job['company']}")
            print(f"   URL: {job['url']}")

            result = {**job, "screenshot": None, "error": None}
            page = context.new_page()

            try:
                # Navigate to the page; raise an error if it takes too long
                page.goto(job["url"], timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")

                # Scroll to the bottom so lazy-loaded content appears
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(SCROLL_PAUSE_S)
                page.evaluate("window.scrollTo(0, 0)")   # Scroll back to top for screenshot

                # Save full-page screenshot
                safe_name = f"job_{job['number']}_{job['company'].replace(' ', '_')}.png"
                screenshot_path = os.path.join(output_dir, safe_name)
                page.screenshot(path=screenshot_path, full_page=True)

                result["screenshot"] = screenshot_path
                print(f"   ✅ Screenshot saved: {screenshot_path}")

            except PlaywrightTimeout:
                result["error"] = f"Timeout — page did not load within {PAGE_TIMEOUT_MS // 1000}s"
                print(f"   ❌ {result['error']}")

            except Exception as e:
                # Catch DNS failures, connection refused, etc.
                error_text = str(e).split("\n")[0]   # First line is usually most informative
                result["error"] = f"Failed to load: {error_text}"
                print(f"   ❌ {result['error']}")

            finally:
                page.close()

            results.append(result)

        browser.close()

    return results


# ─────────────────────────────────────────────
# STEP 3 — Send results via email
# ─────────────────────────────────────────────
def send_email(results: list[dict]) -> None:
    """
    Sends an HTML email summarising all results.
    Screenshots are embedded as inline images.
    Failed URLs are listed with their error messages.
    """
    successes = [r for r in results if r["screenshot"]]
    failures  = [r for r in results if r["error"]]

    # ── Build HTML body ──────────────────────────────────────
    html_parts = ["""
    <html><body style="font-family: Arial, sans-serif; max-width: 800px; margin: auto;">
    <h2 style="color: #2c3e50;">📸 Job Screenshot Agent — Results</h2>
    <p>The agent processed <strong>{total}</strong> job URLs.
       <strong style="color:green">{ok} succeeded</strong>,
       <strong style="color:red">{fail} failed</strong>.</p>
    <hr>
    """.format(total=len(results), ok=len(successes), fail=len(failures))]

    # Section: successful screenshots (embedded inline)
    if successes:
        html_parts.append("<h3>✅ Successful Screenshots</h3>")
        for r in successes:
            html_parts.append(f"""
            <div style="margin-bottom:30px; border:1px solid #ddd; padding:12px; border-radius:6px;">
              <b>#{r['number']} — {r['title']}</b> &nbsp;|&nbsp; {r['company']}<br>
              <small><a href="{r['url']}">{r['url']}</a></small><br><br>
              <img src="cid:screenshot_{r['number']}"
                   style="max-width:100%; border:1px solid #ccc; border-radius:4px;">
            </div>
            """)

    # Section: failed URLs
    if failures:
        html_parts.append("<h3>❌ Failed URLs</h3><table style='border-collapse:collapse;width:100%'>")
        html_parts.append("<tr style='background:#f2f2f2'>"
                          "<th style='padding:8px;border:1px solid #ddd'>Job</th>"
                          "<th style='padding:8px;border:1px solid #ddd'>URL</th>"
                          "<th style='padding:8px;border:1px solid #ddd'>Reason</th></tr>")
        for r in failures:
            html_parts.append(f"""
            <tr>
              <td style='padding:8px;border:1px solid #ddd'>#{r['number']} {r['title']} @ {r['company']}</td>
              <td style='padding:8px;border:1px solid #ddd'><a href='{r['url']}'>{r['url']}</a></td>
              <td style='padding:8px;border:1px solid #ddd;color:red'>{r['error']}</td>
            </tr>""")
        html_parts.append("</table>")

    html_parts.append("</body></html>")
    html_body = "".join(html_parts)

    # ── Assemble the email ───────────────────────────────────
    msg = MIMEMultipart("related")
    msg["Subject"] = f"Job Screenshots — {len(successes)}/{len(results)} captured"
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER

    # Attach HTML body
    msg.attach(MIMEText(html_body, "html"))

    # Attach each screenshot as an inline image
    for r in successes:
        with open(r["screenshot"], "rb") as img_file:
            img = MIMEImage(img_file.read(), _subtype="png")
            img.add_header("Content-ID", f"<screenshot_{r['number']}>")
            img.add_header("Content-Disposition", "inline",
                           filename=os.path.basename(r["screenshot"]))
            msg.attach(img)

    # ── Send via Gmail SMTP ──────────────────────────────────
    print("\n📧 Sending email …")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())

    print(f"✅ Email sent to {EMAIL_RECEIVER}")


# ─────────────────────────────────────────────
# MAIN — ties everything together
# ─────────────────────────────────────────────
def main():
    print("=" * 55)
    print("       JOB SCREENSHOT AGENT — Starting")
    print("=" * 55)

    # 1. Read URLs from Excel
    jobs = load_jobs(EXCEL_FILE)

    # 2. Visit each URL and capture a screenshot
    results = take_screenshots(jobs, SCREENSHOTS_DIR)

    # 3. Print a quick summary to the terminal
    print("\n" + "=" * 55)
    print("SUMMARY")
    print("=" * 55)
    for r in results:
        status = "✅ OK" if r["screenshot"] else f"❌ {r['error']}"
        print(f"  #{r['number']} {r['title']:35s} {status}")

    # 4. Email the results
    send_email(results)

    print("\n🎉 Agent finished!\n")


if __name__ == "__main__":
    main()
