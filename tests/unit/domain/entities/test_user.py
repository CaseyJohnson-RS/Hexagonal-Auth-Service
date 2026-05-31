import pytest
from uuid import uuid4

from app.core.domain.entities.user import User
from app.core.domain.events.user import (
    UserActivated,
    UserCreated,
    UserDeactivated,
    UserEmailVerificationRequested,
    UserEmailVerified,
    UserPasswordChanged,
    UserPasswordRecovered,
    UserPasswordRecoverRequested,
)
from app.core.domain.exceptions.user import UserError
from app.core.domain.exceptions.validation import (
    EmailValidationError,
    PasswordValidationError,
)
from app.core.utils.security import hash_password, verify_password
from app.core.utils.time import utc_now


# ── helpers ───────────────────────────────────────────────────────────────────

def make_user(
    *,
    active: bool = True,
    is_email_verified: bool = True,
    password: str = "Password123",
    email: str = "test@example.com",
) -> User:
    """Construct a User directly, bypassing create() — no events emitted."""
    return User(
        id=uuid4(),
        email=email,
        password_hash=hash_password(password),
        active=active,
        is_email_verified=is_email_verified,
        created_at=utc_now(),
    )


# ── User.create() ─────────────────────────────────────────────────────────────

class TestUserCreate:
    def test_new_user_is_active_and_unverified(self):
        user = User.create("user@example.com", "Password123")

        assert user.active is True
        assert user.is_email_verified is False

    def test_email_normalized_to_lowercase_stripped(self):
        user = User.create("  USER@EXAMPLE.COM  ", "Password123")

        assert user.email == "user@example.com"

    def test_password_is_hashed(self):
        user = User.create("user@example.com", "Password123")

        assert user.password_hash != "Password123"
        assert verify_password("Password123", user.password_hash)

    def test_emits_user_created_event(self):
        user = User.create("user@example.com", "Password123")
        events = user.pull_domain_events()

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, UserCreated)
        assert event.user_id == user.id
        assert event.email == "user@example.com"

    def test_two_users_get_different_ids(self):
        u1 = User.create("a@example.com", "Password123")
        u2 = User.create("b@example.com", "Password123")

        assert u1.id != u2.id

    def test_invalid_email_raises_before_any_user_is_built(self):
        with pytest.raises(EmailValidationError):
            User.create("not-an-email", "Password123")

    def test_invalid_password_raises_before_any_user_is_built(self):
        with pytest.raises(PasswordValidationError):
            User.create("user@example.com", "short")

    def test_constructor_produces_no_events(self):
        """Reconstructing a user from the DB via __init__ must not fire events."""
        user = make_user()

        assert user.pull_domain_events() == []


# ── verify_email() ────────────────────────────────────────────────────────────

class TestVerifyEmail:
    def test_sets_is_email_verified_flag(self):
        user = make_user(is_email_verified=False)
        user.verify_email()

        assert user.is_email_verified is True

    def test_emits_user_email_verified_event(self):
        user = make_user(is_email_verified=False)
        user.verify_email()
        events = user.pull_domain_events()

        assert any(isinstance(e, UserEmailVerified) for e in events)

    def test_raises_if_already_verified(self):
        user = make_user(is_email_verified=True)

        with pytest.raises(UserError):
            user.verify_email()

    def test_failed_second_call_emits_no_extra_event(self):
        user = make_user(is_email_verified=False)
        user.verify_email()
        user.pull_domain_events()  # drain

        with pytest.raises(UserError):
            user.verify_email()

        assert user.pull_domain_events() == []


# ── request_email_verification() ─────────────────────────────────────────────

class TestRequestEmailVerification:
    def test_emits_verification_requested_with_token_and_email(self):
        user = make_user(is_email_verified=False)
        user.request_email_verification("tok-abc-123")
        events = user.pull_domain_events()

        event = next(e for e in events if isinstance(e, UserEmailVerificationRequested))
        assert event.token == "tok-abc-123"
        assert event.email == user.email
        assert event.user_id == user.id

    def test_raises_if_email_already_verified(self):
        user = make_user(is_email_verified=True)

        with pytest.raises(UserError):
            user.request_email_verification("tok-abc-123")


# ── request_password_recover() ───────────────────────────────────────────────

