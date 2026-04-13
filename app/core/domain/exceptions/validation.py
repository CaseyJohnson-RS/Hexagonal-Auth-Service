from . import DomainError


class EmailValidationError(DomainError):
    message = "Email validation error"


class PasswordValidationError(DomainError):
    message = "Password validation error"
