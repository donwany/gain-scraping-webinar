import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import time
import textwrap
from loguru import logger

min_page = 1
max_page = 24
lang = "ewe" # ewe
file_name = f"{lang}_1_JOS_24"
CHAPTER = "JOS"
SUFFIX = "AL"
NUMBER = 1613
BASE = f"https://www.bible.com/audio-bible/{NUMBER}"

# https://www.bible.com/audio-bible/1631/EXO.1.AKNA # Twi
# https://www.bible.com/audio-bible/1613/EXO.1.AL   # Ewe


def extract_data(page_number):
    url = f"{BASE}/{CHAPTER}.{page_number}.{SUFFIX}"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', type='application/ld+json')

        if script_tag:
            try:
                json_data = json.loads(script_tag.string)
                content_url = json_data.get('contentUrl')
                transcript = json_data.get('transcript')

                # Wrap the transcript text
                wrapped_transcript = textwrap.fill(transcript, width=80) if transcript else None

                return content_url, wrapped_transcript
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON on page {page_number}")
                return None, None
    else:
        logger.error(f"Error accessing page {page_number}, status code {response.status_code}")
    return None, None

# Initialize list to hold data
data = []

# Loop through pages
for page in range(min_page, max_page+1):
    # print(f"Processing page {page}")
    content_url, transcript = extract_data(page)
    if content_url and transcript:
        data.append({'Page': page, 'ContentURL': content_url.split("?")[0], 'Transcript': transcript})
        logger.info(f"Successfully processed page {page}")
    else:
        logger.warning(f"Failed to process page {page}")

    # Be polite to the server, add a delay
    time.sleep(1)  # 1 second delay

# Save data to CSV
df = pd.DataFrame(data)
df.to_csv(f'{file_name}.csv', index=False)

print(f"Data extraction completed and saved to {file_name}.csv.")

if __name__ == '__main__':
    print("Scraping complete.")
