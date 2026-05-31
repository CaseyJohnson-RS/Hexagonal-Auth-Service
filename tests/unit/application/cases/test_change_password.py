import pytest
from uuid import uuid4

from app.application.cases.user.change_password import ChangePasswordCase
from app.application.dto.user import ChangePasswordInputDTO
from app.application.exceptions.not_found import UserNotFound
from app.core.domain.events.user import UserPasswordChanged
from app.core.domain.exceptions.user import UserError
from app.core.domain.exceptions.validation import PasswordValidationError

from tests.unit.application.cases.conftest import make_user


@pytest.fixture
def case(tx, user_repo, access_token_verifier, event_publisher):
    return ChangePasswordCase(
        tx=tx,
        user_repo=user_repo,
        access_token_verifier=access_token_verifier,
        event_publisher=event_publisher,
    )


def dto(
    old_password: str = "Password123",
    new_password: str = "NewPassword456",
    access_token: str = "valid.access.token",
) -> ChangePasswordInputDTO:
    return ChangePasswordInputDTO(
        access_token=access_token,
        old_password=old_password,
        new_password=new_password,
    )


# ── happy path ────────────────────────────────────────────────────────────────

class TestChangePasswordHappyPath:
    async def test_saves_user_with_new_password(
        self, case, user_repo, access_token_verifier
    ):
        user = make_user(password="Password123")
        access_token_verifier.verify.return_value = user.id
        user_repo.get_by_id.return_value = user

        await case.execute(dto())

        user_repo.save.assert_awaited_once_with(user)

    async def test_publishes_password_changed_event(
        self, case, user_repo, access_token_verifier, event_publisher
    ):
        user = make_user(password="Password123")
        access_token_verifier.verify.return_value = user.id
        user_repo.get_by_id.return_value = user

        await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        assert any(isinstance(e, UserPasswordChanged) for e in events)

    async def test_user_id_from_token_passed_to_repo(
        self, case, user_repo, access_token_verifier
    ):
        user_id = uuid4()
        user = make_user(password="Password123", user_id=user_id)
        access_token_verifier.verify.return_value = user_id
        user_repo.get_by_id.return_value = user

        await case.execute(dto())

        user_repo.get_by_id.assert_awaited_once_with(user_id)


# ── not found ─────────────────────────────────────────────────────────────────

class TestChangePasswordNotFound:
    async def test_user_not_found_raises(self, case, user_repo, access_token_verifier):
        access_token_verifier.verify.return_value = uuid4()
        user_repo.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            await case.execute(dto())

    async def test_no_save_on_not_found(self, case, user_repo, access_token_verifier):
        access_token_verifier.verify.return_value = uuid4()
        user_repo.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            await case.execute(dto())

        user_repo.save.assert_not_awaited()


# ── domain errors ─────────────────────────────────────────────────────────────

class TestChangePasswordDomainErrors:
    async def test_wrong_old_password_raises_user_error(
        self, case, user_repo, access_token_verifier
    ):
        user = make_user(password="CorrectPassword1")
        access_token_verifier.verify.return_value = user.id
        user_repo.get_by_id.return_value = user

        with pytest.raises(UserError, match="Wrong old password"):
            await case.execute(dto(old_password="WrongPassword1"))

    async def test_same_old_and_new_password_raises_user_error(
        self, case, user_repo, access_token_verifier
    ):
        user = make_user(password="Password123")
        access_token_verifier.verify.return_value = user.id
        user_repo.get_by_id.return_value = user

        with pytest.raises(UserError, match="same as old"):
            await case.execute(dto(old_password="Password123", new_password="Password123"))

    async def test_too_short_new_password_raises_validation_error(
        self, case, user_repo, access_token_verifier
    ):
        user = make_user(password="Password123")
        access_token_verifier.verify.return_value = user.id
        user_repo.get_by_id.return_value = user

        with pytest.raises(PasswordValidationError):
            await case.execute(dto(new_password="short"))

    async def test_no_save_on_domain_error(
        self, case, user_repo, access_token_verifier
    ):
        user = make_user(password="Password123")
        access_token_verifier.verify.return_value = user.id
        user_repo.get_by_id.return_value = user

        with pytest.raises(UserError):
            await case.execute(dto(old_password="WrongPass1"))

        user_repo.save.assert_not_awaited()


# ── token verifier errors ─────────────────────────────────────────────────────

class TestChangePasswordTokenVerifier:
    async def test_invalid_access_token_propagates(
        self, case, access_token_verifier
    ):
        """Any exception from the verifier (expired, tampered) must propagate."""
        from app.core.domain.exceptions.token import InvalidAccessToken
        access_token_verifier.verify.side_effect = InvalidAccessToken()

        with pytest.raises(InvalidAccessToken):
            await case.execute(dto())
