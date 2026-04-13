from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from app.core.domain.events import BaseEvent
from app.core.domain.events.user import (
    UserCreated,
    UserActivated,
    UserDeactivated,
    UserEmailVerified,
    UserPasswordChanged,
    UserPasswordRecovered,
    UserPasswordRecoverRequested,
    UserEmailVerificationRequested,
)
from app.core.domain.validators import validate_email, validate_hash_password
from app.core.domain.exceptions.user import UserError
from app.core.utils.security import verify_password
from app.core.utils.time import utc_now


class User:
    """
    Represents a system user with authentication, email verification,
    and account status management. Tracks domain events for actions
    performed on the user.
    """

    def __init__(
        self,
        id: UUID,
        email: str,
        password_hash: str,
        active: bool,
        is_email_verified: bool,
        created_at: datetime,
    ):
        """
        Initialize a User instance.

        Args:
            id_ (UUID): Unique identifier for the user.
            email (str): User's email address.
            password_hash (str): Hashed password.
            active (bool): Whether the user account is active.
            is_email_verified (bool): Whether the email is verified.
            created_at (datetime): Timestamp of user creation.
        """
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.active = active
        self.is_email_verified = is_email_verified
        self.created_at = created_at

        self._events: List[BaseEvent] = []

    @classmethod
    def create(cls, email: str, password: str) -> "User":
        """
        Factory method to create a new user.

        Validates email and password, sets account as active but unverified,
        and generates a UserCreated event.

        Args:
            email (str): User email address.
            password (str): User password.

        Returns:
            User: New user instance.
        """
        user = cls(
            id=uuid4(),
            email=validate_email(email),
            password_hash=validate_hash_password(password),
            active=True,
            is_email_verified=False,
            created_at=utc_now(),
        )
        user._events.append(UserCreated(user_id=user.id, email=user.email))
        return user

    def request_email_verification(self, token_string: str) -> None:
        """
        Request email verification by generating a verification event.

        Args:
            token_string (str): Verification token.

        Raises:
            UserError: If email is already verified.
        """
        if self.is_email_verified:
            raise UserError("Email already verified")

        self._events.append(
            UserEmailVerificationRequested(
                user_id=self.id,
                email=self.email,
                token=token_string
            )
        )
    
    def request_password_recover(self, token_string: str) -> None:
        if not self.is_email_verified:
            raise UserError("Email is not verified")

        self._events.append(
            UserPasswordRecoverRequested(
                user_id=self.id,
                email=self.email,
                token=token_string,
            )
        )

    def verify_email(self) -> None:
        """
        Mark the user's email as verified and generate a corresponding event.

        Raises:
            UserError: If email is already verified.
        """
        if self.is_email_verified:
            raise UserError("Email already verified")

        self.is_email_verified = True
        self._events.append(UserEmailVerified(user_id=self.id, email=self.email))

    def assert_can_login(self, password: str) -> None:
        """
        Check if the user can log in with the given password.

        Args:
            password (str): Password to verify.

        Raises:
            UserError: If user is deactivated, email not verified, or password invalid.
        """
        if not self.active:
            raise UserError("User is deactivated")
        if not self.is_email_verified:
            raise UserError("Email is not verified")
        if not verify_password(password, self.password_hash):
            raise UserError("Invalid password")

    def verify_password(self, password: str) -> bool:
        """
        Check if the provided password matches the user's password.

        Args:
            password (str): Password to verify.

        Returns:
            bool: True if password matches, False otherwise.
        """
        return verify_password(password, self.password_hash)

    def change_password(self, old_password: str, new_password: str) -> None:
        """
        Change the user's password after verifying the old password.

        Args:
            old_password (str): Current password.
            new_password (str): New password.

        Raises:
            UserError: If old password is incorrect or new password is same as old.
        """
        if not verify_password(old_password, self.password_hash):
            raise UserError("Wrong old password")
        if old_password == new_password:
            raise UserError("New password cannot be the same as old")

        self.password_hash = validate_hash_password(new_password)
        self._events.append(UserPasswordChanged(user_id=self.id))

    def recover_password(self, new_password: str) -> None:
        """
        Recover the user's password without checking the old one.

        Args:
            new_password (str): New password.
        """
        self.password_hash = validate_hash_password(new_password)
        self._events.append(UserPasswordRecovered(user_id=self.id))

    def activate(self) -> None:
        """
        Activate a deactivated user account and generate an activation event.

        Raises:
            UserError: If account is already active.
        """
        if self.active:
            raise UserError("User account is already active")

        self.active = True
        self._events.append(UserActivated(user_id=self.id))

    def deactivate(self) -> None:
        """
        Deactivate the user account (soft delete) and generate a deactivation event.

        Raises:
            UserError: If account is already deactivated.
        """
        if not self.active:
            raise UserError("User account is already deactivated")

        self.active = False
        self._events.append(UserDeactivated(user_id=self.id))

    def pull_domain_events(self) -> List[BaseEvent]:
        """
        Retrieve and clear the accumulated domain events for this user.

        Returns:
            List[BaseEvent]: List of events generated by this user.
        """
        events = self._events[:]
        self._events.clear()
        return events
