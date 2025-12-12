import asyncio
from crawl4ai import AsyncWebCrawler

MIN_PAGE = 2
TOTAL_PAGES = 16
MAIN_URL = "https://presidency.gov.gh/press-releases"
PAGE_URL = "https://presidency.gov.gh/press-releases/page/{}/"

async def fetch_page_markdown(crawler, label, url):
    """Fetch markdown from a page (main or numbered)."""
    try:
        result = await crawler.arun(url=url)
        return f"# {label}\n\n" + result.markdown + "\n\n"
    except Exception as e:
        return f"# {label}\n\nError fetching page: {e}\n\n"


async def main():
    combined_md = ""

    async with AsyncWebCrawler() as crawler:

        tasks = []

        # Add main page first
        tasks.append(fetch_page_markdown(crawler, "Main Page", MAIN_URL))

        # Add pages 1 to 16
        for page in range(MIN_PAGE, TOTAL_PAGES + 1):
            url = PAGE_URL.format(page)
            tasks.append(fetch_page_markdown(crawler, f"Page {page}", url))

        results = await asyncio.gather(*tasks)

        # Combine markdown in order: main page → pages 1–16
        for content in results:
            combined_md += content

    # Save output
    output_file = "presidency_press_releases_combined.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined_md)

    print(f"Markdown extraction complete. Saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
