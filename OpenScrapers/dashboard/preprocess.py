import os
import pandas as pd

DATA_DIR = "data"
OUTPUT_FILE = "combined_output.csv"

def concat_csv_files():
    # List all CSV files
    csv_files = [
        os.path.join(DATA_DIR, f)
        for f in os.listdir(DATA_DIR)
        if f.endswith(".csv")
    ]

    if not csv_files:
        print("No CSV files found in /data folder.")
        return

    print(f"Found {len(csv_files)} files. Combining...")

    # Read and concatenate
    df_list = [pd.read_csv(csv_file) for csv_file in csv_files]
    combined_df = pd.concat(df_list, ignore_index=True)

    # Save final output
    combined_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved concatenated file → {OUTPUT_FILE}")


if __name__ == "__main__":
    concat_csv_files()
