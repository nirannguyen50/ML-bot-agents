#!/usr/bin/env python3
"""
Simple Health Check Script (no external dependencies)
Checks: disk space, data freshness, log files count
"""

import os
import json
import datetime
from pathlib import Path

def check_disk_space_simple():
    """Simple disk space check using os.statvfs"""
    try:
        stat = os.statvfs('/')
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used = total - free
        percent = (used / total) * 100 if total > 0 else 0
        
        return {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "percent_used": round(percent, 2),
            "status": "CRITICAL" if percent > 90 else 
                     "WARNING" if percent > 80 else 
                     "HEALTHY"
        }
    except Exception as e:
        return {"error": str(e), "status": "ERROR"}

def check_data_freshness_simple(data_dir):
    """Check data file freshness"""
    try:
        data_path = Path(data_dir)
        if not data_path.exists():
            return {
                "data_dir_exists": False,
                "file_count": 0,
                "status": "WARNING"
            }
        
        csv_files = list(data_path.glob("*.csv"))
        if not csv_files:
            return {
                "data_dir_exists": True,
                "file_count": 0,
                "status": "WARNING"
            }
        
        # Get latest file
        latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
        latest_time = datetime.datetime.fromtimestamp(latest_file.stat().st_mtime)
        hours_old = (datetime.datetime.now() - latest_time).total_seconds() / 3600
        
        return {
            "data_dir_exists": True,
            "latest_file": latest_file.name,
            "latest_timestamp": latest_time.isoformat(),
            "hours_since_update": round(hours_old, 2),
            "file_count": len(csv_files),
            "status": "CRITICAL" if hours_old > 48 else 
                     "WARNING" if hours_old > 24 else 
                     "HEALTHY"
        }
    except Exception as e:
        return {"error": str(e), "status": "ERROR"}

def check_log_files_simple(logs_dir):
    """Check log files"""
    try:
        logs_path = Path(logs_dir)
        if not logs_path.exists():
            return {
                "logs_dir_exists": False,
                "file_count": 0,
                "status": "WARNING"
            }
        
        log_files = list(logs_path.glob("*.log")) + list(logs_path.glob("*.txt"))
        total_size = sum(f.stat().st_size for f in log_files)
        
        return {
            "logs_dir_exists": True,
            "file_count": len(log_files),
            "total_size_mb": round(total_size / (1024**2), 2),
            "status": "CRITICAL" if total_size > 500 * 1024**2 else 
                     "WARNING" if total_size > 100 * 1024**2 else 
                     "HEALTHY"
        }
    except Exception as e:
        return {"error": str(e), "status": "ERROR"}

def main():
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data" / "raw"
    logs_dir = base_dir / "logs"
    
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "checks": {
            "disk_space": check_disk_space_simple(),
            "data_freshness": check_data_freshness_simple(data_dir),
            "log_files": check_log_files_simple(logs_dir)
        }
    }
    
    # Determine overall status
    statuses = [check["status"] for check in report["checks"].values() 
                if "status" in check]
    
    if "CRITICAL" in statuses:
        report["overall_status"] = "CRITICAL"
    elif "WARNING" in statuses:
        report["overall_status"] = "WARNING"
    elif "ERROR" in statuses:
        report["overall_status"] = "ERROR"
    else:
        report["overall_status"] = "HEALTHY"
    
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())