from uuid import UUID
import jwt

from app.core.ports.services.access_token_verifier import AccessTokenVerifierPort
from app.core.domain.exceptions.token import (
    InvalidAccessToken,
    AccessTokenExpired,
)


class AccessTokenVerifier(AccessTokenVerifierPort):
    def __init__(self, secret: str, algorithm: str):
        self._secret = secret
        self._algorithm = algorithm

    def verify(self, token: str) -> UUID:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise AccessTokenExpired()
        except jwt.InvalidTokenError:
            raise InvalidAccessToken()

        try:
            return UUID(payload["sub"])
        except (KeyError, ValueError):
            raise InvalidAccessToken()
