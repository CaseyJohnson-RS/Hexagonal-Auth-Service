from uuid import UUID
from . import ApplicationEvent  # noqa


class RefreshTokenReuseDetected(ApplicationEvent):
    user_id: UUID
    token_id: UUID
    client_ip: str | None
    user_agent: str | None
    location: str | None = None


class SuspiciousRefreshTokenRevocation(ApplicationEvent):
    user_id: UUID
    token_id: UUID
    client_ip: str | None
    user_agent: str | None
    location: str | None = None