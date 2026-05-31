from uuid import UUID

from . import DomainEvent


class UserEvent(DomainEvent):
    """Base user event"""

    user_id: UUID


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserCreated(UserEvent):
    """User account created"""

    email: str


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserActivated(UserEvent):
    """User account activated"""

    pass


class UserDeactivated(UserEvent):
    """User account deactivated"""

    pass


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserEmailVerificationRequested(UserEvent):
    """Email verification token issued"""

    email: str
    token: str


class UserEmailVerified(UserEvent):
    """User email successfully verified"""

    email: str


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserPasswordChanged(UserEvent):
    """User password changed"""

    pass


class UserPasswordRecoverRequested(UserEvent):
    """Password recovery token issued"""

    email: str
    token: str


class UserPasswordRecovered(UserEvent):
    """Password successfully recovered"""

    pass
