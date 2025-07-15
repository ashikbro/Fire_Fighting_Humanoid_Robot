import requests
import json
import time

BASE_URL = "http://localhost:8081/api/v1"

def test_api():
    session = requests.Session()
    
    # 1. Get initial status
    print("\nGetting initial status...")
    try:
        status_response = session.get(f"{BASE_URL}/status")
        status_response.raise_for_status()
        print(f"Status: {status_response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to get status: {e}")

    # 3. Send movement commands
    commands = ["forward", "left", "right", "backward"]
    for command in commands:
        print(f"\nSending command: {command}")
        try:
            command_response = session.post(
                f"{BASE_URL}/move",
                json={"command": command}
            )
            command_response.raise_for_status()
            print(f"Command '{command}' successful.")
            time.sleep(1)
        except requests.exceptions.RequestException as e:
            print(f"Command '{command}' failed: {e}")

    # 4. Test auto-patrol
    print("\nTesting auto-patrol...")
    try:
        # Start patrol
        print("Starting auto-patrol...")
        start_patrol_response = session.post(f"{BASE_URL}/move", json={"command": "start_auto_patrol"})
        start_patrol_response.raise_for_status()
        print("Auto-patrol started.")
        time.sleep(2)

        # Stop patrol
        print("Stopping auto-patrol...")
        stop_patrol_response = session.post(f"{BASE_URL}/move", json={"command": "stop_auto_patrol"})
        stop_patrol_response.raise_for_status()
        print("Auto-patrol stopped.")
    except requests.exceptions.RequestException as e:
        print(f"Auto-patrol test failed: {e}")

    print("\nAPI simulation test completed.")

if __name__ == "__main__":
    test_api()