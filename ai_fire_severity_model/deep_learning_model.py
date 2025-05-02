import os
import logging
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

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

def build_model(input_dim, num_classes):
    model = Sequential()
    model.add(Dense(64, input_dim=input_dim, activation='relu'))
    model.add(Dropout(0.3))
    model.add(Dense(32, activation='relu'))
    model.add(Dropout(0.3))
    model.add(Dense(num_classes, activation='softmax'))
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
    return model

def main():
    data_path = "data/fire_data_bangladesh_augmented.csv"
    if not os.path.exists(data_path):
        logging.error(f"Dataset file '{data_path}' not found. Please run data augmentation first.")
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

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imputed)

    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    y_categorical = to_categorical(y_encoded)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_categorical, test_size=0.2, random_state=42
    )

    input_dim = X_train.shape[1]
    num_classes = y_categorical.shape[1]

    model = build_model(input_dim, num_classes)

    early_stop = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

    history = model.fit(
        X_train, y_train,
        validation_split=0.2,
        epochs=100,
        batch_size=32,
        callbacks=[early_stop],
        verbose=1
    )

    # Evaluate
    y_pred_prob = model.predict(X_test)
    y_pred = np.argmax(y_pred_prob, axis=1)
    y_true = np.argmax(y_test, axis=1)

    accuracy = accuracy_score(y_true, y_pred)
    logging.info(f"Deep Learning Model Accuracy: {accuracy:.4f}")
    logging.info(f"Classification Report:\n{classification_report(y_true, y_pred, target_names=label_encoder.classes_)}")

    conf_matrix_path = "results/confusion_matrix_DeepLearning.png"
    plot_confusion_matrix(y_true, y_pred, label_encoder.classes_, conf_matrix_path)

    # Save model
    model_path = "models/fire_severity_model_DeepLearning.h5"
    model.save(model_path)
    logging.info(f"Saved deep learning model to {model_path}")

if __name__ == "__main__":
    main()
