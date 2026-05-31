"""Shared fixtures for all application use-case tests.

Every use case gets real domain objects wired through mock ports — no DB,
no HTTP. The fast_hash session fixture from tests/unit/conftest.py is
automatically inherited (autouse=True, scope="session").
"""
import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from app.core.domain.entities.one_time_token import OneTimeToken, OneTimeTokenPurpose
from app.core.domain.entities.refresh_token import RefreshToken
from app.core.domain.entities.user import User
from app.core.utils.security import hash_password
from app.core.utils.time import utc_now


# ── fake transaction ──────────────────────────────────────────────────────────

class FakeTx:
    """No-op async context manager that satisfies TransactionPort."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


# ── port fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def tx():
    return FakeTx()


@pytest.fixture
def user_repo():
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def ott_repo():
    repo = AsyncMock()
    repo.get_by_string = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def refresh_token_repo():
    repo = AsyncMock()
    repo.get_by_string = AsyncMock(return_value=None)
    repo.get_all_by_user = AsyncMock(return_value=[])
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def event_publisher():
    return AsyncMock()


@pytest.fixture
def access_token_issuer():
    mock = MagicMock()
    mock.issue = MagicMock(return_value="header.payload.sig")
    return mock


@pytest.fixture
def access_token_verifier():
    mock = MagicMock()
    mock.verify = MagicMock(return_value=uuid4())
    return mock


@pytest.fixture
def config():
    mock = MagicMock()
    mock.email_token_len = MagicMock(return_value=32)
    mock.email_token_exp = MagicMock(return_value=timedelta(hours=12))
    mock.access_token_exp = MagicMock(return_value=timedelta(minutes=15))
    mock.refresh_token_len = MagicMock(return_value=32)
    mock.refresh_token_exp = MagicMock(return_value=timedelta(days=14))
    mock.password_recover_token_len = MagicMock(return_value=32)
    mock.password_recover_token_exp = MagicMock(return_value=timedelta(minutes=15))
    return mock


# ── entity builder helpers ────────────────────────────────────────────────────

def make_user(
    *,
    active: bool = True,
    is_email_verified: bool = True,
    password: str = "Password123",
    email: str = "test@example.com",
    user_id: UUID | None = None,
) -> User:
    return User(
        id=user_id or uuid4(),
        email=email,
        password_hash=hash_password(password),
        active=active,
        is_email_verified=is_email_verified,
        created_at=utc_now(),
    )


def make_refresh_token(
    *,
    user_id: UUID | None = None,
    revoked: bool = False,
    replaced_by_id: UUID | None = None,
    expires_in: timedelta = timedelta(hours=24),
    client_ip: str | None = None,
    user_agent: str | None = None,
    location: str | None = None,
) -> RefreshToken:
    now = utc_now()
    return RefreshToken(
        id=uuid4(),
        user_id=user_id or uuid4(),
        token_hash="test-hash",
        expires_at=now + expires_in,
        created_at=now,
        revoked_at=now if revoked else None,
        replaced_by_id=replaced_by_id,
        client_ip=client_ip,
        user_agent=user_agent,
        location=location,
    )


def make_ott(
    *,
    user_id: UUID | None = None,
    purpose: OneTimeTokenPurpose = OneTimeTokenPurpose.VERIFY_EMAIL,
    used: bool = False,
    expires_in: timedelta = timedelta(hours=1),
) -> OneTimeToken:
    now = utc_now()
    return OneTimeToken(
        id=uuid4(),
        user_id=user_id or uuid4(),
        token_hash="test-hash",
        expires_at=now + expires_in,
        purpose=purpose,
        used=used,
    )
