import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

email = os.getenv("INTERNSHALA_EMAIL")
password = os.getenv("INTERNSHALA_PASSWORD")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://internshala.com/login/user")
    page.fill("#email", email)
    page.fill("#password", password)
    page.click("#login_submit")
    page.wait_for_timeout(3000)
    page.goto("https://internshala.com/internships/artificial-intelligence-internship/work-from-home-jobs/")
    page.wait_for_timeout(3000)
    cards = page.query_selector_all(".individual_internship")
    print(cards[0].inner_html())
    browser.close()
