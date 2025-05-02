import pytest
from src import predict_fire
import sys

def test_main_function(monkeypatch):
    test_args = ["predict_fire.py"]
    monkeypatch.setattr(sys, 'argv', test_args)

    inputs = iter(["50.0", "100.0", "300.0", "40.0"])  # Mocked input values for temperature, smoke_density, gas_level, humidity
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))

    try:
        predict_fire.main()
    except SystemExit:
        pass
