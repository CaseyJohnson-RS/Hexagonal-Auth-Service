# Authentication Service with Hexagonal Architecture

## Description

This is an authentication service built using FastAPI that enables issuing JWT tokens for other services. It includes features such as user registration, email confirmation, password reset, security event tracking, and much more.

This project is a tutorial with a focus on hexagonal architecture.

## Features

- User registration with email confirmation
- Password hashing with bcrypt
- Email confirmation tokens
- Password reset function
- Refresh tokens
- Security event logging
- PostgreSQL database with asynchronous execution support
- Alembic migrations

## Prerequisites

- uv package manager (for development)
- Docker Compose (for production)

## Startup

1. Build and run the service in a container:

```bash

docker compose up
```
Now you can open
- [localhost:8000/docs](localhost:8000/docs)
- [localhost:8000/auth/audit/events](localhost:8000/auth/audit/events)

## Project Structure

- `app/main.py` - FastAPI application entry point
- `app/routers/` - API routers
- `app/services/` - Services Business logic
- `app/models/` - SQLAlchemy models
- `app/schemas/` - Pydantic schemas
- `app/core/` - Basic settings and configurations
- `migrations/` - Alembic migration files
- `tests/` - Test files