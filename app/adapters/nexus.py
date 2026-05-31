from fastapi import Depends


# ==============================================================================


from app.core.ports.config import ConfigPort
from app.adapters.outbound.config import Config


def get_config() -> ConfigPort:
    return Config()


# ==============================================================================


from app.core.ports.services import AccessTokenIssuerPort  # noqa
from app.core.ports.services import AccessTokenVerifierPort  # noqa
from app.adapters.outbound.access_token.issuer import AccessTokenIssuer  # noqa
from app.adapters.outbound.access_token.verifier import AccessTokenVerifier  # noqa
from app.config import settings  # noqa

_access_token_issuer: AccessTokenIssuerPort | None = None


def get_access_token_issuer() -> AccessTokenIssuerPort:
    global _access_token_issuer
    if not _access_token_issuer:
        _access_token_issuer = AccessTokenIssuer(
            settings.jwt_secret, settings.jwt_algorithm
        )
    return _access_token_issuer


_access_token_verifier: AccessTokenVerifierPort | None = None


def get_access_token_verifier() -> AccessTokenVerifierPort:
    global _access_token_verifier
    if not _access_token_verifier:
        _access_token_verifier = AccessTokenVerifier(
            settings.jwt_secret, settings.jwt_algorithm
        )
    return _access_token_verifier


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


import redis.asyncio as aioredis  # noqa

from app.core.ports.services import EventPublisherPort, EventQueuePort  # noqa
from app.core.ports.services import NotificationPort  # noqa
from app.adapters.outbound.event_bus.in_memory import (  # noqa
    InMemoryNotificationQueue,
    EventPublisher,
)
from app.adapters.outbound.event_bus.redis import RedisEventQueue  # noqa
from app.infrastructure.redis.client import make_redis_client  # noqa

# Redis client — one connection pool for the whole process.
_redis_client: aioredis.Redis = make_redis_client()

_event_queue: EventQueuePort = RedisEventQueue(client=_redis_client)
_notification_queue: NotificationPort = InMemoryNotificationQueue()


def get_redis_client() -> aioredis.Redis:
    return _redis_client


def get_event_queue() -> EventQueuePort:
    return _event_queue


def get_notification_queue() -> NotificationPort:
    return _notification_queue


def get_event_publisher(
    event_queue: EventQueuePort = Depends(get_event_queue),
    notifications: NotificationPort = Depends(get_notification_queue),
) -> EventPublisherPort:
    return EventPublisher(queue=event_queue, notifications=notifications)


# ==============================================================================


from app.infrastructure.db.postgres import async_session_factory  # noqa
from sqlalchemy.ext.asyncio import AsyncSession  # noqa


def get_session() -> AsyncSession:
    return async_session_factory()


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


from app.core.ports.transaction import TransactionPort  # noqa
from app.adapters.outbound.persistence.sqlalchemy.transaction import (  # noqa
    SQLAlchemyTransaction,
)


def get_transaction(session: AsyncSession = Depends(get_session)) -> TransactionPort:
    return SQLAlchemyTransaction(session=session)


# ==============================================================================


from app.core.ports.repositories import (  # noqa
    UserRepositoryPort,
    OneTimeTokenRepositoryPort,
    RefreshTokenRepositoryPort,
)
from app.adapters.outbound.persistence.sqlalchemy.repositories import (  # noqa
    UserRepository,
    OneTimeTokenRepository,
    RefreshTokenRepository,
)


def get_user_repo(session: AsyncSession = Depends(get_session)) -> UserRepositoryPort:
    return UserRepository(session=session)


def get_ott_repo(
    session: AsyncSession = Depends(get_session),
) -> OneTimeTokenRepositoryPort:
    return OneTimeTokenRepository(session=session)


def get_refresh_token_repo(
    session: AsyncSession = Depends(get_session),
) -> RefreshTokenRepositoryPort:
    return RefreshTokenRepository(session=session)


# ==============================================================================


__all__ = [
    "get_config",
    "get_access_token_issuer",
    "get_access_token_verifier",
    "get_redis_client",
    "get_event_queue",
    "get_notification_queue",
    "get_event_publisher",
    "get_session",
    "get_transaction",
    "get_user_repo",
    "get_ott_repo",
    "get_refresh_token_repo",
]
