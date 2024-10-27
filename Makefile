run:
	docker compose up
superuser:
	docker compose run --rm app createsuperuser
migrations:
	docker compose run --rm app makemigrations
migrate:
	docker compose run --rm app migrate
shell:
	docker compose run --rm app shell
lint:
	docker compose run --rm app ruff check --fix
test:
	docker compose run --rm app pytest -svv
