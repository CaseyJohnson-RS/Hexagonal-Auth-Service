.PHONY: migrations

# DB

revision:
ifndef DESCRIPTION
	$(error DESCRIPTION is required)
endif
	uv run alembic revision -m "$(DESCRIPTION)"

migrate:
	docker compose run --rm migrate

# Service

run: migrate
	docker compose up auth

# Testing

test-unit:
	uv run --env-file .env.example pytest tests/unit

test-integration: migrate
	uv run --env-file .env.test pytest tests/integration

test-all: test-unit test-integration

# Linting

lint:
	uv run ruff check .