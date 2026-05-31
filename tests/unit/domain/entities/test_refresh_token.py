import pytest
from datetime import timedelta
from uuid import UUID, uuid4

from app.core.domain.entities.refresh_token import RefreshToken
from app.core.domain.events.token import RefreshTokenCreated, RefreshTokenRevoked
from app.core.domain.exceptions.token import RefreshTokenReuse, TokenError
from app.core.utils.security import hash_token
from app.core.utils.time import utc_now


# ── helpers ───────────────────────────────────────────────────────────────────

def make_token(
    *,
    revoked: bool = False,
    replaced_by_id: UUID | None = None,
    expires_in: timedelta = timedelta(hours=24),
    user_id: UUID | None = None,
) -> RefreshToken:
    """Construct a RefreshToken directly, no events emitted."""
    now = utc_now()
    return RefreshToken(
        id=uuid4(),
        user_id=user_id or uuid4(),
        token_hash="fixed-hash-for-tests",
        expires_at=now + expires_in,
        created_at=now,
        revoked_at=now if revoked else None,
        replaced_by_id=replaced_by_id,
    )


# ── RefreshToken.create() ─────────────────────────────────────────────────────

class TestRefreshTokenCreate:
    def test_returns_token_instance_and_raw_string(self):
        token, raw = RefreshToken.create(uuid4(), 32, timedelta(hours=1))

        assert isinstance(token, RefreshToken)
        assert isinstance(raw, str)
        assert len(raw) > 0

    def test_stores_hash_of_raw_token(self):
        token, raw = RefreshToken.create(uuid4(), 32, timedelta(hours=1))

        assert token.token_hash == hash_token(raw)
        assert token.token_hash != raw

    def test_raw_token_is_not_stored_on_entity(self):
        """The plaintext token string must not be kept anywhere on the instance."""
        token, raw = RefreshToken.create(uuid4(), 32, timedelta(hours=1))

        assert not hasattr(token, "token_string")
        assert raw not in vars(token).values()

    def test_two_creates_produce_unique_tokens(self):
        user_id = uuid4()
        _, raw1 = RefreshToken.create(user_id, 32, timedelta(hours=1))
        _, raw2 = RefreshToken.create(user_id, 32, timedelta(hours=1))

        assert raw1 != raw2

    def test_emits_refresh_token_created_event(self):
        user_id = uuid4()
        token, _ = RefreshToken.create(user_id, 32, timedelta(hours=1))
        events = token.pull_domain_events()

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, RefreshTokenCreated)
        assert event.user_id == user_id
        assert event.token_id == token.id

    def test_client_metadata_stored_on_entity(self):
        token, _ = RefreshToken.create(
            uuid4(), 32, timedelta(hours=1),
            location="Berlin", client_ip="1.2.3.4", user_agent="TestClient/1.0",
        )

        assert token.location == "Berlin"
        assert token.client_ip == "1.2.3.4"
        assert token.user_agent == "TestClient/1.0"

    def test_client_metadata_forwarded_to_created_event(self):
        token, _ = RefreshToken.create(
            uuid4(), 32, timedelta(hours=1),
            client_ip="5.6.7.8", user_agent="UA/2",
        )
        event = token.pull_domain_events()[0]

        assert isinstance(event, RefreshTokenCreated)
        assert event.client_ip == "5.6.7.8"
        assert event.user_agent == "UA/2"

    def test_metadata_optional_defaults_to_none(self):
        token, _ = RefreshToken.create(uuid4(), 32, timedelta(hours=1))

        assert token.location is None
        assert token.client_ip is None
        assert token.user_agent is None

    def test_constructor_produces_no_events(self):
        assert make_token().pull_domain_events() == []


# ── use() ─────────────────────────────────────────────────────────────────────

