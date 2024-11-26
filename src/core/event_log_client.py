import re
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import clickhouse_connect
import structlog
from clickhouse_connect.driver.exceptions import DatabaseError
from django.conf import settings
from sentry_sdk import capture_exception

from core.base_model import Model
from event_logs.models import EventLogModel

logger = structlog.get_logger(__name__)

EVENT_LOG_COLUMNS = [
    'event_type',
    'event_date_time',
    'environment',
    'event_context',
]


class EventLogClient:
    def __init__(self, client: clickhouse_connect.driver.Client) -> None:
        self._client = client

    @classmethod
    @contextmanager
    def init(cls) -> Generator['EventLogClient']:
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
            yield cls(client)
        except Exception as e:
            capture_exception(e)
            logger.error('error while executing clickhouse query', error=str(e))
        finally:
            client.close()

    def query(self, query: str) -> Any:  # noqa: ANN401
        logger.debug('executing clickhouse query', query=query)

        try:
            return self._client.query(query).result_rows
        except DatabaseError as e:
            logger.error('failed to execute clickhouse query', error=str(e))
            return

    @staticmethod
    def log_events(data: list[Model]) -> None:
        for event in data:
            EventLogModel.objects.create(
                event_type=EventLogClient._to_snake_case(event.__class__.__name__),
                event_context=event.model_dump_json(),
            )

    def pull_and_publish_logged_events(self) -> None:
        events = EventLogModel.objects.filter(
            is_published=False
        ).order_by("event_date_time")[:settings.EVENT_LOG_OUTBOX_MAX_BATCH_SIZE]

        if events.count() == 0:
            logger.info("no log events found when pulling outbox")
            return

        self._client.insert(
            data=events.values_list(*EVENT_LOG_COLUMNS),
            column_names=EVENT_LOG_COLUMNS,
            database=settings.CLICKHOUSE_SCHEMA,
            table=settings.CLICKHOUSE_EVENT_LOG_TABLE_NAME,
        )
        EventLogModel.objects.filter(pk__in=events.values("pk")).update(is_published=True)

        logger.info(
            "pulled and published events from the outbox",
            count=events.count()
        )

    @staticmethod
    def _to_snake_case(event_name: str) -> str:
        result = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", event_name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", result).lower()
