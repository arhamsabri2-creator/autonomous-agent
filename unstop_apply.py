from playwright.sync_api import sync_playwright
from unstop_login import login_unstop
import os
import time
from dotenv import load_dotenv

load_dotenv()

def apply_unstop(job_url):
    first_name = os.getenv("UNSTOP_FIRST_NAME", "Arham")
    last_name = os.getenv("UNSTOP_LAST_NAME", "Sabri")
    email = os.getenv("UNSTOP_EMAIL", "")
    mobile = os.getenv("UNSTOP_MOBILE", "")
    gender = os.getenv("UNSTOP_GENDER", "Male")
    location = os.getenv("UNSTOP_LOCATION", "Delhi")
    organization = os.getenv("UNSTOP_ORGANIZATION", "Self")
    user_type = os.getenv("UNSTOP_USER_TYPE", "College Students")
    skills = os.getenv("UNSTOP_SKILLS", "Python")
    differently_abled = os.getenv("UNSTOP_DIFFERENTLY_ABLED", "No")
    with sync_playwright() as p:
        browser, page = login_unstop(p)
        if not browser:
            print("Login failed")
            return False
        page.goto(job_url)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        page.get_by_text("Quick Apply").click()
        time.sleep(3)
        print("Filling page 1...")
        inputs = page.locator("input")
        inputs.nth(0).fill(first_name)
        time.sleep(0.3)
        inputs.nth(1).fill(last_name)
        time.sleep(0.3)
        page.locator("input[type=email]").first.fill(email)
        time.sleep(0.3)
        page.locator("input[type=tel]").first.fill(mobile)
        time.sleep(0.3)
        page.get_by_text(gender, exact=True).click()
        time.sleep(0.5)
        try:
            loc_box = page.locator(".locations").first
            loc_box.click()
            time.sleep(1)
            loc_box.locator("input").type(location, delay=80)
            time.sleep(2)
            page.keyboard.press("ArrowDown")
            time.sleep(0.5)
            page.keyboard.press("Enter")
            time.sleep(1)
            print("Location done")
        except Exception as e:
            print(f"Location failed: {e}")
        page.get_by_text("Next").click()
        time.sleep(3)
        print("Filling page 2...")
        try:
            all_visible_inputs = page.locator("input:visible").all()
            for inp in all_visible_inputs:
                if inp.get_attribute("type") not in ["email","tel","checkbox","radio"]:
                    inp.click()
                    inp.fill(organization)
                    print("Organization filled")
                    break
        except Exception as e:
            print(f"Organization failed: {e}")
        try:
            page.get_by_text(differently_abled, exact=True).click()
            time.sleep(0.3)
        except Exception as e:
            print(f"Differently abled failed: {e}")
        try:
            page.get_by_text(user_type, exact=True).click()
            time.sleep(0.3)
        except Exception as e:
            print(f"User type failed: {e}")
        try:
            skills_input = page.locator("input[placeholder*=kill]").first
            skills_input.click()
            skills_input.type(skills, delay=80)
            time.sleep(2)
            page.locator("li").filter(has_text=skills).first.click()
            time.sleep(0.5)
            page.keyboard.press("Escape")
            time.sleep(0.5)
            print("Skills done")
        except Exception as e:
            print(f"Skills failed: {e}")
        try:
            page.evaluate("document.getElementById(chr(39)+acceptance-input+chr(39)).click()")
            time.sleep(0.5)
            print("Terms accepted")
        except Exception as e:
            print(f"Terms failed: {e}")
        page.screenshot(path="unstop_page2_filled.png")
        page.get_by_text("Next").click()
        time.sleep(3)
        page.screenshot(path="unstop_page3.png")
        print("Done")
        browser.close()
        return True

if __name__ == "__main__":
    test_url = "https://unstop.com/internships/business-development-internship-mia-solutions-1720304"
    apply_unstop(test_url)