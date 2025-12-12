import os
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai import LLMExtractionStrategy
from pydantic import BaseModel, Field
import csv
import json

class GhanaWebModel(BaseModel):
    url: str = Field(..., description="url of the article")
    title: str = Field(..., description="title of the article")

async def main(url: str):
    browser_config = BrowserConfig(verbose=True)
    run_config = CrawlerRunConfig(
        word_count_threshold=1,
        extraction_strategy=LLMExtractionStrategy(
            # Here you can use any provider that Litellm library supports, for instance: ollama/qwen2
            # provider="ollama/qwen2", api_token="no-token",
            llm_config=LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv('OPENAI_API_KEY')),
            schema=GhanaWebModel.model_json_schema(),
            extraction_type="schema",
            instruction="""From the crawled content, extract all mentioned titles of the articles along with their urls. 
            Do not miss any title and url in the entire content. One extracted model JSON format should look like this: 
             {'title': "Dr Ayew Afriye raises alarm over government's failure to prevent Zipline shutdown",
             'url': 'https://www.ghanaweb.com/GhanaHomePage/NewsArchive/Dr-Ayew-Afriye-raises-alarm-over-government-s-failure-to-prevent-Zipline-shutdown-2010997'}.
             """
        ),
        cache_mode=CacheMode.BYPASS,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url=url,
            config=run_config
        )
        print(result.extracted_content)

        # Parse JSON string to Python object
        try:
            data = json.loads(result.extracted_content)
        except json.JSONDecodeError as e:
            print("JSON DECODE ERROR:", e)
            return

        # Handle cases where the extraction returns a single dict
        if isinstance(data, dict):
            data = [data]

        # Save to CSV
        csv_file = "ghanaweb_extracted_news.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "url", "error"])
            writer.writeheader()
            writer.writerows(data)

        print(f"\nSaved {len(data)} records to: {csv_file}\n")


if __name__ == "__main__":
    # url = https://platform.openai.com/docs/pricing
    # url = # url = "https://3news.com/news/politics"
    url = "https://www.ghanaweb.com/GhanaHomePage/NewsArchive"
    asyncio.run(main(url=url))