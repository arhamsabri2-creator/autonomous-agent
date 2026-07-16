import os
from dotenv import load_dotenv
from tavily import TavilyClient
from playwright.sync_api import sync_playwright

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def find_relevant_urls(topic, max_results=3):
    response = tavily_client.search(query=topic, max_results=max_results)
    results = response.get("results", [])

    urls = []
    for result in results:
        url = result.get("url")
        if url:
            urls.append(url)

    return urls


def read_full_page(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=15000)

            text = page.inner_text("body")

            browser.close()
            return text
    except Exception as e:
        return f"[Could not read this page: {str(e)}]"


def deep_research(topic):
    urls = find_relevant_urls(topic, max_results=3)

    if not urls:
        return "No relevant sources found for this topic."

    combined_text = ""

    for url in urls:
        page_text = read_full_page(url)
        combined_text += f"\n\n--- Source: {url} ---\n{page_text}"

    if len(combined_text) > 10000:
        combined_text = combined_text[:10000] + "\n\n[Content cut short - too long to show all at once]"

    return combined_text.strip()