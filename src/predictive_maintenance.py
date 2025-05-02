import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import matplotlib.pyplot as plt
import os

class PredictiveMaintenance:
    def __init__(self, data_path='alerts/prediction_logs.csv'):
        self.data_path = data_path
        self.model = RandomForestRegressor()
        self.trained = False

    def load_data(self):
        df = pd.read_csv(self.data_path)
        # Assume sensor readings and a target variable 'time_to_failure' exist
        # For demo, create a synthetic target
        df['time_to_failure'] = np.random.randint(1, 100, size=len(df))
        return df

    def train_model(self):
        df = self.load_data()
        features = ['temperature', 'smoke_density', 'gas_level', 'humidity']
        X = df[features]
        y = df['time_to_failure']
        self.model.fit(X, y)
        self.trained = True
        print("Predictive maintenance model trained.")

    def predict_maintenance(self, sensor_data):
        if not self.trained:
            self.train_model()
        features = np.array([[sensor_data.get(f, 0) for f in ['temperature', 'smoke_density', 'gas_level', 'humidity']]])
        prediction = self.model.predict(features)[0]
        return prediction

    def plot_feature_importance(self):
        if not self.trained:
            print("Model not trained yet.")
            return
        importances = self.model.feature_importances_
        features = ['temperature', 'smoke_density', 'gas_level', 'humidity']
        plt.bar(features, importances)
        plt.title("Feature Importance for Predictive Maintenance")
        plt.show()

if __name__ == "__main__":
    pm = PredictiveMaintenance()
    pm.train_model()
    sample_data = {'temperature': 30, 'smoke_density': 120, 'gas_level': 40, 'humidity': 35}
    time_to_failure = pm.predict_maintenance(sample_data)
    print(f"Predicted time to failure: {time_to_failure:.2f} units")
    pm.plot_feature_importance()
