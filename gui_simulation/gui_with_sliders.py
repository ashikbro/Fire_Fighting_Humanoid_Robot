import tkinter as tk
from tkinter import messagebox
import requests

API_URL = "http://localhost:8000/predict"

class FireSeveritySliderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fire Severity Prediction with Sensor Sliders")

        self.sensors = {
            "temperature": {"label": "Temperature (°C)", "min": -50, "max": 100},
            "smoke_density": {"label": "Smoke Density", "min": 0, "max": 1000},
            "gas_level": {"label": "Gas Level", "min": 0, "max": 1000},
            "humidity": {"label": "Humidity (%)", "min": 0, "max": 100},
        }

        self.sliders = {}

        for idx, (key, sensor) in enumerate(self.sensors.items()):
            label = tk.Label(root, text=sensor["label"])
            label.grid(row=idx, column=0, padx=10, pady=5, sticky="w")
            slider = tk.Scale(root, from_=sensor["min"], to=sensor["max"], orient=tk.HORIZONTAL, length=300)
            slider.grid(row=idx, column=1, padx=10, pady=5)
            self.sliders[key] = slider

        self.predict_button = tk.Button(root, text="Predict Fire Severity", command=self.predict)
        self.predict_button.grid(row=len(self.sensors), column=0, columnspan=2, pady=10)

        self.result_label = tk.Label(root, text="", font=("Arial", 14))
        self.result_label.grid(row=len(self.sensors)+1, column=0, columnspan=2, pady=10)

    def predict(self):
        data = {key: slider.get() for key, slider in self.sliders.items()}
        try:
            response = requests.post(API_URL, json=data, timeout=5)
            response.raise_for_status()
            result = response.json()
            severity = result.get("fire_severity", "Unknown")
            self.result_label.config(text=f"🔥 Predicted Fire Severity: {severity}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("API Error", f"Failed to get prediction: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FireSeveritySliderApp(root)
    root.mainloop()
