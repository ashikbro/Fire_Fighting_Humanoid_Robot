import streamlit as st
import pandas as pd
import os

DATA_PATH = "alerts/prediction_logs.csv"

def load_alerts():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        return df
    else:
        st.warning(f"Data file {DATA_PATH} not found.")
        return None

def show_alert_history():
    st.title("Alert History")

    df = load_alerts()
    if df is not None:
        if 'timestamp' in df.columns and 'prediction' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            st.dataframe(df.sort_values(by='timestamp', ascending=False))
            threshold = st.slider("Alert Threshold", 0.0, 1.0, 0.5)
            alerts = df[df['prediction'] >= threshold]
            st.subheader(f"Alerts with prediction >= {threshold}")
            st.dataframe(alerts.sort_values(by='timestamp', ascending=False))
        else:
            st.warning("Required columns 'timestamp' and 'prediction' not found in data.")

if __name__ == "__main__":
    show_alert_history()
