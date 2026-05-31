import pytest
from uuid import uuid4
from datetime import timedelta

from app.application.exceptions.concurrency import ConcurrencyError
from app.core.utils.security import hash_token
from app.core.utils.time import utc_now
from tests.integration.repositories.conftest import make_user, make_refresh_token


class TestRefreshTokenRepositorySave:
    async def test_insert_new_token(self, user_repo, rt_repo, saved_user):
        token = make_refresh_token(user_id=saved_user.id)
        await rt_repo.save(token)
        fetched = await rt_repo.get_by_string("raw-refresh-token")
        assert fetched is not None
        assert fetched.id == token.id

    async def test_insert_sets_version_to_one(self, rt_repo, saved_user):
        token = make_refresh_token(user_id=saved_user.id)
        assert not hasattr(token, "__version")
        await rt_repo.save(token)
        assert getattr(token, "__version") == 1

    async def test_update_persists_revoked_at(self, rt_repo, saved_user):
        token = make_refresh_token(user_id=saved_user.id, token_string="revoke-me")
        await rt_repo.save(token)
        revoke_time = utc_now()
        token.revoked_at = revoke_time
        await rt_repo.save(token)

        fetched = await rt_repo.get_by_string("revoke-me")
        assert fetched.revoked_at is not None

    async def test_update_persists_replaced_by_id(self, rt_repo, saved_user):
        token = make_refresh_token(user_id=saved_user.id, token_string="old-token")
        await rt_repo.save(token)
        new_id = uuid4()
        token.replaced_by_id = new_id
        await rt_repo.save(token)

        fetched = await rt_repo.get_by_string("old-token")
        assert fetched.replaced_by_id == new_id

    async def test_update_increments_version(self, rt_repo, saved_user):
        token = make_refresh_token(user_id=saved_user.id, token_string="ver-token")
        await rt_repo.save(token)
        token.revoked_at = utc_now()
        await rt_repo.save(token)
        assert getattr(token, "__version") == 2

    async def test_optimistic_lock_conflict_raises_concurrency_error(self, rt_repo, saved_user):
        token = make_refresh_token(user_id=saved_user.id, token_string="conflict-token")
        await rt_repo.save(token)

        copy_a = await rt_repo.get_by_string("conflict-token")
        copy_b = await rt_repo.get_by_string("conflict-token")

        copy_a.revoked_at = utc_now()
        await rt_repo.save(copy_a)

        copy_b.replaced_by_id = uuid4()
        with pytest.raises(ConcurrencyError):
            await rt_repo.save(copy_b)

    async def test_update_with_wrong_version_raises(self, rt_repo, saved_user):
        token = make_refresh_token(user_id=saved_user.id)
        setattr(token, "__version", 99)
        with pytest.raises(ConcurrencyError):
            await rt_repo.save(token)


class TestRefreshTokenRepositoryGetByString:
    async def test_finds_token_by_raw_string(self, rt_repo, saved_user):
        token = make_refresh_token(user_id=saved_user.id, token_string="known-raw")
        await rt_repo.save(token)
        fetched = await rt_repo.get_by_string("known-raw")
        assert fetched.id == token.id

    async def test_returns_none_for_unknown_string(self, rt_repo):
        result = await rt_repo.get_by_string("does-not-exist")
        assert result is None

    async def test_does_not_find_by_hash_string(self, rt_repo, saved_user):
        raw = "raw-for-hash-test"
        token = make_refresh_token(user_id=saved_user.id, token_string=raw)
        await rt_repo.save(token)
        result = await rt_repo.get_by_string(hash_token(raw))
        assert result is None

    async def test_returns_correct_token_when_multiple_exist(self, rt_repo, saved_user):
        t1 = make_refresh_token(user_id=saved_user.id, token_string="token-one")
        t2 = make_refresh_token(user_id=saved_user.id, token_string="token-two")
        await rt_repo.save(t1)
        await rt_repo.save(t2)
        fetched = await rt_repo.get_by_string("token-two")
        assert fetched.id == t2.id

    async def test_preserves_all_fields(self, rt_repo, saved_user):
        now = utc_now()
        new_id = uuid4()
        token = make_refresh_token(
            user_id=saved_user.id,
            token_string="full-fields-token",
            expires_in=timedelta(hours=3),
        )
        token.replaced_by_id = new_id
        await rt_repo.save(token)
        token.revoked_at = now
        await rt_repo.save(token)

        fetched = await rt_repo.get_by_string("full-fields-token")
        assert fetched.user_id == saved_user.id
        assert fetched.replaced_by_id == new_id
        assert fetched.revoked_at is not None
        assert getattr(fetched, "__version") == 2

    async def test_expired_token_is_still_retrievable(self, rt_repo, saved_user):
        token = make_refresh_token(
            user_id=saved_user.id,
            token_string="expired-token",
            expires_in=timedelta(seconds=-1),
        )
        await rt_repo.save(token)
        fetched = await rt_repo.get_by_string("expired-token")
        assert fetched is not None
        assert fetched.id == token.id


