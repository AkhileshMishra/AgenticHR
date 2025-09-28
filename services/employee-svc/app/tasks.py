"""Celery tasks for the service."""

from celery import Celery
import structlog

logger = structlog.get_logger(__name__)

# Initialize Celery app
celery_app = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

@celery_app.task(bind=True)
def sample_task(self, message: str):
    """Sample task for testing."""
    logger.info("Processing sample task", message=message, task_id=self.request.id)
    return f"Processed: {message}"

@celery_app.task(bind=True)
def send_notification(self, recipient: str, subject: str, body: str):
    """Send notification task."""
    logger.info("Sending notification", recipient=recipient, subject=subject, task_id=self.request.id)
    # TODO: Implement actual notification sending
    return f"Notification sent to {recipient}"
