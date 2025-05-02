import time
import random
import json
import requests

def generate_sensor_data():
    return {
        "temperature": round(random.uniform(20, 80), 2),
        "smoke_density": round(random.uniform(0, 200), 2),
        "gas_level": round(random.uniform(0, 500), 2),
        "humidity": round(random.uniform(10, 90), 2)
    }

def send_data_to_api(api_url):
    while True:
        data = generate_sensor_data()
        print(f"Sending data: {data}")
        try:
            response = requests.post(api_url, json=data)
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error sending data: {e}")
        time.sleep(5)  # send data every 5 seconds

if __name__ == "__main__":
    api_url = "http://localhost:8000/predict"
    send_data_to_api(api_url)