class TestRefreshTokenRepositoryGetAllByUser:
    async def test_returns_all_tokens_for_user(self, rt_repo, saved_user):
        for i in range(3):
            await rt_repo.save(make_refresh_token(
                user_id=saved_user.id, token_string=f"token-{i}"
            ))
        tokens = await rt_repo.get_all_by_user(saved_user.id)
        assert len(tokens) == 3

    async def test_returns_empty_for_user_with_no_tokens(self, rt_repo, saved_user):
        tokens = await rt_repo.get_all_by_user(saved_user.id)
        assert tokens == []

    async def test_does_not_return_other_users_tokens(self, user_repo, rt_repo):
        u1 = make_user(email="owner@example.com")
        u2 = make_user(email="other@example.com")
        await user_repo.save(u1)
        await user_repo.save(u2)
        await rt_repo.save(make_refresh_token(user_id=u1.id, token_string="u1-token"))
        await rt_repo.save(make_refresh_token(user_id=u2.id, token_string="u2-token"))

        tokens = await rt_repo.get_all_by_user(u1.id)
        assert len(tokens) == 1
        assert tokens[0].user_id == u1.id

    async def test_includes_revoked_and_expired_tokens(self, rt_repo, saved_user):
        await rt_repo.save(make_refresh_token(
            user_id=saved_user.id, token_string="active-one"
        ))
        await rt_repo.save(make_refresh_token(
            user_id=saved_user.id, token_string="revoked-one", revoked=True
        ))
        await rt_repo.save(make_refresh_token(
            user_id=saved_user.id, token_string="expired-one",
            expires_in=timedelta(seconds=-1)
        ))
        tokens = await rt_repo.get_all_by_user(saved_user.id)
        assert len(tokens) == 3

    async def test_returns_empty_for_nonexistent_user(self, rt_repo):
        tokens = await rt_repo.get_all_by_user(uuid4())
        assert tokens == []


class TestRefreshTokenRepositoryDelete:
    async def test_delete_removes_token(self, rt_repo, saved_user):
        token = make_refresh_token(user_id=saved_user.id, token_string="to-delete")
        await rt_repo.save(token)
        await rt_repo.delete(token)
        result = await rt_repo.get_by_string("to-delete")
        assert result is None

    async def test_delete_stale_version_raises_concurrency_error(self, rt_repo, saved_user):
        token = make_refresh_token(user_id=saved_user.id, token_string="stale-del")
        await rt_repo.save(token)

        stale = await rt_repo.get_by_string("stale-del")
        token.revoked_at = utc_now()
        await rt_repo.save(token)

        with pytest.raises(ConcurrencyError):
            await rt_repo.delete(stale)

    async def test_delete_nonexistent_raises_concurrency_error(self, rt_repo, saved_user):
        phantom = make_refresh_token(user_id=saved_user.id)
        setattr(phantom, "__version", 1)
        with pytest.raises(ConcurrencyError):
            await rt_repo.delete(phantom)

    async def test_delete_removes_only_target_token(self, rt_repo, saved_user):
        t1 = make_refresh_token(user_id=saved_user.id, token_string="del-t1")
        t2 = make_refresh_token(user_id=saved_user.id, token_string="del-t2")
        await rt_repo.save(t1)
        await rt_repo.save(t2)
        await rt_repo.delete(t1)
        assert await rt_repo.get_by_string("del-t1") is None
        assert await rt_repo.get_by_string("del-t2") is not None
