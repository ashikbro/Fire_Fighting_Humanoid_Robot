# Fire Severity Prediction Project

This project trains a machine learning model to predict fire severity based on sensor data such as temperature, smoke density, gas level, and humidity. It includes scripts for training the model, making predictions, a REST API for real-time prediction, visualization utilities, and a GUI application.

## Project Structure

```
Fire_Fighting_Humanoid_Robot/
│
├── src/
│   ├── train_fire_model.py       # Training script
│   ├── predict_fire.py           # Prediction script (supports CLI and batch prediction)
│   ├── api.py                   # FastAPI REST API for real-time prediction
│   ├── visualization.py         # Visualization utilities for data and model
│   └── fire_gui_app.py          # Tkinter GUI application for fire severity prediction
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

### Real-time Robot API

The API is a Flask application. Start it with:

```bash
python src/api.py
```

The server listens on `http://127.0.0.1:5000` by default. Configure `API_HOST`,
`API_PORT`, `SIMULATION_MODE`, and other settings in a local `.env` file.

Send movement commands to `http://localhost:5000/api/v1/move`:

```json
{
  "command": "stop"
}
```

Protected endpoints use HTTP Basic Authentication. Create a local `users.txt`
from `users.example.txt`; credentials are intentionally not committed. Passwords
must be Werkzeug password hashes, not plaintext. Generate one with:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-password'))"
```

The unauthenticated health endpoint is available at
`GET /api/v1/health`. Docker Compose runs the service in simulation mode and
uses this endpoint for its container health check.

### Docker

```bash
docker compose up --build
```

The container exposes the API on port `5000`.

### GUI Application

Run the Tkinter GUI application to input sensor data and get fire severity predictions via the API:

```bash
python src/fire_gui_app.py
```

## Notes

- Ensure the dataset file is in the `data/` directory.
- The trained model and label encoder files must be present in the `models/` directory to run predictions.
- The confusion matrix and feature importance images will be saved in the `results/` directory after training.
- The API server must be running to use the GUI application.
