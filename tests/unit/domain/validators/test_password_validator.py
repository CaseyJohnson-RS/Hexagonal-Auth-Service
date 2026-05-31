import pytest

from app.core.domain.validators.password import (
    max_password_len,
    min_password_len,
    validate_password,
)
from app.core.domain.exceptions.validation import PasswordValidationError


# ── type check ────────────────────────────────────────────────────────────────

class TestPasswordTypeCheck:
    def test_non_string_raises(self):
        with pytest.raises(PasswordValidationError, match="string"):
            validate_password(12345678)

    def test_none_raises(self):
        with pytest.raises(PasswordValidationError, match="string"):
            validate_password(None)

    def test_list_raises(self):
        with pytest.raises(PasswordValidationError, match="string"):
            validate_password(["password"])

    def test_bytes_raises(self):
        with pytest.raises(PasswordValidationError, match="string"):
            validate_password(b"password")


# ── length boundary conditions ────────────────────────────────────────────────

class TestPasswordLength:
    def test_exactly_min_length_is_valid(self):
        pw = "a" * min_password_len
        assert validate_password(pw) == pw

    def test_one_below_min_raises(self):
        with pytest.raises(PasswordValidationError, match="at least"):
            validate_password("a" * (min_password_len - 1))

    def test_exactly_max_length_is_valid(self):
        pw = "a" * max_password_len
        assert validate_password(pw) == pw

    def test_one_above_max_raises(self):
        with pytest.raises(PasswordValidationError, match="exceed"):
            validate_password("a" * (max_password_len + 1))

    def test_length_between_boundaries_is_valid(self):
        pw = "a" * (min_password_len + 10)
        assert validate_password(pw) == pw


# ── strip behaviour ───────────────────────────────────────────────────────────

class TestPasswordStripping:
    def test_strips_surrounding_whitespace_before_length_check(self):
        """'  abc  ' strips to 'abc' (3 chars) — below minimum, not 7."""
        with pytest.raises(PasswordValidationError, match="at least"):
            validate_password("  abc  ")

    def test_all_spaces_raises(self):
        """min_password_len spaces strip to empty string — below minimum."""
        with pytest.raises(PasswordValidationError):
            validate_password(" " * min_password_len)

    def test_valid_password_with_padding_returns_stripped(self):
        padded = "  Password1  "
        result = validate_password(padded)
        assert result == "Password1"

    def test_padding_does_not_inflate_effective_length(self):
        """7 real chars + 2 spaces = 9 total, but strips to 7 → below min."""
        short_with_spaces = " " + "a" * (min_password_len - 1) + " "
        with pytest.raises(PasswordValidationError, match="at least"):
            validate_password(short_with_spaces)

    def test_no_whitespace_password_returned_unchanged(self):
        pw = "Password123"
        assert validate_password(pw) == pw


# ── return value ─────────────────────────────────────────────────────────────

class TestPasswordReturnValue:
    def test_returns_stripped_password_not_original(self):
        result = validate_password("  Password123  ")
        assert result == "Password123"

    def test_returns_password_string_not_hash(self):
        """validate_password is the validator; validate_hash_password does the hash."""
        result = validate_password("Password123")
        assert result == "Password123"


# ── unicode ───────────────────────────────────────────────────────────────────

class TestPasswordUnicode:
    def test_unicode_chars_counted_as_code_points_not_bytes(self):
        """'пароль12' is 8 Unicode code points — meets minimum length."""
        pw = "пароль12"  # 8 chars, each 2 bytes in UTF-8
        assert validate_password(pw) == pw

    def test_unicode_below_min_raises(self):
        pw = "пасс"  # 4 Unicode chars — below minimum
        with pytest.raises(PasswordValidationError, match="at least"):
            validate_password(pw)
