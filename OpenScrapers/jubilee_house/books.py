import requests
from bs4 import BeautifulSoup
import pandas as pd

books = []
START = 1
END = 50

for page in range(START, END + 1):  # pages 1 to 50
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
        rating = item.p["class"][1]  # e.g., "Three"

        books.append({
            "Title": title,
            "Rating": rating,
            "Price": price.encode("ascii", errors="ignore").decode(),
            "Stock Status": stock
        })

    print(f"Scraped page {page}")

if __name__ == '__main__':

    # Convert to DataFrame
    df = pd.DataFrame(books)

    # Save to CSV
    df.to_csv("books_page_1_to_50.csv", index=False)

    print("\nFinished! Saved to books_page_1_to_50.csv")

