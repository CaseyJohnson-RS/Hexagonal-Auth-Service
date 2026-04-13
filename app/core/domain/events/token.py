from uuid import UUID

from . import DomainEvent


class TokenEvent(DomainEvent):
    """Событие токена"""

    user_id: UUID
    token_id: UUID


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class RefreshTokenCreated(TokenEvent):
    """Создан refresh token (создана новая рабочая сессия)"""

    client_ip: str | None = None
    user_agent: str | None = None
    location: str | None = None


class RefreshTokenRevoked(TokenEvent):
    """Отзыв рефреш токена (сессии)"""

    pass
