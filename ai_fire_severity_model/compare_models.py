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

from sklearn.neural_network import MLPClassifier

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def plot_confusion_matrix(y_true, y_pred, classes, output_path):
    conf_matrix = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 4))
    sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='OrRd',
                xticklabels=classes, yticklabels=classes)
    plt.title("Confusion Matrix")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logging.info(f"Confusion matrix saved as '{output_path}'")

def plot_feature_importance(importances, feature_names, output_path, model_name):
    plt.figure(figsize=(8, 6))
    sns.barplot(x=importances, y=feature_names, palette="viridis")
    plt.title(f"Feature Importance - {model_name}")
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    logging.info(f"Feature importance saved as '{output_path}'")

def main():
    # Use combined dataset including UCI Forest Fires
    data_path = "data/fire_data_uci_forest_fires_preprocessed.csv"
    if not os.path.exists(data_path):
        logging.error(f"Dataset file '{data_path}' not found. Please run download_public_dataset.py first.")
        return

    df = pd.read_csv(data_path)

    required_columns = ['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity', 'FireSeverity']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logging.error(f"Missing columns in dataset: {missing_columns}")
        return

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
        plot_confusion_matrix(y_test, y_pred, label_encoder.classes_, conf_matrix_path)

        if hasattr(model, "feature_importances_"):
            feature_importance_path = f"results/feature_importance_{name}.png"
            plot_feature_importance(model.feature_importances_, X.columns, feature_importance_path, name)

        model_path = f"models/fire_severity_model_{name}.pkl"
        joblib.dump(model, model_path)
        logging.info(f"Saved {name} model to {model_path}")

        results[name] = accuracy

    # Print summary
    logging.info("Model comparison results:")
    for name, acc in results.items():
        logging.info(f"{name}: Accuracy = {acc:.4f}")

if __name__ == "__main__":
    main()
