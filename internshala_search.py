import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

AI_KEYWORDS = [
    "machine learning", "artificial intelligence", "ai ", " ai",
    "data science", "nlp", "deep learning", "python",
    "data analytics", "llm", "generative"
]

def is_ai_related(title):
    title_lower = title.lower()
    for keyword in AI_KEYWORDS:
        if keyword in title_lower:
            return True
    return False

def search_internshala_jobs():
    email = os.getenv("INTERNSHALA_EMAIL")
    password = os.getenv("INTERNSHALA_PASSWORD")

    try:
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

                    if not is_ai_related(title):
                        continue

                    results.append({
                        "title": title,
                        "company": company,
                        "stipend": stipend,
                        "link": link
                    })
                except Exception:
                    continue

            browser.close()

            if len(results) == 0:
                return "No AI-related internships found"

            return results

    except Exception as e:
        return "Search failed with error: " + str(e)
