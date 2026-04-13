from typing import Protocol
from uuid import UUID


class AccessTokenVerifierPort(Protocol):
    def verify(self, token: str) -> UUID:
        pass
