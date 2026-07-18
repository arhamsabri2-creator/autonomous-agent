from playwright.sync_api import sync_playwright
import time

def debug_unstop():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        print("Navigating to Unstop login...")
        page.goto("https://unstop.com/auth/login")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        print("Clicking Ok Continue...")
        try:
            page.get_by_text("Ok, Continue").click()
            time.sleep(1)
        except Exception as e:
            print(f"Ok Continue failed: {e}")
        print("Clicking Im a Candidate...")
        try:
            page.get_by_text("I'm a Candidate").click()
            time.sleep(2)
        except Exception as e:
            print(f"Candidate click failed: {e}")
        print("Clicking Login via Password...")
        try:
            page.get_by_text("Login via Password").click()
            time.sleep(2)
        except Exception as e:
            print(f"Login via Password click failed: {e}")
        page.screenshot(path="unstop_after_password_link.png")
        print("Screenshot saved")
        print("Checking for email and password inputs...")
        try:
            page.locator("input[type=email], input[name=email]").first.wait_for(timeout=5000)
            print("SUCCESS: Email input found")
        except Exception as e:
            print(f"Email input not found: {e}")
        try:
            page.locator("input[type=password]").first.wait_for(timeout=5000)
            print("SUCCESS: Password input found")
        except Exception as e:
            print(f"Password input not found: {e}")
        page.screenshot(path="unstop_final.png")
        print("Done. Check unstop_final.png")
        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    debug_unstop()