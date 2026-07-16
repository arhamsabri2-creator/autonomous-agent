import os
from datetime import date
from playwright.sync_api import sync_playwright
import pdfplumber

BASE_FOLDER = "cause_lists"


def already_downloaded_today():
    today_str = str(date.today())
    folder = os.path.join(BASE_FOLDER, today_str)

    if os.path.exists(folder) and len(os.listdir(folder)) > 0:
        return True, folder
    else:
        return False, folder


def download_cause_lists(folder):
    os.makedirs(folder, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://delhihighcourt.nic.in/web/cause-lists/cause-list")
        page.wait_for_load_state("networkidle")

        pdf_links = page.locator("a[href$='.pdf']")
        count = pdf_links.count()

        for i in range(count):
            link = pdf_links.nth(i)
            file_url = link.get_attribute("href")

            if file_url.startswith("/"):
                file_url = "https://delhihighcourt.nic.in" + file_url

            file_name = file_url.split("/")[-1]

            response = context.request.get(file_url)
            save_path = os.path.join(folder, file_name)
            with open(save_path, "wb") as f:
                f.write(response.body())

        browser.close()


def read_pdfs_as_text(folder):
    all_text = ""

    for file_name in os.listdir(folder):
        if file_name.endswith(".pdf"):
            file_path = os.path.join(folder, file_name)
            all_text += f"\n\n--- {file_name} ---\n"

            try:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages[:3]:
                        text = page.extract_text()
                        if text:
                            all_text += text + "\n"
            except Exception as e:
                all_text += f"[Could not read this file: {str(e)}]\n"

    return all_text.strip()


def check_court_cause_list(query=""):
    already_done, folder = already_downloaded_today()

    if already_done:
        status = "Using today's cause lists, already downloaded earlier."
    else:
        status = "Downloading today's cause lists from the court website..."
        download_cause_lists(folder)

    text = read_pdfs_as_text(folder)

    if len(text) > 8000:
        text = text[:8000] + "\n\n[Content cut short - too long to show all at once]"

    return f"{status}\n\nCause List Content:\n{text}"