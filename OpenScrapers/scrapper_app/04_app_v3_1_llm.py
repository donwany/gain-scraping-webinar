import os
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai import LLMExtractionStrategy
from pydantic import BaseModel, Field
import csv
import json

class ElectoralCommission(BaseModel):
    region: str = Field(..., description="region where vote was cast")
    total_votes: str = Field(..., description="total votes cast")
    winning_party: str = Field(..., description="winning party")

async def main(url: str):
    browser_config = BrowserConfig(verbose=True, )
    run_config = CrawlerRunConfig(
        word_count_threshold=1,
        extraction_strategy=LLMExtractionStrategy(
            # Here you can use any provider that Litellm library supports, for instance: ollama/qwen2
            # provider="ollama/qwen2", api_token="no-token",
            llm_config=LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv('OPENAI_API_KEY')),
            schema=ElectoralCommission.model_json_schema(),
            extraction_type="schema",
            instruction="""From the crawled content, extract all mentioned region, total votes, winning party from the article 
            Do not miss any region, total votes and winning party in the entire content. One extracted model JSON format should look like this: 
             {'region': "volta", 'total_votes': '300,489', 'winning_party: 'ndc'}.
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
        print(type(result.extracted_content))

        # articles = json.loads(result.extracted_content)
        # print(f"Successfully extracted {len(articles)} articles")
        # print(json.dumps(articles[0], indent=2))

        # Parse JSON string to Python object
        try:
            data = json.loads(str(result.extracted_content))
        except json.JSONDecodeError as e:
            print("JSON DECODE ERROR:", e)
            return

        # Ensure list
        if isinstance(data, dict):
            data = [data]

        # Save to CSV
        csv_file = "ghanaweb_extracted_votes.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["region", "total_votes", "winning_party", "error"])
            writer.writeheader()
            writer.writerows(data)

        print(f"\nSaved {len(data)} records to: {csv_file}\n")


if __name__ == "__main__":
    url = "https://www.ghanaweb.com/elections/2024/"
    asyncio.run(main(url=url))