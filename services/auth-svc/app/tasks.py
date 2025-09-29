from celery import Celery
from kombu import Exchange, Queue

BROKER = "amqp://guest:guest@rabbitmq:5672//"

celery_app = Celery("auth-tasks", broker=BROKER, backend=None)
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

# Auth service queues
celery_app.conf.task_default_exchange = "auth"
celery_app.conf.task_queues = (
    Queue("auth.default", Exchange("auth", type="topic"), routing_key="auth.default", durable=True),
    Queue("auth.dlq", Exchange("auth.dlx", type="fanout"), durable=True),
)

@celery_app.task(bind=True, name="auth.sample_task")
def sample_task(self, message: str):
    return {"ok": True, "message": message}

@celery_app.task(bind=True, name="auth.send_login_notification")
def send_login_notification(self, user_id: str, ip_address: str):
    """Send a login notification to the user."""
    return {"ok": True, "user_id": user_id, "ip_address": ip_address}

@celery_app.task(bind=True, name="auth.cleanup_expired_sessions")
def cleanup_expired_sessions(self):
    """Clean up expired user sessions."""
    return {"ok": True, "cleaned": 0}
