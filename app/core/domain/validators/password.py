from app.core.domain.exceptions.validation import PasswordValidationError
from app.core.utils.security import hash_password

min_password_len = 8
max_password_len = 255


def validate_password(password: str) -> str:
    """
    Валидатор пароля для домена.

    - Проверяет длину пароля
    - Возвращает пароль
    - Бросает исключение PasswordValidationError
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

    # TODO: добавить проверку сложности пароля (цифры, символы, регистр и т.д.)

    return password


def validate_hash_password(password: str) -> str:
    """
    Валидатор пароля для домена.

    - Проверяет длину пароля
    - Возвращает хэш пароля
    - Бросает исключение PasswordValidationError
    """
    return hash_password(validate_password(password))
