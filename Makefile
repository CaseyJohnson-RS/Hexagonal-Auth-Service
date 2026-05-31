.PHONY: migrations

# DB

db-up:
	docker compose up -d postgres

db-stop:
	docker compose stop postgres

revision:
ifndef DESCRIPTION
	$(error DESCRIPTION is required)
endif
	uv run alembic revision -m "$(DESCRIPTION)"

migrate:
	docker compose run --rm migrate

# Project

run: db-up migrate
	docker compose up auth	