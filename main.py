import threading
import subprocess
import time
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def run_subprocess(command, name):
    try:
        logging.info(f"Starting {name} subprocess: {' '.join(command)}")
        process = subprocess.Popen(command)
        return process
    except Exception as e:
        logging.error(f"Failed to start {name} subprocess: {e}")
        return None

def run_api():
    # Run FastAPI server
    return run_subprocess([sys.executable, "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"], "API")

def run_gui():
    # Run GUI application
    try:
        logging.info("Starting GUI application")
        subprocess.run([sys.executable, "gui_simulation/gui_app.py"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"GUI application exited with error: {e}")
    except Exception as e:
        logging.error(f"Failed to start GUI application: {e}")

def run_gui_visuals():
    # Run GUI for model comparison visuals
    return run_subprocess([sys.executable, "gui_simulation/gui_with_visuals.py"], "GUI Visuals")

def run_vision_detection():
    # Run vision fire detection module
    return run_subprocess([sys.executable, "vision_fire_detection/fire_detection.py"], "Vision Detection")

def main():
    # Start API server in a separate thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()

    # Start vision detection in a separate thread
    vision_thread = threading.Thread(target=run_vision_detection, daemon=True)
    vision_thread.start()

    # Wait a bit for API and vision detection to start
    time.sleep(5)

    # Start GUI application (blocking)
    run_gui()

    # Start GUI visuals in a separate thread
    visuals_thread = threading.Thread(target=run_gui_visuals, daemon=True)
    visuals_thread.start()

if __name__ == "__main__":
    main()
