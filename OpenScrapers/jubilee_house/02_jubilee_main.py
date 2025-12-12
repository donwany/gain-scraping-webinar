import json
from bs4 import BeautifulSoup
import requests

HEADERS = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

# main page
jubilee_house = "https://presidency.gov.gh/press-releases/"

response = requests.get(jubilee_house, headers=HEADERS)
soup = BeautifulSoup(response.text, "html.parser")

# extract article URLs
urls = [a["href"] for a in soup.select("div.article-i-button a.button-custom")]

results = []

def extract_image_urls(img_tag):
    urls = set()
    if img_tag.get("src"):
        urls.add(img_tag["src"])
    if img_tag.get("srcset"):
        for p in img_tag["srcset"].split(","):
            url = p.strip().split(" ")[0]
            urls.add(url)
    return list(urls)

# process each article page
for url in urls:
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        print(f"Failed: {url}")
        continue

    soup_url = BeautifulSoup(r.text, "html.parser")

    # extract data
    title = soup_url.find("h1", class_="h2").get_text(strip=True)
    content_div = soup_url.find("div", class_="content")
    content = content_div.get_text(separator="\n", strip=True)

    # Extract date if available
    date_tag = soup_url.find("div", class_="article-date")

    date_text = ""
    if date_tag:
        date_text = date_tag.get_text(strip=True)

    # extract all images in article content
    image_urls = []
    for img in content_div.find_all("img"):
        image_urls.extend(extract_image_urls(img))

    results.append({
        "title": title,
        "date": date_text,
        "content": content,
        "link": url,
        "images": image_urls,
    })


if __name__ == '__main__':

    # print results cleanly
    print(json.dumps(results, indent=4))

    # Save results as JSON
    with open("data/press_releases.jsonl", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("\nSaved to press_releases.jsonl")

