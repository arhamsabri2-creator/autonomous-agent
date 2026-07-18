from playwright.sync_api import sync_playwright
from unstop_login import login_unstop
import time

def search_unstop(topic="python", max_results=5):
    with sync_playwright() as p:
        browser, page = login_unstop(p)
        if not browser:
            print("Login failed")
            return []
        url = f"https://unstop.com/internships?searchTerm={topic}"
        print(f"Searching Unstop for: {topic}")
        page.goto(url)
        page.wait_for_load_state("networkidle")
        time.sleep(3)
        titles = page.locator("h3[itemprop=name]")
        count = titles.count()
        print(f"Found {count} listings")
        if count == 0:
            print("No listings found")
            browser.close()
            return []
        q = chr(39)
        sel = "a[href*=" + q + "/internships/" + q + "]"
        all_links = page.locator(sel)
        link_count = all_links.count()
        hrefs = []
        for j in range(link_count):
            h = all_links.nth(j).get_attribute("href")
            if h and h not in hrefs:
                hrefs.append(h)
        results = []
        for i in range(min(count, max_results)):
            try:
                title = titles.nth(i).inner_text().strip()
                try:
                    company = page.locator("p.single-wrap").nth(i).inner_text().strip()
                except:
                    company = "Unknown Company"
                link = f"https://unstop.com{hrefs[i]}" if i < len(hrefs) else "No link"
                results.append({"title": title, "company": company, "link": link})
                print(f"{i+1}. {title} | {company}")
                print(f"   {link}")
            except Exception as e:
                print(f"Card {i} error: {e}")
        browser.close()
        return results

if __name__ == "__main__":
    search_unstop("python", 5)