from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    print("Opening file download page...")
    page.goto("https://the-internet.herokuapp.com/download")

    print("Clicking a file to download...")
    with page.expect_download() as download_info:
        page.click("a[href$='.txt']")
    download = download_info.value

    save_path = "downloaded_file.txt"
    download.save_as(save_path)
    print(f"File downloaded and saved as {save_path}")

    print("Opening file upload page...")
    page.goto("https://the-internet.herokuapp.com/upload")

    print("Uploading the file we just downloaded...")
    page.set_input_files("#file-upload", save_path)
    page.click("#file-submit")

    page.wait_for_load_state("networkidle")
    print("Upload result page title:", page.title())

    input("Press Enter in terminal to close browser...")
    browser.close()