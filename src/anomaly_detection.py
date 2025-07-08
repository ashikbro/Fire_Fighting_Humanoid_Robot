import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt
import os

def detect_anomalies(data_path):
    df = pd.read_csv(data_path)
    features = ['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity']
    X = df[features]

    # Fit Isolation Forest
    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    preds = iso_forest.fit_predict(X)

    # Add anomaly column
    df['anomaly'] = preds
    anomalies = df[df['anomaly'] == -1]

    print(f"Detected {len(anomalies)} anomalies out of {len(df)} samples.")

    # Plot anomalies
    plt.figure(figsize=(10,6))
    plt.scatter(df.index, df['Temperature'], c='blue', label='Normal')
    plt.scatter(anomalies.index, anomalies['Temperature'], c='red', label='Anomaly')
    plt.xlabel('Sample Index')
    plt.ylabel('Temperature')
    plt.title('Anomaly Detection in Temperature Sensor Data')
    plt.legend()
    plt.show()

if __name__ == "__main__":
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'fire_data_bangladesh.csv')
    detect_anomalies(data_path)