class TestRequestPasswordRecover:
    def test_emits_event_for_verified_user(self):
        user = make_user(is_email_verified=True)
        user.request_password_recover("recover-tok")
        events = user.pull_domain_events()

        event = next(e for e in events if isinstance(e, UserPasswordRecoverRequested))
        assert event.token == "recover-tok"
        assert event.email == user.email

    def test_raises_if_email_not_verified(self):
        """Recovery token is sent to the email — sending it unverified makes no sense."""
        user = make_user(is_email_verified=False)

        with pytest.raises(UserError):
            user.request_password_recover("recover-tok")

    def test_deactivated_but_verified_user_can_request_recovery(self):
        """No active-status guard on this method."""
        user = make_user(active=False, is_email_verified=True)
        user.request_password_recover("recover-tok")  # must not raise

        events = user.pull_domain_events()
        assert any(isinstance(e, UserPasswordRecoverRequested) for e in events)


# ── assert_can_login() ────────────────────────────────────────────────────────

class TestAssertCanLogin:
    def test_passes_for_active_verified_correct_password(self):
        user = make_user(active=True, is_email_verified=True, password="Password123")
        user.assert_can_login("Password123")  # must not raise

    def test_deactivated_user_raises_deactivated_error(self):
        user = make_user(active=False, is_email_verified=True)

        with pytest.raises(UserError, match="deactivated"):
            user.assert_can_login("Password123")

    def test_deactivated_hides_email_verification_state(self):
        """Deactivated check comes first — does not expose whether email is verified."""
        user = make_user(active=False, is_email_verified=False)

        with pytest.raises(UserError, match="deactivated"):
            user.assert_can_login("Password123")

    def test_deactivated_hides_password_correctness(self):
        """Deactivated check comes before password check."""
        user = make_user(active=False, is_email_verified=True)

        with pytest.raises(UserError, match="deactivated"):
            user.assert_can_login("wrong-password")

    def test_unverified_email_raises(self):
        user = make_user(active=True, is_email_verified=False)

        with pytest.raises(UserError, match="not verified"):
            user.assert_can_login("Password123")

    def test_wrong_password_raises(self):
        user = make_user(active=True, is_email_verified=True, password="Password123")

        with pytest.raises(UserError, match="Invalid password"):
            user.assert_can_login("WrongPassword")

    def test_newly_created_user_cannot_login(self):
        """User.create() sets is_email_verified=False, so login is blocked."""
        user = User.create("user@example.com", "Password123")

        with pytest.raises(UserError):
            user.assert_can_login("Password123")


# ── verify_password() ─────────────────────────────────────────────────────────

class TestVerifyPasswordMethod:
    def test_correct_password_returns_true(self):
        user = make_user(password="Password123")

        assert user.verify_password("Password123") is True

    def test_wrong_password_returns_false(self):
        user = make_user(password="Password123")

        assert user.verify_password("wrong") is False


# ── change_password() ─────────────────────────────────────────────────────────

class TestChangePassword:
    def test_updates_hash_to_new_password(self):
        user = make_user(password="OldPass123")
        old_hash = user.password_hash
        user.change_password("OldPass123", "NewPass456")

        assert user.password_hash != old_hash
        assert verify_password("NewPass456", user.password_hash)

    def test_emits_password_changed_event(self):
        user = make_user(password="OldPass123")
        user.change_password("OldPass123", "NewPass456")
        events = user.pull_domain_events()

        assert any(isinstance(e, UserPasswordChanged) for e in events)

    def test_raises_on_wrong_old_password(self):
        user = make_user(password="OldPass123")

        with pytest.raises(UserError, match="Wrong old password"):
            user.change_password("DefinitelyWrong", "NewPass456")

    def test_raises_if_new_password_equals_old_plaintext(self):
        user = make_user(password="OldPass123")

        with pytest.raises(UserError, match="same as old"):
            user.change_password("OldPass123", "OldPass123")

    def test_raises_if_new_password_too_short(self):
        """Validation runs after old-password and sameness checks."""
        user = make_user(password="OldPass123")

        with pytest.raises(PasswordValidationError):
            user.change_password("OldPass123", "short")

    def test_wrong_old_password_takes_priority_over_sameness_check(self):
        """If the old password is wrong, we never reach the same-password guard."""
        user = make_user(password="OldPass123")

        with pytest.raises(UserError, match="Wrong old password"):
            user.change_password("BadOld", "BadOld")

    def test_old_hash_not_reused_after_change(self):
        """Verify the old hash is gone — we can't log in with the old password."""
        user = make_user(password="OldPass123")
        user.change_password("OldPass123", "NewPass456")

        assert not verify_password("OldPass123", user.password_hash)


