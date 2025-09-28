#!/usr/bin/env python3
"""
Celery smoke test - verify workers are running and can execute tasks
"""
import sys
import os
import time
from pathlib import Path

# Add service paths
sys.path.append(str(Path(__file__).parent.parent / "services" / "employee-svc"))
sys.path.append(str(Path(__file__).parent.parent / "services" / "auth-svc"))
sys.path.append(str(Path(__file__).parent.parent / "libs" / "py-hrms-auth" / "src"))

def test_employee_tasks():
    """Test employee service Celery tasks"""
    print("🧪 Testing employee service Celery tasks...")
    
    try:
        from app.main import celery_app, send_welcome_email, reindex_employee
        
        # Test welcome email task
        print("  📧 Testing welcome email task...")
        result = send_welcome_email.delay(123, "test@example.com")
        print(f"     Task ID: {result.id}")
        
        # Test reindex task
        print("  🔍 Testing reindex task...")
        result = reindex_employee.delay(123)
        print(f"     Task ID: {result.id}")
        
        print("  ✅ Employee tasks dispatched successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Employee tasks failed: {e}")
        return False

def test_auth_tasks():
    """Test auth service Celery tasks"""
    print("🧪 Testing auth service Celery tasks...")
    
    try:
        from app.main import celery_app, send_login_notification, cleanup_expired_sessions
        
        # Test login notification task
        print("  🔔 Testing login notification task...")
        result = send_login_notification.delay("user123", "192.168.1.1")
        print(f"     Task ID: {result.id}")
        
        # Test session cleanup task
        print("  🧹 Testing session cleanup task...")
        result = cleanup_expired_sessions.delay()
        print(f"     Task ID: {result.id}")
        
        print("  ✅ Auth tasks dispatched successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Auth tasks failed: {e}")
        return False

def check_celery_workers():
    """Check if Celery workers are running"""
    print("🔍 Checking Celery worker status...")
    
    try:
        # Import one of the Celery apps
        sys.path.append(str(Path(__file__).parent.parent / "services" / "employee-svc"))
        from app.main import celery_app
        
        # Get active workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            print("  ✅ Active workers found:")
            for worker, tasks in active_workers.items():
                print(f"     {worker}: {len(tasks)} active tasks")
            return True
        else:
            print("  ⚠️  No active workers found")
            return False
            
    except Exception as e:
        print(f"  ❌ Failed to check workers: {e}")
        return False

def main():
    """Run Celery smoke tests"""
    print("🚀 Starting Celery smoke tests...\n")
    
    # Check workers
    workers_ok = check_celery_workers()
    print()
    
    # Test tasks
    employee_ok = test_employee_tasks()
    print()
    
    auth_ok = test_auth_tasks()
    print()
    
    # Summary
    print("📊 Test Results:")
    print(f"  Workers: {'✅' if workers_ok else '❌'}")
    print(f"  Employee tasks: {'✅' if employee_ok else '❌'}")
    print(f"  Auth tasks: {'✅' if auth_ok else '❌'}")
    
    if all([workers_ok, employee_ok, auth_ok]):
        print("\n🎉 All Celery tests passed!")
        return 0
    else:
        print("\n💥 Some Celery tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
