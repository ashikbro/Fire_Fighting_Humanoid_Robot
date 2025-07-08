import time
import shutil
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# This script simulates automated data update by copying new prediction logs periodically

SOURCE_LOG = "alerts/prediction_logs_new.csv"  # New data source file (simulate)
TARGET_LOG = "alerts/prediction_logs.csv"      # Dashboard data file

def update_data():
    if os.path.exists(SOURCE_LOG):
        try:
            shutil.copy2(SOURCE_LOG, TARGET_LOG)
            logging.info(f"Updated data file {TARGET_LOG} from {SOURCE_LOG}")
        except Exception as e:
            logging.error(f"Failed to update data file: {e}")
    else:
        logging.warning(f"Source data file {SOURCE_LOG} not found. No update performed.")

if __name__ == "__main__":
    while True:
        update_data()
        time.sleep(3600)  # Update every hour
