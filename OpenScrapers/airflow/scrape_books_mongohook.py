from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

from airflow.providers.mongo.hooks.mongo import MongoHook
import requests
from bs4 import BeautifulSoup


def scrape_with_mongohook():

    books = []
    START = 1
    END = 50

    for page in range(START, END + 1):
        url = f"https://books.toscrape.com/catalogue/page-{page}.html"
        response = requests.get(url, timeout=15)

        if response.status_code != 200:
            print(f"Page {page} not found, skipping…")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("article.product_pod")

        for item in items:
            books.append({
                "Title": item.h3.a["title"],
                "Rating": item.p["class"][1],
                "Price": item.select_one(".price_color").text.strip().encode("ascii", errors="ignore").decode(),
                "Stock Status": item.select_one(".instock.availability").text.strip(),
                "ScrapedAt": datetime.utcnow()
            })

    print(f"Scraped {len(books)} books")

    # -------------------------
    # Store to MongoDB via MongoHook
    # -------------------------
    hook = MongoHook(conn_id="mongo_default")
    mongo_client = hook.get_conn()

    db = mongo_client[hook.schema]  # schema = database name
    collection = db["books"]

    if books:
        collection.insert_many(books)
        print("Inserted into MongoDB:", len(books))


# ---------------------------------------------------------
# DAG Definition
# ---------------------------------------------------------

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=10),
}

dag = DAG(
    "scrape_books_mongohook",
    default_args=default_args,
    start_date=datetime(2025, 12, 3),
    schedule="*/3 * * * *",  # run every 3 minutes
    catchup=False,
    description="Scrape books.toscrape.com using MongoHook",
)

run_scraper = PythonOperator(
    task_id="scrape_and_store",
    python_callable=scrape_with_mongohook,
    dag=dag,
)
