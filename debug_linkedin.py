import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

email = os.getenv("LINKEDIN_EMAIL")
password = os.getenv("LINKEDIN_PASSWORD")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
    context = browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", viewport={"width": 1280, "height": 800})
    page = context.new_page()
    page.goto("https://www.linkedin.com/login")
    page.wait_for_timeout(3000)
    page.fill("#username", email)
    page.fill("#password", password)
    page.click("button[type=submit]")
    page.wait_for_timeout(5000)
    print("URL after login:", page.url)
    page.goto("https://www.linkedin.com/jobs/search/?keywords=python&f_AL=true&f_WT=2")
    page.wait_for_timeout(4000)
    jobs = page.query_selector_all(".job-card-container")
    print("Job cards found:", len(jobs))
    browser.close()