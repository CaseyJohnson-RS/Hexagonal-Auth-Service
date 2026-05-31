import pytest

from app.core.domain.validators.email import validate_email
from app.core.domain.exceptions.validation import EmailValidationError


# ── required guard ───────────────────────────────────────────────────────────

class TestEmailRequired:
    def test_none_raises_required(self):
        with pytest.raises(EmailValidationError, match="required"):
            validate_email(None)

    def test_empty_string_raises_required(self):
        with pytest.raises(EmailValidationError, match="required"):
            validate_email("")

    def test_non_string_raises_type_error(self):
        with pytest.raises(EmailValidationError, match="string"):
            validate_email(42)

    def test_zero_raises_type_error_not_required(self):
        """int 0 is not None and not '', so it hits the isinstance check."""
        with pytest.raises(EmailValidationError, match="string"):
            validate_email(0)

    def test_whitespace_only_raises_format_error_not_required(self):
        """'   ' passes the None/''/isinstance guards but strips to '', fails regex.
        The error message says 'Invalid email format', not 'required'."""
        with pytest.raises(EmailValidationError, match="Invalid email format"):
            validate_email("   ")


# ── normalisation ────────────────────────────────────────────────────────────

class TestEmailNormalisation:
    def test_strips_surrounding_whitespace(self):
        assert validate_email("  user@example.com  ") == "user@example.com"

    def test_converts_to_lowercase(self):
        assert validate_email("USER@EXAMPLE.COM") == "user@example.com"

    def test_strips_and_lowercases_together(self):
        assert validate_email("  USER@EXAMPLE.COM  ") == "user@example.com"

    def test_already_normalised_unchanged(self):
        assert validate_email("user@example.com") == "user@example.com"


# ── valid formats ────────────────────────────────────────────────────────────

class TestValidEmailFormats:
    def test_standard_address(self):
        assert validate_email("user@example.com") == "user@example.com"

    def test_subdomain(self):
        assert validate_email("user@mail.example.com") == "user@mail.example.com"

    def test_multiple_subdomains(self):
        assert validate_email("u@a.b.c.d") == "u@a.b.c.d"

    def test_minimal_valid_address(self):
        assert validate_email("a@b.c") == "a@b.c"

    def test_plus_sign_in_local_part(self):
        assert validate_email("user+tag@example.com") == "user+tag@example.com"

    def test_dots_in_local_part(self):
        assert validate_email("first.last@example.com") == "first.last@example.com"

    def test_hyphen_in_domain(self):
        assert validate_email("user@my-company.com") == "user@my-company.com"


# ── invalid formats ──────────────────────────────────────────────────────────

class TestInvalidEmailFormats:
    def test_missing_at_sign(self):
        with pytest.raises(EmailValidationError):
            validate_email("userexample.com")

    def test_missing_local_part(self):
        with pytest.raises(EmailValidationError):
            validate_email("@example.com")

    def test_missing_domain(self):
        with pytest.raises(EmailValidationError):
            validate_email("user@")

    def test_missing_dot_in_domain(self):
        """Regex requires at least one dot after the @."""
        with pytest.raises(EmailValidationError):
            validate_email("user@example")

    def test_domain_starts_with_dot(self):
        """No characters before the last dot in domain → regex fails."""
        with pytest.raises(EmailValidationError):
            validate_email("user@.com")

    def test_multiple_at_signs(self):
        """Second @ is a non-@ char only in the local part; the domain
        part starts with @ which violates [^@]+."""
        with pytest.raises(EmailValidationError):
            validate_email("user@@example.com")

    def test_at_sign_only(self):
        with pytest.raises(EmailValidationError):
            validate_email("@")
