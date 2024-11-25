import structlog
from celery import shared_task

from core.event_log_client import EventLogClient

logger = structlog.get_logger(__name__)


@shared_task
def pull_and_publish_outbox_events_log() -> None:
    with EventLogClient.init() as client:
        client.pull_and_publish_logged_events()
