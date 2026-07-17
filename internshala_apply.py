import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

IS_HF = os.getenv("SPACE_ID") is not None

def apply_to_internship(link):
    email = os.getenv("INTERNSHALA_EMAIL")
    password = os.getenv("INTERNSHALA_PASSWORD")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=IS_HF)
            page = browser.new_page()

            page.goto("https://internshala.com/login/user")
            page.fill("#email", email)
            page.fill("#password", password)
            page.click("#login_submit")
            page.wait_for_timeout(5000)

            current_url = page.url
            if "login" in current_url:
                browser.close()
                return "Login failed - URL: " + current_url

            page.goto(link)
            page.wait_for_timeout(5000)

            current_url = page.url
            if "registration" in current_url or "login" in current_url:
                browser.close()
                return "Session lost after navigation - URL: " + current_url

            try:
                close_btn = page.query_selector(".close-button, .modal-close, button[aria-label='Close'], .ic-16-cross")
                if close_btn:
                    close_btn.click()
                    page.wait_for_timeout(1000)
            except Exception:
                pass

            apply_btn = page.query_selector("button:has-text('Apply now')")

            if not apply_btn:
                browser.close()
                return "Apply button not found on page: " + link

            page.evaluate("btn => btn.click()", apply_btn)
            page.wait_for_timeout(4000)

            page_text = page.inner_text("body")

            if "already applied" in page_text.lower():
                result = "Already applied to this internship"
            elif
cat > internshala_search.py << 'PYEOF'
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

IS_HF = os.getenv("SPACE_ID") is not None

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
            browser = p.chromium.launch(headless=IS_HF)
            page = browser.new_page()

            page.goto("https://internshala.com/login/user")
            page.fill("#email", email)
            page.fill("#password", password)
            page.click("#login_submit")
            page.wait_for_timeout(5000)

            page.goto("https://internshala.com/internships/artificial-intelligence-internship/work-from-home-jobs/")
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
