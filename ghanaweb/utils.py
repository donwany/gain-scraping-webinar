import os
from loguru import logger
from dataclasses import dataclass

HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}


@dataclass
class Article:
    title: str
    content: str
    author: str
    category: str
    published_date: str
    page_url: str


class SaveFile:
    """a class to save file"""

    @staticmethod
    def mkdir(path):
        """Create directory"""
        try:
            if not os.path.exists(path):
                os.mkdir(path)
            else:
                logger.info(f" * Directory already exists = {path}")
        except OSError as err:
            raise OSError(f"{err}")
