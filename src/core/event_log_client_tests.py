from collections.abc import Generator
from unittest.mock import ANY

import pytest
from clickhouse_connect.driver import Client
from django.conf import settings

from core.base_model import Model
from core.event_log_client import EventLogClient
from event_logs.models import EventLogModel

pytestmark = [pytest.mark.django_db]


@pytest.fixture(autouse=True)
def f_clean_up_event_log(f_ch_client: Client) -> Generator:
    f_ch_client.query(f'TRUNCATE TABLE {settings.CLICKHOUSE_EVENT_LOG_TABLE_NAME}')
    yield


class TestEvent(Model):
    text: str


def test_event_log_entry_not_published_immediately(f_ch_client: Client) -> None:
    EventLogClient.log_events([TestEvent(text="unpublished test event")])

    log = f_ch_client.query("SELECT * FROM default.event_log WHERE event_type = 'test_event'")

    assert log.result_rows == []


def test_event_log_outbox_entry_created() -> None:
    init_event_log_count = EventLogModel.objects.count()

    EventLogClient.log_events([TestEvent(text="test event")])

    assert EventLogModel.objects.count() == init_event_log_count + 1
    assert EventLogModel.objects.filter().first().is_published == False


def test_event_log_pulled_and_published_to_clickhouse(f_ch_client: Client) -> None:
    client = EventLogClient(f_ch_client)
    client.log_events([TestEvent(text="published test event")])

    client.pull_and_publish_logged_events()
    log = client.query("SELECT * FROM default.event_log WHERE event_type = 'test_event'")

    assert EventLogModel.objects.count() == 1
    assert EventLogModel.objects.filter().first().is_published == True
    assert log == [
        (
            'test_event',
            ANY,
            'Local',
            TestEvent(text="published test event").model_dump_json(),
            1,
        ),
    ]


def test_events_are_marked_as_published(f_ch_client: Client) -> None:
    client = EventLogClient(f_ch_client)
    client.log_events([TestEvent(text="published test event")])

    client.pull_and_publish_logged_events()
    client.pull_and_publish_logged_events()
    log = client.query("SELECT * FROM default.event_log WHERE event_type = 'test_event'")

    assert log == [
        (
            'test_event',
            ANY,
            'Local',
            TestEvent(text="published test event").model_dump_json(),
            1,
        ),
    ]


def test_events_are_published_in_batches(f_ch_client: Client) -> None:
    settings.EVENT_LOG_OUTBOX_MAX_BATCH_SIZE = 2
    client = EventLogClient(f_ch_client)
    client.log_events([
        TestEvent(text="first"),
        TestEvent(text="second"),
        TestEvent(text="third"),
    ])

    log = client.query("SELECT * FROM default.event_log WHERE event_type = 'test_event'")
    assert log == []

    client.pull_and_publish_logged_events()
    log = client.query("SELECT * FROM default.event_log WHERE event_type = 'test_event'")
    assert log == [
        (
            'test_event',
            ANY,
            'Local',
            TestEvent(text="first").model_dump_json(),
            1,
        ),
        (
            'test_event',
            ANY,
            'Local',
            TestEvent(text="second").model_dump_json(),
            1,
        ),
    ]

    client.pull_and_publish_logged_events()
    log = client.query("SELECT * FROM default.event_log WHERE event_type = 'test_event'")
    assert len(log) == 3


def test_events_are_published_atomically(f_ch_client: Client) -> None:
    settings.EVENT_LOG_OUTBOX_MAX_BATCH_SIZE = 2
    client = EventLogClient(f_ch_client)
    client.log_events([
        TestEvent(text="first"),
        TestEvent(text="second"),
        TestEvent(text="third"),
    ])

    log = client.query("SELECT * FROM default.event_log WHERE event_type = 'test_event'")
    assert log == []

    client.pull_and_publish_logged_events()
    log = client.query("SELECT * FROM default.event_log WHERE event_type = 'test_event'")
    assert log == [
        (
            'test_event',
            ANY,
            'Local',
            TestEvent(text="first").model_dump_json(),
            1,
        ),
        (
            'test_event',
            ANY,
            'Local',
            TestEvent(text="second").model_dump_json(),
            1,
        ),
    ]

    client.pull_and_publish_logged_events()
    log = client.query("SELECT * FROM default.event_log WHERE event_type = 'test_event'")
    assert len(log) == 3
