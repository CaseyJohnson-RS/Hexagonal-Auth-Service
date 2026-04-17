from app.core.domain.exceptions.validation import PasswordValidationError
from app.core.utils.security import hash_password

min_password_len = 8
max_password_len = 255


def validate_password(password: str) -> str:
    """
    Domain password validator.

    - Checks password length
    - Returns the validated password
    - Raises PasswordValidationError on failure
    """
    if not isinstance(password, str):
        raise PasswordValidationError("Password must be a string")

    password = password.strip()

    if len(password) < min_password_len:
        raise PasswordValidationError(
            f"Password must be at least {min_password_len} characters"
        )

    if len(password) > max_password_len:
        raise PasswordValidationError(
            f"Password must not exceed {max_password_len} characters"
        )

    # TODO: add password complexity checks (digits, symbols, mixed case, etc.)

    return password


def validate_hash_password(password: str) -> str:
    """
    Domain password validator that returns a hash.

    - Checks password length
    - Returns the hashed password
    - Raises PasswordValidationError on failure
    """
    return hash_password(validate_password(password))
