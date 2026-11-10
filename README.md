# Fire Severity Prediction Project

This project trains a machine learning model to predict fire severity based on sensor data such as temperature, smoke density, gas level, and humidity. It includes scripts for training the model, making predictions, a REST API for real-time prediction, visualization utilities, and a GUI application.

## Project Structure

```
Fire_Fighting_Humanoid_Robot/
│
├── src/
│   ├── train_fire_model.py       # Training script
│   ├── predict_fire.py           # Prediction script (supports CLI and batch prediction)
│   ├── api.py                   # Flask robot control API (port 5000)
│   ├── api_part1.py             # FastAPI fire severity prediction API (port 8000)
│   ├── auth.py                  # API user management (hashed passwords)
│   ├── visualization.py         # Visualization utilities for data and model
│   └── fire_gui_app.py          # Tkinter GUI application for fire severity prediction
│
├── data/
│   └── fire_data_bangladesh.csv  # Dataset (not committed, see Notes)
│
├── models/
│   ├── fire_severity_model.pkl   # Trained model (created by training)
│   └── label_encoder.pkl         # Label encoder
│
├── results/
│   ├── confusion_matrix.png      # Confusion matrix image
│   └── feature_importance.png    # Feature importance image
│
├── .gitignore
├── README.md
├── requirements.txt
└── venv/                        # Virtual environment (ignored)
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

### Robot Control API (Flask)

The robot control API is in `src/api.py`. Some endpoints need a login, so create
at least one user first. Users are stored in `users.txt` (git-ignored) with
hashed passwords:

```bash
cp .env.example .env
python -m src.auth add admin admin
```

Then start the server (listens on `API_HOST:API_PORT`, default `127.0.0.1:5000`):

```bash
python src/api.py
```

Endpoints are under `/api/v1`, for example `GET /api/v1/status` and
`POST /api/v1/move` with `{"command": "move_forward"}`. Admin/operator endpoints
use HTTP Basic auth.

### Fire Severity Prediction API (FastAPI)

```bash
uvicorn src.api_part1:app --port 8000
```

Send POST requests to `http://localhost:8000/predict` with JSON body:

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

`python main.py` starts both APIs, the vision detector and the GUI together.

### GUI Application

Run the Tkinter GUI application to input sensor data and get fire severity predictions via the API:

```bash
python src/fire_gui_app.py
```

## Notes

- The dataset and trained models are **not** in the repository (`*.csv` and
  `*.pkl` are git-ignored). Put the dataset at `data/fire_data_bangladesh.csv`
  and run `python src/train_fire_model.py` to create the files in `models/`.
- Secrets (alert e-mail login, users file) go in `.env`, never in code. See `.env.example`.
- The trained model and label encoder files must be present in the `models/` directory to run predictions.
- The confusion matrix and feature importance images will be saved in the `results/` directory after training.
- The API server must be running to use the GUI application.
