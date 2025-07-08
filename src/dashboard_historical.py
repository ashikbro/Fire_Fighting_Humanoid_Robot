import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

DATA_PATH = "alerts/prediction_logs.csv"

def load_data():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        return df
    else:
        st.warning(f"Data file {DATA_PATH} not found.")
        return None

def plot_trends(df):
    st.subheader("Fire Prediction Trends")
    if 'timestamp' in df.columns and 'prediction' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        daily_sum = df['prediction'].resample('D').sum()
        st.line_chart(daily_sum)
    else:
        st.warning("Required columns 'timestamp' and 'prediction' not found in data.")

def plot_heatmap(df):
    st.subheader("Prediction Heatmap by Hour and Day")
    if 'timestamp' in df.columns and 'prediction' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day'] = df['timestamp'].dt.dayofweek
        heatmap_data = df.pivot_table(index='hour', columns='day', values='prediction', aggfunc='mean')
        fig, ax = plt.subplots()
        sns.heatmap(heatmap_data, ax=ax, cmap="YlOrRd")
        st.pyplot(fig)
    else:
        st.warning("Required columns 'timestamp' and 'prediction' not found in data.")

def main():
    st.title("Fire Fighting Humanoid Robot - Historical Data Analysis")

    df = load_data()
    if df is not None:
        plot_trends(df)
        plot_heatmap(df)

if __name__ == "__main__":
    main()
