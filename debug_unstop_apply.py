from playwright.sync_api import sync_playwright
from unstop_login import login_unstop
import time

def debug_unstop_apply():
    with sync_playwright() as p:
        browser, page = login_unstop(p)
        if not browser:
            return
        test_url = "https://unstop.com/internships/business-development-internship-mia-solutions-1720304"
        print("Opening job page...")
        page.goto(test_url)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        print("Clicking Quick Apply...")
        try:
            page.get_by_text("Quick Apply").click()
            time.sleep(3)
            page.screenshot(path="unstop_after_apply_click.png")
            print("Screenshot saved")
        except Exception as e:
            print(f"Click failed: {e}")
        browser.close()

if __name__ == "__main__":
    debug_unstop_apply()