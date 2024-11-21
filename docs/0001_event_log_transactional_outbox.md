# Technical Solution

We use a [transactional outbox][1] pattern, writing event logs to the
application database in a single transaction with the main event.

Writing event logs to ClickHouse becomes the responsibility of a separate
service, thus network write errors will not cause poor UX anymore. We use
Celery to schedule periodic tasks pulling event logs from the outbox into
ClickHouse.

According to a [blog post][2] by ClickHouse, in the observability use case, it
makes sense to use asynchronous inserts, for which batching is performed on the
side of the database, and not on the client.

It is suggested to enable async inserts for a separate user, as seen in [3]. An
alternative approach would be to switch to using `clickhouse-driver` and
enabling async inserts on a per-query basis.

# Links

[1]: https://microservices.io/patterns/data/transactional-outbox.html
[2]: https://clickhouse.com/blog/asynchronous-data-inserts-in-clickhouse#sometimes-client-side-batching-is-not-feasible
[3]: https://clickhouse.com/docs/en/optimize/asynchronous-inserts#enabling-asynchronous-inserts
