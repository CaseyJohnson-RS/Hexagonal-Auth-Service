import pytest
from uuid import uuid4
from datetime import timedelta

from app.core.domain.entities.user import User as UserDomain
from app.core.domain.entities.refresh_token import RefreshToken
from app.core.domain.entities.one_time_token import OneTimeToken, OneTimeTokenPurpose
from app.core.utils.time import utc_now
from app.core.utils.security import hash_token
from app.adapters.outbound.persistence.sqlalchemy.repositories.user import UserRepository
from app.adapters.outbound.persistence.sqlalchemy.repositories.refresh_token import (
    RefreshTokenRepository,
)
from app.adapters.outbound.persistence.sqlalchemy.repositories.one_time_token import (
    OneTimeTokenRepository,
)


def make_user(
    *,
    email: str = "user@example.com",
    password_hash: str = "fake-hash",
    active: bool = True,
    is_email_verified: bool = True,
) -> UserDomain:
    return UserDomain(
        id=uuid4(),
        email=email,
        password_hash=password_hash,
        active=active,
        is_email_verified=is_email_verified,
        created_at=utc_now(),
    )


def make_refresh_token(
    *,
    user_id,
    token_string: str = "raw-refresh-token",
    expires_in: timedelta = timedelta(hours=1),
    revoked: bool = False,
    replaced_by_id=None,
) -> RefreshToken:
    now = utc_now()
    return RefreshToken(
        id=uuid4(),
        user_id=user_id,
        token_hash=hash_token(token_string),
        expires_at=now + expires_in,
        created_at=now,
        revoked_at=now if revoked else None,
        replaced_by_id=replaced_by_id,
    )


def make_one_time_token(
    *,
    user_id,
    token_string: str = "raw-ott-token",
    purpose: OneTimeTokenPurpose = OneTimeTokenPurpose.VERIFY_EMAIL,
    expires_in: timedelta = timedelta(hours=1),
    used: bool = False,
) -> OneTimeToken:
    now = utc_now()
    return OneTimeToken(
        id=uuid4(),
        user_id=user_id,
        token_hash=hash_token(token_string),
        expires_at=now + expires_in,
        purpose=purpose,
        used=used,
    )


@pytest.fixture
def user_repo(async_session):
    return UserRepository(async_session)


@pytest.fixture
def rt_repo(async_session):
    return RefreshTokenRepository(async_session)


@pytest.fixture
def ott_repo(async_session):
    return OneTimeTokenRepository(async_session)


@pytest.fixture
async def saved_user(user_repo) -> UserDomain:
    user = make_user()
    await user_repo.save(user)
    return user
