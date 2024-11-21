import uuid
from collections.abc import Generator
from unittest.mock import ANY

import pytest
from clickhouse_connect.driver import Client
from django.conf import settings

from core.event_log_client import pull_logged_events
from event_logs.models import EventLogModel
from users.models import User
from users.use_cases import CreateUser, CreateUserRequest, UserCreated

pytestmark = [pytest.mark.django_db]


@pytest.fixture()
def f_use_case() -> CreateUser:
    return CreateUser()


@pytest.fixture(autouse=True)
def f_clean_up_event_log(f_ch_client: Client) -> Generator:
    f_ch_client.query(f'TRUNCATE TABLE {settings.CLICKHOUSE_EVENT_LOG_TABLE_NAME}')
    yield


def test_event_log_entry_not_published_immediately(
    f_use_case: CreateUser,
    f_ch_client: Client,
) -> None:
    email = f'test_{uuid.uuid4()}@email.com'
    request = CreateUserRequest(
        email=email, first_name='Test', last_name='Testovich',
    )

    f_use_case.execute(request)
    log = f_ch_client.query("SELECT * FROM default.event_log WHERE event_type = 'user_created'")

    assert log.result_rows == []


def test_event_log_outbox_entry_created(
    f_use_case: CreateUser,
) -> None:
    email = f'test_{uuid.uuid4()}@email.com'
    request = CreateUserRequest(
        email=email, first_name='Test', last_name='Testovich',
    )
    init_user_count = User.objects.count()
    init_event_log_count = EventLogModel.objects.count() == 1

    f_use_case.execute(request)

    assert User.objects.count() == init_user_count + 1
    assert EventLogModel.objects.count() == init_event_log_count + 1


def test_event_log_pulled_to_clickhouse(
    f_use_case: CreateUser,
    f_ch_client: Client,
) -> None:
    email = f'test_{uuid.uuid4()}@email.com'
    request = CreateUserRequest(
        email=email, first_name='Test', last_name='Testovich',
    )

    f_use_case.execute(request)
    pull_logged_events(f_ch_client)
    log = f_ch_client.query("SELECT * FROM default.event_log WHERE event_type = 'user_created'")

    assert EventLogModel.objects.count() == 0
    assert log.result_rows == [
        (
            'user_created',
            ANY,
            'Local',
            UserCreated(email=email, first_name='Test', last_name='Testovich').model_dump_json(),
            1,
        ),
    ]

