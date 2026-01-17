"""
Database Initialization Script
Run this script to create the database and tables
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import init_db

if __name__ == "__main__":
    print("🔧 Initializing database...")
    try:
        init_db()
        print("✅ Database initialized successfully!")
        print("📁 Database location: database/cassette_tracking.db")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)
