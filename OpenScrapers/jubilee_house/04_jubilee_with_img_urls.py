import json
import time

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

BASE_URL = "https://presidency.gov.gh/press-releases/"
OUTPUT_FILE = "data/press_releases_with_img_urls.jsonl"
START_PAGE = 2
LAST_PAGE = 17

def get_page_urls():
    """Collect all listing pages: main page + pages 2–16"""
    pages = [BASE_URL]  # main page
    for i in range(START_PAGE, LAST_PAGE + 1):
        pages.append(f"https://presidency.gov.gh/press-releases/page/{i}/")
    return pages


def extract_article_links(page_url):
    """Extract all article URLs from a listing page"""
    res = requests.get(page_url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    urls = [a["href"] for a in soup.select("div.article-i-button a.button-custom")]
    return urls


def extract_images(soup, base_url):
    """Extract all image URLs (src + srcset) and return absolute URLs"""
    urls = set()
    imgs = soup.find_all("img")

    for img in imgs:
        # Direct src
        if img.get("src"):
            urls.add(urljoin(base_url, img["src"]))

        # srcset (multiple images)
        if img.get("srcset"):
            parts = img["srcset"].split(",")
            for p in parts:
                url = p.strip().split(" ")[0]
                urls.add(urljoin(base_url, url))

    return list(urls)


def parse_article(url):
    """Parse title, date, content, and images of a single article"""
    res = requests.get(url, headers=HEADERS)
    time.sleep(1)
    soup = BeautifulSoup(res.text, "html.parser")

    title_tag = soup.find("h1", class_="h2")
    content_tag = soup.find("div", class_="content")
    date_tag = soup.find("div", class_="article-date")

    title = title_tag.get_text(strip=True) if title_tag else ""
    content = content_tag.get_text("\n", strip=True) if content_tag else ""
    date_text = date_tag.get_text(strip=True) if date_tag else ""

    image_urls = extract_images(soup, url)

    return {
        "title": title,
        "date": date_text,
        "content": content,
        "link": url,
        "image_urls": image_urls,
    }


def scrape_press_releases():
    all_data = []

    page_urls = get_page_urls()
    print(f"Scraping {len(page_urls)} listing pages...")

    # Get all links
    all_links = []
    for page in page_urls:
        print(f"Collecting article links from: {page}")
        all_links.extend(extract_article_links(page))

    # Remove duplicates
    all_links = list(set(all_links))
    print(f"Total articles collected: {len(all_links)}")

    for i, link in enumerate(all_links, 1):
        print(f"[{i}/{len(all_links)}] Scraping article: {link}")
        data = parse_article(link)
        all_data.append(data)

    # Save JSON file
    # with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    #     json.dump(all_data, f, indent=4, ensure_ascii=False)

    # Save JSONL file
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(all_data) + "\n")
    except Exception as e:
        print(f"Failed to save data! Error: {e}")

    print("Data saved successfully!")


if __name__ == "__main__":
    scrape_press_releases()
