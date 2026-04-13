from uuid import UUID

from . import DomainEvent


class UserEvent(DomainEvent):
    """Событие пользователя"""

    user_id: UUID


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserCreated(UserEvent):
    """Произошло создание пользователя"""

    email: str


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserActivated(UserEvent):
    """Активация пользователя"""

    pass


class UserDeactivated(UserEvent):
    """Деактивация пользователя"""

    pass


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserEmailVerificationRequested(UserEvent):
    """Создан токен для подтверждения почты"""

    email: str
    token: str


class UserEmailVerified(UserEvent):
    """Почта пользователя успешно подтверждена"""

    email: str


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class UserPasswordChanged(UserEvent):
    """Пользователь сменил пароль"""

    pass


class UserPasswordRecoverRequested(UserEvent):
    """Создан токен для восстанвления пароля"""

    email: str
    token: str


class UserPasswordRecovered(UserEvent):
    """Пароль восстановлен"""

    pass