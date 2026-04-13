import re
from app.core.domain.exceptions.validation import EmailValidationError

_EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")


def validate_email(email: str) -> str:
    """
    Валидатор email для домена.

    - Возвращает очищенный (strip + lower) email
    - Бросает исключения EmailValidationError
    """
    if email is None or email == "":
        raise EmailValidationError("Email is required")

    if not isinstance(email, str):
        raise EmailValidationError("Email must be a string")

    email = email.strip().lower()
    if not _EMAIL_REGEX.fullmatch(email):
        raise EmailValidationError(f"Invalid email format: '{email}'")

    return email
