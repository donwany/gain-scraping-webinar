from datetime import datetime, timedelta
from airflow import DAG
import pandas as pd
import logging
import requests
from bs4 import BeautifulSoup
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

# ---------------------------------------------------------
# 1) fetch book data (extract) 2) clean data (transform)
# ---------------------------------------------------------

# headers = {
#     "Referer": 'https://www.amazon.com/',
#     "Sec-Ch-Ua": "Not_A Brand",
#     "Sec-Ch-Ua-Mobile": "?0",
#     "Sec-Ch-Ua-Platform": "macOS",
#     'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
# }

POSTGRES_CONN_ID = "books_connection"
TABLE_NAME = "books"

HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}


def scrape_and_store(ti):
    """scrape books data"""
    books = []
    START = 1
    END = 50

    for page in range(START, END + 1):
        url = f"https://books.toscrape.com/catalogue/page-{page}.html"
        response = requests.get(url, headers=HEADERS)

        if response.status_code != 200:
            print(f"Page {page} not found, skipping...")
            logging.warning("Page %s returned status %s - skipping", page, response.status_code)
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
                "Stock_Status": stock,
                "ScrapedAt": datetime.utcnow().isoformat()
            })

        print(f"Scraped page {page}")
        logging.info("Scraped page %s, total so far: %s", page, len(books))

    # Convert the list of dictionaries into a DataFrame
    df = pd.DataFrame(books)
    # Remove duplicates based on 'Title' column
    df.drop_duplicates(subset="Title", inplace=True)
    # Push the DataFrame to XCom
    ti.xcom_push(key='book_data', value=df.to_dict('records'))


# create and store data in table on postgres (load)
# def insert_book_data_into_postgres(ti):
#     book_data = ti.xcom_pull(key='book_data', task_ids='fetch_book_data')
#     print(book_data)
#     if not book_data:
#         raise ValueError("No book data found")
#
#     postgres_hook = PostgresHook(postgres_conn_id='books_connection')
#     # insert_query = """
#     # INSERT INTO books (Title, Rating, Price, Stock_Status, ScrapedAt)
#     # VALUES (%s, %s, %s, %s, %s)
#     # """
#     # for book in book_data:
#     #     postgres_hook.run(insert_query, parameters=(book['Title'], book['Rating'], book['Price'], book['Stock_Status'], book['ScrapedAt']))
#     #
#
#     postgres_hook.insert_rows(table="books", rows = book_data.to_dict('records'), target_fields = ["Title", "Rating", "Price", "Stock_Status", "ScrapedAt"])

def insert_book_data_into_postgres(ti):
    records = ti.xcom_pull(key="book_data", task_ids="scrape_and_save_to_postgres")
    if not records:
        raise ValueError("NO data received from XCom")

    postgres_hook = PostgresHook(postgres_conn_id="books_connection")
    # convert dict → tuple in correct order
    rows = [
        (
            rec["Title"],
            rec["Rating"],
            rec["Price"],
            rec["Stock_Status"],
            rec["ScrapedAt"]
        )
        for rec in records
    ]

    postgres_hook.insert_rows(
        table="books",
        rows=rows,
        target_fields=["Title", "Rating", "Price", "Stock_Status", "ScrapedAt"]
    )

    print(f"Inserted {len(rows)} rows into Postgres.")


# ---------------------------------------------------------
# DAG DEFINITION
# ---------------------------------------------------------

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    "scrape_books_every_3min",
    default_args=default_args,
    description="Scrape books.toscrape.com and store in postgres every 3 minutes",
    schedule_interval="*/3 * * * *",
    start_date=datetime(2025, 12, 4),
    catchup=False,
)

fetch_book_data_task = PythonOperator(
    task_id="scrape_and_save_to_postgres",
    python_callable=scrape_and_store,
    dag=dag,
)

# create_table_task = PostgresOperator(
#     task_id='create_table',
#     postgres_conn_id='books_connection',
#     sql="""
#     CREATE TABLE IF NOT EXISTS books (
#         id SERIAL PRIMARY KEY,
#         Title TEXT NOT NULL,
#         Rating TEXT,
#         Price TEXT,
#         Stock_Status TEXT,
#         ScrapedAt TEXT
#     );
#     """,
#     dag=dag,
# )

insert_book_data_task = PythonOperator(
    task_id='insert_book_data',
    python_callable=insert_book_data_into_postgres,
    dag=dag,
)

# dependencies
fetch_book_data_task >> insert_book_data_task

# fetch_book_data_task.set_downstream(create_table_task)
# create_table_task.set_downstream(insert_book_data_task)

