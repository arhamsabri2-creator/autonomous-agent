from playwright.sync_api import sync_playwright
from unstop_login import login_unstop
import time

def debug_unstop_search():
    with sync_playwright() as p:
        browser, page = login_unstop(p)
        if not browser:
            print("Login failed")
            return
        print("Going to search page...")
        page.goto("https://unstop.com/internships?searchTerm=python")
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        page.screenshot(path="unstop_search_debug.png")
        print("Screenshot saved")
        print("Title:", page.title())
        print("URL:", page.url)
        browser.close()

if __name__ == "__main__":
    debug_unstop_search()