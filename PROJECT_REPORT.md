# Fire Severity Prediction Project Report

## Project Overview
This project develops a machine learning system to predict fire severity using sensor data such as temperature, smoke density, gas level, and humidity. It integrates model training, prediction via CLI and REST API, visualization tools, and real-time monitoring through a dashboard and GUI applications. The system also includes a vision-based fire detection module and robot control APIs for a Fire Fighting Humanoid Robot.

## Dataset and Features
- Dataset: `data/fire_data_bangladesh.csv`
- Features: Temperature, SmokeDensity, GasLevel, Humidity
- Target variable: FireSeverity (categorical)
- Missing data handled by mean imputation during training

## Model Training
- Model: RandomForestClassifier with hyperparameter tuning using GridSearchCV
- Hyperparameters tuned: n_estimators, max_depth, min_samples_split, min_samples_leaf
- Data split: 80% training, 20% testing
- Evaluation: classification report, confusion matrix, accuracy score
- Model and label encoder saved in `models/`
- Confusion matrix and feature importance plots saved in `results/`

### Training Code Snippet
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [50, 100, 150],
    'max_depth': [None, 10, 20],
    'min_samples_split': [2, 5],
    'min_samples_leaf': [1, 2]
}
rf = RandomForestClassifier(random_state=42)
grid_search = GridSearchCV(rf, param_grid, cv=3, n_jobs=-1, verbose=1)
grid_search.fit(X_train, y_train)
best_model = grid_search.best_estimator_
```

## AI Model Training Comparison
- Multiple models were trained and compared on a combined dataset including UCI Forest Fires.
- Models compared: RandomForest, GradientBoosting, SVM, MLP, ExtraTrees, AdaBoost, KNN, LogisticRegression, XGBoost, LightGBM, CatBoost (if installed).
- Each model was evaluated on accuracy, classification report, confusion matrix, and feature importance (if available).
- Models were saved for future use.

### Model Comparison Code Snippet
```python
import pandas as pd
import os
import logging
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier, AdaBoostClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

# Import additional models
try:
    from xgboost import XGBClassifier
except ImportError:
    XGBClassifier = None
    logging.warning("XGBoost not installed. Skipping XGBClassifier.")

try:
    import lightgbm as lgb
except ImportError:
    lgb = None
    logging.warning("LightGBM not installed. Skipping LightGBM.")

try:
    from catboost import CatBoostClassifier
except ImportError:
    CatBoostClassifier = None
    logging.warning("CatBoost not installed. Skipping CatBoostClassifier.")

# Load and preprocess data
data_path = "data/fire_data_uci_forest_fires_preprocessed.csv"
df = pd.read_csv(data_path)
X = df[['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity']]
y = df['FireSeverity']

imputer = SimpleImputer(strategy='mean')
X_imputed = pd.DataFrame(imputer.fit_transform(X), columns=X.columns)

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

X_train, X_test, y_train, y_test = train_test_split(
    X_imputed, y_encoded, test_size=0.2, random_state=42
)

models = {
    "RandomForest": RandomForestClassifier(random_state=42),
    "GradientBoosting": GradientBoostingClassifier(random_state=42),
    "SVM": SVC(probability=True, random_state=42),
    "MLP": MLPClassifier(random_state=42, max_iter=500),
    "ExtraTrees": ExtraTreesClassifier(random_state=42),
    "AdaBoost": AdaBoostClassifier(random_state=42),
    "KNN": KNeighborsClassifier(),
    "LogisticRegression": LogisticRegression(max_iter=500, random_state=42)
}

if XGBClassifier is not None:
    models["XGBoost"] = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', random_state=42)
if lgb is not None:
    models["LightGBM"] = lgb.LGBMClassifier(random_state=42)
if CatBoostClassifier is not None:
    models["CatBoost"] = CatBoostClassifier(verbose=0, random_state=42)

results = {}

for name, model in models.items():
    logging.info(f"Training {name}...")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logging.info(f"{name} Accuracy: {accuracy:.4f}")
    logging.info(f"Classification Report for {name}:\n{classification_report(y_test, y_pred, target_names=label_encoder.classes_)}")

    conf_matrix_path = f"results/confusion_matrix_{name}.png"
    # Confusion matrix plotting code here

    if hasattr(model, "feature_importances_"):
        feature_importance_path = f"results/feature_importance_{name}.png"
        # Feature importance plotting code here

    model_path = f"models/fire_severity_model_{name}.pkl"
    joblib.dump(model, model_path)
    logging.info(f"Saved {name} model to {model_path}")

    results[name] = accuracy

