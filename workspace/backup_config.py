import os
import json
import hashlib
from datetime import datetime, timedelta
import subprocess

class BackupConfig:
    def __init__(self):
        self.backup_dir = "data/backups/"
        self.db_backup_interval = 6  # hours
        self.config_backup_on_deploy = True
        self.retention_days = 30
        self.checksum_algorithm = "sha256"
        
    def get_backup_status(self):
        """Check latest backup status"""
        if not os.path.exists(self.backup_dir):
            return {"status": "error", "message": "Backup directory not found"}
            
        backups = sorted(os.listdir(self.backup_dir))
        if not backups:
            return {"status": "error", "message": "No backups found"}
            
        latest = backups[-1]
        backup_path = os.path.join(self.backup_dir, latest)
        
        return {
            "status": "healthy",
            "latest_backup": latest,
            "size_mb": os.path.getsize(backup_path) / (1024*1024),
            "modified": datetime.fromtimestamp(os.path.getmtime(backup_path)).isoformat()
        }
        
    def verify_backup_integrity(self, backup_file):
        """Verify backup checksum"""
        filepath = os.path.join(self.backup_dir, backup_file)
        if not os.path.exists(filepath):
            return False
            
        # Calculate checksum
        with open(filepath, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            
        # Check against stored checksum
        checksum_file = filepath + ".checksum"
        if os.path.exists(checksum_file):
            with open(checksum_file, 'r') as f:
                stored_hash = f.read().strip()
            return file_hash == stored_hash
        return False

# Singleton instance
backup_config = BackupConfig()