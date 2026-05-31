from uuid import UUID

from . import DomainEvent, NotificationEvent


class UserEvent(DomainEvent):
    """Base audit event for user actions."""

    user_id: UUID


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserCreated(UserEvent):
    """User account created."""

    email: str


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserActivated(UserEvent):
    """User account activated."""

    pass


class UserDeactivated(UserEvent):
    """User account deactivated."""

    pass


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserEmailVerified(UserEvent):
    """User email successfully verified."""

    email: str


class UserPasswordChanged(UserEvent):
    """User password changed."""

    pass


class UserPasswordRecovered(UserEvent):
    """Password successfully recovered."""

    pass


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserEmailVerificationRequested(NotificationEvent):
    """Email verification token issued."""

    user_id: UUID
    email: str
    token: str


class UserPasswordRecoverRequested(NotificationEvent):
    """Password recovery token issued."""

    user_id: UUID
    email: str
    token: str
