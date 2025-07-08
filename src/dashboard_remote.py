import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import time

DATA_PATH = "alerts/prediction_logs.csv"

def load_data():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        return df
    else:
        st.warning(f"Data file {DATA_PATH} not found.")
        return None

def plot_fire_predictions(df):
    st.subheader("Fire Prediction Logs Overview")
    st.write(df.head())

    if 'timestamp' in df.columns and 'prediction' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        prediction_counts = df['prediction'].resample('D').sum()
        st.line_chart(prediction_counts)
    else:
        st.warning("Required columns 'timestamp' and 'prediction' not found in data.")

def check_alerts(df):
    if df is None or 'prediction' not in df.columns:
        return
    latest_prediction = df['prediction'].iloc[-1]
    if latest_prediction >= 0.5:
        st.error(f"🔥 Fire Alert! Latest prediction confidence: {latest_prediction}")
    else:
        st.success("No fire detected in latest prediction.")

def main():
    st.title("Fire Fighting Humanoid Robot - Remote Monitoring Dashboard")

    while True:
        df = load_data()
        if df is not None:
            plot_fire_predictions(df)
            check_alerts(df)
        time.sleep(60)  # refresh every 60 seconds

if __name__ == "__main__":
    main()
