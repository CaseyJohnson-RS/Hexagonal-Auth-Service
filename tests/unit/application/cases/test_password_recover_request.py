import pytest

from app.application.cases.user.password_recover_request import PasswordRecoverRequestCase
from app.application.dto.user import PasswordRecoverRequestInputDTO
from app.application.exceptions.not_found import UserNotFound
from app.core.domain.entities.one_time_token import OneTimeTokenPurpose
from app.core.domain.events.user import UserPasswordRecoverRequested
from app.core.domain.exceptions.user import UserError

from tests.unit.application.cases.conftest import make_user


@pytest.fixture
def case(tx, user_repo, ott_repo, config, event_publisher):
    return PasswordRecoverRequestCase(
        tx=tx,
        user_repo=user_repo,
        ott_repo=ott_repo,
        config=config,
        event_publisher=event_publisher,
    )


def dto(email: str = "test@example.com") -> PasswordRecoverRequestInputDTO:
    return PasswordRecoverRequestInputDTO(email=email)


# ── happy path ────────────────────────────────────────────────────────────────

class TestPasswordRecoverRequestHappyPath:
    async def test_saves_user_and_ott(self, case, user_repo, ott_repo):
        user_repo.get_by_email.return_value = make_user(is_email_verified=True)

        await case.execute(dto())

        user_repo.save.assert_awaited_once()
        ott_repo.save.assert_awaited_once()

    async def test_publishes_password_recover_requested_event(
        self, case, user_repo, event_publisher
    ):
        user_repo.get_by_email.return_value = make_user(is_email_verified=True)

        await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        assert any(isinstance(e, UserPasswordRecoverRequested) for e in events)

    async def test_event_carries_user_email(self, case, user_repo, event_publisher):
        user_repo.get_by_email.return_value = make_user(
            is_email_verified=True, email="alice@example.com"
        )

        await case.execute(dto(email="alice@example.com"))

        events = event_publisher.publish.call_args[0][0]
        event = next(e for e in events if isinstance(e, UserPasswordRecoverRequested))
        assert event.email == "alice@example.com"

    async def test_ott_purpose_is_recover_password(self, case, user_repo, ott_repo):
        user_repo.get_by_email.return_value = make_user(is_email_verified=True)

        await case.execute(dto())

        saved_ott = ott_repo.save.call_args[0][0]
        assert saved_ott.purpose == OneTimeTokenPurpose.RECOVER_PASSWORD


# ── not found ─────────────────────────────────────────────────────────────────

class TestPasswordRecoverRequestNotFound:
    async def test_unknown_email_raises_user_not_found(self, case, user_repo):
        user_repo.get_by_email.return_value = None

        with pytest.raises(UserNotFound):
            await case.execute(dto())

    async def test_nothing_saved_on_not_found(self, case, user_repo, ott_repo):
        user_repo.get_by_email.return_value = None

        with pytest.raises(UserNotFound):
            await case.execute(dto())

        user_repo.save.assert_not_awaited()
        ott_repo.save.assert_not_awaited()


# ── domain errors ─────────────────────────────────────────────────────────────

class TestPasswordRecoverRequestDomainErrors:
    async def test_unverified_user_raises_user_error(self, case, user_repo):
        """user.request_password_recover() guards on is_email_verified.
        The recovery token is sent to the email — sending to an unverified address
        is blocked at the domain level."""
        user_repo.get_by_email.return_value = make_user(is_email_verified=False)

        with pytest.raises(UserError):
            await case.execute(dto())

    async def test_unverified_user_nothing_saved(self, case, user_repo, ott_repo):
        user_repo.get_by_email.return_value = make_user(is_email_verified=False)

        with pytest.raises(UserError):
            await case.execute(dto())

        user_repo.save.assert_not_awaited()
        ott_repo.save.assert_not_awaited()
