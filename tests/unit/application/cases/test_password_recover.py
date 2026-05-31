import pytest

from app.application.cases.user.password_recover import PasswordRecoverCase
from app.application.dto.user import PasswordRecoverInputDTO
from app.application.exceptions.not_found import OneTimeTokenNotFound, UserNotFound
from app.core.domain.entities.one_time_token import OneTimeTokenPurpose
from app.core.domain.events.user import UserPasswordRecovered
from app.core.domain.exceptions.validation import PasswordValidationError

from tests.unit.application.cases.conftest import make_ott, make_user


@pytest.fixture
def case(tx, user_repo, ott_repo, event_publisher):
    return PasswordRecoverCase(
        tx=tx,
        user_repo=user_repo,
        ott_repo=ott_repo,
        event_publisher=event_publisher,
    )


def dto(
    recover_token: str = "recover-token",
    password: str = "NewPassword456",
) -> PasswordRecoverInputDTO:
    return PasswordRecoverInputDTO(
        password_recover_token=recover_token,
        password=password,
    )


# ── happy path ────────────────────────────────────────────────────────────────

class TestPasswordRecoverHappyPath:
    async def test_user_password_is_updated(self, case, ott_repo, user_repo):
        from app.core.utils.security import verify_password
        user = make_user(password="OldPassword1")
        ott = make_ott(
            user_id=user.id, purpose=OneTimeTokenPurpose.RECOVER_PASSWORD
        )
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        await case.execute(dto(password="NewPassword456"))

        assert verify_password("NewPassword456", user.password_hash)

    async def test_saves_user_and_ott(self, case, ott_repo, user_repo):
        user = make_user()
        ott = make_ott(user_id=user.id, purpose=OneTimeTokenPurpose.RECOVER_PASSWORD)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        await case.execute(dto())

        user_repo.save.assert_awaited_once()
        ott_repo.save.assert_awaited_once()

    async def test_publishes_password_recovered_event(
        self, case, ott_repo, user_repo, event_publisher
    ):
        user = make_user()
        ott = make_ott(user_id=user.id, purpose=OneTimeTokenPurpose.RECOVER_PASSWORD)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        assert any(isinstance(e, UserPasswordRecovered) for e in events)

    async def test_ott_is_not_consumed(self, case, ott_repo, user_repo):
        user = make_user()
        ott = make_ott(user_id=user.id, purpose=OneTimeTokenPurpose.RECOVER_PASSWORD)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        await case.execute(dto())

        assert ott.used is True


# ── not found ─────────────────────────────────────────────────────────────────

class TestPasswordRecoverNotFound:
    async def test_unknown_token_raises(self, case, ott_repo):
        ott_repo.get_by_string.return_value = None

        with pytest.raises(OneTimeTokenNotFound):
            await case.execute(dto())

    async def test_orphan_token_no_user_raises(self, case, ott_repo, user_repo):
        ott = make_ott(purpose=OneTimeTokenPurpose.RECOVER_PASSWORD)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            await case.execute(dto())

    async def test_nothing_saved_on_token_not_found(self, case, ott_repo, user_repo):
        ott_repo.get_by_string.return_value = None

        with pytest.raises(OneTimeTokenNotFound):
            await case.execute(dto())

        user_repo.save.assert_not_awaited()
        ott_repo.save.assert_not_awaited()


# ── domain errors ─────────────────────────────────────────────────────────────

class TestPasswordRecoverDomainErrors:
    async def test_invalid_new_password_raises_validation_error(
        self, case, ott_repo, user_repo
    ):
        user = make_user()
        ott = make_ott(user_id=user.id, purpose=OneTimeTokenPurpose.RECOVER_PASSWORD)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        with pytest.raises(PasswordValidationError):
            await case.execute(dto(password="short"))

    async def test_no_save_on_invalid_password(
        self, case, ott_repo, user_repo
    ):
        user = make_user()
        ott = make_ott(user_id=user.id, purpose=OneTimeTokenPurpose.RECOVER_PASSWORD)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        with pytest.raises(PasswordValidationError):
            await case.execute(dto(password="short"))

        user_repo.save.assert_not_awaited()
