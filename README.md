# Authentication Service — Hexagonal Architecture

An authentication microservice built using **FastAPI**, structured based on the **hexagonal architecture**.

The domain core has no dependencies on frameworks—all infrastructure tasks (database, HTTP, tokens) are located behind port interfaces and implemented via adapters.

## Architecture

```mermaid
LR graph
Inbound Adapters subgraph
HTTP[FastAPI Routers]
end

Application Layer subgraph
UC[Use Cases]
DTO[DTOs]
EV_APP[Event Handlers]
end

Core / Domain subgraph
ENT[Entities and Aggregates]
DS[Domain Services]
DE[Domain Events]
VAL[Validators]
PORTS[[Ports - Protocol Interfaces]]
end

Outbound Adapters subgraph
REPO[SQLAlchemy Repositories]
JWT_A[JWT Publisher/Verifier]
BUS[In-Memory Event Bus]
TX[Transaction Manager]
end

HTTP -->|calls| UC
UC -->|uses| ENT
UC -->|uses| DS
UC -->|depends on| PORTS
PORTS -.-|implemented| REPO
PORTS -.-|implemented| JWT_A
PORTS -.-|implemented| BUS
PORTS -.-|implemented| TX
```

### Layer Responsibilities

**Core/Domain** (`app/core/`) — Business rules without external dependencies. Entities generate domain events; ports are defined as Python `Protocol` classes (structural subtyping, without inheritance from framework base classes).

**Application** (`app/application/`) — Use cases that organize the domain logic. Each use case receives ports via constructor injection, executes within a transaction, and publishes the collected domain events upon commit.

**Adapters** (`app/adapters/`) — Concrete port implementations. Split into *incoming* (HTTP routing via FastAPI) and *outgoing* (data storage in PostgreSQL via SQLAlchemy, JWT token management, in-memory event bus).

**Composition root** (`app/adapters/nexus.py`) — binds ports to adapter implementations using FastAPI `Depends`. A single location where all concrete types are specified.

## Project Structure

```
app/
├── core/ # Domain — without framework imports
│ ├── domain/
│ │ ├── entities/ # User, RefreshToken, OneTimeToken
│ │ ├── events/ # Domain events (UserCreated, etc.)
│ │ ├── exceptions/ # Domain-specific errors
│ │ ├── services/ # Email validation, RefreshToken rotation
│ │ └── validators/ # Email and password validation
│ ├── ports/ # Port interfaces (protocol classes)
│ │ ├── repositories.py # UserRepositoryPort, etc.
│ │ ├── transaction.py # TransactionPort
│ │ └── services/ # AccessTokenIssuerPort, EventPublisherPort, ...
│ └── utils/ # Security helpers, timing utilities
│
├── application/ # Use cases
│ ├── cases/user/ # Registration, login, email verification, password change, ...
│ ├── dto/ # I/O DTOs
│ ├── events/ # Application-level event handling
│ └── exceptions/ # Application-level errors (conflict, not) found)
│
├── adapters/
│ ├── inbound/http/ # FastAPI routers, request/response schemes
│ ├── outbound/
│ │ ├── persistence/sqlalchemy/ # ORM models and repository implementations
│ │ ├── access_token/ # JWT publisher and verifier adapters
│ │ └── event_bus/in_memory/ # Event queue and in-memory publisher
│ └── nexus.py # Composition root (DI wiring)
│
├── infrastructure/db/ # Asynchronous session factory PostgreSQL
├── config/ # Pydantic Settings
└── main.py # FastAPI Application Entry Point
```

## Realization moments

**Ports as Protocols** — Port interfaces use `typing.Protocol` instead of abstract base classes. Adapters conform to them structurally — there is no need to inherit from a common base class.

**Domain Events on Aggregates** — The `User` entity collects domain events internally (the `_events` list). Use cases call `pull_domain_events()` after the operation and publish them outside the transaction.

**One Use Case Per File** — Each application use case (`RegisterUserCase`, `LoginCase`, etc.) is in its own module with explicit dependencies declared in `__init__`.

**Transaction Port** — Transaction management is abstracted behind `TransactionPort` (an asynchronous context management protocol), ensuring that use cases are unaware of SQLAlchemy session details.

## Tech Stack

| Tier | Technology |
|---|---|
| HTTP Framework | FastAPI + Uvicorn |
| Database | PostgreSQL 15 (asynchronous via asyncpg) |
| ORM | SQLAlchemy (asynchronous) |
| Migrations | Alembic |
| Authentication Tokens | PyJWT (access) + refresh and database-based one-time tokens |
| Password Hashing | passlib / bcrypt |
| Validation | Pydantic v2 |
| Containerization | Docker Compose |
| Testing | pytest + pytest-asyncio + httpx |

## How to run

```bash
# Clone and run
docker compose up

# API documentation
open http://localhost:8000/docs

#Security audit events dashboard
open http://localhost:8000/auth/audit/events
```

## Features

- User registration with email verification flow
- Login with JWT access + refresh token pair
- Refresh token rotation with security policy
- Password change & password recovery via one-time tokens
- Domain event publishing (security audit log)
- Soft delete (user deactivation)