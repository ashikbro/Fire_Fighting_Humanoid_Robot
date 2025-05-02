import os
import requests
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def download_uci_forest_fires(csv_path):
    uci_url = "https://archive.ics.uci.edu/ml/machine-learning-databases/forest-fires/forestfires.csv"
    if not os.path.exists(csv_path):
        logging.info("Downloading UCI Forest Fires dataset CSV...")
        r = requests.get(uci_url)
        with open(csv_path, 'wb') as f:
            f.write(r.content)
    else:
        logging.info("UCI Forest Fires dataset CSV already exists.")

def load_and_preprocess_uci_forest_fires(csv_path):
    logging.info(f"Loading UCI Forest Fires dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    # Basic preprocessing: convert categorical month and day to numeric
    df['month'] = df['month'].map({'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12})
    df['day'] = df['day'].map({'mon':1,'tue':2,'wed':3,'thu':4,'fri':5,'sat':6,'sun':7})
    # Drop rows with missing values if any
    df = df.dropna()
    logging.info(f"Dataset loaded with {len(df)} records after preprocessing.")
    return df

if __name__ == "__main__":
    data_dir = "data/uci_forest_fires"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    csv_path = os.path.join(data_dir, "forestfires.csv")
    download_uci_forest_fires(csv_path)
    df = load_and_preprocess_uci_forest_fires(csv_path)
    preprocessed_path = "data/fire_data_uci_forest_fires_preprocessed.csv"
    df.to_csv(preprocessed_path, index=False)
    logging.info(f"Preprocessed dataset saved to {preprocessed_path}")
