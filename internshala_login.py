import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

def login_to_internshala():
    email = os.getenv("INTERNSHALA_EMAIL")
    password = os.getenv("INTERNSHALA_PASSWORD")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto("https://internshala.com/login/user")
            page.fill("#email", email)
            page.fill("#password", password)
            page.click("#login_submit")
            page.wait_for_timeout(3000)

            current_url = page.url

            if "login" in current_url:
                result = "Login likely failed - still on login page"
            else:
                result = "Login appears successful - redirected to " + current_url

            browser.close()
            return result

    except Exception as e:
        return "Internshala login failed with error: " + str(e)
