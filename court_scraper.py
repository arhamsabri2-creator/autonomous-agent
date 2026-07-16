import os
from playwright.sync_api import sync_playwright

os.makedirs("cause_lists", exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    print("Opening Delhi High Court cause list page...")
    page.goto("https://delhihighcourt.nic.in/web/cause-lists/cause-list")
    page.wait_for_load_state("networkidle")

    print("Finding all PDF download links...")
    pdf_links = page.locator("a[href$='.pdf']")
    count = pdf_links.count()
    print(f"Found {count} PDF cause lists on this page")

    for i in range(count):
        link = pdf_links.nth(i)
        file_url = link.get_attribute("href")

        if file_url.startswith("/"):
            file_url = "https://delhihighcourt.nic.in" + file_url

        file_name = file_url.split("/")[-1]

        print(f"Downloading ({i+1}/{count}): {file_name}")

        response = context.request.get(file_url)
        save_path = os.path.join("cause_lists", file_name)
        with open(save_path, "wb") as f:
            f.write(response.body())

        print(f"Saved to {save_path}")

    print("All cause lists downloaded successfully!")
    browser.close()