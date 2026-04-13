from datetime import datetime, timedelta
from enum import Enum
from typing import Tuple
from uuid import UUID, uuid4

from app.core.domain.exceptions.token import TokenError
from app.core.utils.security import generate_token, hash_token
from app.core.utils.time import utc_now


class OneTimeTokenPurpose(str, Enum):
    """
    Enum representing the purpose of a one-time token.
    """
    VERIFY_EMAIL = "verify_email"
    RECOVER_PASSWORD = "recover_password"


class OneTimeToken:
    """
    Represents a one-time token associated with a user for a specific purpose,
    such as email verification or password recovery. Tracks usage and expiration.
    """

    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        purpose: OneTimeTokenPurpose,
        used: bool = False,
    ):
        """
        Initialize a OneTimeToken instance.

        Args:
            id (UUID): Unique token ID.
            user_id (UUID): ID of the user this token belongs to.
            token_hash (str): Hashed token value.
            expires_at (datetime): Token expiration timestamp.
            purpose (OneTimeTokenPurpose): Purpose of this token.
            used (bool, optional): Whether the token has been used. Defaults to False.
        """
        self.id = id
        self.user_id = user_id
        self.token_hash = token_hash
        self.expires_at = expires_at
        self.purpose = purpose
        self.used = used

    @classmethod
    def create(
        cls,
        user_id: UUID,
        token_length: int,
        expiry: timedelta,
        purpose: OneTimeTokenPurpose,
    ) -> Tuple["OneTimeToken", str]:
        """
        Factory method to create a new one-time token.

        Args:
            user_id (UUID): User ID to associate the token with.
            token_length (int): Length of the token string to generate.
            expiry (timedelta): Duration before the token expires.
            purpose (OneTimeTokenPurpose): Purpose of the token.

        Returns:
            Tuple[OneTimeToken, str]: The new token instance and the raw token string.
        """
        now = utc_now()
        token_string = generate_token(token_length)
        token_hash = hash_token(token_string)
        expires_at = now + expiry

        token = cls(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            purpose=purpose,
            used=False,
        )
        return token, token_string

    def use(self, purpose: OneTimeTokenPurpose) -> None:
        """
        Mark the token as used.

        Args:
            purpose (OneTimeTokenPurpose): The intended purpose of the token usage.

        Raises:
            TokenError: If the purpose does not match or the token is invalid.
        """
        if self.purpose != purpose:
            raise TokenError("Token purpose mismatch")

        if not self.is_usable():
            raise TokenError("Cannot use invalid token")

        self.used = True

    def is_usable(self) -> bool:
        """
        Check if the token is still valid and unused.

        Returns:
            bool: True if token is not used and not expired.
        """
        now = utc_now()
        return not self.used and now <= self.expires_at
