from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
from firecrawl import Firecrawl
import os

load_dotenv()

firecrawl = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

class Article(BaseModel):
    title: str
    points: int
    by: str
    commentsURL: str

class TopArticles(BaseModel):
    top: List[Article] = Field(..., description="Top 5 stories")

# Use JSON format with a Pydantic schema
doc = firecrawl.scrape(
    "https://news.ycombinator.com",
    formats=[{"type": "json", "schema": TopArticles}],
)
if __name__ == '__main__':

    print(doc.json)