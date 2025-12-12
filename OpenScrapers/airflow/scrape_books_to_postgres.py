from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import pandas as pd
from urllib.parse import quote_plus


# ------------------------------
# MongoDB Credentials
# ------------------------------
MONGO_USER = "admin"
MONGO_PASS = "admin"
MONGO_HOST = "localhost"
MONGO_PORT = 27017

# Encode credentials safely
USER = quote_plus(MONGO_USER)
PASS = quote_plus(MONGO_PASS)

MONGO_URI = f"mongodb://{USER}:{PASS}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"

DB_NAME = "books_db"
COLLECTION_NAME = "books"


def scrape_and_store():

    books = []
    START = 1
    END = 50

    for page in range(START, END + 1):
        url = f"https://books.toscrape.com/catalogue/page-{page}.html"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Page {page} not found, skipping...")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("article.product_pod")

        for item in items:
            title = item.h3.a["title"]
            price = item.select_one(".price_color").text.strip()
            stock = item.select_one(".instock.availability").text.strip()
            rating = item.p["class"][1]

            books.append({
                "Title": title,
                "Rating": rating,
                "Price": price.encode("ascii", errors="ignore").decode(),
                "Stock Status": stock,
                "ScrapedAt": datetime.utcnow()
            })

        print(f"Scraped page {page}")

    # Insert into MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    if books:
        collection.insert_many(books)
        print(f"Inserted {len(books)} records into MongoDB.")


# ---------------------------------------------------------
# DAG DEFINITION
# ---------------------------------------------------------

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=10),
}

dag = DAG(
    "scrape_books_every_3min",
    default_args=default_args,
    description="Scrape books.toscrape.com and store in MongoDB every 3 minutes",
    schedule_interval="*/3 * * * *",
    start_date=datetime(2025, 12, 3),
    catchup=False,
)

run_task = PythonOperator(
    task_id="scrape_and_save_to_mongo",
    python_callable=scrape_and_store,
    dag=dag,
)
