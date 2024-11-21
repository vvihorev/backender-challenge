import re
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import clickhouse_connect
import structlog
from clickhouse_connect.driver.exceptions import DatabaseError
from django.conf import settings

from core.base_model import Model
from event_logs.models import EventLogModel

logger = structlog.get_logger(__name__)

EVENT_LOG_COLUMNS = [
    'event_type',
    'event_date_time',
    'environment',
    'event_context',
]


def _to_snake_case(event_name: str) -> str:
    result = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", event_name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", result).lower()


def log_events(data: list[Model]) -> None:
    for event in data:
        EventLogModel.objects.create(
            event_type=_to_snake_case(event.__class__.__name__),
            event_context=event.model_dump_json(),
        )


def pull_logged_events(client: clickhouse_connect.driver.Client) -> None:
    events = EventLogModel.objects.order_by("event_date_time")[:1000]

    if events.count() == 0:
        logger.info("no log events found when pulling outbox")
        return

    events_data = events.values_list(*EVENT_LOG_COLUMNS)
    ic = client.create_insert_context(
        column_names=EVENT_LOG_COLUMNS,
        database=settings.CLICKHOUSE_SCHEMA,
        table=settings.CLICKHOUSE_EVENT_LOG_TABLE_NAME,
    )
    for event, event_data in zip(events, events_data, strict=False):
        logger.info(event=event, data=event_data)
        ic.data = [event_data]
        client.insert(context=ic)
        event.delete()
    logger.info("pulled events from the outbox", count=events.count())


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
