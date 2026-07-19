import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

IS_HF = os.getenv("SPACE_ID") is not None

def apply_to_internship(link):
    email = os.getenv("INTERNSHALA_EMAIL")
    password = os.getenv("INTERNSHALA_PASSWORD")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=IS_HF)
            page = browser.new_page()
            page.goto("https://internshala.com/login/user")
            page.fill("#email", email)
            page.fill("#password", password)
            page.click("#login_submit")
            page.wait_for_timeout(5000)
            current_url = page.url
            if "login" in current_url:
                browser.close()
                return "Login failed - URL: " + current_url
            page.goto(link)
            page.wait_for_timeout(5000)
            current_url = page.url
            if "registration" in current_url or "login" in current_url:
                browser.close()
                return "Session lost - URL: " + current_url
            try:
                close_btn = page.query_selector(".close-button, .modal-close, .ic-16-cross")
                if close_btn:
                    close_btn.click()
                    page.wait_for_timeout(1000)
            except Exception:
                pass
            apply_btn = page.query_selector("button:has-text('Apply now')")
            if not apply_btn:
                browser.close()
                return "Apply button not found on page: " + link
            page.evaluate("btn => btn.click()", apply_btn)
            page.wait_for_timeout(4000)
            page_text = page.inner_text("body")
            title = page.title()
            if "already applied" in page_text.lower():
                result = "Already applied to this internship"
            elif "application" in page_text.lower() or "submitted" in page_text.lower() or "thank" in page_text.lower():
                result = "Application submitted successfully"
                try:
                    from sheets_tool import log_job_to_sheet
                    log_job_to_sheet(
                        title=title,
                        company="Unknown",
                        platform="Internshala",
                        link=link,
                        status="Applied"
                    )
                except Exception as e:
                    print(f"Sheets logging failed: {e}")
            else:
                result = "Clicked Apply now - current page: " + page.url
            browser.close()
            return result
    except Exception as e:
        return "Apply failed with error: " + str(e)