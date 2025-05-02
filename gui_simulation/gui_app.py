import tkinter as tk
from tkinter import messagebox
import requests

API_URL = "http://localhost:8000/predict"

class FireSeverityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fire Severity Prediction")

        # Create input fields
        self.create_input_field("Temperature (°C):", 0)
        self.create_input_field("Smoke Density:", 1)
        self.create_input_field("Gas Level:", 2)
        self.create_input_field("Humidity (%):", 3)

        # Predict button
        self.predict_button = tk.Button(root, text="Predict Fire Severity", command=self.predict)
        self.predict_button.grid(row=4, column=0, columnspan=2, pady=10)

        # Result label
        self.result_label = tk.Label(root, text="", font=("Arial", 14))
        self.result_label.grid(row=5, column=0, columnspan=2, pady=10)

        # Add Clear button
        self.clear_button = tk.Button(root, text="Clear Inputs", command=self.clear_inputs)
        self.clear_button.grid(row=6, column=0, columnspan=2, pady=5)

    def create_input_field(self, label_text, row):
        label = tk.Label(self.root, text=label_text)
        label.grid(row=row, column=0, padx=10, pady=5, sticky="e")
        entry = tk.Entry(self.root)
        entry.grid(row=row, column=1, padx=10, pady=5)
        setattr(self, f"entry_{row}", entry)

    def clear_inputs(self):
        for i in range(4):
            entry = getattr(self, f"entry_{i}")
            entry.delete(0, tk.END)
        self.result_label.config(text="")

    def predict(self):
        try:
            data = {
                "temperature": float(self.entry_0.get()),
                "smoke_density": float(self.entry_1.get()),
                "gas_level": float(self.entry_2.get()),
                "humidity": float(self.entry_3.get())
            }
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numeric values.")
            return

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
    app = FireSeverityApp(root)
    root.mainloop()
