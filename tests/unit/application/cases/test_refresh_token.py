import pytest
from datetime import timedelta

from app.application.cases.user.refresh_token import RefreshTokenCase
from app.application.dto.user import RefreshTokenInputDTO, TokenPairDTO
from app.application.events.security import RefreshTokenReuseDetected
from app.application.exceptions.not_found import RefreshTokenNotFound
from app.core.domain.exceptions.token import RefreshTokenReuse

from tests.unit.application.cases.conftest import make_refresh_token


@pytest.fixture
def case(tx, refresh_token_repo, config, event_publisher, access_token_issuer):
    return RefreshTokenCase(
        tx=tx,
        refresh_token_repo=refresh_token_repo,
        config=config,
        event_publisher=event_publisher,
        access_token_issuer=access_token_issuer,
    )


def dto(
    token: str = "old-refresh-token",
    client_ip: str = "10.0.0.1",
    user_agent: str = "UA/1",
    location: str | None = None,
) -> RefreshTokenInputDTO:
    return RefreshTokenInputDTO(
        refresh_token=token,
        client_ip=client_ip,
        user_agent=user_agent,
        location=location,
    )


# ── happy path ────────────────────────────────────────────────────────────────

class TestRefreshTokenHappyPath:
    async def test_returns_new_token_pair(self, case, refresh_token_repo):
        rt = make_refresh_token()
        refresh_token_repo.get_by_string.return_value = rt

        result = await case.execute(dto())

        assert isinstance(result, TokenPairDTO)
        assert result.access_token
        assert result.refresh_token

    async def test_old_token_is_saved_as_used(self, case, refresh_token_repo):
        rt = make_refresh_token()
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(dto())

        # old token should be revoked (use() sets revoked_at)
        assert rt.revoked_at is not None

    async def test_two_tokens_saved_old_and_new(self, case, refresh_token_repo):
        rt = make_refresh_token()
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(dto())

        assert refresh_token_repo.save.await_count == 2

    async def test_access_token_comes_from_issuer(
        self, case, refresh_token_repo, access_token_issuer
    ):
        rt = make_refresh_token()
        refresh_token_repo.get_by_string.return_value = rt
        access_token_issuer.issue.return_value = "new.access.jwt"

        result = await case.execute(dto())

        assert result.access_token == "new.access.jwt"

    async def test_new_refresh_token_belongs_to_same_user(
        self, case, refresh_token_repo
    ):
        rt = make_refresh_token()
        refresh_token_repo.get_by_string.return_value = rt

        await case.execute(dto())

        # second save is the new token
        saves = refresh_token_repo.save.await_args_list
        new_rt = saves[1][0][0]  # second call, first positional arg
        assert new_rt.user_id == rt.user_id


# ── token not found ───────────────────────────────────────────────────────────

class TestRefreshTokenNotFound:
    async def test_unknown_token_raises(self, case, refresh_token_repo):
        refresh_token_repo.get_by_string.return_value = None

        with pytest.raises(RefreshTokenNotFound):
            await case.execute(dto())

    async def test_no_saves_on_not_found(self, case, refresh_token_repo):
        refresh_token_repo.get_by_string.return_value = None

        with pytest.raises(RefreshTokenNotFound):
            await case.execute(dto())

        refresh_token_repo.save.assert_not_awaited()


# ── reuse detection ───────────────────────────────────────────────────────────

class TestRefreshTokenReuseDetection:
    async def test_reuse_re_raises_refresh_token_reuse(
        self, case, refresh_token_repo
    ):
        """Token already replaced → use() raises RefreshTokenReuse, which must
        propagate to the caller after reuse detection handling."""
        replaced_rt = make_refresh_token(replaced_by_id=make_refresh_token().id)
        refresh_token_repo.get_by_string.return_value = replaced_rt

        with pytest.raises(RefreshTokenReuse):
            await case.execute(dto())

    async def test_reuse_publishes_reuse_detected_event(
        self, case, refresh_token_repo, event_publisher
    ):
        replaced_rt = make_refresh_token(replaced_by_id=make_refresh_token().id)
        refresh_token_repo.get_by_string.return_value = replaced_rt

        with pytest.raises(RefreshTokenReuse):
            await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        assert any(isinstance(e, RefreshTokenReuseDetected) for e in events)

    async def test_reuse_event_carries_client_metadata(
        self, case, refresh_token_repo, event_publisher
    ):
        replaced_rt = make_refresh_token(replaced_by_id=make_refresh_token().id)
        refresh_token_repo.get_by_string.return_value = replaced_rt

        with pytest.raises(RefreshTokenReuse):
            await case.execute(dto(client_ip="9.9.9.9", user_agent="Attacker/1"))

        events = event_publisher.publish.call_args[0][0]
        event = next(e for e in events if isinstance(e, RefreshTokenReuseDetected))
        assert event.client_ip == "9.9.9.9"
        assert event.user_agent == "Attacker/1"

    async def test_reuse_event_carries_user_and_token_ids(
        self, case, refresh_token_repo, event_publisher
    ):
        from uuid import uuid4
        replaced_rt = make_refresh_token(replaced_by_id=uuid4())
        refresh_token_repo.get_by_string.return_value = replaced_rt

        with pytest.raises(RefreshTokenReuse):
            await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        event = next(e for e in events if isinstance(e, RefreshTokenReuseDetected))
        assert event.user_id == replaced_rt.user_id
        assert event.token_id == replaced_rt.id

    async def test_reuse_with_missing_token_in_second_query_still_re_raises(
        self, case, refresh_token_repo, event_publisher
    ):
        """Token disappears between the first and second DB query (deleted by
        concurrent cleanup). The exception must still be re-raised; only the
        event is omitted."""
        replaced_rt = make_refresh_token(replaced_by_id=make_refresh_token().id)
        # First call returns the replaced token; second (in reuse handler) returns None.
        refresh_token_repo.get_by_string.side_effect = [replaced_rt, None]

        with pytest.raises(RefreshTokenReuse):
            await case.execute(dto())

        events = event_publisher.publish.call_args[0][0]
        assert not any(isinstance(e, RefreshTokenReuseDetected) for e in events)

    async def test_expired_token_raises_token_error_not_reuse(
        self, case, refresh_token_repo
    ):
        """An expired (but not replaced) token raises TokenError, not RefreshTokenReuse.
        The reuse detection handler should NOT be triggered."""
        from app.core.domain.exceptions.token import TokenError
        expired_rt = make_refresh_token(expires_in=timedelta(seconds=-1))
        refresh_token_repo.get_by_string.return_value = expired_rt

        with pytest.raises(TokenError):
            await case.execute(dto())

        # Only one get_by_string call — the reuse handler didn't open second tx
        assert refresh_token_repo.get_by_string.await_count == 1
