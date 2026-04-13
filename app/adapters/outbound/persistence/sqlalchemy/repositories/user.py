from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result

from app.application.exceptions.concurrency import ConcurrencyError
from app.core.ports.repositories import UserRepositoryPort
from app.core.domain.entities.user import User as UserDomain
from app.adapters.outbound.persistence.sqlalchemy.models import User as UserORM


class UserRepository(UserRepositoryPort):
    """
    SQLAlchemy repository for User aggregate.

    Uses optimistic concurrency control via a version field.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> UserDomain | None:
        """
        Retrieve a user by email.
        """
        result = await self.session.execute(
            select(UserORM).where(UserORM.email == email)
        )
        orm_user = result.scalar_one_or_none()
        return orm2domain(orm_user) if orm_user else None

    async def get_by_id(self, user_id: UUID) -> UserDomain | None:
        """
        Retrieve a user by id.
        """
        result = await self.session.execute(
            select(UserORM).where(UserORM.id == user_id)
        )
        orm_user = result.scalar_one_or_none()
        return orm2domain(orm_user) if orm_user else None

    async def save(self, user: UserDomain):
        """
        Persist a user aggregate.

        Inserts new users or updates existing ones using optimistic
        locking on the version field.
        """
        expected_version = getattr(user, "__version", None)

        # New entity
        if expected_version is None:
            orm_user = domain2orm(user)
            orm_user.version = 1
            self.session.add(orm_user)
            await self.session.flush()
            setattr(user, "__version", orm_user.version)
            return

        # Existing entity
        stmt = (
            update(UserORM)
            .where(
                UserORM.id == user.id,
                UserORM.version == expected_version,
            )
            .values(
                email=user.email,
                password_hash=user.password_hash,
                active=user.active,
                is_email_verified=user.is_email_verified,
                created_at=user.created_at,
                version=expected_version + 1,
            )
        )

        result: Result = await self.session.execute(stmt)

        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConcurrencyError("User version conflict")

        await self.session.flush()
        setattr(user, "__version", expected_version + 1)

    async def delete(self, user: UserDomain):
        """
        Delete a user using optimistic concurrency control.
        """
        expected_version = getattr(user, "__version", None)

        stmt = delete(UserORM).where(
            UserORM.id == user.id,
            UserORM.version == expected_version,
        )

        result: Result = await self.session.execute(stmt)

        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConcurrencyError("User version conflict on delete")

        await self.session.flush()


def orm2domain(user: UserORM) -> UserDomain:
    """
    Convert ORM user model to domain entity.
    """
    domain_user = UserDomain(
        id=user.id,
        email=user.email,
        password_hash=user.password_hash,
        active=user.active,
        is_email_verified=user.is_email_verified,
        created_at=user.created_at,
    )
    setattr(domain_user, "__version", user.version)
    return domain_user


def domain2orm(user: UserDomain) -> UserORM:
    """
    Convert domain user entity to ORM model.
    """
    return UserORM(
        id=user.id,
        email=user.email,
        password_hash=user.password_hash,
        active=user.active,
        is_email_verified=user.is_email_verified,
        created_at=user.created_at,
        version=getattr(user, "__version", 0),
    )
