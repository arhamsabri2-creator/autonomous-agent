import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

def apply_to_internship(link):
    email = os.getenv("INTERNSHALA_EMAIL")
    password = os.getenv("INTERNSHALA_PASSWORD")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://internshala.com/login/user")
            page.fill("#email", email)
            page.fill("#password", password)
            page.click("#login_submit")
            page.wait_for_timeout(3000)

            page.goto(link)
            page.wait_for_timeout(3000)

            apply_btn = page.query_selector("button:has-text('Apply now')")

            if not apply_btn:
                browser.close()
                return "Apply button not found on page: " + link

            apply_btn.click()
            page.wait_for_timeout(3000)

            current_url = page.url
            page_text = page.inner_text("body")

            if "already applied" in page_text.lower():
                result = "Already applied to this internship"
            elif "application" in page_text.lower() or "submitted" in page_text.lower():
                result = "Application submitted successfully"
            else:
                result = "Clicked Apply now - current page: " + current_url

            browser.close()
            return result

    except Exception as e:
        return "Apply failed with error: " + str(e)
