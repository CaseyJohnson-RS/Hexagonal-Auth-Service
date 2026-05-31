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


from app.core.ports.services import EventPublisherPort, EventQueuePort  # noqa
from app.adapters.outbound.event_bus.in_memory import (  # noqa
    InMemoryEventQueue,
    EventPublisher,
)

_event_queue: EventQueuePort = InMemoryEventQueue()


def get_event_queue() -> EventQueuePort:
    global _event_queue
    return _event_queue


def get_event_publisher(
    event_queue: EventQueuePort = Depends(get_event_queue),
) -> EventPublisherPort:
    return EventPublisher(event_queue)


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
    "get_event_queue",
    "get_event_publisher",
    "get_session",
    "get_transaction",
    "get_user_repo",
    "get_ott_repo",
    "get_refresh_token_repo",
]
