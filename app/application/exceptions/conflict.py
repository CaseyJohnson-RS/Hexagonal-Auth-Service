from . import ApplicationError


class UserAlreadyExists(ApplicationError):
    message = "User already exists"
