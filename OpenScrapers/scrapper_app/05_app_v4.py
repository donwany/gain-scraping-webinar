from pydantic import BaseModel, Field
from typing import List, override
from firecrawl import Firecrawl
from dotenv import load_dotenv
import  os
import csv
import json
import pandas as pd

load_dotenv(override=True)

firecrawl = Firecrawl(api_key="" + os.getenv("FIRECRAWL_API_KEY"))

class Article(BaseModel):
    url: str = Field(..., description="url of the article")
    title: str = Field(..., description="title of the article")

class TopArticles(BaseModel):
    top: List[Article] = Field(..., description="Top stories")


if __name__ == '__main__':
    url = "https://www.myjoyonline.com/news/"
    # url = "https://www.ghanaweb.com/GhanaHomePage/NewsArchive"
    # Use JSON format with a Pydantic schema
    doc = firecrawl.scrape(
        url,
        formats=[{"type": "json", "schema": Article}],
    )
    print(doc.json)
    # print(doc.markdown)

    # Parse JSON string to Python object
    try:
        data = doc.json
        # Ensure list
        if isinstance(data, dict):
            data = [data]

        # Save to CSV
        csv_file = "firecrawl_myjoyonline_extracted.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "url"])
            writer.writeheader()
            writer.writerows(data)

        print(f"\nSaved {len(data)} records to: {csv_file}\n")
    except json.JSONDecodeError as e:
        print("JSON DECODE ERROR:", e)


