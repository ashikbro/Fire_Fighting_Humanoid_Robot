import streamlit as st
import pandas as pd
import time
import os

DATA_PATH = "alerts/prediction_logs.csv"

def load_data():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        return df
    else:
        st.warning(f"Data file {DATA_PATH} not found.")
        return None

def main():
    st.title("Fire Fighting Humanoid Robot - Real-time Dashboard")

    placeholder = st.empty()

    while True:
        df = load_data()
        if df is not None:
            with placeholder.container():
                st.subheader("Latest Fire Prediction Logs")
                st.write(df.tail(10))
                if 'prediction' in df.columns:
                    latest_pred = df['prediction'].iloc[-1]
                    if latest_pred >= 0.5:
                        st.error(f"🔥 Fire Alert! Latest prediction confidence: {latest_pred}")
                    else:
                        st.success("No fire detected in latest prediction.")
        time.sleep(10)

if __name__ == "__main__":
    main()
