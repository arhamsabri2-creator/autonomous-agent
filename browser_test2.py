from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    
    # Load the saved session instead of starting fresh
    context = browser.new_context(storage_state="session.json")
    page = context.new_page()
    
    print("Opening DuckDuckGo using the SAVED session...")
    page.goto("https://duckduckgo.com")
    
    page.wait_for_load_state("networkidle")
    print("Page title:", page.title())
    
    input("Press Enter in terminal to close browser...")
    browser.close()
    print("Done!")