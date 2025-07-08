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

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    parser = argparse.ArgumentParser(description="Train a fire severity prediction model.")
    parser.add_argument("--data", type=str, nargs='+', default=["data/fire_data_bangladesh.csv"], help="Paths to dataset CSV files.")
    parser.add_argument("--model", type=str, default="models/fire_severity_model.pkl", help="Path to save the trained model.")
    parser.add_argument("--encoder", type=str, default="models/label_encoder.pkl", help="Path to save the label encoder.")
    parser.add_argument("--confusion", type=str, default="results/confusion_matrix.png", help="Path to save the confusion matrix image.")
    parser.add_argument("--feature_importance", type=str, default="results/feature_importance.png", help="Path to save the feature importance image.")
    parser.add_argument("--model_type", type=str, default="random_forest", choices=["random_forest", "gradient_boosting"], help="Type of model to train.")
    args = parser.parse_args()

    # Load and combine datasets with error handling
    dfs = []
    for data_path in args.data:
        if not os.path.exists(data_path):
            logging.error(f"❌ Error: Dataset file '{data_path}' not found.")
            exit(1)
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
    logging.info("📊 Classification Report:\n%s", classification_report(y_test, y_pred, target_names=label_encoder.classes_))

    # Confusion matrix
    conf_matrix = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(6, 4))
    sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='OrRd',
                xticklabels=label_encoder.classes_, yticklabels=label_encoder.classes_)
    plt.title("Confusion Matrix")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    plt.savefig(args.confusion)
    plt.close()
    logging.info(f"🖼️ Confusion matrix saved as '{args.confusion}'")

    # Feature importance plot
    importances = best_model.feature_importances_
    feature_names = X.columns
    plt.figure(figsize=(8, 6))
    sns.barplot(x=importances, y=feature_names, palette="viridis")
    plt.title("Feature Importance")
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    plt.savefig(args.feature_importance)
    plt.close()
    logging.info(f"🖼️ Feature importance saved as '{args.feature_importance}'")

    # Ensure directories exist before saving
    model_dir = os.path.dirname(args.model)
    encoder_dir = os.path.dirname(args.encoder)
    confusion_dir = os.path.dirname(args.confusion)
    feature_importance_dir = os.path.dirname(args.feature_importance)

    for directory in [model_dir, encoder_dir, confusion_dir, feature_importance_dir]:
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    # Save model and encoder
    try:
        joblib.dump(best_model, args.model)
        joblib.dump(label_encoder, args.encoder)
        joblib.dump(scaler, os.path.join(os.path.dirname(args.model), 'scaler.pkl'))
        logging.info(f"✅ Model saved as '{args.model}'")
        logging.info(f"✅ Label encoder saved as '{args.encoder}'")
        logging.info(f"✅ Scaler saved as '{os.path.join(os.path.dirname(args.model), 'scaler.pkl')}'")
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