# ── recover_password() ────────────────────────────────────────────────────────

class TestRecoverPassword:
    def test_sets_new_password_without_old_password(self):
        user = make_user(password="OldPass123")
        user.recover_password("NewRecovered1")

        assert verify_password("NewRecovered1", user.password_hash)

    def test_emits_password_recovered_event(self):
        user = make_user(password="OldPass123")
        user.recover_password("NewRecovered1")
        events = user.pull_domain_events()

        assert any(isinstance(e, UserPasswordRecovered) for e in events)

    def test_works_on_deactivated_user(self):
        """No active-status guard — admin recovery path."""
        user = make_user(active=False, password="OldPass123")
        user.recover_password("NewRecovered1")

        assert verify_password("NewRecovered1", user.password_hash)

    def test_works_on_unverified_user(self):
        """No email-verified guard either — token already proves ownership."""
        user = make_user(is_email_verified=False, password="OldPass123")
        user.recover_password("NewRecovered1")

        assert verify_password("NewRecovered1", user.password_hash)

    def test_invalid_new_password_raises(self):
        user = make_user(password="OldPass123")

        with pytest.raises(PasswordValidationError):
            user.recover_password("short")


# ── activate() / deactivate() ─────────────────────────────────────────────────

class TestActivateDeactivate:
    def test_deactivate_clears_active_flag(self):
        user = make_user(active=True)
        user.deactivate()

        assert user.active is False

    def test_deactivate_emits_deactivated_event(self):
        user = make_user(active=True)
        user.deactivate()
        events = user.pull_domain_events()

        assert any(isinstance(e, UserDeactivated) for e in events)

    def test_activate_sets_active_flag(self):
        user = make_user(active=False)
        user.activate()

        assert user.active is True

    def test_activate_emits_activated_event(self):
        user = make_user(active=False)
        user.activate()
        events = user.pull_domain_events()

        assert any(isinstance(e, UserActivated) for e in events)

    def test_deactivate_already_inactive_raises(self):
        user = make_user(active=False)

        with pytest.raises(UserError):
            user.deactivate()

    def test_activate_already_active_raises(self):
        user = make_user(active=True)

        with pytest.raises(UserError):
            user.activate()

    def test_deactivate_then_activate_cycle(self):
        user = make_user(active=True)
        user.deactivate()
        user.activate()

        assert user.active is True

    def test_deactivated_user_cannot_login(self):
        user = make_user(active=True, is_email_verified=True, password="Password123")
        user.deactivate()

        with pytest.raises(UserError, match="deactivated"):
            user.assert_can_login("Password123")


# ── pull_domain_events() ──────────────────────────────────────────────────────

class TestPullDomainEvents:
    def test_returns_empty_list_when_no_events(self):
        user = make_user()

        assert user.pull_domain_events() == []

    def test_clears_events_on_first_pull(self):
        user = make_user(is_email_verified=False)
        user.verify_email()

        first = user.pull_domain_events()
        second = user.pull_domain_events()

        assert len(first) == 1
        assert second == []

    def test_returned_list_is_a_copy(self):
        """Mutating the returned list does not affect internal event state."""
        user = make_user(is_email_verified=False)
        user.verify_email()

        pulled = user.pull_domain_events()
        pulled.append("injected_garbage")

        # Internal list was already cleared by pull — nothing to leak back
        assert user.pull_domain_events() == []

    def test_events_accumulate_in_order(self):
        user = make_user(is_email_verified=False, active=True)
        user.verify_email()
        user.deactivate()
        events = user.pull_domain_events()

        assert len(events) == 2
        assert isinstance(events[0], UserEmailVerified)
        assert isinstance(events[1], UserDeactivated)

    def test_multiple_pulls_do_not_accumulate_across_calls(self):
        user = make_user(active=True)
        user.deactivate()
        user.pull_domain_events()  # first pull, drains

        user.activate()
        second_pull = user.pull_domain_events()

        assert len(second_pull) == 1
        assert isinstance(second_pull[0], UserActivated)
