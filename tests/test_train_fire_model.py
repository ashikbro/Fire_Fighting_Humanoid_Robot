import pytest
import pandas as pd
from src import train_fire_model
import sys

def test_data_loading():
    df = pd.read_csv('data/fire_data_bangladesh.csv')
    assert not df.empty
    assert all(col in df.columns for col in ['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity', 'FireSeverity'])

def test_main_function(monkeypatch):
    test_args = ["train_fire_model.py", "--data", "data/fire_data_bangladesh.csv"]
    monkeypatch.setattr(sys, 'argv', test_args)
    try:
        train_fire_model.main()
    except SystemExit:
        # main() calls exit(), which raises SystemExit, so we catch it here
        pass
