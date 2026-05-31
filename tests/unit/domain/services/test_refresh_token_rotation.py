from datetime import timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from app.core.domain.entities.refresh_token import RefreshToken
from app.core.domain.services.refresh_token_rotation import RefreshTokenRotationService
from app.core.utils.time import utc_now


def make_old_token(user_id=None):
    now = utc_now()
    return RefreshToken(
        id=uuid4(),
        user_id=user_id or uuid4(),
        token_hash="old-hash",
        expires_at=now + timedelta(days=1),
        created_at=now,
    )


def fake_issuer(return_value: str = "new.access.jwt"):
    mock = MagicMock()
    mock.issue = MagicMock(return_value=return_value)
    return mock


def rotate(old_token, issuer=None):
    return RefreshTokenRotationService.rotate(
        old_token=old_token,
        refresh_token_length=32,
        refresh_token_expiry=timedelta(days=14),
        access_token_expiry=timedelta(minutes=15),
        access_token_issuer=issuer or fake_issuer(),
    )


# ── return values ─────────────────────────────────────────────────────────────

class TestRotationReturnValues:
    def test_returns_new_refresh_token_raw_string_access_token(self):
        old = make_old_token()
        new_rt, new_rt_str, access_token = rotate(old)

        assert isinstance(new_rt, RefreshToken)
        assert isinstance(new_rt_str, str) and len(new_rt_str) > 0
        assert isinstance(access_token, str) and len(access_token) > 0

    def test_new_refresh_token_belongs_to_same_user(self):
        user_id = uuid4()
        old = make_old_token(user_id=user_id)
        new_rt, _, _ = rotate(old)

        assert new_rt.user_id == user_id

    def test_new_and_old_tokens_have_different_ids(self):
        old = make_old_token()
        new_rt, _, _ = rotate(old)

        assert new_rt.id != old.id

    def test_access_token_comes_from_issuer(self):
        old = make_old_token()
        issuer = fake_issuer(return_value="custom.access.token")
        _, _, access_token = rotate(old, issuer=issuer)

        assert access_token == "custom.access.token"
        issuer.issue.assert_called_once_with(old.user_id, timedelta(minutes=15))


# ── old token state after rotation ───────────────────────────────────────────

class TestOldTokenAfterRotation:
    def test_old_token_replaced_by_id_is_set(self):
        old = make_old_token()
        rotate(old)

        assert old.replaced_by_id is not None

    def test_old_token_replaced_by_id_points_to_itself_not_new_token(self):
        old = make_old_token()
        new_rt, _, _ = rotate(old)

        assert old.replaced_by_id == new_rt.id

    def test_old_token_not_yet_revoked_by_rotation_service(self):
        """The rotation service only calls mark_as_replaced_by, not revoke().
        Revocation (revoked_at) is set by use() in the use case before rotate()."""
        old = make_old_token()
        rotate(old)

        assert old.revoked_at is None


# ── new token state ───────────────────────────────────────────────────────────

class TestNewTokenAfterRotation:
    def test_new_token_is_usable(self):
        old = make_old_token()
        new_rt, _, _ = rotate(old)

        assert new_rt.is_usable() is True

    def test_new_token_emits_created_event(self):
        from app.core.domain.events.token import RefreshTokenCreated
        old = make_old_token()
        new_rt, _, _ = rotate(old)

        events = new_rt.pull_domain_events()
        assert any(isinstance(e, RefreshTokenCreated) for e in events)
