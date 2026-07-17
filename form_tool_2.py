from playwright.sync_api import sync_playwright


def fill_test_login(details):
    try:
        parts = details.split("|")
        username = parts[0].strip().strip('"').strip("'") if len(parts) > 0 else "tomsmith"
        password = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else "SuperSecretPassword!"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://the-internet.herokuapp.com/login")

            page.fill("#username", username)
            page.fill("#password", password)

            page.click("button[type='submit']")
            page.wait_for_timeout(1000)

            result_text = page.inner_text("body")

            browser.close()
            return result_text
    except Exception as e:
        return f"Login form filling failed with error: {str(e)}"