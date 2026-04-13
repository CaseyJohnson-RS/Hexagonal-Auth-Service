from . import ApplicationError


class UserNotFound(ApplicationError):
    message = "User not found"


class OneTimeTokenNotFound(ApplicationError):
    message = "One time token not found"


class RefreshTokenNotFound(ApplicationError):
    message = "Refresh token not found"
