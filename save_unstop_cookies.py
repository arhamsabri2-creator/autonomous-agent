from playwright.sync_api import sync_playwright
import json
import time

def save_unstop_cookies():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        print("Opening Unstop login page...")
        page.goto("https://unstop.com/auth/login")
        print("")
        print(">>> LOGIN MANUALLY IN THE BROWSER WINDOW <<<")
        print(">>> After you are fully logged in, come back here and press ENTER <<<")
        input()
        cookies = context.cookies()
        with open("unstop_cookies.json", "w") as f:
            json.dump(cookies, f)
        print(f"Saved {len(cookies)} cookies to unstop_cookies.json")
        browser.close()

if __name__ == "__main__":
    save_unstop_cookies()