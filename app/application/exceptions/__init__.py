from app.core.domain.exceptions import BaseError


class ApplicationError(BaseError):
    message = "Application error"
