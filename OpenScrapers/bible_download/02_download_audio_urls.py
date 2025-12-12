import pandas as pd
import glob
import os
import requests

# Folder containing the .csv files
folder_path = '/home/ts75080/Desktop/Scrapers/OpenScrapers/bible_download/'

# Use glob to find all .csv files in the folder
csv_files = glob.glob(os.path.join(folder_path, '*.csv'))

# List to hold contentURL data
content_urls = []

# Iterate over each .csv file
for file in csv_files:
    # Read the .csv file into a DataFrame
    df = pd.read_csv(file)

    # Check if 'contentURL' column exists
    if 'ContentURL' in df.columns:
        # Extract the 'contentURL' column and extend the list
        content_urls.extend(df['ContentURL'].dropna().tolist())
    else:
        print(f"'ContentURL' column not found in {file}")

# Optionally: Print or save the collected content URLs
print(content_urls[:5])

if __name__ == '__main__':
    # Save collected content URLs to a new CSV file
    output_df = pd.DataFrame(content_urls, columns=['ContentURL'])
    output_df.to_csv('collected_content_urls.csv', index=False)
    print("Collected content URLs saved to 'collected_content_urls.csv'")

    for url in content_urls:
        # The name of the local file to save the downloaded content
        local_filename = url.split("/")[-1] #.split("?")[0]
        # Folder to save the downloaded file
        folder_path = "downloaded_audio"
        # Create the folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        # Full path to the file
        file_path = os.path.join(folder_path, local_filename)
        # Send a GET request to the URL
        response = requests.get(url, stream=True)
        # Check if the request was successful
        if response.status_code == 200:
            # Open a local file with write-binary mode and save the content
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded audio file saved as '{file_path}'")
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
