from datetime import datetime, timedelta
from typing import List, Tuple
from uuid import UUID, uuid4

from app.core.domain.events import BaseEvent
from app.core.domain.events.token import RefreshTokenCreated, RefreshTokenRevoked
from app.core.domain.exceptions.token import TokenError, RefreshTokenReuse
from app.core.utils.security import generate_token, hash_token
from app.core.utils.time import utc_now


class RefreshToken:
    """
    Represents a refresh token associated with a user, including expiration,
    revocation, and rotation tracking. Tracks domain events for token creation
    and revocation.
    """

    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        created_at: datetime,
        revoked_at: datetime | None = None,
        replaced_by_id: UUID | None = None,
        location: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ):
        """
        Initialize a RefreshToken instance.

        Args:
            id (UUID): Unique token ID.
            user_id (UUID): ID of the user this token belongs to.
            token_hash (str): Hashed token value.
            expires_at (datetime): Token expiration timestamp.
            created_at (datetime): Token creation timestamp.
            revoked_at (datetime | None): Revocation timestamp.
            replaced_by_id (UUID | None): ID of a token that replaced this one.
            location (str | None): Optional location metadata.
            client_ip (str | None): Optional client IP metadata.
            user_agent (str | None): Optional user-agent metadata.
        """
        self.id = id
        self.user_id = user_id
        self.token_hash = token_hash
        self.expires_at = expires_at
        self.created_at = created_at
        self.revoked_at = revoked_at
        self.replaced_by_id = replaced_by_id
        self.location = location
        self.client_ip = client_ip
        self.user_agent = user_agent

        self._events: List[BaseEvent] = []

    @classmethod
    def create(
        cls,
        user_id: UUID,
        token_length: int,
        expiry: timedelta,
        location: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> Tuple["RefreshToken", str]:
        """
        Factory method to create a new refresh token.

        Args:
            user_id (UUID): User ID to associate the token with.
            token_length (int): Length of the token string to generate.
            expiry (timedelta): Duration before the token expires.
            location (str | None): Optional location metadata.
            client_ip (str | None): Optional client IP metadata.
            user_agent (str | None): Optional user-agent metadata.

        Returns:
            Tuple[RefreshToken, str]: The new RefreshToken instance and the raw token string.
        """
        token_string = generate_token(token_length)
        token_hash = hash_token(token_string)
        now = utc_now()
        expires_at = now + expiry

        token = cls(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=now,
            location=location,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        token._events.append(
            RefreshTokenCreated(
                user_id=user_id,
                token_id=token.id,
                client_ip=client_ip,
                user_agent=user_agent,
                location=location,
            )
        )

        return token, token_string

    def revoke(self) -> None:
        """
        Revoke this token if it is currently valid.

        Raises:
            TokenError: If the token is already revoked or expired.
        """
        if self._is_revoked_or_expired():
            raise TokenError("Cannot revoke invalid token")

        self.revoked_at = utc_now()
        self._events.append(RefreshTokenRevoked(token_id=self.id, user_id=self.user_id))

    def mark_as_replaced_by(self, new_token_id: UUID) -> None:
        """
        Mark this token as replaced by another token.

        Args:
            new_token_id (UUID): ID of the token that replaces this one.

        Raises:
            TokenError: If this token is already marked as replaced.
        """
        if self.replaced_by_id is not None:
            raise TokenError("Token is already replaced")
        self.replaced_by_id = new_token_id

    def use(self) -> None:
        """
        Mark the token as used for refresh or rotation.
        This revokes the token and prevents reuse.

        Raises:
            RefreshTokenReuse: If the token has already been replaced.
            TokenError: If the token is revoked or expired.
        """
        print(self.replaced_by_id)
        if self.replaced_by_id:
            raise RefreshTokenReuse()
        if self._is_revoked_or_expired():
            raise TokenError("Token cannot be used")

        self.revoked_at = utc_now()
        self._events.append(RefreshTokenRevoked(token_id=self.id, user_id=self.user_id))

    def is_usable(self) -> bool:
        """
        Check if the token can currently be used.

        Returns:
            bool: True if token is neither revoked, expired, nor replaced.
        """
        return not self._is_revoked_or_expired() and self.replaced_by_id is None

    def pull_domain_events(self) -> List[BaseEvent]:
        """
        Retrieve and clear domain events generated by this token.

        Returns:
            List[BaseEvent]: List of events.
        """
        events = self._events[:]
        self._events.clear()
        return events

    def _is_revoked_or_expired(self) -> bool:
        """
        Check if the token is revoked or expired.

        Returns:
            bool: True if token is revoked or expired.
        """
        return self.revoked_at is not None or utc_now() > self.expires_at
