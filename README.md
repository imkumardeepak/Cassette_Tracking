# 📦 Cassette Tracking System (CTS)

A comprehensive **Cassette & RFID Tracking System** built with **FastAPI** backend and a modern **Bootstrap 5** web frontend. The system enables real-time tracking of cassettes using RFID technology with GPIO hardware integration for industrial automation.

![Version](https://img.shields.io/badge/Version-2.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Table of Contents

- [🎯 Overview](#-overview)
- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [📁 Project Structure](#-project-structure)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Configuration](#️-configuration)
- [📚 API Documentation](#-api-documentation)
- [🔌 Hardware Integration](#-hardware-integration)
- [🌐 WebSocket Events](#-websocket-events)
- [📖 Deployment](#-deployment)
- [🐛 Troubleshooting](#-troubleshooting)
- [📄 License](#-license)

---

## 🎯 Overview

The **Cassette Tracking System** is designed for industrial environments where tracking cassettes with RFID technology is essential. It provides:

- **RFID Tag Management**: Read, assign, and track RFID tags to cassettes
- **Real-time Monitoring**: WebSocket-based live updates on RFID scans
- **GPIO Control**: Hardware output control for industrial automation (Cygnus Board)
- **Transaction Logging**: Complete audit trail of all RFID events
- **Web Dashboard**: Modern, responsive UI for management and monitoring

### Use Cases
- Manufacturing cassette/pallet tracking
- Warehouse inventory management
- Industrial automation with RFID gates
- Asset tracking and monitoring

---

## ✨ Features

### 🏷️ Cassette Master Management
- Create, read, update, and delete cassette records
- Assign RFID tags to cassettes
- Configure GPIO output per cassette
- Search and filter cassettes

### 📡 RFID Integration
- Real-time RFID tag reading via TCP connection
- Background RFID scanning service
- Automatic RFID-to-Cassette mapping
- RFID validation (H/E prefix with hex format)

### ⚡ GPIO Control (Cygnus Board)
- 4 Digital Outputs (DO0-DO3)
- Automatic output triggering on RFID scan
- Manual output control via API
- Simulation mode for testing

### 📊 Dashboard & Monitoring
- Real-time statistics
- Recent transaction history
- WebSocket notifications
- System health status

### 📜 Transaction Logging
- Complete RFID scan history
- Event types: scan, assign, unassign
- Status tracking: success, error, pending
- Filterable transaction logs

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Cassette Tracking System                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐ │
│  │   Frontend   │────▶│   FastAPI    │────▶│     SQLite Database     │ │
│  │  (Bootstrap) │     │   Backend    │     │  (cassette_tracking.db) │ │
│  └──────────────┘     └──────────────┘     └──────────────────────────┘ │
│         │                    │                                          │
│         │                    │                                          │
│         ▼                    ▼                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐ │
│  │  WebSocket   │◀────│ RFID Service │────▶│    RFID Reader Device   │ │
│  │  Manager     │     │ (Background) │     │    (TCP Connection)     │ │
│  └──────────────┘     └──────────────┘     └──────────────────────────┘ │
│         │                    │                                          │
│         │                    ▼                                          │
│         │             ┌──────────────┐     ┌──────────────────────────┐ │
│         └────────────▶│    GPIO      │────▶│   Cygnus Board (GPIO)   │ │
│                       │  Controller  │     │   DO0, DO1, DO2, DO3    │ │
│                       └──────────────┘     └──────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend Framework** | FastAPI 0.100+ |
| **Database** | SQLite with SQLAlchemy ORM |
| **Validation** | Pydantic 2.0+ |
| **ASGI Server** | Uvicorn / Gunicorn |
| **Frontend** | HTML5, Bootstrap 5, Vanilla JS |
| **Real-time** | WebSocket |

---

## 📁 Project Structure

```
Cassette_Tracking/
├── 📂 app/                         # Main application package
│   ├── 📂 api/                     # API route handlers
│   │   ├── __init__.py
│   │   └── cassette.py             # Cassette CRUD & RFID endpoints
│   │
│   ├── __init__.py
│   ├── crud.py                     # Database CRUD operations
│   ├── database.py                 # Database connection & session
│   ├── gpio_controller.py          # GPIO hardware control (Cygnus Board)
│   ├── main.py                     # FastAPI application entry point
│   ├── models.py                   # SQLAlchemy ORM models
│   ├── rfid_reader.py              # RFID device TCP communication
│   ├── rfid_service.py             # Background RFID scanning service
│   ├── schemas.py                  # Pydantic request/response schemas
│   └── websocket_manager.py        # WebSocket connection management
│
├── 📂 database/                    # SQLite database storage
│   └── cassette_tracking.db        # Database file (auto-created)
│
├── 📂 scripts/                     # Utility scripts
│   ├── __init__.py
│   └── init_db.py                  # Database initialization script
│
├── 📂 static/                      # Frontend static assets
│   ├── 📂 css/
│   │   ├── style.css               # Custom styles
│   │   └── 📂 vendor/              # Bootstrap CSS
│   ├── 📂 js/
│   │   ├── api.js                  # API client module
│   │   ├── app.js                  # Main application logic
│   │   ├── websocket.js            # WebSocket client
│   │   └── 📂 vendor/              # Bootstrap JS
│   ├── 📂 fonts/                   # Custom fonts
│   └── index.html                  # Main HTML entry point
│
├── config.py                       # Application configuration
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── LINUX_DEPLOYMENT.md             # Linux deployment guide
└── .gitignore                      # Git ignore rules
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** installed
- **pip** package manager
- Optional: RFID reader device for hardware integration

### 1. Clone/Download the Project

```bash
cd d:\PROJECT\HINDALCO\Cassette_Tracking
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database

```bash
python -c "from app.database import init_db; init_db()"
```

### 5. Run the Application

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8005

# Or run directly
python -m app.main
```

### 6. Access the Application

| Resource | URL |
|----------|-----|
| **Web Dashboard** | http://localhost:8005 |
| **Swagger UI** | http://localhost:8005/api/docs |
| **ReDoc** | http://localhost:8005/api/redoc |
| **Health Check** | http://localhost:8005/health |

---

## ⚙️ Configuration

Edit `config.py` to customize the application:

```python
# config.py

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Database Configuration
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_DIR}/cassette_tracking.db"

# Server Configuration
HOST = "0.0.0.0"
PORT = 8005
DEBUG = True

# Pagination
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# CORS Configuration
ALLOWED_ORIGINS = [
    "http://localhost:8005",
    "http://127.0.0.1:8005",
    "*"  # Allow all in development
]

# RFID Device Configuration
RFID_HOST = os.getenv("RFID_HOST", "192.168.1.100")       # RFID reader IP
RFID_PORT = int(os.getenv("RFID_PORT", "8080"))           # RFID reader port
RFID_TIMEOUT = int(os.getenv("RFID_TIMEOUT", "5"))        # Connection timeout
RFID_SERVICE_ENABLED = os.getenv("RFID_SERVICE_ENABLED", "false").lower() == "true"
RFID_READ_INTERVAL = int(os.getenv("RFID_READ_INTERVAL", "5"))  # Scan interval (seconds)
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RFID_HOST` | RFID reader IP address | `192.168.1.100` |
| `RFID_PORT` | RFID reader TCP port | `8080` |
| `RFID_TIMEOUT` | Connection timeout (seconds) | `5` |
| `RFID_SERVICE_ENABLED` | Enable background RFID scanning | `false` |
| `RFID_READ_INTERVAL` | Scan interval (seconds) | `5` |

---

## 📚 API Documentation

### Base URL
```
http://localhost:8005/api
```

### Cassette Master Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/cassettes` | Get all cassettes (paginated) |
| `GET` | `/api/cassettes/{id}` | Get cassette by ID |
| `POST` | `/api/cassettes` | Create new cassette |
| `PUT` | `/api/cassettes/{id}` | Update cassette |
| `DELETE` | `/api/cassettes/{id}` | Delete cassette |
| `GET` | `/api/cassettes/search/` | Search cassettes |

### RFID Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/cassettes/read-rfid` | Read RFID from device |
| `POST` | `/api/cassettes/{id}/assign-rfid` | Read and assign RFID to cassette |
| `GET` | `/api/rfid/status` | Get RFID service status |

### Transaction Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/transactions` | Get all transactions (paginated) |
| `GET` | `/api/transactions/recent` | Get recent transactions |
| `GET` | `/api/transactions/rfid/{rfid_number}` | Get transactions by RFID |

### GPIO Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/gpio/status` | Get GPIO controller status |
| `POST` | `/api/gpio/output/{output_name}` | Set GPIO output (0 or 1) |
| `POST` | `/api/gpio/reset` | Reset all outputs to LOW |
| `POST` | `/api/gpio/mapping` | Configure RFID-GPIO mapping |

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/statistics` | System statistics |

### Example: Create Cassette

```bash
curl -X POST "http://localhost:8005/api/cassettes" \
  -H "Content-Type: application/json" \
  -d '{
    "cassette_code": "CASS-001",
    "desc": "Production Line A Cassette",
    "gpio_output": "DO0"
  }'
```

### Example: Assign RFID

```bash
curl -X POST "http://localhost:8005/api/cassettes/1/assign-rfid"
```

---

## 🔌 Hardware Integration

### RFID Reader

The system communicates with RFID readers via **TCP socket connection**:

- **Protocol**: TCP (not HTTP)
- **Command**: `READ\r\n`
- **Response Format**: `H30395DFA81582E424BD7BB45` (H/E prefix + hex)

**Supported RFID Format:**
- Must start with `H` or `E`
- Followed by hexadecimal characters (0-9, A-F)
- Example: `HE2007B037AB374B16D7BE5D2`

### GPIO Controller (Cygnus Board)

The system controls digital outputs on the Cygnus industrial board:

| Output | GPIO Pin | Linux GPIO Number |
|--------|----------|-------------------|
| `DO0` | GPIO 18 | 403 (385 + 18) |
| `DO1` | GPIO 19 | 404 (385 + 19) |
| `DO2` | PM_GPIO 4 | 378 (374 + 4) |
| `DO3` | PM_GPIO 8 | 382 (374 + 8) |

**GPIO Control Flow:**
1. RFID tag scanned
2. System looks up RFID → Cassette mapping
3. If cassette has `gpio_output` configured, trigger that output HIGH
4. Send WebSocket notification

**Simulation Mode:**
When running on Windows or systems without `/sys/class/gpio`, the GPIO controller automatically enters simulation mode and logs output state changes.

---

## 🌐 WebSocket Events

Connect to WebSocket for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8005/ws/rfid');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Event:', data);
};
```

### Event Types

| Event Type | Description | Payload |
|------------|-------------|---------|
| `connection` | Initial connection | `{message, timestamp}` |
| `rfid_scan` | RFID tag scanned | `{rfid_number, cassette_code, status, message, timestamp}` |
| `rfid_assign` | RFID assigned to cassette | `{rfid_number, cassette_code, cassette_id, status, timestamp}` |
| `notification` | General notification | `{notification_type, title, message, timestamp}` |
| `pong` | Keep-alive response | `{type: "pong", message}` |

---

## 📖 Deployment

### Development (Windows)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
```

### Production (Linux with Gunicorn)

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8005
```

### Production with Systemd

See [LINUX_DEPLOYMENT.md](LINUX_DEPLOYMENT.md) for complete Linux deployment instructions including:

- Systemd service configuration
- Nginx reverse proxy setup
- SSL/HTTPS with Let's Encrypt
- Docker deployment
- Security best practices

---

## 🗃️ Database Schema

### CassetteMaster Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment primary key |
| `cassette_code` | VARCHAR(100) | Unique cassette identifier |
| `desc` | VARCHAR(200) | Cassette description |
| `rfid_number` | VARCHAR(100) | Assigned RFID tag (nullable) |
| `gpio_output` | VARCHAR(10) | GPIO output (DO0-DO3, nullable) |
| `created_at` | DATETIME | Creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |

### RFIDTransaction Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-increment primary key |
| `rfid_number` | VARCHAR(100) | RFID tag number |
| `cassette_id` | INTEGER | Linked cassette ID (nullable) |
| `cassette_code` | VARCHAR(100) | Linked cassette code (nullable) |
| `event_type` | VARCHAR(50) | Event: scan, assign, unassign |
| `status` | VARCHAR(50) | Status: success, error, pending |
| `message` | VARCHAR(500) | Event message |
| `extra_data` | VARCHAR(1000) | JSON extra data |
| `created_at` | DATETIME | Event timestamp |

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :8005
taskkill /PID <PID> /F

# Linux
lsof -i :8005
kill -9 <PID>
```

### Database Locked

```bash
# Stop the server and restart
# The SQLite database doesn't support concurrent writes
```

### RFID Connection Failed

1. Verify RFID reader IP and port in `config.py`
2. Test connectivity: `ping <RFID_HOST>`
3. Check if RFID reader is powered on
4. Verify network firewall allows connection

### Module Not Found

```bash
# Ensure virtual environment is activated
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux

# Reinstall dependencies
pip install -r requirements.txt
```

### GPIO Not Working

- System runs in simulation mode on Windows
- On Linux, ensure `/sys/class/gpio` exists
- Verify user has GPIO access permissions
- Check Cygnus board is properly connected

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | ≥0.100.0 | Web framework |
| `uvicorn[standard]` | ≥0.23.0 | ASGI server |
| `sqlalchemy` | ≥2.0.0 | ORM |
| `pydantic` | ≥2.0.0 | Data validation |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 📞 Support

For issues or questions:
- Review this documentation
- Check [LINUX_DEPLOYMENT.md](LINUX_DEPLOYMENT.md) for deployment issues
- Access API docs at `/api/docs`
- Check application logs

---

**Version**: 2.0.0  
**Last Updated**: January 2026  
**Developed for**: Hindalco Industries
