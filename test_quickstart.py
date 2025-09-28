#!/usr/bin/env python3
"""Quick Start validation script for AgenticHR."""

import subprocess
import time
import requests
import sys
import os

def run_command(cmd, timeout=30):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"

def test_service_health(port, service_name):
    """Test if a service health endpoint is responding."""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {service_name} health check passed: {data}")
            return True
        else:
            print(f"❌ {service_name} health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {service_name} health check failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Testing AgenticHR Quick Start Process")
    print("=" * 50)
    
    # Test 1: Check if Poetry is available
    print("\n1. Testing Poetry availability...")
    success, stdout, stderr = run_command("poetry --version")
    if success:
        print(f"✅ Poetry is available: {stdout.strip()}")
    else:
        print(f"❌ Poetry not available: {stderr}")
        return False
    
    # Test 2: Check if dependencies are installed
    print("\n2. Testing Python dependencies...")
    success, stdout, stderr = run_command("poetry run python -c 'import fastapi, pydantic, uvicorn; print(\"Dependencies OK\")'")
    if success:
        print("✅ Python dependencies are installed")
    else:
        print(f"❌ Python dependencies missing: {stderr}")
        return False
    
    # Test 3: Test auth library import
    print("\n3. Testing auth library...")
    os.environ['PYTHONPATH'] = 'libs/py-hrms-auth/src'
    success, stdout, stderr = run_command("poetry run python -c 'from py_hrms_auth import AuthContext; print(\"Auth library OK\")'")
    if success:
        print("✅ Auth library imports successfully")
    else:
        print(f"❌ Auth library import failed: {stderr}")
        return False
    
    # Test 4: Test service compilation
    print("\n4. Testing service compilation...")
    success, stdout, stderr = run_command("python3 -m py_compile services/auth-svc/app/main.py")
    if success:
        print("✅ Auth service compiles successfully")
    else:
        print(f"❌ Auth service compilation failed: {stderr}")
        return False
    
    success, stdout, stderr = run_command("python3 -m py_compile services/employee-svc/app/main.py")
    if success:
        print("✅ Employee service compiles successfully")
    else:
        print(f"❌ Employee service compilation failed: {stderr}")
        return False
    
    print("\n🎉 All Quick Start validation tests passed!")
    print("\nNext steps:")
    print("- Run 'make dev.up' to start the full development environment")
    print("- Services will be available at:")
    print("  - Auth Service: http://localhost:9001")
    print("  - Employee Service: http://localhost:9002")
    print("  - Kong Gateway: http://localhost:8000")
    print("  - Keycloak: http://localhost:8080")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
