from datetime import timedelta
from typing import Protocol
from uuid import UUID


class AccessTokenIssuerPort(Protocol):
    def issue(self, user_id: UUID, expiry: timedelta) -> str:
        pass
