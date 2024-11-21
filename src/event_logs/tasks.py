import clickhouse_connect
import structlog
from celery import shared_task
from django.conf import settings
from sentry_sdk import capture_exception

from core.event_log_client import pull_logged_events

logger = structlog.get_logger(__name__)


@shared_task
def pull_outbox_events_log() -> None:
    client = clickhouse_connect.get_client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        user=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
        query_retries=2,
        connect_timeout=30,
        send_receive_timeout=10,
    )

    try:
        pull_logged_events(client)
    except Exception as e:
        capture_exception(e)
        logger.error("error pushing event log outbox to clickhouse", error=str(e))
    finally:
        client.close()
