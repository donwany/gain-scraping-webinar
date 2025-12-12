import json
from bs4 import BeautifulSoup
import requests


HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

jubilee_house = "https://presidency.gov.gh/press-releases"
OUTPUT_FILE = "data/press_releases_main.jsonl"

response = requests.get(jubilee_house, headers=HEADERS)
soup = BeautifulSoup(response.text, "html.parser")

urls = [a["href"] for a in soup.select("div.article-i-button a.button-custom")]
print(urls)

def process_article(urls: list):
    """process articles"""
    articles = []

    for url in urls:
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print(f"Failed: {url}")
            continue

        soup_url = BeautifulSoup(r.text, "html.parser")

        title = soup_url.find("h1", class_="h2").get_text(strip=True)
        content = soup_url.find("div", class_="content").get_text(strip=True)
        date_tag = soup_url.find("div", class_="article-date").get_text(strip=True)

        article = {
            "title": title,
            "content": content,
            "link": url,
            "published_date": date_tag
        }

        articles.append(article)

    # Save results as JSON
    # with open("press_releases_main.json", "w", encoding="utf-8") as f:
    #     json.dump(articles, f, ensure_ascii=False, indent=4)
    # print("\nSaved to press_releases_main.json")

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(json.dumps(articles) + "\n")
        print(f"\nSaved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Failed to save data! Error: {e}")

    return json.dumps(articles, indent=4)


if __name__ == '__main__':
    print(process_article(urls=urls))
