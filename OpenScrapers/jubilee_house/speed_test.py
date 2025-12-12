import json
from bs4 import BeautifulSoup
import requests
from pymongo import MongoClient

HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

JUBILEE_HOUSE = "https://presidency.gov.gh/press-releases/"

# -------------------------------
#  MongoDB Setup
# -------------------------------
client = MongoClient("mongodb://localhost:27017/")
db = client["jubilee_house"]
collection = db["press_releases"]

# Ensure no duplicates (based on link)
collection.create_index("link", unique=True)

# -------------------------------
#  Scrape Main Page
# -------------------------------
response = requests.get(JUBILEE_HOUSE, headers=HEADERS)
soup = BeautifulSoup(response.text, "html.parser")

urls = [a["href"] for a in soup.select("div.article-i-button a.button-custom")]
print("Found URLs:", len(urls))

articles = []

# -------------------------------
#  Scrape Each Article
# -------------------------------
for url in urls:
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        print(f"Skipping {url}, status: {r.status_code}")
        continue

    soup_url = BeautifulSoup(r.text, "html.parser")

    title = soup_url.find("h1", class_="h2").get_text(strip=True)
    content = soup_url.find("div", class_="content").get_text(strip=True)
    p_date = soup_url.find("div", class_="article-date").get_text(strip=True)

    article = {
        "title": title,
        "content": content,
        "link": url,
        "published_date": p_date,
    }

    # Save to MongoDB
    try:
        collection.insert_one(article)
        print(f"Inserted: {title}")
    except Exception as e:
        print(f"Duplicate or error inserting {url}: {e}")

    articles.append(article)

# -------------------------------
#  Preview Output
# -------------------------------
if __name__ == "__main__":
    print(json.dumps(articles, indent=4))
