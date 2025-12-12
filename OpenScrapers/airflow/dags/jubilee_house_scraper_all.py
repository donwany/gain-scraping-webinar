from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
import time


# =============================================================================
# HEADERS + CONFIG
# =============================================================================
HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/56.0.2924.87 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

POSTGRES_CONN_ID = "books_connection"  # change if needed
TABLE_NAME = "presidency_press_releases"
BASE_URL = "https://presidency.gov.gh/press-releases"
START_PAGE = 2
LAST_PAGE = 16

# =============================================================================
# SAFE HTTP GET (RETRIES)
# =============================================================================
def safe_get(url, max_retries=3, delay=2):
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.raise_for_status()
            return res
        except Exception as e:
            print(f"[ERROR] Failed ({attempt}/{max_retries}) for {url}: {e}")
            if attempt == max_retries:
                return None
            time.sleep(delay)


# =============================================================================
# SCRAPER LOGIC (ALL-IN-ONE)
# =============================================================================
def get_page_urls():
    pages = [BASE_URL]
    pages.extend([f"{BASE_URL}/page/{i}/" for i in range(START_PAGE, LAST_PAGE + 1)])
    return pages


def extract_article_links(page_url):
    print(f"[INFO] Fetching listing page: {page_url}")
    res = safe_get(page_url)
    if not res:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    links = [
        a["href"]
        for a in soup.select("div.article-i-button a.button-custom")
        if a.get("href")
    ]
    print(f"[INFO] Found {len(links)} links")
    return links


def parse_article(url):
    print(f"[INFO] Parsing article: {url}")
    res = safe_get(url)
    if not res:
        return None

    soup = BeautifulSoup(res.text, "html.parser")

    title_tag = soup.find("h1", class_="h2")
    content_tag = soup.find("div", class_="content")
    date_tag = soup.find("div", class_="article-date")

    return {
        "title": title_tag.get_text(strip=True) if title_tag else "",
        "content": content_tag.get_text("\n", strip=True) if content_tag else "",
        "published_date": date_tag.get_text(strip=True) if date_tag else "",
        "link": url,
        "scraped_at": datetime.utcnow().isoformat()
    }


def scrape_press_releases():
    """Scrape all presidency press release pages."""
    page_urls = get_page_urls()
    all_links = []

    for page in page_urls:
        all_links.extend(extract_article_links(page))

    all_links = list(set(all_links))
    print(f"[INFO] Unique article links found: {len(all_links)}")

    results = []
    for i, link in enumerate(all_links, start=1):
        print(f"[{i}/{len(all_links)}] Scraping: {link}")
        article = parse_article(link)
        if article:
            results.append(article)

    return results


# =============================================================================
# STORE INTO POSTGRES
# =============================================================================
def store_articles_in_postgres(**context):
    articles = context["ti"].xcom_pull(task_ids="scrape_press_releases")

    pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id BIGSERIAL PRIMARY KEY,
            title TEXT,
            content TEXT,
            link TEXT UNIQUE,
            published_date TEXT,
            scraped_at TEXT, 
            UNIQUE(title, scraped_at)
        );
    """)

    inserted = 0
    updated = 0

    for article in articles:
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (title, content, link, published_date, scraped_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (link)
            DO UPDATE SET
                title = EXCLUDED.title,
                published_date = EXCLUDED.published_date,
                content = EXCLUDED.content;
        """, (
            article["title"],
            article["content"],
            article["link"],
            article["published_date"],
            article["scraped_at"],
        ))

        if cursor.rowcount == 1:
            inserted += 1
        else:
            updated += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"[DONE] Inserted: {inserted}, Updated: {updated}")


# =============================================================================
# AIRFLOW DAG
# =============================================================================
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 5,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="presidency_scraper_postgres",
    description="Scrape presidency.gov.gh press releases and store in Postgres",
    start_date=datetime(2025, 12, 5),
    schedule_interval="@daily",   # runs every 15 min or @daily "*/60 * * * *"
    catchup=False,
    default_args=default_args,
    tags=["ghana", "scraper", "presidency"],
) as dag:

    scrape_task = PythonOperator(
        task_id="scrape_press_releases",
        python_callable=scrape_press_releases,
    )

    save_task = PythonOperator(
        task_id="save_to_postgres",
        python_callable=store_articles_in_postgres,
        provide_context=True,
    )

    scrape_task >> save_task
