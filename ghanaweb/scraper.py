import csv
import os
import sys
import time
import unicodedata
import uuid
from dataclasses import asdict
from datetime import datetime
from datetime import datetime, UTC
import requests
from bs4 import BeautifulSoup
from loguru import logger

from utils import HEADERS, SaveFile, Article


class GhanaWeb:
    def __init__(self, url: str):
        if not url.startswith(("http://", "https://")):
            raise ValueError(
                "Invalid URL: must start with 'http://' or 'https://'")
        self.url = url
        self.home_page = "https://www.ghanaweb.com"
        self.file_name = str(uuid.uuid4().hex)
        self.response = None
        self.soup = None

    def download(self, output_dir=None):
        """scrape data"""
        self.response = requests.request(
            "GET", self.url, headers=HEADERS
        )
        if self.response.status_code != 200:
            logger.error(
                f"Request: {requests}; status code:{self.response.status_code}")
            self.response.raise_for_status()
            sys.exit(1)
        self.soup = BeautifulSoup(self.response.text, "html.parser")

        div_element = self.soup.find(
            "div", {"class": ["afcon-news list", "right_artl_list", "left_artl_list"]})

        if div_element is None:
            logger.error("Unable to find the div class 'afcon-news list'")
            sys.exit(1)

        lst_pages = [a for a in div_element.find_all("a")]

        try:
            logger.info("Saving results to csv...")
            output_dir = output_dir or os.getcwd()
            SaveFile.mkdir(output_dir)
            if not os.path.isdir(output_dir):
                raise ValueError(
                    f"Invalid output directory: {output_dir} is not a directory"
                )
            logger.info(f"File will be saved to: {output_dir}")

            # stamp = datetime.strftime(datetime.utcnow(), "%Y-%m-%d")
            stamp = datetime.now(UTC).strftime("%Y-%m-%d")

            file_path = os.path.join(
                output_dir, self.file_name + f"_{stamp}.csv")
            logger.info(f"Saving file as: {file_path}")
            with open(
                    file_path,
                    mode="w",
                    newline=""
            ) as csv_file:
                fieldnames = ["title", "content", "author", "category", "published_date", "page_url"]
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()

                for page in lst_pages:
                    try:
                        page_url = self.home_page + page["href"]
                        if page_url:
                            with requests.Session() as session:
                                response_page = session.get(
                                    page_url, headers=HEADERS)
                                time.sleep(2)
                            soup_page = BeautifulSoup(
                                response_page.text, "html.parser")
                            try:
                                title = soup_page.find(
                                    "h1", {"style": "clear: both;"}).text.strip()
                                title = unicodedata.normalize("NFKD", title).encode(
                                    "ASCII", "ignore").decode("utf-8")
                                # title = title.text.strip if title else ""
                            except Exception:
                                title = ""
                            try:
                                content = soup_page.find("p", id="article-123").get_text(separator="\n", strip=True) # soup_page.find("p", {"style": "clear:right"}).text.strip()
                                # content = content.text.strip() if content else ""
                                content = unicodedata.normalize("NFKD", content).encode("ASCII", "ignore").decode("utf-8")
                            except Exception:
                                content = ""
                            try:
                                published_date = soup_page.find(
                                    "p", class_="floatLeft").text.split(",")[-1]
                            except Exception:
                                published_date = ""
                            try:
                                author = soup_page.find("p", class_="floatRight").text.split(
                                    ":")[-1].split(",")[-2]
                            except Exception:
                                author = ""

                            try:
                                category = soup_page.find(
                                    "p", class_="floatLeft").text.split(" ")[0]
                            except Exception:
                                category = ""

                            article = Article(
                                title=title,
                                content=content,
                                author=author,
                                category=category,
                                published_date=published_date,
                                page_url=page_url,
                            )
                            # write data
                            writer.writerow(asdict(article))

                    except Exception:
                        continue
                logger.info("Writing data to file...")
        except Exception as e:
            logger.error(f"error: {e}")

        logger.info(f"All file(s) saved to: {output_dir} successfully!")
        logger.info("Done!")


if __name__ == '__main__':
    urls = [
        'https://www.ghanaweb.com/GhanaHomePage/politics/',
        'https://www.ghanaweb.com/GhanaHomePage/health/',
        'https://www.ghanaweb.com/GhanaHomePage/crime/',
        'https://www.ghanaweb.com/GhanaHomePage/regional/',
    ]

    for url in urls:
        print(f"Downloading: {url}")
        web = GhanaWeb(url=url)
        web.download(output_dir=None)
