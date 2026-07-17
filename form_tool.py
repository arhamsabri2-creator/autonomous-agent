from playwright.sync_api import sync_playwright


def fill_government_form(details):
    try:
        parts = details.split("|")
        name = parts[0].strip()
        comment = parts[1].strip() if len(parts) > 1 else ""

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://demoqa.com/text-box")

            page.fill("#userName", name)
            page.fill("#userEmail", "test@example.com")
            page.fill("#currentAddress", comment)
            page.fill("#permanentAddress", comment)

            page.click("#submit")
            page.wait_for_timeout(1000)

            result_text = page.inner_text("body")

            browser.close()
            return result_text
    except Exception as e:
        return f"Form filling failed with error: {str(e)}"