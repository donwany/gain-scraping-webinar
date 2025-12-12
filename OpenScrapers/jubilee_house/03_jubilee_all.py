import json
import time

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

BASE_URL = "https://presidency.gov.gh/press-releases"
OUTPUT_FILE = "data/press_releases_all.jsonl"
START_PAGE = 2
LAST_PAGE = 16

def get_page_urls():
    """Collect all listing pages: main page + pages 2–16"""
    pages = [BASE_URL]  # main page (page 1)

    # Add pages 2 to 16
    for i in range(START_PAGE, LAST_PAGE + 1):
        pages.append(f"{BASE_URL}/page/{i}/")

    return pages


def extract_article_links(page_url):
    """Extract all article URLs from a listing page"""
    res = requests.get(page_url, headers=HEADERS)
    time.sleep(1)
    soup = BeautifulSoup(res.text, "html.parser")

    links = [a["href"] for a in soup.select("div.article-i-button a.button-custom")]
    return links


def parse_article(url):
    """Parse title + content of a single article"""
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")

    title_tag = soup.find("h1", class_="h2")
    content_tag = soup.find("div", class_="content")

    title = title_tag.get_text(strip=True) if title_tag else ""
    content = content_tag.get_text("\n", strip=True) if content_tag else ""

    # Extract date if available
    date_tag = soup.find("div", class_="article-date")

    date_text = ""
    if date_tag:
        date_text = date_tag.get_text(strip=True)

    return {
        "title": title,
        "date": date_text,
        "content": content,
        "link": url,
    }


def scrape_press_releases():
    all_data = []

    page_urls = get_page_urls()
    print(f"Scraping {len(page_urls)} listing pages...")

    # Extract article links from all pages
    all_links = []
    for page in page_urls:
        print(f"Getting article links from: {page}")
        links = extract_article_links(page)
        all_links.extend(links)

    print(f"Total articles found: {len(all_links)}")

    # Remove duplicates if any
    all_links = list(set(all_links))

    # Parse each article page
    for i, link in enumerate(all_links, start=1):
        print(f"[{i}/{len(all_links)}] Parsing: {link}")
        data = parse_article(link)
        all_data.append(data)

    # Save JSON
    # try:
    #     with open("press_releases_all.json", "w", encoding="utf-8") as f:
    #         json.dump(all_data, f, indent=4, ensure_ascii=False)
    # except Exception as e:
    #     print(f"Failed to save data! Error: {e}")

    # Save JSONL file
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(all_data) + "\n")
    except Exception as e:
        print(f"Failed to save data! Error: {e}")

    print("Saved to press_releases_all.")


if __name__ == "__main__":
    scrape_press_releases()
