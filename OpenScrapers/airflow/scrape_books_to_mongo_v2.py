from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mongo.hooks.mongo import MongoHook

import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
import math

MONGO_CONN_ID = "mongo_books_conn"
DB_NAME = "booksdb"
COLLECTION_NAME = "books"

HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}


def scrape_books(ti):
    """Scrape books and push to XCom."""
    books = []
    START, END = 1, 50

    for page in range(START, END + 1):
        url = f"https://books.toscrape.com/catalogue/page-{page}.html"
        resp = requests.get(url, headers=HEADERS, timeout=10)

        if resp.status_code != 200:
            logging.warning(f"Page {page} missing: {resp.status_code}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("article.product_pod")

        for item in items:
            try:
                books.append({
                    "Title": item.h3.a["title"],
                    "Rating": item.p["class"][1],
                    "Price": item.select_one(".price_color").text.strip(),
                    "Stock_Status": item.select_one(".instock.availability").text.strip(),
                    "ScrapedAt": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logging.exception(f"Error parsing item: {e}")

        logging.info(f"Scraped page {page} — total {len(books)}")

    if not books:
        ti.xcom_push(key="book_data", value=[])
        return

    df = pd.DataFrame(books)
    df.drop_duplicates(subset="Title", inplace=True)

    ti.xcom_push(key="book_data", value=df.to_dict("records"))
    logging.info(f"Pushed {len(df)} records to XCom")


def insert_into_mongo(ti):
    """Insert scraped books into MongoDB using MongoHook."""
    records = ti.xcom_pull(key="book_data", task_ids="scrape_books")

    if not records:
        logging.warning("No records to insert")
        return

    hook = MongoHook(conn_id=MONGO_CONN_ID)
    client = hook.get_conn()
    db = client[DB_NAME]
    col = db[COLLECTION_NAME]

    total = len(records)
    batch_size = 200
    batches = math.ceil(total / batch_size)
    inserted = 0

    for i in range(batches):
        start, end = i * batch_size, (i + 1) * batch_size
        chunk = records[start:end]

        try:
            result = col.insert_many(chunk, ordered=False)
            inserted += len(result.inserted_ids)
            logging.info(f"Inserted batch {i+1}/{batches} ({len(chunk)} rows)")
        except Exception as e:
            logging.exception(f"Insert batch {i+1} failed: {e}")
            raise

    logging.info(f"✔ Successfully inserted {inserted}/{total} records into MongoDB")


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

dag = DAG(
    "scrape_books_every_3min_mongo",
    default_args=default_args,
    description="Scrape books.toscrape.com and store in MongoDB every 3 minutes",
    schedule="*/3 * * * *",
    start_date=datetime(2025, 12, 4),
    catchup=False,
)

scrape_task = PythonOperator(
    task_id="scrape_books",
    python_callable=scrape_books,
    dag=dag,
)

insert_task = PythonOperator(
    task_id="insert_into_mongo",
    python_callable=insert_into_mongo,
    dag=dag,
)

scrape_task >> insert_task
