import joblib
import numpy as np
import logging
import argparse
import pandas as pd
import os

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler and a stream handler
file_handler = logging.FileHandler('fire_severity_prediction.log')
stream_handler = logging.StreamHandler()

# Create a formatter and set it for the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

MODEL = None
LABEL_ENCODER = None

def get_models():
    """Load and cache model and label encoder to avoid repeated disk loads."""
    global MODEL, LABEL_ENCODER
    if MODEL is None or LABEL_ENCODER is None:
        MODEL = joblib.load("models/fire_severity_model.pkl")
        LABEL_ENCODER = joblib.load("models/label_encoder.pkl")
    return MODEL, LABEL_ENCODER

def get_sensor_input():
    print("Enter sensor values for prediction:")
    while True:
        try:
            temperature = float(input("Temperature: "))
            smoke_density = float(input("Smoke Density: "))
            gas_level = float(input("Gas Level: "))
            humidity = float(input("Humidity: "))
            break
        except ValueError:
            print("Invalid input. Please enter numeric values.")
    return np.array([[temperature, smoke_density, gas_level, humidity]])

def batch_predict(input_csv, output_csv):
    if not os.path.exists(input_csv):
        logger.error(f"Input file {input_csv} does not exist.")
        print(f"Error: Input file {input_csv} does not exist.")
        return
    try:
        df = pd.read_csv(input_csv)
        features = ['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity']
        if not all(col in df.columns for col in features):
            logger.error("Input CSV missing required columns.")
            print("Error: Input CSV missing required columns.")
            return
        X = df[features].values
        except Exception as e:
            logger.error(f"Error reading input CSV: {e}")
            print(f"Error reading input CSV: {e}")
            return

        try:
            model, label_encoder = get_models()
        except Exception as e:
            logger.error(f"Error loading model or encoder: {e}")
            print(f"Error loading model or encoder: {e}")
            return

    try:
        predictions = model.predict(X)
        predicted_labels = label_encoder.inverse_transform(predictions)
        df['PredictedFireSeverity'] = predicted_labels

        # Ensure output directory exists
        import os
        output_dir = os.path.dirname(output_csv)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        df.to_csv(output_csv, index=False)
        logger.info(f"Batch predictions saved to {output_csv}")
        print(f"Batch predictions saved to {output_csv}")
    except Exception as e:
        logger.error(f"Error during prediction: {e}")
        print(f"Error during prediction: {e}")

def main():
    parser = argparse.ArgumentParser(description="Fire severity prediction script.")
    parser.add_argument('--batch', type=str, help='Path to input CSV file for batch prediction.')
    parser.add_argument('--output', type=str, default='batch_predictions.csv', help='Path to save batch prediction results.')
    args = parser.parse_args()

    if args.batch:
        batch_predict(args.batch, args.output)
    else:
        sample_data = get_sensor_input()
        try:
            model, label_encoder = get_models()
        except Exception as e:
            logger.error(f"Error loading model or encoder: {e}")
            print(f"Error loading model or encoder: {e}")
            return

        try:
            prediction = model.predict(sample_data)
            predicted_label = label_encoder.inverse_transform(prediction)
            print(f"🔥 Predicted Fire Severity: {predicted_label[0]}")
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            print(f"Error during prediction: {e}")

if __name__ == "__main__":
    main()
