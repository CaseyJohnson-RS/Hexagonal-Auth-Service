import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.adapters.nexus import get_notification_queue
from app.core.domain.events.user import (
    UserEmailVerificationRequested,
    UserPasswordRecoverRequested,
)


EMAIL = "api_test@example.com"
PASSWORD = "StrongPass99!"


# ─── helpers ──────────────────────────────────────────────────────────────────


def _last_token(queue, event_cls) -> str:
    for event in reversed(queue.get_all()):
        if isinstance(event, event_cls):
            return event.token
    raise AssertionError(f"No {event_cls.__name__} found in notification queue")


def get_verify_token(queue) -> str:
    return _last_token(queue, UserEmailVerificationRequested)


def get_recover_token(queue) -> str:
    return _last_token(queue, UserPasswordRecoverRequested)


# ─── base fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
async def clean_db(async_session):
    """Truncates all tables before each test (delegated to parent conftest)."""


@pytest.fixture(autouse=True)
def notification_queue():
    """Returns the global notification queue, cleared before each test."""
    queue = get_notification_queue()
    queue.clear()
    return queue


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ─── user-state fixtures ──────────────────────────────────────────────────────


@pytest.fixture
async def registered(client, notification_queue):
    """Register a user; return the OTT string from the emitted event."""
    resp = await client.post(
        "/auth/api/register", json={"email": EMAIL, "password": PASSWORD}
    )
    assert resp.status_code == 200
    return get_verify_token(notification_queue)


@pytest.fixture
async def verified(client, registered, notification_queue):
    """Register + verify email; return the email."""
    resp = await client.post(
        "/auth/api/verify_email", json={"one_time_token": registered}
    )
    assert resp.status_code == 200
    return EMAIL


@pytest.fixture
async def tokens(client, verified):
    """Full login; return the token-pair dict {access_token, refresh_token}."""
    resp = await client.post(
        "/auth/api/token", json={"email": EMAIL, "password": PASSWORD}
    )
    assert resp.status_code == 200
    return resp.json()
