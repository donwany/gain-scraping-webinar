from firecrawl import Firecrawl
from dotenv import load_dotenv
import os

load_dotenv()

firecrawl = Firecrawl(api_key=os.getenv("FIRECRAWL_API_KEY"))

# Scrape a website (returns a Document)
# scrapes a URL and get its content in LLM-ready format (markdown, structured data via LLM Extract, screenshot, html)
doc = firecrawl.scrape(
    "https://firecrawl.dev",
    formats=["markdown", "html"],
)


# Crawl a website
# scrapes all the URLs of a web page and return content in LLM-ready format

# response = firecrawl.crawl(
#     "https://firecrawl.dev",
#     limit=100,
#     scrape_options={"formats": ["markdown", "html"]},
#     poll_interval=30,
# )

if __name__ == '__main__':
    print(doc.markdown)
    # print(response)