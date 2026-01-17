import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Database
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_DIR}/cassette_tracking.db"

# Server
HOST = "0.0.0.0"
PORT = 8005
DEBUG = True

# Pagination
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# CORS
ALLOWED_ORIGINS = [
    "http://localhost:8005",
    "http://127.0.0.1:8005",
    "*"  # Allow all in development
]

# RFID Device Configuration
RFID_HOST = os.getenv("RFID_HOST", "192.168.1.100")  # RFID device IP address
RFID_PORT = int(os.getenv("RFID_PORT", "8080"))      # RFID device TCP port
RFID_TIMEOUT = int(os.getenv("RFID_TIMEOUT", "5"))   # Connection timeout in seconds
RFID_SERVICE_ENABLED = os.getenv("RFID_SERVICE_ENABLED", "false").lower() == "true"  # Enable/disable background service
RFID_READ_INTERVAL = int(os.getenv("RFID_READ_INTERVAL", "5"))  # Background service read interval in seconds

