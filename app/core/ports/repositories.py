from typing import List, Protocol, TypeVar
from uuid import UUID

from app.core.domain.entities.one_time_token import OneTimeToken
from app.core.domain.entities.refresh_token import RefreshToken
from app.core.domain.entities.user import User


T = TypeVar("T", contravariant=True)


class RepositoryPort(Protocol[T]):
    async def save(self, entity: T):
        pass

    async def delete(self, entity: T):
        pass


class UserRepositoryPort(RepositoryPort[User], Protocol):
    async def get_by_email(self, email: str) -> User | None:
        pass

    async def get_by_id(self, user_id: UUID) -> User | None:
        pass


class OneTimeTokenRepositoryPort(RepositoryPort[OneTimeToken], Protocol):
    async def get_by_string(self, token_string: str) -> OneTimeToken | None:
        pass


class RefreshTokenRepositoryPort(RepositoryPort[RefreshToken], Protocol):
    async def get_by_string(self, token_string: str) -> RefreshToken | None:
        pass

    async def get_all_by_user(self, user_id: UUID) -> List[RefreshToken]:
        pass
