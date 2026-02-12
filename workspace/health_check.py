#!/usr/bin/env python3
"""
Health Check Script for ML Trading Bot System
Checks: Disk space, memory usage, data freshness, log files count
Outputs: JSON report with metrics and status
"""

import os
import sys
import json
import psutil
import datetime
from pathlib import Path
from typing import Dict, Any, List

class HealthChecker:
    def __init__(self):
        self.report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "system": {},
            "checks": {},
            "overall_status": "UNKNOWN",
            "alerts": []
        }
        
        # Define paths relative to project root
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data" / "raw"
        self.logs_dir = self.project_root / "logs"
        self.workspace_dir = self.project_root / "workspace"
        
    def check_disk_space(self) -> Dict[str, Any]:
        """Check disk usage for root partition"""
        try:
            disk_usage = psutil.disk_usage('/')
            result = {
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "percent_used": disk_usage.percent,
                "status": "HEALTHY" if disk_usage.percent < 80 else "WARNING" if disk_usage.percent < 90 else "CRITICAL"
            }
            
            if disk_usage.percent > 80:
                self.report["alerts"].append(f"Disk usage high: {disk_usage.percent}%")
            if disk_usage.percent > 90:
                self.report["alerts"].append(f"Disk usage critical: {disk_usage.percent}% - Immediate action required")
                
            return result
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """Check system memory usage"""
        try:
            memory = psutil.virtual_memory()
            result = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent_used": memory.percent,
                "status": "HEALTHY" if memory.percent < 85 else "WARNING" if memory.percent < 95 else "CRITICAL"
            }
            
            if memory.percent > 85:
                self.report["alerts"].append(f"Memory usage high: {memory.percent}%")
            if memory.percent > 95:
                self.report["alerts"].append(f"Memory usage critical: {memory.percent}% - Risk of OOM")
                
            return result
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}
    
    def check_data_freshness(self) -> Dict[str, Any]:
        """Check when data files were last modified"""
        try:
            if not self.data_dir.exists():
                return {"error": f"Data directory not found: {self.data_dir}", "status": "ERROR"}
            
            data_files = list(self.data_dir.glob("*.csv"))
            if not data_files:
                return {"file_count": 0, "status": "WARNING", "message": "No data files found"}
            
            # Get the most recent file
            latest_file = max(data_files, key=lambda f: f.stat().st_mtime)
            last_modified = datetime.datetime.fromtimestamp(latest_file.stat().st_mtime)
            hours_old = (datetime.datetime.now() - last_modified).total_seconds() / 3600
            
            result = {
                "file_count": len(data_files),
                "latest_file": latest_file.name,
                "last_modified": last_modified.isoformat(),
                "hours_old": round(hours_old, 2),
                "status": "HEALTHY" if hours_old < 24 else "WARNING" if hours_old < 48 else "CRITICAL"
            }
            
            if hours_old > 24:
                self.report["alerts"].append(f"Data stale: {latest_file.name} is {hours_old:.1f} hours old")
            if hours_old > 48:
                self.report["alerts"].append(f"Data very stale: {latest_file.name} is {hours_old:.1f} hours old - Update required")
                
            return result
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}
    
    def check_log_files(self) -> Dict[str, Any]:
        """Check log files count and sizes"""
        try:
            if not self.logs_dir.exists():
                return {"error": f"Logs directory not found: {self.logs_dir}", "status": "ERROR"}
            
            log_files = list(self.logs_dir.glob("*.log"))
            total_size_mb = sum(f.stat().st_size for f in log_files) / (1024 * 1024)
            
            # Check for large log files (>100MB)
            large_logs = [f.name for f in log_files if f.stat().st_size > 100 * 1024 * 1024]
            
            result = {
                "file_count": len(log_files),
                "total_size_mb": round(total_size_mb, 2),
                "large_files": large_logs,
                "large_file_count": len(large_logs),
                "status": "HEALTHY" if len(large_logs) == 0 else "WARNING"
            }
            
            if large_logs:
                self.report["alerts"].append(f"Large log files detected: {', '.join(large_logs)}")
            if total_size_mb > 1000:
                self.report["alerts"].append(f"Total log size large: {total_size_mb:.1f}MB - Consider cleanup")
                
            return result
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}
    
    def check_processes(self) -> Dict[str, Any]:
        """Check if key processes are running"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                try:
                    if 'python' in proc.info['name'].lower():
                        processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "status": proc.info['status']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                "python_processes": len(processes),
                "processes": processes[:10],  # Limit to first 10
                "status": "HEALTHY" if len(processes) > 0 else "WARNING"
            }
        except Exception as e:
            return {"error": str(e), "status": "ERROR"}
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and generate report"""
        
        # System info
        self.report["system"] = {
            "hostname": psutil.os.uname().nodename,
            "platform": sys.platform,
            "python_version": sys.version,
            "cpu_count": psutil.cpu_count(),
            "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
        
        # Run checks
        checks = {
            "disk_space": self.check_disk_space(),
            "memory_usage": self.check_memory_usage(),
            "data_freshness": self.check_data_freshness(),
            "log_files": self.check_log_files(),
            "processes": self.check_processes()
        }
        
        self.report["checks"] = checks
        
        # Determine overall status
        status_priority = {"CRITICAL": 3, "ERROR": 2, "WARNING": 1, "HEALTHY": 0}
        worst_status = "HEALTHY"
        
        for check_name, check_result in checks.items():
            status = check_result.get("status", "UNKNOWN")
            if status_priority.get(status, 0) > status_priority.get(worst_status, 0):
                worst_status = status
        
        self.report["overall_status"] = worst_status
        
        # Add summary metrics
        self.report["summary"] = {
            "total_checks": len(checks),
            "healthy_checks": sum(1 for c in checks.values() if c.get("status") == "HEALTHY"),
            "warning_checks": sum(1 for c in checks.values() if c.get("status") == "WARNING"),
            "critical_checks": sum(1 for c in checks.values() if c.get("status") == "CRITICAL"),
            "error_checks": sum(1 for c in checks.values() if c.get("status") == "ERROR"),
            "alert_count": len(self.report["alerts"])
        }
        
        return self.report
    
    def print_report(self):
        """Print formatted JSON report"""
        report = self.run_all_checks()
        print(json.dumps(report, indent=2, default=str))

def main():
    """Main entry point"""
    try:
        checker = HealthChecker()
        checker.print_report()
        
        # Exit with appropriate code
        if checker.report["overall_status"] == "CRITICAL":
            sys.exit(2)
        elif checker.report["overall_status"] == "ERROR":
            sys.exit(1)
        elif checker.report["overall_status"] == "WARNING":
            sys.exit(0)  # Warning is still OK for automation
        else:
            sys.exit(0)
            
    except Exception as e:
        error_report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "error": str(e),
            "status": "ERROR"
        }
        print(json.dumps(error_report, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()