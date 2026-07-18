from playwright.sync_api import sync_playwright
from unstop_login import login_unstop
import time

def save_form_html():
    with sync_playwright() as p:
        browser, page = login_unstop(p)
        if not browser:
            return
        page.goto("https://unstop.com/internships/business-development-internship-mia-solutions-1720304")
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        page.get_by_text("Quick Apply").click()
        time.sleep(3)
        html = page.inner_html("body")
        with open("unstop_form.html", "w") as f:
            f.write(html)
        print("Form HTML saved")
        browser.close()

if __name__ == "__main__":
    save_form_html()