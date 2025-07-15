import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score, roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import argparse
import logging
import os
from sklearn.impute import SimpleImputer
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def download_file(url, dest_path):
    """Download a file from a URL to a destination path."""
    if not os.path.exists(os.path.dirname(dest_path)):
        os.makedirs(os.path.dirname(dest_path))
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for bad status codes
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"✅ Downloaded '{dest_path}' from '{url}'")
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error downloading file from '{url}': {e}")
        exit(1)

def main():
    parser = argparse.ArgumentParser(description="Train a fire severity prediction model.")
    parser.add_argument("--data", type=str, nargs='+', default=["data/fire_data_bangladesh.csv"], help="Paths to dataset CSV files.")
    parser.add_argument("--model_dir", type=str, default="models", help="Directory to save the trained models.")
    parser.add_argument("--results_dir", type=str, default="results", help="Directory to save the evaluation results.")
    parser.add_argument("--model_type", type=str, default="random_forest", choices=["random_forest", "gradient_boosting"], help="Type of model to train.")
    args = parser.parse_args()

    # Create directories if they don't exist
    os.makedirs(args.model_dir, exist_ok=True)
    os.makedirs(args.results_dir, exist_ok=True)

    # Define the dataset URL
    DATASET_URL = "https://raw.githubusercontent.com/a-m-a-n-s-i-n-g-h/Fire-Fighting-Humanoid-Robot/main/data/fire_data_bangladesh.csv"

    # Load and combine datasets with error handling
    dfs = []
    for data_path in args.data:
        if not os.path.exists(data_path):
            logging.warning(f"⚠️ Dataset file '{data_path}' not found. Attempting to download...")
            download_file(DATASET_URL, data_path)
        
        try:
            df_part = pd.read_csv(data_path)
            dfs.append(df_part)
        except Exception as e:
            logging.error(f"❌ Error loading dataset '{data_path}': {e}")
            exit(1)
    df = pd.concat(dfs, ignore_index=True)

    # Check if required columns exist
    required_columns = ['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity', 'FireSeverity']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logging.error(f"❌ Missing columns in dataset: {missing_columns}")
        exit(1)

    # Features and target
    X = df[['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity']]
    y = df['FireSeverity']

    # Feature engineering: add interaction terms and polynomial features
    X['Temp_Smoke_Interaction'] = X['Temperature'] * X['SmokeDensity']
    X['Gas_Humidity_Interaction'] = X['GasLevel'] * X['Humidity']
    X['Temp_Squared'] = X['Temperature'] ** 2
    X['Smoke_Squared'] = X['SmokeDensity'] ** 2
    X['Gas_Squared'] = X['GasLevel'] ** 2
    X['Humidity_Squared'] = X['Humidity'] ** 2

    # Handle missing values by imputing with mean
    imputer = SimpleImputer(strategy='mean')
    X_imputed = pd.DataFrame(imputer.fit_transform(X), columns=X.columns)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)

    # Encode target labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    # Split dataset
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_encoded, test_size=0.2, random_state=42
    )

    # Select model type
    if args.model_type == "random_forest":
        model = RandomForestClassifier(random_state=42)
        param_grid = {
            'n_estimators': [50, 100, 150],
            'max_depth': [None, 10, 20],
            'min_samples_split': [2, 5],
            'min_samples_leaf': [1, 2]
        }
    elif args.model_type == "gradient_boosting":
        model = GradientBoostingClassifier(random_state=42)
        param_grid = {
            'n_estimators': [50, 100, 150],
            'learning_rate': [0.01, 0.1, 0.2],
            'max_depth': [3, 5, 7]
        }

    # Hyperparameter tuning with GridSearchCV
    logging.info(f"🔍 Starting hyperparameter tuning for {args.model_type} with GridSearchCV...")
    grid_search = GridSearchCV(model, param_grid, cv=3, n_jobs=-1, verbose=1)
    grid_search.fit(X_train, y_train)
    best_model = grid_search.best_estimator_
    logging.info(f"✅ Best parameters found: {grid_search.best_params_}")

    # Predict
    y_pred = best_model.predict(X_test)

    # Classification report
    report = classification_report(y_test, y_pred, target_names=label_encoder.classes_, output_dict=True)
    report_df = pd.DataFrame(report).transpose()
    report_path = os.path.join(args.results_dir, "classification_report.csv")
    report_df.to_csv(report_path)
    logging.info(f"📊 Classification report saved to '{report_path}'")

    # Confusion matrix
    conf_matrix = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(6, 4))
    sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='OrRd',
                xticklabels=label_encoder.classes_, yticklabels=label_encoder.classes_)
    plt.title("Confusion Matrix")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    confusion_path = os.path.join(args.results_dir, "confusion_matrix.png")
    plt.savefig(confusion_path)
    plt.close()
    logging.info(f"🖼️ Confusion matrix saved as '{confusion_path}'")

    # Feature importance plot
    importances = best_model.feature_importances_
    feature_names = X.columns
    plt.figure(figsize=(8, 6))
    sns.barplot(x=importances, y=feature_names, palette="viridis")
    plt.title("Feature Importance")
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    feature_importance_path = os.path.join(args.results_dir, "feature_importance.png")
    plt.savefig(feature_importance_path)
    plt.close()
    logging.info(f"🖼️ Feature importance saved as '{feature_importance_path}'")

    # Model versioning
    version = 1
    while os.path.exists(os.path.join(args.model_dir, f"fire_severity_model_v{version}.pkl")):
        version += 1

    model_path = os.path.join(args.model_dir, f"fire_severity_model_v{version}.pkl")
    encoder_path = os.path.join(args.model_dir, f"label_encoder_v{version}.pkl")
    scaler_path = os.path.join(args.model_dir, f"scaler_v{version}.pkl")

    # Save model and encoder
    try:
        joblib.dump(best_model, model_path)
        joblib.dump(label_encoder, encoder_path)
        joblib.dump(scaler, scaler_path)
        logging.info(f"✅ Model saved as '{model_path}'")
        logging.info(f"✅ Label encoder saved as '{encoder_path}'")
        logging.info(f"✅ Scaler saved as '{scaler_path}'")
    except Exception as e:
        logging.error(f"❌ Error saving model or label encoder: {e}")
        exit(1)

    # Accuracy
    accuracy = accuracy_score(y_test, y_pred)
    logging.info(f"Accuracy: {accuracy:.2f}")
    print(f"Accuracy: {accuracy:.2f}")

    # Additional evaluation metrics
    f1 = f1_score(y_test, y_pred, average='weighted')
    try:
        # For multiclass, use 'ovr' (one-vs-rest) strategy
        y_proba = best_model.predict_proba(X_test)
        auc = roc_auc_score(y_test, y_proba, multi_class='ovr')
    except Exception as e:
        logging.warning(f"Could not compute AUC: {e}")
        auc = None

    logging.info(f"F1 Score: {f1:.2f}")
    print(f"F1 Score: {f1:.2f}")
    if auc is not None:
        logging.info(f"AUC: {auc:.2f}")
        print(f"AUC: {auc:.2f}")

if __name__ == "__main__":
    main()