# Print summary
logging.info("Model comparison results:")
for name, acc in results.items():
    logging.info(f"{name}: Accuracy = {acc:.4f}")
```

## Prediction Methods
- CLI interactive mode: user inputs sensor values, model predicts fire severity
- Batch prediction: input CSV file with sensor data, output CSV with predicted fire severity
- REST API: FastAPI server (`src/api.py`) accepts JSON sensor data, computes engineered features, and returns predicted fire severity

## Deep Learning Model
- A deep learning model was developed using TensorFlow Keras with a sequential architecture.
- The model consists of two hidden layers with 64 and 32 neurons respectively, each followed by dropout layers to prevent overfitting.
- Input features include Temperature, SmokeDensity, GasLevel, and Humidity, with FireSeverity as the target.
- Data preprocessing includes mean imputation for missing values, feature scaling, and label encoding.
- The model was trained with early stopping based on validation loss to avoid overfitting.
- Evaluation metrics include accuracy, classification report, and confusion matrix.
- The trained model is saved as `models/fire_severity_model_DeepLearning.h5`.
- Confusion matrix visualization is saved as `results/confusion_matrix_DeepLearning.png`.

### Deep Learning Model Code Snippet
```python
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
import pandas as pd
import numpy as np

# Data preprocessing
df = pd.read_csv("data/fire_data_bangladesh_augmented.csv")
X = df[['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity']]
y = df['FireSeverity']

imputer = SimpleImputer(strategy='mean')
X_imputed = imputer.fit_transform(X)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
y_categorical = np.eye(len(np.unique(y_encoded)))[y_encoded]

# Model building
model = Sequential()
model.add(Dense(64, input_dim=X_scaled.shape[1], activation='relu'))
model.add(Dropout(0.3))
model.add(Dense(32, activation='relu'))
model.add(Dropout(0.3))
model.add(Dense(len(np.unique(y_encoded)), activation='softmax'))
model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

# Training with early stopping
early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
model.fit(X_scaled, y_categorical, validation_split=0.2, epochs=100, batch_size=32, callbacks=[early_stop])

## Visualization Utilities
- Sensor data distribution plots
- Fire severity class counts
- Feature importance bar plot
- ROC curve for model evaluation (if supported)
- Implemented in `src/visualization.py`

## System Architecture
- `main.py` orchestrates:
  - FastAPI API server for prediction
  - Vision fire detection module (`vision_fire_detection/fire_detection.py`)
  - GUI application for user interaction (`gui_simulation/gui_app.py`)
  - GUI for model comparison visuals (`gui_simulation/gui_with_visuals.py`)

## Dashboard and Robot Control
- Dashboard (`dashboard/firebot_updated.html`) features:
  - Live camera feed with detection overlays
  - Robot status panel (AI model status, movement mode, location, battery, uptime)
  - Sensor data display (temperature, flame detection, gas/smoke level, power consumption)
  - Control panel for robot movement, speed, extinguisher activation, AI restart, and reboot
  - Detection history chart and table
  - System logs with filtering and clearing

- Robot Control API (`src/api_control.py`) provides endpoints for:
  - Retrieving sensor data and robot status
  - Sending movement commands (direction and speed)
  - Sending control commands (activate extinguisher, restart AI, reboot)

## Usage Instructions
- Install dependencies: `pip install -r requirements.txt`
- Train model: `python src/train_fire_model.py`
- Run CLI prediction: `python src/predict_fire.py`
- Run batch prediction: `python src/predict_fire.py --batch input.csv --output output.csv`
- Start API server: `uvicorn src.api:app --reload`
- Run GUI app: `python gui_simulation/gui_app.py`
- Open dashboard: open `dashboard/firebot_updated.html` in a browser
- Run main orchestration: `python main.py`

## Summary
This project integrates machine learning, real-time prediction, visualization, and robotic control to create a comprehensive Fire Severity Prediction system. The modular design supports easy extension and deployment in firefighting humanoid robots, enhancing safety and response efficiency.

---

*Report generated from project source code and documentation.*
