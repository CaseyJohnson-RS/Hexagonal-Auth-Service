from datetime import timedelta
from uuid import UUID
import jwt

from app.core.ports.services.access_token_issuer import AccessTokenIssuerPort

from app.core.utils.time import utc_now


class AccessTokenIssuer(AccessTokenIssuerPort):
    def __init__(self, secret: str, algorithm: str):
        self._secret = secret
        self._algorithm = algorithm

    def issue(self, user_id: UUID, expiry: timedelta) -> str:
        now = utc_now()
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + expiry,
            "type": "access",
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)
