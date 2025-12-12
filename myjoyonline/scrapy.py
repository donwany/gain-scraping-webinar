import csv
import os
import sys
import time
import unicodedata
import uuid
from dataclasses import asdict
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from loguru import logger
from selenium import webdriver

from utils import HEADERS, SaveFile, Article


class MyJoyOnlineNews:
    def __init__(self, url: str, driver_name: str = 'firefox'):
        if not url.startswith(("http://", "https://")):
            raise ValueError("Invalid URL: must start with 'http://' or 'https://'")
        self.url = url
        self.file_name = str(uuid.uuid4().hex)
        self.BASE_URL = "https://myjoyonline.com"
        self.NUMBER_OF_TIMES_TO_SCROLL = 5
        self.driver_name = driver_name
        # Create a new instance of the driver
        driver_options = {
            "chrome": webdriver.ChromeOptions,
            "firefox": webdriver.FirefoxOptions,
        }

        driver_name = self.driver_name.lower()
        if driver_name not in driver_options:
            raise ValueError(
                "Invalid driver specified. Supported drivers are 'chrome' and 'firefox'."
            )

        options = driver_options[driver_name]()
        options.headless = True
        options.page_load_timeout = 600  # 600 seconds
        options.implicitly_wait = 600  # 600 seconds

        self.driver = (
            webdriver.Chrome(options=options)
            if driver_name == "chrome"
            else webdriver.Firefox(options=options)
        )

    def tear_down(self):
        """tear down driver"""
        self.driver.quit()

    def download(self, output_dir=None):
        """scrape data"""
        with requests.Session() as session:
            response = session.get(self.url, headers=HEADERS)
            if response.status_code != 200:
                logger.error(f"Request: {requests}; status code:{response.status_code}")
                response.raise_for_status()
                sys.exit(1)

        try:
            logger.info("Saving results to csv...")
            if output_dir is None:
                output_dir = os.getcwd()
                SaveFile.mkdir(output_dir)
            if not os.path.isdir(output_dir):
                raise ValueError(
                    f"Invalid output directory: {output_dir} is not a directory"
                )
            logger.info(f"File will be saved to: {output_dir}")

            stamp = datetime.strftime(datetime.utcnow(), "%Y-%m-%d")
            file_path = os.path.join(output_dir, self.file_name + f"_{stamp}.csv")
            logger.info(f"Saving file as: {file_path}")
            with open(file_path, mode="w", newline="", encoding="utf-8") as csv_file:
                fieldnames = [
                    "title",
                    "content",
                    "author",
                    "category",
                    "published_date",
                    "page_url",
                ]
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()

                # Open the webpage
                self.driver.get(self.url)

                for _ in range(self.NUMBER_OF_TIMES_TO_SCROLL):
                    # Perform scrolling actions to reveal hidden content
                    self.driver.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight);"
                    )
                    # Wait for some time to allow the page to load more content
                    time.sleep(2)

                # Parse the HTML content
                soup = BeautifulSoup(self.driver.page_source, "html.parser")

                # Find all the pages
                pages = soup.find_all("div", class_="feeditem")
                # build all urls
                URLS = [self.BASE_URL + page.find("a")["href"] for page in pages]

                for url in URLS:
                    self.driver.get(url)
                    soup = BeautifulSoup(self.driver.page_source, "html.parser")

                    title = soup.find("div", class_="article-title")
                    if title is not None:
                        title = title.text.strip()
                        title = (
                            unicodedata.normalize("NFKD", title)
                            .encode("ASCII", "ignore")
                            .decode("utf-8")
                        )
                    else:
                        logger.warning("Article title element not found.")

                    content = soup.find_all("div", class_="article-text")
                    content = "\n".join([element.text.strip() for element in content])
                    content = (
                        unicodedata.normalize("NFKD", content)
                        .encode("ASCII", "ignore")
                        .decode("utf-8")
                    )

                    source = soup.find(
                        "div",
                        {
                            "style": "color: rgb(151, 146, 146); font-size: 12px; margin: 10px 0px; display: flex; justify-content: space-between;"
                        },
                    )

                    author = None
                    published_date = None
                    if source is not None:
                        spans = source.find_all("span")
                        if len(spans) == 2:
                            author = spans[0].text.strip().split(":")[-1]
                            published_date = spans[1].text.strip()
                        else:
                            logger.info("Invalid number of <span> elements found.")
                    else:
                        logger.warning("No source element found")

                    article = Article(
                        title=title,
                        content=content,
                        author=author,
                        category=self.url.split("/")[-2] if self.url.endswith("/") else self.url.split("/")[-1],
                        published_date=published_date,
                        page_url=url,
                    )
                    # write data
                    writer.writerow(asdict(article))

                logger.info("Writing data to file...")
        except Exception as err:
            logger.error(f"error: {err}")

        logger.info(f"All file(s) saved to: {output_dir} successfully!")
        logger.info("Done!")
        logger.info("Gracefully shutting down driver...")
        self.tear_down()


if __name__ == "__main__":
    joy = MyJoyOnlineNews(url="https://myjoyonline.com/news/")
    joy.download()
