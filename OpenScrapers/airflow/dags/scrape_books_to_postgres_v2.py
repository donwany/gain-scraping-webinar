from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

import requests
from bs4 import BeautifulSoup
import pandas as pd
import math
import logging

HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

POSTGRES_CONN_ID = "books_connection"
TABLE_NAME = "books"
START = 1
END = 50

def scrape_and_push_xcom(ti):
    """Scrape books and push records (list of dicts) to XCom."""
    books = []
    for page in range(START, END + 1):
        url = f"https://books.toscrape.com/catalogue/page-{page}.html"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            logging.warning("Page %s returned status %s - skipping", page, resp.status_code)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("article.product_pod")

        for item in items:
            try:
                title = item.h3.a["title"]
                rating = item.p["class"][1]
                price = item.select_one(".price_color").text.strip()
                stock = item.select_one(".instock.availability").text.strip()
            except Exception as e:
                logging.exception("Failed to parse an item on page %s: %s", page, e)
                continue

            books.append({
                "Title": title,
                "Rating": rating,
                "Price": price.encode("ascii", errors="ignore").decode(),
                "Stock_Status": stock,
                # store as ISO string to avoid type problems
                "ScrapedAt": datetime.utcnow().isoformat()
            })

        logging.info("Scraped page %s, total so far: %s", page, len(books))

    # Remove duplicates by Title
    if books:
        df = pd.DataFrame(books)
        df.drop_duplicates(subset="Title", inplace=True)
        records = df.to_dict("records")
    else:
        records = []

    # NOTE: XCom size can be limited by your backend. If you have many rows, consider storing CSV in shared storage (S3) or inserting directly here.
    ti.xcom_push(key="book_data", value=records)
    logging.info("Pushed %s records to XCom", len(records))


def insert_book_data_into_postgres(ti):
    """Pull scraped data from XCom and insert into Postgres using PostgresHook.insert_rows in batches."""
    records = ti.xcom_pull(key="book_data", task_ids="scrape_and_save_to_postgres")
    if not records:
        raise ValueError("No book data found in XCom")

    # Ensure records is a list
    if not isinstance(records, list):
        raise ValueError("Unexpected XCom payload (expected list of dicts)")

    # Convert dicts to tuples in the exact column order
    ordered_rows = []
    for r in records:
        try:
            ordered_rows.append((
                r.get("Title"),
                r.get("Rating"),
                r.get("Price"),
                r.get("Stock_Status"),
                r.get("ScrapedAt")
            ))
        except Exception as e:
            logging.exception("Skipping bad record: %s", e)

    if not ordered_rows:
        raise ValueError("No valid rows to insert after conversion")

    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # OPTIONAL: Create table if not exists (safe to run every time)
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id SERIAL PRIMARY KEY,
        Title TEXT NOT NULL,
        Rating TEXT,
        Price TEXT,
        Stock_Status TEXT,
        ScrapedAt TEXT
    );
    """
    hook.run(create_sql)
    logging.info("Ensured table %s exists", TABLE_NAME)

    # Insert in batches to avoid too large single insert
    batch_size = 200  # tune this for your environment
    total = len(ordered_rows)
    batches = math.ceil(total / batch_size)
    inserted = 0

    for i in range(batches):
        start = i * batch_size
        end = start + batch_size
        chunk = ordered_rows[start:end]
        try:
            hook.insert_rows(
                table=TABLE_NAME,
                rows=chunk,
                target_fields=["Title", "Rating", "Price", "Stock_Status", "ScrapedAt"]
            )
            inserted += len(chunk)
            logging.info("Inserted batch %s/%s (%s rows)", i + 1, batches, len(chunk))
        except Exception as e:
            logging.exception("Failed to insert batch %s: %s", i + 1, e)
            raise

    logging.info("Successfully inserted %s rows into %s", inserted, TABLE_NAME)


# DAG definition
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 5,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "scrape_books_every_3min_postgres",
    default_args=default_args,
    description="Scrape books.toscrape.com and store in Postgres every 15 minutes",
    schedule_interval="@daily", # @daily "*/60 * * * *"
    start_date=datetime(2025, 12, 5),
    catchup=False,
)

fetch_task = PythonOperator(
    task_id="scrape_and_save_to_postgres",
    python_callable=scrape_and_push_xcom,
    dag=dag,
)

create_table_task = PythonOperator(
    task_id="create_table",
    python_callable=lambda: PostgresHook(postgres_conn_id=POSTGRES_CONN_ID).run(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            Title TEXT NOT NULL,
            Rating TEXT,
            Price TEXT,
            Stock_Status TEXT,
            ScrapedAt TEXT
        );
    """),
    dag=dag,
)

insert_task = PythonOperator(
    task_id="insert_book_data",
    python_callable=insert_book_data_into_postgres,
    dag=dag,
)

# set dependencies
fetch_task >> create_table_task >> insert_task
