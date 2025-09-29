from celery import Celery
from kombu import Exchange, Queue

BROKER = "amqp://guest:guest@rabbitmq:5672//"

celery_app = Celery("leave-tasks", broker=BROKER, backend=None)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=120,
    task_soft_time_limit=110,
    broker_heartbeat=30,
    broker_connection_retry_on_startup=True,
)

# Leave service queues
celery_app.conf.task_default_exchange = "leave"
celery_app.conf.task_queues = (
    Queue("leave.default", Exchange("leave", type="topic"), routing_key="leave.default", durable=True),
    Queue("leave.dlq", Exchange("leave.dlx", type="fanout"), durable=True),
)

@celery_app.task(bind=True, name="leave.sample_task")
def sample_task(self, message: str):
    return {"ok": True, "message": message}

@celery_app.task(bind=True, name="leave.send_approval_notification")
def send_approval_notification(self, leave_request_id: int, status: str):
    """Send leave approval notification."""
    return {"ok": True, "leave_request_id": leave_request_id, "status": status}

@celery_app.task(bind=True, name="leave.update_balance")
def update_balance(self, employee_id: int, leave_type: str, days: float):
    """Update leave balance for an employee."""
    return {"ok": True, "employee_id": employee_id, "leave_type": leave_type, "days": days}
