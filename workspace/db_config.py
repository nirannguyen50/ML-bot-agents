import sqlite3
import json
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="data/trading.db"):
        self.db_path = db_path
        self.backup_path = "data/backups/"
        self.ensure_directories()
        self.init_database()
        
    def ensure_directories(self):
        """Create necessary directories"""
        os.makedirs("data/", exist_ok=True)
        os.makedirs(self.backup_path, exist_ok=True)
        
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trading positions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            quantity REAL NOT NULL,
            entry_price REAL NOT NULL,
            entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'open'
        )
        ''')
        
        # Market data table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL
        )
        ''')
        
        # System metrics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            latency_ms REAL,
            active_connections INTEGER
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def create_backup(self):
        """Create database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"trading_backup_{timestamp}.db"
        backup_full_path = os.path.join(self.backup_path, backup_file)
        
        # Copy database
        import shutil
        shutil.copy2(self.db_path, backup_full_path)
        
        # Create checksum
        import hashlib
        with open(backup_full_path, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
            
        with open(backup_full_path + ".checksum", 'w') as f:
            f.write(checksum)
            
        return {
            "backup_file": backup_file,
            "size_mb": os.path.getsize(backup_full_path) / (1024*1024),
            "checksum": checksum,
            "timestamp": timestamp
        }
        
    def simulate_corruption(self):
        """Simulate data corruption for testing"""
        with open(self.db_path, 'rb+') as f:
            f.seek(100)  # Offset 100 bytes
            f.write(b'CORRUPTED_DATA_' * 10)
        return True

# Global instance
db_manager = DatabaseManager()