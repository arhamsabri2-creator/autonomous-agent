from playwright.sync_api import sync_playwright
from unstop_login import login_unstop
import os
import time
from dotenv import load_dotenv

load_dotenv()

def save_page2_html():
    with sync_playwright() as p:
        browser, page = login_unstop(p)
        if not browser:
            return
        page.goto("https://unstop.com/internships/business-development-internship-mia-solutions-1720304")
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        page.get_by_text("Quick Apply").click()
        time.sleep(3)
        page.locator("input").nth(0).fill("Arham")
        time.sleep(0.3)
        page.locator("input").nth(1).fill("Sabri")
        time.sleep(0.3)
        page.locator("input[type=email]").first.fill(os.getenv("UNSTOP_EMAIL", ""))
        time.sleep(0.3)
        page.locator("input[type=tel]").first.fill(os.getenv("UNSTOP_MOBILE", ""))
        time.sleep(0.3)
        page.get_by_text("Male", exact=True).click()
        time.sleep(0.3)
        page.get_by_text("Next").click()
        time.sleep(3)
        html = page.inner_html("body")
        with open("unstop_form_page2.html", "w") as f:
            f.write(html)
        print("Page 2 HTML saved")
        browser.close()

if __name__ == "__main__":
    save_page2_html()