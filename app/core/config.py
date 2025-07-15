import os
from dotenv import load_dotenv

load_dotenv()

# Path settings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_FILE = os.path.join(BASE_DIR, 'firebot.db')
MODELS_DIR = os.path.join(BASE_DIR, 'models')


# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Security settings

API_KEY = os.getenv("API_KEY", "your_secret_api_key")

# Robot settings
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "True").lower() in ("true", "1", "t")
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))