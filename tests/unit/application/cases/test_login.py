import pytest

from app.application.cases.user.login import LoginUserCase
from app.application.dto.user import LoginUserInputDTO, TokenPairDTO
from app.application.exceptions.not_found import UserNotFound
from app.core.domain.events.token import RefreshTokenCreated
from app.core.domain.exceptions.user import UserError

from tests.unit.application.cases.conftest import make_user


@pytest.fixture
def case(tx, user_repo, refresh_token_repo, config, event_publisher, access_token_issuer):
    return LoginUserCase(
        tx=tx,
        user_repo=user_repo,
        refresh_token_repo=refresh_token_repo,
        config=config,
        event_publisher=event_publisher,
        access_token_issuer=access_token_issuer,
    )


def dto(
    email="test@example.com",
    password="Password123",
    client_ip=None,
    user_agent=None,
    location=None,
) -> LoginUserInputDTO:
    return LoginUserInputDTO(
        email=email,
        password=password,
        client_ip=client_ip,
        user_agent=user_agent,
        location=location,
    )


# ── happy path ────────────────────────────────────────────────────────────────

class TestLoginHappyPath:
    async def test_returns_token_pair_dto(self, case, user_repo):
        user_repo.get_by_email.return_value = make_user(password="Password123")

        result = await case.execute(dto())

        assert isinstance(result, TokenPairDTO)
        assert result.access_token
        assert result.refresh_token

    async def test_access_token_comes_from_issuer(self, case, user_repo, access_token_issuer):
        user_repo.get_by_email.return_value = make_user(password="Password123")
        access_token_issuer.issue.return_value = "custom.access.token"

        result = await case.execute(dto())

        assert result.access_token == "custom.access.token"

    async def test_saves_refresh_token(self, case, user_repo, refresh_token_repo):
        user_repo.get_by_email.return_value = make_user(password="Password123")

        await case.execute(dto())

        refresh_token_repo.save.assert_awaited_once()

    async def test_publishes_refresh_token_created_event(
        self, case, user_repo, event_publisher
    ):
        user_repo.get_by_email.return_value = make_user(password="Password123")

        await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        assert any(isinstance(e, RefreshTokenCreated) for e in events)

    async def test_client_metadata_forwarded_to_refresh_token(
        self, case, user_repo, refresh_token_repo
    ):
        user_repo.get_by_email.return_value = make_user(password="Password123")

        await case.execute(
            dto(client_ip="10.0.0.1", user_agent="TestBrowser/1", location="Paris")
        )

        saved_rt = refresh_token_repo.save.call_args[0][0]
        assert saved_rt.client_ip == "10.0.0.1"
        assert saved_rt.user_agent == "TestBrowser/1"
        assert saved_rt.location == "Paris"

    async def test_refresh_token_created_event_carries_client_metadata(
        self, case, user_repo, event_publisher
    ):
        user_repo.get_by_email.return_value = make_user(password="Password123")

        await case.execute(dto(client_ip="10.0.0.1", user_agent="UA/2"))

        events = event_publisher.publish.call_args[0][0]
        event = next(e for e in events if isinstance(e, RefreshTokenCreated))
        assert event.client_ip == "10.0.0.1"
        assert event.user_agent == "UA/2"


# ── not found ─────────────────────────────────────────────────────────────────

class TestLoginNotFound:
    async def test_unknown_email_raises_user_not_found(self, case, user_repo):
        user_repo.get_by_email.return_value = None

        with pytest.raises(UserNotFound):
            await case.execute(dto())

    async def test_no_tokens_saved_on_not_found(self, case, user_repo, refresh_token_repo):
        user_repo.get_by_email.return_value = None

        with pytest.raises(UserNotFound):
            await case.execute(dto())

        refresh_token_repo.save.assert_not_awaited()


# ── domain errors propagation ─────────────────────────────────────────────────

class TestLoginDomainErrors:
    async def test_deactivated_user_raises_user_error(self, case, user_repo):
        user_repo.get_by_email.return_value = make_user(
            active=False, password="Password123"
        )

        with pytest.raises(UserError, match="deactivated"):
            await case.execute(dto())

    async def test_unverified_email_raises_user_error(self, case, user_repo):
        user_repo.get_by_email.return_value = make_user(
            is_email_verified=False, password="Password123"
        )

        with pytest.raises(UserError, match="not verified"):
            await case.execute(dto())

    async def test_wrong_password_raises_user_error(self, case, user_repo):
        user_repo.get_by_email.return_value = make_user(password="CorrectPass1")

        with pytest.raises(UserError, match="Invalid password"):
            await case.execute(dto(password="WrongPass1"))

    async def test_no_events_published_on_domain_error(
        self, case, user_repo, event_publisher
    ):
        user_repo.get_by_email.return_value = make_user(active=False)

        with pytest.raises(UserError):
            await case.execute(dto())

        event_publisher.publish.assert_not_awaited()
