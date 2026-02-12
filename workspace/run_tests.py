#!/usr/bin/env python3
"""
Test runner for ML Trading Bot
Compatible with Windows encoding
"""

import sys
import subprocess
import os

def run_tests():
    """Run all unit tests"""
    print("=== Running ML Trading Bot Tests ===")
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Install dependencies if needed
    print("\n1. Checking dependencies...")
    try:
        import pytest
        print("   pytest: OK")
    except ImportError:
        print("   Installing pytest...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest"])
    
    # Run tests
    print("\n2. Running unit tests...")
    test_dir = "tests/unit"
    
    if not os.path.exists(test_dir):
        print(f"   ERROR: Test directory '{test_dir}' not found")
        return 1
    
    cmd = [sys.executable, "-m", "pytest", test_dir, "-v"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    print("\n3. Test Summary:")
    if result.returncode == 0:
        print("   ALL TESTS PASSED")
        return 0
    else:
        print("   SOME TESTS FAILED")
        return result.returncode

if __name__ == "__main__":
    sys.exit(run_tests())