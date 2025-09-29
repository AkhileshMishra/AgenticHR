from celery import Celery
from kombu import Exchange, Queue

BROKER = "amqp://guest:guest@rabbitmq:5672//"

celery_app = Celery("employee-tasks", broker=BROKER, backend=None)
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

# Employee service queues
celery_app.conf.task_default_exchange = "employee"
celery_app.conf.task_queues = (
    Queue("employee.default", Exchange("employee", type="topic"), routing_key="employee.default", durable=True),
    Queue("employee.dlq", Exchange("employee.dlx", type="fanout"), durable=True),
)

@celery_app.task(bind=True, name="employee.sample_task")
def sample_task(self, message: str):
    return {"ok": True, "message": message}

@celery_app.task(bind=True, name="employee.send_welcome_email")
def send_welcome_email(self, employee_id: int, email: str):
    """Send a welcome email to a new employee."""
    return {"ok": True, "employee_id": employee_id, "email": email}

@celery_app.task(bind=True, name="employee.reindex_employee")
def reindex_employee(self, employee_id: int):
    """Reindex an employee in the search service."""
    return {"ok": True, "employee_id": employee_id}
