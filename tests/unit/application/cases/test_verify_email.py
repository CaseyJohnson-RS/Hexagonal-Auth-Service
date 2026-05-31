import pytest
from uuid import uuid4

from app.application.cases.user.verify_email import VerifyEmailCase
from app.application.dto.user import VerifyEmailInputDTO
from app.application.exceptions.not_found import OneTimeTokenNotFound, UserNotFound
from app.core.domain.entities.one_time_token import OneTimeTokenPurpose
from app.core.domain.events.user import UserEmailVerified
from app.core.domain.exceptions.token import TokenError
from app.core.domain.exceptions.user import UserError

from tests.unit.application.cases.conftest import make_ott, make_user


@pytest.fixture
def case(tx, user_repo, ott_repo, event_publisher):
    return VerifyEmailCase(
        tx=tx,
        user_repo=user_repo,
        ott_repo=ott_repo,
        event_publisher=event_publisher,
    )


def dto(token: str = "valid-token") -> VerifyEmailInputDTO:
    return VerifyEmailInputDTO(one_time_token=token)


# ── happy path ────────────────────────────────────────────────────────────────

class TestVerifyEmailHappyPath:
    async def test_marks_user_email_verified(self, case, ott_repo, user_repo):
        user = make_user(is_email_verified=False)
        ott = make_ott(user_id=user.id, purpose=OneTimeTokenPurpose.VERIFY_EMAIL)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        await case.execute(dto())

        assert user.is_email_verified is True

    async def test_ott_is_consumed(self, case, ott_repo, user_repo):
        user = make_user(is_email_verified=False)
        ott = make_ott(user_id=user.id, purpose=OneTimeTokenPurpose.VERIFY_EMAIL)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        await case.execute(dto())

        assert ott.used is True

    async def test_saves_user_and_ott(self, case, ott_repo, user_repo):
        user = make_user(is_email_verified=False)
        ott = make_ott(user_id=user.id)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        await case.execute(dto())

        user_repo.save.assert_awaited_once()
        ott_repo.save.assert_awaited_once()

    async def test_publishes_email_verified_event(
        self, case, ott_repo, user_repo, event_publisher
    ):
        user = make_user(is_email_verified=False)
        ott = make_ott(user_id=user.id)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        assert any(isinstance(e, UserEmailVerified) for e in events)


# ── not found ─────────────────────────────────────────────────────────────────

class TestVerifyEmailNotFound:
    async def test_unknown_token_raises(self, case, ott_repo):
        ott_repo.get_by_string.return_value = None

        with pytest.raises(OneTimeTokenNotFound):
            await case.execute(dto())

    async def test_orphan_token_no_user_raises(self, case, ott_repo, user_repo):
        """Token exists but the associated user was deleted."""
        ott = make_ott(purpose=OneTimeTokenPurpose.VERIFY_EMAIL)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            await case.execute(dto())

    async def test_nothing_saved_on_not_found(self, case, ott_repo, user_repo):
        ott_repo.get_by_string.return_value = None

        with pytest.raises(OneTimeTokenNotFound):
            await case.execute(dto())

        user_repo.save.assert_not_awaited()
        ott_repo.save.assert_not_awaited()


# ── domain errors ─────────────────────────────────────────────────────────────

class TestVerifyEmailDomainErrors:
    async def test_expired_ott_raises_token_error(self, case, ott_repo, user_repo):
        from datetime import timedelta
        user = make_user(is_email_verified=False)
        expired_ott = make_ott(
            user_id=user.id,
            expires_in=timedelta(seconds=-1),
        )
        ott_repo.get_by_string.return_value = expired_ott
        user_repo.get_by_id.return_value = user

        with pytest.raises(TokenError):
            await case.execute(dto())

    async def test_already_used_ott_raises_token_error(self, case, ott_repo, user_repo):
        user = make_user(is_email_verified=False)
        used_ott = make_ott(user_id=user.id, used=True)
        ott_repo.get_by_string.return_value = used_ott
        user_repo.get_by_id.return_value = user

        with pytest.raises(TokenError):
            await case.execute(dto())

    async def test_already_verified_user_raises_user_error(
        self, case, ott_repo, user_repo
    ):
        """OTT is valid but user is already verified.
        ott.use() succeeds first; user.verify_email() then raises UserError."""
        user = make_user(is_email_verified=True)
        ott = make_ott(user_id=user.id)
        ott_repo.get_by_string.return_value = ott
        user_repo.get_by_id.return_value = user

        with pytest.raises(UserError):
            await case.execute(dto())

    async def test_wrong_purpose_ott_raises_token_error(self, case, ott_repo, user_repo):
        """A RECOVER_PASSWORD token cannot be used for email verification."""
        user = make_user(is_email_verified=False)
        recover_ott = make_ott(
            user_id=user.id,
            purpose=OneTimeTokenPurpose.RECOVER_PASSWORD,
        )
        ott_repo.get_by_string.return_value = recover_ott
        user_repo.get_by_id.return_value = user

        with pytest.raises(TokenError, match="purpose mismatch"):
            await case.execute(dto())
