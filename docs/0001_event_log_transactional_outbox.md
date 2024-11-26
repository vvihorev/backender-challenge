# Technical Solution

![image](https://github.com/user-attachments/assets/7699720c-cc91-40c8-9665-32fcdb78fd13)

We use a [transactional outbox][1] pattern, writing event logs to the
application database in a single transaction with the main event.

Publishing event logs to ClickHouse becomes the responsibility of a separate
service, thus network write errors will not cause poor UX anymore. We use
Celery to schedule periodic tasks pulling event logs from the outbox into
ClickHouse.

We perform EventLog batching by pulling out and publishing at most
`EVENT_LOG_OUTBOX_MAX_BATCH_SIZE` rows from the EventLog outbox.

[1]: https://microservices.io/patterns/data/transactional-outbox.html
