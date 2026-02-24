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
RFID_HOST = os.getenv("RFID_HOST", "192.168.20.87")  # RFID device IP address
RFID_PORT = int(os.getenv("RFID_PORT", "2189"))      # RFID device TCP port
RFID_TIMEOUT = int(os.getenv("RFID_TIMEOUT", "5"))   # Connection timeout in seconds
RFID_SERVICE_ENABLED = os.getenv("RFID_SERVICE_ENABLED", "true").lower() == "true"  # Enable/disable background service
RFID_READ_INTERVAL = int(os.getenv("RFID_READ_INTERVAL", "5"))  # Background service read interval in seconds

# Modbus RTU Configuration (RS-485 Relay Board)
MODBUS_PORT = os.getenv("MODBUS_PORT", "/dev/ttyHS2")        # RS-485 serial port
MODBUS_BAUDRATE = int(os.getenv("MODBUS_BAUDRATE", "9600"))   # Baud rate
MODBUS_PARITY = os.getenv("MODBUS_PARITY", "N")              # N=None, E=Even, O=Odd
MODBUS_STOPBITS = int(os.getenv("MODBUS_STOPBITS", "1"))     # Stop bits
MODBUS_BYTESIZE = int(os.getenv("MODBUS_BYTESIZE", "8"))     # Data bits
MODBUS_SLAVE_ID = int(os.getenv("MODBUS_SLAVE_ID", "1"))     # Slave address (1-247, except 35, 42)
MODBUS_TIMEOUT = int(os.getenv("MODBUS_TIMEOUT", "1"))       # Timeout in seconds
MODBUS_RELAY_COUNT = 8                                        # Number of relay outputs to use (out of 10 available)

