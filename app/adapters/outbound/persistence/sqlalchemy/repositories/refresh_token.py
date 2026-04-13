from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result

from app.core.ports.repositories import RefreshTokenRepositoryPort
from app.core.domain.entities.refresh_token import RefreshToken as RefreshTokenDomain
from app.adapters.outbound.persistence.sqlalchemy.models import (
    RefreshToken as RefreshTokenORM,
)

from app.core.utils.security import hash_token
from app.application.exceptions.concurrency import ConcurrencyError


class RefreshTokenRepository(RefreshTokenRepositoryPort):
    """
    SQLAlchemy repository for RefreshToken domain entity.

    Uses optimistic concurrency control based on a version column.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_string(self, token_string: str) -> RefreshTokenDomain | None:
        """
        Retrieve a refresh token by its raw string value.

        Args:
            token_string: Raw refresh token string.

        Returns:
            RefreshTokenDomain or None if not found.
        """
        result = await self.session.execute(
            select(RefreshTokenORM).where(
                RefreshTokenORM.token_hash == hash_token(token_string)
            )
        )
        orm_token = result.scalar_one_or_none()
        if orm_token:
            return orm2domain(orm_token)
        return None

    async def get_all_by_user(self, user_id):
        """
        Retrieve all refresh tokens belonging to a user.
        """
        result = await self.session.execute(
            select(RefreshTokenORM).where(RefreshTokenORM.user_id == user_id)
        )
        return [orm2domain(token) for token in result.scalars().all()]

    async def save(self, token: RefreshTokenDomain):
        """
        Persist a refresh token.

        Inserts new tokens or updates existing ones using optimistic
        concurrency control.
        """
        expected_version = getattr(token, "__version", None)

        # New entity
        if expected_version is None:
            orm_token = domain2orm(token)
            orm_token.version = 1
            self.session.add(orm_token)
            await self.session.flush()
            setattr(token, "__version", orm_token.version)
            return

        # Existing entity
        stmt = (
            update(RefreshTokenORM)
            .where(
                RefreshTokenORM.id == token.id,
                RefreshTokenORM.version == expected_version,
            )
            .values(
                user_id=token.user_id,
                token_hash=token.token_hash,
                expires_at=token.expires_at,
                revoked_at=token.revoked_at,
                replaced_by_id=token.replaced_by_id,
                created_at=token.created_at,
                version=expected_version + 1,
            )
        )

        result: Result = await self.session.execute(stmt)

        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConcurrencyError("RefreshToken version conflict")

        await self.session.flush()
        setattr(token, "__version", expected_version + 1)

    async def delete(self, token: RefreshTokenDomain):
        """
        Delete a refresh token using optimistic concurrency control.
        """
        expected_version = getattr(token, "__version", None)

        stmt = delete(RefreshTokenORM).where(
            RefreshTokenORM.id == token.id,
            RefreshTokenORM.version == expected_version,
        )

        result: Result = await self.session.execute(stmt)

        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConcurrencyError("RefreshToken version conflict on delete")

        await self.session.flush()


def orm2domain(token: RefreshTokenORM) -> RefreshTokenDomain:
    """
    Convert ORM refresh token to domain entity.
    """
    domain_token = RefreshTokenDomain(
        id=token.id,
        user_id=token.user_id,
        token_hash=token.token_hash,
        expires_at=token.expires_at,
        revoked_at=token.revoked_at,
        replaced_by_id=token.replaced_by_id,
        created_at=token.created_at,
    )
    setattr(domain_token, "__version", token.version)
    return domain_token


def domain2orm(token: RefreshTokenDomain) -> RefreshTokenORM:
    """
    Convert domain refresh token to ORM model.
    """
    return RefreshTokenORM(
        id=token.id,
        user_id=token.user_id,
        token_hash=token.token_hash,
        expires_at=token.expires_at,
        revoked_at=token.revoked_at,
        replaced_by_id=token.replaced_by_id,
        created_at=token.created_at,
        version=getattr(token, "__version", 0),
    )
