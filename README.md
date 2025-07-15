# Fire Severity Prediction Project

This project trains a machine learning model to predict fire severity based on sensor data such as temperature, smoke density, gas level, and humidity. It includes scripts for training the model, making predictions, a REST API for real-time prediction, and visualization utilities.

## Project Structure

```
Fire_Fighting_Humanoid_Robot/
│
├── src/
│   ├── api.py                   # FastAPI REST API for real-time prediction
│   ├── train_fire_model.py       # Training script
│   ├── predict_fire.py           # Prediction script (supports CLI and batch prediction)
│   └── visualization.py         # Visualization utilities for data and model
│
├── data/
│   └── fire_data_bangladesh.csv  # Dataset
│
├── models/
│   ├── fire_severity_model.pkl   # Trained model
│   └── label_encoder.pkl         # Label encoder
│
├── results/
│   ├── confusion_matrix.png      # Confusion matrix image
│   └── feature_importance.png    # Feature importance image
│
├── .gitignore
├── README.md
├── requirements.txt
├── main.py                      # Main entry point for the application
└── docker-compose.yml
```

## Requirements

- Python 3.x
- Install dependencies using:

```bash
pip install -r requirements.txt
```

## Usage

### Training the Model

Run the training script to train the model and save the artifacts:

```bash
python src/train_fire_model.py
```

### Predicting Fire Severity (CLI)

Run the prediction script and enter sensor values when prompted:

```bash
python src/predict_fire.py
```

#### Batch Prediction

You can also perform batch predictions by providing an input CSV file with sensor data:

```bash
python src/predict_fire.py --batch path/to/input.csv --output path/to/output.csv
```

The output CSV will contain an additional column `PredictedFireSeverity`.

### Visualization

Use the visualization utilities to explore data distributions, fire severity counts, feature importance, and ROC curves. You can import and call functions from `src/visualization.py` in your scripts or interactive sessions.

### Real-time Prediction API

Start the FastAPI server:

```bash
python main.py
```

Or with auto-reload for development:

```bash
uvicorn src.api:app --reload
```

Send POST requests to `http://localhost:8000/api/v1/predict` with JSON body:

```json
{
  "temperature": 55.0,
  "smoke_density": 120.0,
  "gas_level": 450.0,
  "humidity": 25.0
}
```

Response:

```json
{
  "fire_severity": "Moderate"
}
```

## User Management

To add a new user to the system, run the `scripts/hash_password.py` script and follow the prompts:

```bash
python scripts/hash_password.py
```

This will securely hash the password and add the new user to the `users.txt` file.

## Notes

- Ensure the dataset file is in the `data/` directory.
- The trained model and label encoder files must be present in the `models/` directory to run predictions.
- The confusion matrix and feature importance images will be saved in the `results/` directory after training.
