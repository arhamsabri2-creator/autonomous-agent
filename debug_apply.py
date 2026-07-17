import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

email = os.getenv("INTERNSHALA_EMAIL")
password = os.getenv("INTERNSHALA_PASSWORD")

test_link = "https://internshala.com/internship/detail/work-from-home-machine-learning-internship-at-basti-ki-pathshala-foundation1784266938"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://internshala.com/login/user")
    page.fill("#email", email)
    page.fill("#password", password)
    page.click("#login_submit")
    page.wait_for_timeout(3000)
    page.goto(test_link)
    page.wait_for_timeout(3000)
    apply_btn = page.query_selector("#apply_now_btn")
    if apply_btn:
        print("Apply button found:", apply_btn.inner_text())
    else:
        print("Apply button NOT found with #apply_now_btn")
        buttons = page.query_selector_all("button")
        for b in buttons:
            print("Button found:", b.inner_text().strip())
    browser.close()
