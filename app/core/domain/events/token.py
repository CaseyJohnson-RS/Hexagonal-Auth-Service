from uuid import UUID

from . import DomainEvent


class TokenEvent(DomainEvent):
    """Base token event"""

    user_id: UUID
    token_id: UUID


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class RefreshTokenCreated(TokenEvent):
    """Refresh token created (new session started)"""

    client_ip: str | None = None
    user_agent: str | None = None
    location: str | None = None


class RefreshTokenRevoked(TokenEvent):
    """Refresh token revoked (session terminated)"""

    pass
