from celery import Celery
from kombu import Exchange, Queue

BROKER = "amqp://guest:guest@rabbitmq:5672//"

celery_app = Celery("attendance-tasks", broker=BROKER, backend=None)
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

# Attendance service queues
celery_app.conf.task_default_exchange = "attendance"
celery_app.conf.task_queues = (
    Queue("attendance.default", Exchange("attendance", type="topic"), routing_key="attendance.default", durable=True),
    Queue("attendance.dlq", Exchange("attendance.dlx", type="fanout"), durable=True),
)

@celery_app.task(bind=True, name="attendance.sample_task")
def sample_task(self, message: str):
    return {"ok": True, "message": message}

@celery_app.task(bind=True, name="attendance.process_timesheet")
def process_timesheet(self, employee_id: int, date: str):
    """Process timesheet for an employee."""
    return {"ok": True, "employee_id": employee_id, "date": date}

@celery_app.task(bind=True, name="attendance.generate_report")
def generate_report(self, report_type: str, period: str):
    """Generate attendance report."""
    return {"ok": True, "report_type": report_type, "period": period}
