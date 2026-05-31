import pytest

from app.application.cases.user.revoke_token import RevokeTokenCase
from app.application.dto.user import RevokeRefreshTokenInputDTO
from app.application.events.security import SuspiciousRefreshTokenRevocation
from app.application.exceptions.not_found import RefreshTokenNotFound
from app.core.domain.exceptions.token import TokenError

from tests.unit.application.cases.conftest import make_refresh_token


@pytest.fixture
def case(tx, refresh_token_repo, config, event_publisher):
    return RevokeTokenCase(
        tx=tx,
        refresh_token_repo=refresh_token_repo,
        config=config,
        event_publisher=event_publisher,
    )


def dto(
    token: str = "some-token",
    client_ip: str | None = "10.0.0.1",
    user_agent: str | None = "Browser/1",
    location: str | None = None,
) -> RevokeRefreshTokenInputDTO:
    return RevokeRefreshTokenInputDTO(
        refresh_token=token,
        client_ip=client_ip,
        user_agent=user_agent,
        location=location,
    )


# ── happy path: no security threat ───────────────────────────────────────────

class TestRevokeTokenHappyPath:
    async def test_token_is_revoked(self, case, refresh_token_repo):
        rt = make_refresh_token(client_ip="10.0.0.1", user_agent="Browser/1")
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(dto(client_ip="10.0.0.1", user_agent="Browser/1"))

        assert rt.revoked_at is not None

    async def test_token_is_saved(self, case, refresh_token_repo):
        rt = make_refresh_token(client_ip="10.0.0.1")
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(dto())

        refresh_token_repo.save.assert_awaited_once()

    async def test_no_suspicious_event_when_metadata_matches(
        self, case, refresh_token_repo, event_publisher
    ):
        rt = make_refresh_token(client_ip="10.0.0.5", user_agent="Browser/1")
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(
            dto(client_ip="10.0.0.99", user_agent="Browser/1")
        )

        events = event_publisher.publish.call_args[0][0]
        assert not any(isinstance(e, SuspiciousRefreshTokenRevocation) for e in events)


# ── security threat detection ─────────────────────────────────────────────────

class TestRevokeTokenSuspicious:
    async def test_different_user_agent_triggers_suspicious_event(
        self, case, refresh_token_repo, event_publisher
    ):
        rt = make_refresh_token(client_ip="10.0.0.1", user_agent="Browser/1")
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(dto(client_ip="10.0.0.1", user_agent="DifferentBrowser/2"))

        events = event_publisher.publish.call_args[0][0]
        assert any(isinstance(e, SuspiciousRefreshTokenRevocation) for e in events)

    async def test_different_ip_subnet_triggers_suspicious_event(
        self, case, refresh_token_repo, event_publisher
    ):
        rt = make_refresh_token(client_ip="10.0.0.1")
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(dto(client_ip="192.168.1.1"))

        events = event_publisher.publish.call_args[0][0]
        assert any(isinstance(e, SuspiciousRefreshTokenRevocation) for e in events)

    async def test_suspicious_event_carries_current_client_metadata(
        self, case, refresh_token_repo, event_publisher
    ):
        rt = make_refresh_token(client_ip="10.0.0.1", user_agent="LegitBrowser/1")
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(
            dto(client_ip="99.99.99.1", user_agent="Suspicious/99", location="Moscow")
        )

        events = event_publisher.publish.call_args[0][0]
        event = next(e for e in events if isinstance(e, SuspiciousRefreshTokenRevocation))
        assert event.client_ip == "99.99.99.1"
        assert event.user_agent == "Suspicious/99"
        assert event.location == "Moscow"

    async def test_suspicious_event_carries_user_and_token_ids(
        self, case, refresh_token_repo, event_publisher
    ):
        rt = make_refresh_token(client_ip="10.0.0.1", user_agent="UA/1")
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(dto(client_ip="99.1.1.1", user_agent="Other/1"))

        events = event_publisher.publish.call_args[0][0]
        event = next(e for e in events if isinstance(e, SuspiciousRefreshTokenRevocation))
        assert event.user_id == rt.user_id
        assert event.token_id == rt.id

    async def test_token_revoked_even_when_suspicious(
        self, case, refresh_token_repo, event_publisher
    ):
        """Security event is advisory — the token is still revoked."""
        rt = make_refresh_token(client_ip="10.0.0.1", user_agent="UA/1")
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(dto(client_ip="99.1.1.1", user_agent="Other/1"))

        assert rt.revoked_at is not None


# ── not found ─────────────────────────────────────────────────────────────────

class TestRevokeTokenNotFound:
    async def test_unknown_token_raises(self, case, refresh_token_repo):
        refresh_token_repo.get_by_string.return_value = None

        with pytest.raises(RefreshTokenNotFound):
            await case.execute(dto())

    async def test_no_saves_on_not_found(self, case, refresh_token_repo):
        refresh_token_repo.get_by_string.return_value = None

        with pytest.raises(RefreshTokenNotFound):
            await case.execute(dto())

        refresh_token_repo.save.assert_not_awaited()


# ── domain errors ─────────────────────────────────────────────────────────────

class TestRevokeTokenDomainErrors:
    async def test_already_revoked_token_raises_token_error(
        self, case, refresh_token_repo
    ):
        """revoke() on an already-revoked token raises TokenError from the domain."""
        rt = make_refresh_token(revoked=True)
        refresh_token_repo.get_by_string.return_value = rt

        with pytest.raises(TokenError):
            await case.execute(dto())
