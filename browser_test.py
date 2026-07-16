from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    
    # This creates a "context" - think of it as one continuous browsing session
    context = browser.new_context()
    page = context.new_page()
    
    print("Opening DuckDuckGo...")
    page.goto("https://duckduckgo.com")
    page.fill("input[name='q']", "Playwright browser automation Python")
    page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle")
    
    print("Search done. Saving session (cookies) to a file...")
    context.storage_state(path="session.json")
    
    print("Session saved! Check your folder for session.json")
    
    input("Press Enter in terminal to close browser...")
    browser.close()
    print("Done!")