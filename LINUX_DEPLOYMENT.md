# 🐧 Linux Deployment Guide - Cassette & RFID Tracking System

Complete guide for deploying the Cassette & RFID Tracking System on Linux servers (Ubuntu/Debian/CentOS/RHEL).

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Method 1: Development Deployment](#method-1-development-deployment)
3. [Method 2: Production Deployment with Systemd](#method-2-production-deployment-with-systemd)
4. [Method 3: Production with Nginx Reverse Proxy](#method-3-production-with-nginx-reverse-proxy)
5. [Method 4: Docker Deployment](#method-4-docker-deployment)
6. [Security Best Practices](#security-best-practices)
7. [Monitoring and Logs](#monitoring-and-logs)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+, Debian 10+, CentOS 8+, or RHEL 8+
- **RAM**: Minimum 512MB (1GB+ recommended)
- **Disk**: 1GB free space
- **Python**: 3.8 or higher
- **User**: Non-root user with sudo privileges

### Install Python and Dependencies

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

#### CentOS/RHEL
```bash
sudo yum update -y
sudo yum install -y python3 python3-pip git
```

### Verify Installation
```bash
python3 --version  # Should be 3.8+
pip3 --version
```

---

## Method 1: Development Deployment

**Best for**: Testing, development, local use

### Step 1: Upload Project to Linux Server

**Option A: Using Git**
```bash
cd /home/yourusername
git clone <your-repository-url>
cd Cassette_Tracking
```

**Option B: Using SCP (from Windows)**
```bash
# From Windows PowerShell
scp -r d:\PROJECT\HINDALCO\Cassette_Tracking username@server-ip:/home/username/
```

**Option C: Using SFTP**
```bash
# Use FileZilla, WinSCP, or similar tools
# Upload the entire Cassette_Tracking folder
```

### Step 2: Set Up Virtual Environment
```bash
cd /home/yourusername/Cassette_Tracking

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Initialize Database
```bash
python -c "from app.database import init_db; init_db()"
```

### Step 5: Run the Application
```bash
# Development mode (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8005

# Or use the Python module directly
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
```

### Step 6: Access the Application
- **Local**: http://localhost:8000
- **Remote**: http://server-ip:8000

### Step 7: Run in Background (Development)
```bash
# Using nohup
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &

# Check if running
ps aux | grep uvicorn

# Stop the application
pkill -f uvicorn
```

---

## Method 2: Production Deployment with Systemd

**Best for**: Production servers, automatic startup, process management

### Step 1: Complete Steps 1-4 from Method 1

### Step 2: Install Gunicorn
```bash
source venv/bin/activate
pip install gunicorn
```

### Step 3: Create Systemd Service File
```bash
sudo nano /etc/systemd/system/cassette-tracking.service
```

**Add the following content** (adjust paths to match your setup):

```ini
[Unit]
Description=Cassette & RFID Tracking System
After=network.target

[Service]
Type=notify
User=yourusername
Group=yourusername
WorkingDirectory=/home/yourusername/Cassette_Tracking
Environment="PATH=/home/yourusername/Cassette_Tracking/venv/bin"

# Production command with Gunicorn
ExecStart=/home/yourusername/Cassette_Tracking/venv/bin/gunicorn \
    app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/cassette-tracking/access.log \
    --error-logfile /var/log/cassette-tracking/error.log \
    --log-level info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 4: Create Log Directory
```bash
sudo mkdir -p /var/log/cassette-tracking
sudo chown yourusername:yourusername /var/log/cassette-tracking
```

### Step 5: Enable and Start Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable cassette-tracking

# Start service
sudo systemctl start cassette-tracking

# Check status
sudo systemctl status cassette-tracking
```

### Step 6: Manage the Service
```bash
# Start
sudo systemctl start cassette-tracking

# Stop
sudo systemctl stop cassette-tracking

# Restart
sudo systemctl restart cassette-tracking

# View logs
sudo journalctl -u cassette-tracking -f

# View last 100 lines
sudo journalctl -u cassette-tracking -n 100
```

---

## Method 3: Production with Nginx Reverse Proxy

**Best for**: Production with HTTPS, domain names, load balancing

### Step 1: Complete Method 2 (Systemd Setup)

### Step 2: Install Nginx
```bash
# Ubuntu/Debian
sudo apt install -y nginx

# CentOS/RHEL
sudo yum install -y nginx
```

### Step 3: Configure Nginx
```bash
sudo nano /etc/nginx/sites-available/cassette-tracking
```

**Add the following configuration**:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or server IP

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files (optional optimization)
    location /static {
        alias /home/yourusername/Cassette_Tracking/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Step 4: Enable Nginx Configuration
```bash
# Ubuntu/Debian
sudo ln -s /etc/nginx/sites-available/cassette-tracking /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 5: Configure Firewall
```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 'Nginx Full'
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### Step 6: Access Application
- **HTTP**: http://your-domain.com or http://server-ip

### Step 7: Add HTTPS with Let's Encrypt (Recommended)

```bash
# Install Certbot
# Ubuntu/Debian
sudo apt install -y certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

After SSL setup, access via: **https://your-domain.com**

---

## Method 4: Docker Deployment

**Best for**: Containerized environments, easy scaling, cloud deployments

### Step 1: Create Dockerfile
```bash
cd /home/yourusername/Cassette_Tracking
nano Dockerfile
```

**Dockerfile content**:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create database directory
RUN mkdir -p /app/database

# Initialize database
RUN python -c "from app.database import init_db; init_db()"

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 2: Create .dockerignore
```bash
nano .dockerignore
```

**Content**:
```
venv/
__pycache__/
*.pyc
*.pyo
*.db
.git/
.gitignore
*.md
```

### Step 3: Build Docker Image
```bash
docker build -t cassette-tracking:latest .
```

### Step 4: Run Docker Container
```bash
# Run container
docker run -d \
  --name cassette-tracking \
  -p 8000:8000 \
  -v $(pwd)/database:/app/database \
  --restart unless-stopped \
  cassette-tracking:latest

# Check logs
docker logs -f cassette-tracking

# Stop container
docker stop cassette-tracking

# Start container
docker start cassette-tracking
```

### Step 5: Docker Compose (Optional)
```bash
nano docker-compose.yml
```

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  cassette-tracking:
    build: .
    container_name: cassette-tracking
    ports:
      - "8000:8000"
    volumes:
      - ./database:/app/database
    restart: unless-stopped
    environment:
      - DEBUG=False
```

**Run with Docker Compose**:
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f
```

---

## Security Best Practices

### 1. Update config.py for Production
```python
# config.py
DEBUG = False  # Disable debug mode

ALLOWED_ORIGINS = [
    "https://your-domain.com",
    "http://your-domain.com"
]  # Specify exact origins, remove "*"
```

### 2. Set File Permissions
```bash
# Set proper ownership
sudo chown -R yourusername:yourusername /home/yourusername/Cassette_Tracking

# Restrict permissions
chmod 755 /home/yourusername/Cassette_Tracking
chmod 644 /home/yourusername/Cassette_Tracking/database/*.db
```

### 3. Use Environment Variables
```bash
# Create .env file
nano .env
```

**Content**:
```
DATABASE_URL=sqlite:///database/cassette_tracking.db
DEBUG=False
SECRET_KEY=your-secret-key-here
```

### 4. Regular Updates
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Update Python packages
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### 5. Backup Database
```bash
# Create backup script
nano /home/yourusername/backup.sh
```

**backup.sh**:
```bash
#!/bin/bash
BACKUP_DIR="/home/yourusername/backups"
DB_PATH="/home/yourusername/Cassette_Tracking/database/cassette_tracking.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp $DB_PATH $BACKUP_DIR/cassette_tracking_$DATE.db

# Keep only last 7 days of backups
find $BACKUP_DIR -name "cassette_tracking_*.db" -mtime +7 -delete
```

**Make executable and schedule**:
```bash
chmod +x /home/yourusername/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /home/yourusername/backup.sh
```

---

## Monitoring and Logs

### View Application Logs

**Systemd Service**:
```bash
# Real-time logs
sudo journalctl -u cassette-tracking -f

# Last 100 lines
sudo journalctl -u cassette-tracking -n 100

# Logs from today
sudo journalctl -u cassette-tracking --since today
```

**Gunicorn Logs**:
```bash
# Access logs
tail -f /var/log/cassette-tracking/access.log

# Error logs
tail -f /var/log/cassette-tracking/error.log
```

**Nginx Logs**:
```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

### Monitor System Resources
```bash
# CPU and Memory usage
htop

# Disk usage
df -h

# Check specific process
ps aux | grep uvicorn
```

---

## Troubleshooting

### Issue: Port 8000 already in use
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

### Issue: Permission denied
```bash
# Fix ownership
sudo chown -R $USER:$USER /home/yourusername/Cassette_Tracking

# Fix permissions
chmod -R 755 /home/yourusername/Cassette_Tracking
```

### Issue: Database locked
```bash
# Stop the service
sudo systemctl stop cassette-tracking

# Check for zombie processes
ps aux | grep uvicorn
sudo kill -9 <PID>

# Restart service
sudo systemctl start cassette-tracking
```

### Issue: Module not found
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Cannot connect from external network
```bash
# Check if service is listening on 0.0.0.0
sudo netstat -tlnp | grep 8000

# Check firewall
sudo ufw status  # Ubuntu/Debian
sudo firewall-cmd --list-all  # CentOS/RHEL

# Allow port 8000
sudo ufw allow 8000  # Ubuntu/Debian
sudo firewall-cmd --permanent --add-port=8000/tcp  # CentOS/RHEL
sudo firewall-cmd --reload
```

---

## Quick Reference Commands

### Service Management
```bash
# Start
sudo systemctl start cassette-tracking

# Stop
sudo systemctl stop cassette-tracking

# Restart
sudo systemctl restart cassette-tracking

# Status
sudo systemctl status cassette-tracking

# Enable on boot
sudo systemctl enable cassette-tracking
```

### Log Viewing
```bash
# Application logs
sudo journalctl -u cassette-tracking -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Database Backup
```bash
# Manual backup
cp database/cassette_tracking.db database/cassette_tracking_backup_$(date +%Y%m%d).db
```

---

## Production Checklist

Before going to production, ensure:

- [ ] `DEBUG = False` in config.py
- [ ] Specific CORS origins configured (no `*`)
- [ ] HTTPS enabled with SSL certificate
- [ ] Firewall configured properly
- [ ] Systemd service enabled for auto-start
- [ ] Database backups scheduled
- [ ] Log rotation configured
- [ ] Monitoring set up
- [ ] Strong file permissions set
- [ ] Regular security updates scheduled
- [ ] Application tested thoroughly

---

## Support

For issues or questions:
- Check logs: `sudo journalctl -u cassette-tracking -n 100`
- Review this guide
- Check main README.md
- Review TECHNICAL_DESIGN.md

---

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Platform**: Linux (Ubuntu/Debian/CentOS/RHEL)
