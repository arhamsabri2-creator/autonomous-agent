import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

IS_HF = os.getenv("SPACE_ID") is not None

def search_internshala_jobs(topic="artificial-intelligence"):
    email = os.getenv("INTERNSHALA_EMAIL")
    password = os.getenv("INTERNSHALA_PASSWORD")

    topic_slug = topic.lower().strip().replace(" ", "-")
    url = "https://internshala.com/internships/keywords-" + topic_slug + "/work-from-home-jobs/"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=IS_HF)
            page = browser.new_page()

            page.goto("https://internshala.com/login/user")
            page.fill("#email", email)
            page.fill("#password", password)
            page.click("#login_submit")
            page.wait_for_timeout(5000)

            page.goto(url)
            page.wait_for_timeout(4000)

            cards = page.query_selector_all(".individual_internship")
            results = []

            for card in cards:
                try:
                    title_el = card.query_selector("a.job-title-href")
                    company_el = card.query_selector("p.company-name")
                    stipend_el = card.query_selector(".stipend")

                    title = title_el.inner_text().strip() if title_el else "N/A"
                    company = company_el.inner_text().strip() if company_el else "N/A"
                    stipend = stipend_el.inner_text().strip() if stipend_el else "N/A"
                    link = "https://internshala.com" + title_el.get_attribute("href") if title_el else "N/A"

                    results.append({"title": title, "company": company, "stipend": stipend, "link": link})
                except Exception:
                    continue

            browser.close()

            if len(results) == 0:
                return "No internships found for topic: " + topic

            return results

    except Exception as e:
        return "Search failed with error: " + str(e)
