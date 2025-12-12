import json
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient, errors

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

# ------------------------------------------
# MongoDB connection
# ------------------------------------------
def get_mongo_collection(
    username="admin",
    password="admin",
    host="localhost",
    port=27017,
    db_name="jubilee_house",
    collection_name="press_releases",
):
    # MongoDB connection URI with authentication
    uri = f"mongodb://{username}:{password}@{host}:{port}/"
    client = MongoClient(uri)
    db = client[db_name]
    collection = db[collection_name]
    # Ensure unique links
    collection.create_index("link", unique=True)
    return collection


# ------------------------------------------
# Scrape Main Page → Get Article URLs
# ------------------------------------------
def fetch_article_urls():
    response = requests.get(JUBILEE_HOUSE, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")
    urls = [a["href"] for a in soup.select("div.article-i-button a.button-custom")]
    return urls

# ------------------------------------------
# Scrape a Single Article Page
# ------------------------------------------
def scrape_article(url: str) -> dict | None:
    try:
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            print(f"[WARN] Skipping {url}, status {r.status_code}")
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.find("h1", class_="h2").get_text(strip=True)
        content = soup.find("div", class_="content").get_text(strip=True)
        p_date = soup.find("div", class_="article-date").get_text(strip=True)

        return {
            "title": title,
            "content": content,
            "link": url,
            "published_date": p_date,
        }

    except Exception as e:
        print(f"[ERROR] Failed scraping {url}: {e}")
        return None


# ------------------------------------------
# Main Scraper Function (For Airflow Task)
# ------------------------------------------
def collect_press_releases(**context):
    """
    This is the function Airflow will call (PythonOperator).
    """
    collection = get_mongo_collection()
    urls = fetch_article_urls()

    print(f"[INFO] Found {len(urls)} URLs")

    inserted_count = 0

    for url in urls:
        article = scrape_article(url)
        if not article:
            continue

        # Insert into MongoDB
        try:
            collection.insert_one(article)
            inserted_count += 1
            print(f"[INSERTED] {article['title']}")
        except errors.DuplicateKeyError:
            print(f"[DUPLICATE] {url} already exists")
        except Exception as e:
            print(f"[DB ERROR] {e}")

    print(f"[DONE] Inserted {inserted_count} new articles")

    return inserted_count
