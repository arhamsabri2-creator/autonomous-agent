from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    print("Opening demo login page...")
    page.goto("https://the-internet.herokuapp.com/login")
    
    print("Filling username...")
    page.fill("#username", "tomsmith")
    
    print("Filling password...")
    page.fill("#password", "SuperSecretPassword!")
    
    print("Clicking login button...")
    page.click("button[type='submit']")
    
    page.wait_for_load_state("networkidle")
    
    print("Page title after login:", page.title())
    print("Current URL:", page.url)
    
    # Save this logged-in session
    context.storage_state(path="login_session.json")
    print("Logged-in session saved!")
    
    input("Press Enter in terminal to close browser...")
    browser.close()