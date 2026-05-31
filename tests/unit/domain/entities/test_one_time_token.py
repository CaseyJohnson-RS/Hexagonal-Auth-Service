import pytest
from datetime import timedelta
from uuid import uuid4

from app.core.domain.entities.one_time_token import OneTimeToken, OneTimeTokenPurpose
from app.core.domain.exceptions.token import TokenError
from app.core.utils.security import hash_token
from app.core.utils.time import utc_now


# ── helpers ───────────────────────────────────────────────────────────────────

VERIFY = OneTimeTokenPurpose.VERIFY_EMAIL
RECOVER = OneTimeTokenPurpose.RECOVER_PASSWORD


def make_ott(
    *,
    purpose: OneTimeTokenPurpose = VERIFY,
    used: bool = False,
    expires_in: timedelta = timedelta(hours=1),
) -> OneTimeToken:
    """Construct a OneTimeToken directly."""
    now = utc_now()
    return OneTimeToken(
        id=uuid4(),
        user_id=uuid4(),
        token_hash="fixed-hash-for-tests",
        expires_at=now + expires_in,
        purpose=purpose,
        used=used,
    )


# ── OneTimeToken.create() ─────────────────────────────────────────────────────

class TestOneTimeTokenCreate:
    def test_returns_token_and_raw_string(self):
        token, raw = OneTimeToken.create(uuid4(), 32, timedelta(hours=1), VERIFY)

        assert isinstance(token, OneTimeToken)
        assert isinstance(raw, str)
        assert len(raw) > 0

    def test_stores_hash_of_raw_token(self):
        token, raw = OneTimeToken.create(uuid4(), 32, timedelta(hours=1), VERIFY)

        assert token.token_hash == hash_token(raw)
        assert token.token_hash != raw

    def test_token_is_unused_on_creation(self):
        token, _ = OneTimeToken.create(uuid4(), 32, timedelta(hours=1), VERIFY)

        assert token.used is False

    def test_purpose_stored_correctly(self):
        verify_token, _ = OneTimeToken.create(uuid4(), 32, timedelta(hours=1), VERIFY)
        recover_token, _ = OneTimeToken.create(uuid4(), 32, timedelta(hours=1), RECOVER)

        assert verify_token.purpose == VERIFY
        assert recover_token.purpose == RECOVER

    def test_has_no_domain_events_mechanism(self):
        """OneTimeToken deliberately has no event tracking, unlike User/RefreshToken."""
        token, _ = OneTimeToken.create(uuid4(), 32, timedelta(hours=1), VERIFY)

        assert not hasattr(token, "pull_domain_events")
        assert not hasattr(token, "_events")


# ── use() ─────────────────────────────────────────────────────────────────────

class TestOneTimeTokenUse:
    def test_correct_purpose_marks_token_used(self):
        token = make_ott(purpose=VERIFY)
        token.use(VERIFY)

        assert token.used is True

    def test_use_twice_with_correct_purpose_raises(self):
        token = make_ott(purpose=VERIFY)
        token.use(VERIFY)

        with pytest.raises(TokenError, match="Cannot use invalid token"):
            token.use(VERIFY)

    def test_wrong_purpose_raises_purpose_mismatch(self):
        token = make_ott(purpose=VERIFY)

        with pytest.raises(TokenError, match="purpose mismatch"):
            token.use(RECOVER)

    def test_purpose_check_runs_before_expiry_check(self):
        """An expired token with the wrong purpose exposes purpose_mismatch, not
        an expiry error. The purpose check comes first in use(), which means the
        error message doesn't reveal that the token is also expired."""
        token = make_ott(purpose=VERIFY, expires_in=timedelta(seconds=-1))

        with pytest.raises(TokenError, match="purpose mismatch"):
            token.use(RECOVER)

    def test_purpose_check_runs_before_used_check(self):
        """An already-used token with the wrong purpose → purpose mismatch."""
        token = make_ott(purpose=VERIFY, used=True)

        with pytest.raises(TokenError, match="purpose mismatch"):
            token.use(RECOVER)

    def test_expired_token_correct_purpose_raises_invalid(self):
        token = make_ott(purpose=VERIFY, expires_in=timedelta(seconds=-1))

        with pytest.raises(TokenError, match="Cannot use invalid token"):
            token.use(VERIFY)

    def test_already_used_correct_purpose_raises_invalid(self):
        token = make_ott(purpose=VERIFY, used=True)

        with pytest.raises(TokenError, match="Cannot use invalid token"):
            token.use(VERIFY)

    def test_verify_email_token_cannot_be_used_as_recover_password(self):
        """Cross-purpose usage must always fail — tokens are not interchangeable."""
        token = make_ott(purpose=VERIFY)
        token.use(VERIFY)  # valid first use

        fresh_token = make_ott(purpose=RECOVER)
        with pytest.raises(TokenError, match="purpose mismatch"):
            fresh_token.use(VERIFY)

    def test_recover_password_token_cannot_be_used_for_email_verification(self):
        token = make_ott(purpose=RECOVER)

        with pytest.raises(TokenError, match="purpose mismatch"):
            token.use(VERIFY)


# ── is_usable() ───────────────────────────────────────────────────────────────

class TestIsUsable:
    def test_fresh_unused_valid_token_is_usable(self):
        assert make_ott().is_usable() is True

    def test_used_token_not_usable(self):
        assert make_ott(used=True).is_usable() is False

    def test_expired_token_not_usable(self):
        assert make_ott(expires_in=timedelta(seconds=-1)).is_usable() is False

    def test_used_and_expired_not_usable(self):
        assert make_ott(used=True, expires_in=timedelta(seconds=-1)).is_usable() is False

    def test_token_valid_at_boundary_just_before_expiry(self):
        """Token created with future expiry is immediately usable."""
        token = make_ott(expires_in=timedelta(seconds=30))

        assert token.is_usable() is True


# ── purpose enum ─────────────────────────────────────────────────────────────

class TestOneTimeTokenPurpose:
    def test_enum_values_are_strings(self):
        assert OneTimeTokenPurpose.VERIFY_EMAIL.value == "verify_email"
        assert OneTimeTokenPurpose.RECOVER_PASSWORD.value == "recover_password"

    def test_purposes_are_not_equal_to_each_other(self):
        assert VERIFY != RECOVER
