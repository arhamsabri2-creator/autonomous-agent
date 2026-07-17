import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

def apply_to_internship(link):
    email = os.getenv("INTERNSHALA_EMAIL")
    password = os.getenv("INTERNSHALA_PASSWORD")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()

            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            page.goto("https://internshala.com/login/user")
            page.wait_for_timeout(2000)
            page.fill("#email", email)
            page.fill("#password", password)
            page.click("#login_submit")
            page.wait_for_timeout(6000)

            current_url = page.url
            if "login" in current_url:
                browser.close()
                return "Login failed - bot detection or wrong credentials. URL: " + current_url

            page.goto(link)
            page.wait_for_timeout(5000)

            current_url = page.url
            if "registration" in current_url or "login" in current_url:
                browser.close()
                return "Session lost after navigation - URL: " + current_url

            try:
                close_btn = page.query_selector(".close-button, .modal-close, button[aria-label='Close'], .ic-16-cross")
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

            if "already applied" in page_text.lower():
                result = "Already applied to this internship"
            elif "application" in page_text.lower() or "submitted" in page_text.lower() or "thank" in page_text.lower():
                result = "Application submitted successfully"
            else:
                result = "Clicked Apply now - current page: " + page.url

            browser.close()
            return result

    except Exception as e:
        return "Apply failed with error: " + str(e)
