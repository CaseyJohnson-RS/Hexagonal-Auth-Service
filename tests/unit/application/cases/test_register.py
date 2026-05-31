import pytest
from unittest.mock import AsyncMock, call

from app.application.cases.user.register import RegisterUserCase
from app.application.dto.user import RegisterUserInputDTO
from app.application.exceptions.conflict import UserAlreadyExists
from app.core.domain.events.user import UserCreated, UserEmailVerificationRequested
from app.core.domain.exceptions.validation import EmailValidationError, PasswordValidationError

from tests.unit.application.cases.conftest import make_user


@pytest.fixture
def case(tx, user_repo, ott_repo, config, event_publisher):
    return RegisterUserCase(
        tx=tx,
        user_repo=user_repo,
        ott_repo=ott_repo,
        config=config,
        event_publisher=event_publisher,
    )


def dto(email="new@example.com", password="Password123") -> RegisterUserInputDTO:
    return RegisterUserInputDTO(email=email, password=password)


# ── happy path: new user ──────────────────────────────────────────────────────

class TestRegisterNewUser:
    async def test_saves_user_and_ott(self, case, user_repo, ott_repo):
        await case.execute(dto())

        user_repo.save.assert_awaited_once()
        ott_repo.save.assert_awaited_once()

    async def test_publishes_created_and_verification_events(
        self, case, event_publisher
    ):
        await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        types = {type(e) for e in events}
        assert UserCreated in types
        assert UserEmailVerificationRequested in types

    async def test_published_events_carry_correct_email(self, case, event_publisher):
        await case.execute(dto(email="bob@example.com"))

        events = event_publisher.publish.call_args[0][0]
        created = next(e for e in events if isinstance(e, UserCreated))
        assert created.email == "bob@example.com"

    async def test_events_published_after_saves(self, case, user_repo, ott_repo, event_publisher):
        """Transaction discipline: persistence must complete before event dispatch."""
        order = []
        user_repo.save.side_effect = lambda _: order.append("user_save") or None
        ott_repo.save.side_effect = lambda _: order.append("ott_save") or None
        event_publisher.publish.side_effect = lambda _: order.append("publish") or None

        await case.execute(dto())

        assert order.index("user_save") < order.index("publish")
        assert order.index("ott_save") < order.index("publish")


# ── re-registration: existing unverified user ─────────────────────────────────

class TestRegisterExistingUnverifiedUser:
    async def test_does_not_raise(self, case, user_repo):
        user_repo.get_by_email.return_value = make_user(is_email_verified=False)
        await case.execute(dto())  # must not raise

    async def test_does_not_emit_user_created_event(self, case, user_repo, event_publisher):
        """Existing user is reused — no second UserCreated event should be published."""
        user_repo.get_by_email.return_value = make_user(is_email_verified=False)

        await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        assert not any(isinstance(e, UserCreated) for e in events)

    async def test_emits_verification_requested_event(self, case, user_repo, event_publisher):
        user_repo.get_by_email.return_value = make_user(is_email_verified=False)

        await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        assert any(isinstance(e, UserEmailVerificationRequested) for e in events)

    async def test_saves_existing_user_and_new_ott(self, case, user_repo, ott_repo):
        existing = make_user(is_email_verified=False)
        user_repo.get_by_email.return_value = existing

        await case.execute(dto())

        saved_user = user_repo.save.call_args[0][0]
        assert saved_user is existing
        ott_repo.save.assert_awaited_once()


# ── conflict: verified user already exists ────────────────────────────────────

class TestRegisterVerifiedUserConflict:
    async def test_raises_user_already_exists(self, case, user_repo):
        user_repo.get_by_email.return_value = make_user(is_email_verified=True)

        with pytest.raises(UserAlreadyExists):
            await case.execute(dto())

    async def test_nothing_saved_on_conflict(self, case, user_repo, ott_repo):
        user_repo.get_by_email.return_value = make_user(is_email_verified=True)

        with pytest.raises(UserAlreadyExists):
            await case.execute(dto())

        user_repo.save.assert_not_awaited()
        ott_repo.save.assert_not_awaited()

    async def test_no_events_published_on_conflict(self, case, user_repo, event_publisher):
        user_repo.get_by_email.return_value = make_user(is_email_verified=True)

        with pytest.raises(UserAlreadyExists):
            await case.execute(dto())

        event_publisher.publish.assert_not_awaited()


# ── domain validation propagation ─────────────────────────────────────────────

class TestRegisterDomainValidation:
    async def test_invalid_email_raises_validation_error(self, case):
        with pytest.raises(EmailValidationError):
            await case.execute(dto(email="not-an-email"))

    async def test_too_short_password_raises_validation_error(self, case):
        with pytest.raises(PasswordValidationError):
            await case.execute(dto(password="short"))
