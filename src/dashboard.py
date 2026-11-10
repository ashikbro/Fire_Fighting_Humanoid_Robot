"""Streamlit dashboard for fire prediction logs.

Run with:  streamlit run src/dashboard.py

Combines the former dashboard.py, dashboard_realtime.py, dashboard_remote.py
and dashboard_historical.py: overview, daily trend, hour/day heatmap, latest
alert, and optional auto-refresh (sidebar).
"""

import os
import time

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

DATA_PATH = "alerts/prediction_logs.csv"
REQUIRED_COLUMNS = ("timestamp", "prediction")


def load_data():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        if all(col in df.columns for col in REQUIRED_COLUMNS):
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    st.warning(f"Data file {DATA_PATH} not found.")
    return None


def has_required_columns(df):
    if all(col in df.columns for col in REQUIRED_COLUMNS):
        return True
    st.warning("Required columns 'timestamp' and 'prediction' not found in data.")
    return False


def show_latest(df):
    st.subheader("Latest Fire Prediction Logs")
    st.write(df.tail(10))


def plot_trends(df):
    st.subheader("Fire Prediction Trends (daily)")
    if has_required_columns(df):
        daily_sum = df.set_index("timestamp")["prediction"].resample("D").sum()
        st.line_chart(daily_sum)


def plot_heatmap(df):
    st.subheader("Prediction Heatmap by Hour and Day")
    if has_required_columns(df):
        heatmap_data = df.assign(
            hour=df["timestamp"].dt.hour, day=df["timestamp"].dt.day_of_week
        ).pivot_table(index="hour", columns="day", values="prediction", aggfunc="mean")
        fig, ax = plt.subplots()
        sns.heatmap(heatmap_data, ax=ax, cmap="YlOrRd")
        st.pyplot(fig)


def check_alerts(df):
    if df.empty or "prediction" not in df.columns:
        return
    latest_prediction = df["prediction"].iloc[-1]
    if latest_prediction >= 0.5:
        st.error(f"🔥 Fire Alert! Latest prediction confidence: {latest_prediction}")
    else:
        st.success("No fire detected in latest prediction.")


def main():
    st.title("Fire Fighting Humanoid Robot - Dashboard")

    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=False)
    interval = st.sidebar.slider("Refresh interval (seconds)", 5, 120, 10, disabled=not auto_refresh)

    df = load_data()
    if df is not None:
        check_alerts(df)
        show_latest(df)
        plot_trends(df)
        plot_heatmap(df)

    if auto_refresh:
        time.sleep(interval)
        st.rerun()


if __name__ == "__main__":
    main()
