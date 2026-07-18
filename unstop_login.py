from playwright.sync_api import sync_playwright
import json
import os
import time

def login_unstop(playwright):
    is_hf = os.getenv("SPACE_ID") is not None
    browser = playwright.chromium.launch(headless=is_hf)
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    context = browser.new_context(user_agent=ua)
    cookie_file = "unstop_cookies.json"
    if not os.path.exists(cookie_file):
        print("ERROR: unstop_cookies.json not found")
        browser.close()
        return None, None
    with open(cookie_file, "r") as f:
        cookies = json.load(f)
    context.add_cookies(cookies)
    print(f"Loaded {len(cookies)} cookies")
    page = context.new_page()
    print("Navigating to Unstop dashboard...")
    page.goto("https://unstop.com/dashboard")
    page.wait_for_load_state("networkidle")
    time.sleep(3)
    current_url = page.url
    print(f"Current URL: {current_url}")
    if "login" in current_url or "auth" in current_url:
        print("WARNING: Cookies expired — run save_unstop_cookies.py again")
        page.screenshot(path="unstop_login_failed.png")
        browser.close()
        return None, None
    print("SUCCESS: Logged in to Unstop via cookies")
    page.screenshot(path="unstop_login_success.png")
    return browser, page

if __name__ == "__main__":
    with sync_playwright() as p:
        browser, page = login_unstop(p)
        if browser:
            print("Login test passed")
            time.sleep(3)
            browser.close()
        else:
            print("Login test FAILED")