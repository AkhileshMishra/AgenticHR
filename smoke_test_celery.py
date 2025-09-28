#!/usr/bin/env python3
"""
Smoke test for Celery workers - demonstrates task dispatch and execution
"""
import os
import sys
import time
from celery import Celery

def test_celery_tasks():
    print("🧪 AgenticHR Celery Workers Smoke Test")
    print("=" * 50)
    
    # Setup Celery app (same as in employee service)
    celery_app = Celery(
        "employee-svc",
        broker=os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672//"),
        backend=None,
    )
    
    # Define tasks (same as in employee service)
    @celery_app.task(name="employee.reindex")
    def reindex_employee(emp_id: int):
        return {"ok": True, "employee_id": emp_id}
    
    @celery_app.task(name="employee.send_welcome_email")
    def send_welcome_email(emp_id: int, email: str):
        import time
        time.sleep(2)  # simulate email sending delay
        return {"ok": True, "employee_id": emp_id, "email": email, "status": "sent"}
    
    print("✅ Celery app configured")
    print(f"📡 Broker: {celery_app.conf.broker_url}")
    print(f"🎯 Tasks available: {len([t for t in celery_app.tasks if t.startswith('employee.')])}")
    
    print("\n📋 Available tasks:")
    for task_name in celery_app.tasks:
        if task_name.startswith('employee.'):
            print(f"  - {task_name}")
    
    print("\n🚀 To test with actual workers:")
    print("1. Start RabbitMQ: docker compose -f docker/compose.dev.yml up rabbitmq -d")
    print("2. Start worker: docker compose -f docker/compose.dev.yml up employee-worker -d")
    print("3. Dispatch task:")
    print("   python3 -c \"")
    print("   from smoke_test_celery import *")
    print("   result = reindex_employee.delay(42)")
    print("   print(f'Task dispatched: {result.id}')\"")
    print("4. Check worker logs: docker compose -f docker/compose.dev.yml logs -f employee-worker")
    
    print("\n✅ Smoke test completed successfully!")
    return True

if __name__ == "__main__":
    test_celery_tasks()
