import os
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    """
    Automates the process of retraining the fire severity prediction model.
    """
    logging.info("🚀 Starting automated model retraining pipeline...")

    # Define paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    training_script_path = os.path.join(project_root, 'src', 'train_fire_model.py')
    data_path = os.path.join(project_root, 'data', 'fire_data_bangladesh.csv')
    model_dir = os.path.join(project_root, 'models')
    results_dir = os.path.join(project_root, 'results')

    # Step 1: (Optional) Add logic here to download new data if applicable
    # For example, you could download new data from a URL and append it to the existing CSV.
    logging.info("📥 Skipping data download for now. Using existing data.")

    # Step 2: Run the training script
    logging.info(f"🔥 Running training script: {training_script_path}")
    try:
        subprocess.run(
            [
                "python",
                training_script_path,
                "--data",
                data_path,
                "--model_dir",
                model_dir,
                "--results_dir",
                results_dir,
            ],
            check=True,
        )
        logging.info("✅ Model training completed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Model training failed with exit code {e.returncode}")
        logging.error(f"   Error output: {e.stderr}")
    except FileNotFoundError:
        logging.error("❌ 'python' command not found. Make sure Python is installed and in your PATH.")

    logging.info("🎉 Automated model retraining pipeline finished.")

if __name__ == "__main__":
    main()