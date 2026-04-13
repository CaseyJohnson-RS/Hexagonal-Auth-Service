from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result

from app.core.ports.repositories import OneTimeTokenRepositoryPort
from app.core.domain.entities.one_time_token import OneTimeToken as OneTimeTokenDomain
from app.core.domain.entities.one_time_token import OneTimeTokenPurpose
from app.adapters.outbound.persistence.sqlalchemy.models import OneTimeToken as OneTimeTokenORM

from app.core.utils.security import hash_token
from app.application.exceptions.concurrency import ConcurrencyError


class OneTimeTokenRepository(OneTimeTokenRepositoryPort):
    """
    SQLAlchemy repository for OneTimeToken domain entity.

    Handles CRUD operations with optimistic concurrency control using
    a version field.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_string(self, token_string: str) -> OneTimeTokenDomain | None:
        """
        Retrieve a one-time token by its plain string value.

        Args:
            token_string: The raw token string to hash and search for.

        Returns:
            OneTimeTokenDomain or None if not found.
        """
        result = await self.session.execute(
            select(OneTimeTokenORM)
            .where(OneTimeTokenORM.token_hash == hash_token(token_string))
            .options(selectinload(OneTimeTokenORM.user))
        )
        orm_token = result.scalar_one_or_none()
        if orm_token:
            return orm2domain(orm_token)
        return None

    async def save(self, token: OneTimeTokenDomain):
        """
        Persist a domain token to the database.

        Performs insert for new tokens or update for existing tokens using
        optimistic concurrency control.
        """
        expected_version = getattr(token, "__version", None)

        if expected_version is None:
            # New entity
            orm_token = domain2orm(token)
            orm_token.version = 1
            self.session.add(orm_token)
            await self.session.flush()
            setattr(token, "__version", orm_token.version)
            return

        # Existing entity, update with optimistic concurrency
        stmt = (
            update(OneTimeTokenORM)
            .where(
                OneTimeTokenORM.id == token.id,
                OneTimeTokenORM.version == expected_version,
            )
            .values(
                token_hash=token.token_hash,
                user_id=token.user_id,
                expires_at=token.expires_at,
                used=token.used,
                version=expected_version + 1,
            )
        )
        result: Result = await self.session.execute(stmt)

        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConcurrencyError("OneTimeToken version conflict")

        await self.session.flush()
        setattr(token, "__version", expected_version + 1)

    async def delete(self, token: OneTimeTokenDomain):
        """
        Delete a token using optimistic concurrency control.

        Raises:
            ConcurrencyError if the token version does not match.
        """
        expected_version = getattr(token, "__version", None)

        stmt = delete(OneTimeTokenORM).where(
            OneTimeTokenORM.id == token.id,
            OneTimeTokenORM.version == expected_version,
        )

        result = await self.session.execute(stmt)

        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConcurrencyError("OneTimeToken version conflict on delete")

        await self.session.flush()


def orm2domain(token: OneTimeTokenORM) -> OneTimeTokenDomain:
    """
    Map SQLAlchemy ORM token to domain entity.

    Preserves version for optimistic concurrency.
    """
    domain_token = OneTimeTokenDomain(
        id=token.id,
        user_id=token.user_id,
        token_hash=token.token_hash,
        expires_at=token.expires_at,
        purpose=OneTimeTokenPurpose(token.purpose),
        used=token.used,
    )
    setattr(domain_token, "__version", token.version)
    return domain_token


def domain2orm(token: OneTimeTokenDomain) -> OneTimeTokenORM:
    """
    Map domain token to SQLAlchemy ORM model.

    Uses __version attribute for concurrency control.
    """
    return OneTimeTokenORM(
        id=token.id,
        user_id=token.user_id,
        token_hash=token.token_hash,
        expires_at=token.expires_at,
        purpose=token.purpose.value,
        used=token.used,
        version=getattr(token, "__version", 0),
    )
