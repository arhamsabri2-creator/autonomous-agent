from playwright.sync_api import sync_playwright
from unstop_login import login_unstop
import time

def find_card_selector():
    with sync_playwright() as p:
        browser, page = login_unstop(p)
        if not browser:
            return
        page.goto("https://unstop.com/internships?searchTerm=python")
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        html = page.inner_html("body")
        with open("unstop_page.html", "w") as f:
            f.write(html)
        print("HTML saved")
        browser.close()

if __name__ == "__main__":
    find_card_selector()