class TestRefreshTokenUse:
    def test_use_valid_token_sets_revoked_at(self):
        token = make_token()
        token.use()

        assert token.revoked_at is not None

    def test_use_emits_revoked_event(self):
        token = make_token()
        token.use()
        events = token.pull_domain_events()

        assert any(isinstance(e, RefreshTokenRevoked) for e in events)

    def test_use_replaced_token_raises_refresh_token_reuse(self):
        """replaced_by_id set → token was already rotated → replay attack."""
        token = make_token(replaced_by_id=uuid4())

        with pytest.raises(RefreshTokenReuse):
            token.use()

    def test_use_revoked_token_raises_token_error(self):
        token = make_token(revoked=True)

        with pytest.raises(TokenError):
            token.use()

    def test_use_expired_token_raises_token_error(self):
        token = make_token(expires_in=timedelta(seconds=-1))

        with pytest.raises(TokenError):
            token.use()

    def test_replaced_check_wins_over_revoked(self):
        """Token is both replaced AND revoked → RefreshTokenReuse, not TokenError.

        The replaced check runs first, which is important: revocation of a
        replaced token should still surface the reuse signal so the caller
        can act on a potential token-theft scenario.
        """
        token = make_token(revoked=True, replaced_by_id=uuid4())

        with pytest.raises(RefreshTokenReuse):
            token.use()

    def test_replaced_check_wins_over_expired(self):
        """Token is both replaced AND expired → RefreshTokenReuse, not TokenError."""
        token = make_token(replaced_by_id=uuid4(), expires_in=timedelta(seconds=-1))

        with pytest.raises(RefreshTokenReuse):
            token.use()

    def test_use_twice_raises_on_second_call(self):
        """After use(), revoked_at is set, so a second use() hits TokenError."""
        token = make_token()
        token.use()

        with pytest.raises(TokenError):
            token.use()


# ── revoke() ──────────────────────────────────────────────────────────────────

class TestRefreshTokenRevoke:
    def test_revoke_valid_token_sets_revoked_at(self):
        token = make_token()
        token.revoke()

        assert token.revoked_at is not None

    def test_revoke_emits_revoked_event(self):
        token = make_token()
        token.revoke()
        events = token.pull_domain_events()

        assert any(isinstance(e, RefreshTokenRevoked) for e in events)

    def test_revoke_already_revoked_raises(self):
        token = make_token(revoked=True)

        with pytest.raises(TokenError):
            token.revoke()

    def test_revoke_expired_token_raises(self):
        """Expired token is treated as invalid — revoking it is not allowed."""
        token = make_token(expires_in=timedelta(seconds=-1))

        with pytest.raises(TokenError):
            token.revoke()

    def test_revoke_replaced_token_succeeds(self):
        """replaced_by_id alone does NOT mark a token revoked/expired.
        We must be able to explicitly revoke a replaced-but-still-active token."""
        token = make_token(replaced_by_id=uuid4())
        token.revoke()  # must not raise

        assert token.revoked_at is not None


# ── mark_as_replaced_by() ─────────────────────────────────────────────────────

class TestMarkAsReplacedBy:
    def test_sets_replaced_by_id(self):
        token = make_token()
        successor_id = uuid4()
        token.mark_as_replaced_by(successor_id)

        assert token.replaced_by_id == successor_id

    def test_raises_if_already_replaced(self):
        token = make_token(replaced_by_id=uuid4())

        with pytest.raises(TokenError):
            token.mark_as_replaced_by(uuid4())

    def test_works_on_revoked_token(self):
        """A revoked token can still be linked to its successor for audit chain."""
        token = make_token(revoked=True)
        new_id = uuid4()
        token.mark_as_replaced_by(new_id)

        assert token.replaced_by_id == new_id

    def test_works_on_expired_token(self):
        """Expiry does not block updating the rotation chain."""
        token = make_token(expires_in=timedelta(seconds=-1))
        new_id = uuid4()
        token.mark_as_replaced_by(new_id)

        assert token.replaced_by_id == new_id

    def test_does_not_emit_any_event(self):
        token = make_token()
        token.mark_as_replaced_by(uuid4())

        assert token.pull_domain_events() == []


# ── is_usable() ───────────────────────────────────────────────────────────────

class TestIsUsable:
    def test_fresh_token_is_usable(self):
        assert make_token().is_usable() is True

    def test_revoked_token_not_usable(self):
        assert make_token(revoked=True).is_usable() is False

    def test_expired_token_not_usable(self):
        assert make_token(expires_in=timedelta(seconds=-1)).is_usable() is False

    def test_replaced_token_not_usable(self):
        assert make_token(replaced_by_id=uuid4()).is_usable() is False

    def test_revoked_and_replaced_not_usable(self):
        assert make_token(revoked=True, replaced_by_id=uuid4()).is_usable() is False


# ── pull_domain_events() ──────────────────────────────────────────────────────

class TestPullDomainEvents:
    def test_clears_events_after_first_pull(self):
        token = make_token()
        token.revoke()

        first = token.pull_domain_events()
        second = token.pull_domain_events()

        assert len(first) == 1
        assert second == []

    def test_events_from_revoke_and_use_are_both_revoked_events(self):
        """use() and revoke() both emit RefreshTokenRevoked."""
        token1 = make_token()
        token1.revoke()
        events1 = token1.pull_domain_events()

        token2 = make_token()
        token2.use()
        events2 = token2.pull_domain_events()

        assert isinstance(events1[0], RefreshTokenRevoked)
        assert isinstance(events2[0], RefreshTokenRevoked)
