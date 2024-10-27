# Die Hard

Проект для тестового задания middle-backend developer.

Требования к тестовому заданию можно найти по [ссылке](docs/task.md)

Тех стек:
- Python 3.13
- Django 5
- pytest
- Docker & docker-compose
- PostgreSQL
- ClickHouse

## Installing 

Положите файл `.env` в директорию `src/core`, например:

```
cp src/core/.env.ci src/core/.env
```

Затем:
```
make migrations
make migrate
make superuser
make run
```

## Tests

`make test`

## Linter

`make lint`
