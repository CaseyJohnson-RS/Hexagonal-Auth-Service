from app.core.domain.exceptions import DomainError


class UserError(DomainError):
    message = "User error"
