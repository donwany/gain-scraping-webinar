from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import logging

HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

JUBILEE_HOUSE = "https://presidency.gov.gh/press-releases"
POSTGRES_CONN_ID = "books_connection"  # change if needed
TABLE_NAME = "press_releases"


# -----------------------------------------------------
# Scrape main page -> extract article URLs
# -----------------------------------------------------
def fetch_article_urls():
    try:
        r = requests.get(JUBILEE_HOUSE, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")
        urls = [a["href"] for a in soup.select("div.article-i-button a.button-custom")]
        return urls
    except Exception as e:
        logging.error(f"Failed to fetch main page: {e}")
        return []


# -----------------------------------------------------
# Scrape a single article page
# -----------------------------------------------------
def scrape_article(url: str) -> dict | None:
    try:
        r = requests.get(url, headers=HEADERS)
        if r.status_code != 200:
            logging.warning(f"Skipping {url}, status {r.status_code}")
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
            "scraped_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logging.error(f"Scrape failed for {url}: {e}")
        return None


# -----------------------------------------------------
# Main Airflow task: scrape + save to Postgres
# -----------------------------------------------------
def collect_press_releases(**context):
    pg = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    conn = pg.get_conn()
    cursor = conn.cursor()

    # Create table if not exists
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id BIGSERIAL PRIMARY KEY,
        title TEXT,
        content TEXT,
        link TEXT UNIQUE,
        published_date TEXT,
        scraped_at TEXT,
        UNIQUE(title, scraped_at)
    );
    """
    cursor.execute(create_table_sql)
    conn.commit()

    urls = fetch_article_urls()
    logging.info(f"Found {len(urls)} URLs")

    inserted_count = 0

    for url in urls:
        article = scrape_article(url)
        if not article:
            continue

        try:
            cursor.execute(f"""
                INSERT INTO {TABLE_NAME} (title, content, link, published_date, scraped_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (link) DO NOTHING;
            """, (
                article["title"],
                article["content"],
                article["link"],
                article["published_date"],
                article["scraped_at"]
            ))
            conn.commit()

            if cursor.rowcount > 0:
                inserted_count += 1
                logging.info(f"[INSERTED] {article['title']}")
            else:
                logging.info(f"[DUPLICATE] {article['link']}")

        except Exception as e:
            logging.error(f"[DB ERROR] {e}")
            conn.rollback()

    logging.info(f"[DONE] Inserted {inserted_count} new articles")
    return inserted_count


# -----------------------------------------------------
# DAG definition
# -----------------------------------------------------
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 5,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "dag_jubilee_scraper_postgres",
    default_args=default_args,
    description="Scrape Jubilee House press releases into Postgres",
    schedule_interval="@daily",  # every 15 minutes "*/60 * * * *"
    start_date=datetime(2025, 12, 5),
    catchup=False,
) as dag:

    scrape_task = PythonOperator(
        task_id="collect_press_releases",
        python_callable=collect_press_releases,
    )
