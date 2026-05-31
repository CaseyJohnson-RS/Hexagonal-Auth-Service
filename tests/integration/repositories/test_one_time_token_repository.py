import pytest
from datetime import timedelta

from app.application.exceptions.concurrency import ConcurrencyError
from app.core.domain.entities.one_time_token import OneTimeTokenPurpose
from app.core.utils.security import hash_token
from tests.integration.repositories.conftest import make_one_time_token


class TestOneTimeTokenRepositorySave:
    async def test_insert_new_token(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id)
        await ott_repo.save(token)
        fetched = await ott_repo.get_by_string("raw-ott-token")
        assert fetched is not None
        assert fetched.id == token.id

    async def test_insert_sets_version_to_one(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id)
        assert not hasattr(token, "__version")
        await ott_repo.save(token)
        assert getattr(token, "__version") == 1

    async def test_update_marks_token_as_used(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id, token_string="use-me")
        await ott_repo.save(token)
        token.used = True
        await ott_repo.save(token)
        fetched = await ott_repo.get_by_string("use-me")
        assert fetched.used is True

    async def test_update_increments_version(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id, token_string="inc-ver")
        await ott_repo.save(token)
        token.used = True
        await ott_repo.save(token)
        assert getattr(token, "__version") == 2

    async def test_optimistic_lock_conflict_raises_concurrency_error(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id, token_string="conflict-ott")
        await ott_repo.save(token)

        copy_a = await ott_repo.get_by_string("conflict-ott")
        copy_b = await ott_repo.get_by_string("conflict-ott")

        copy_a.used = True
        await ott_repo.save(copy_a)

        copy_b.used = True
        with pytest.raises(ConcurrencyError):
            await ott_repo.save(copy_b)

    async def test_update_with_wrong_version_raises(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id)
        setattr(token, "__version", 99)
        with pytest.raises(ConcurrencyError):
            await ott_repo.save(token)


class TestOneTimeTokenRepositoryGetByString:
    async def test_finds_token_by_raw_string(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id, token_string="known-ott")
        await ott_repo.save(token)
        fetched = await ott_repo.get_by_string("known-ott")
        assert fetched.id == token.id

    async def test_returns_none_for_unknown_string(self, ott_repo):
        result = await ott_repo.get_by_string("no-such-token")
        assert result is None

    async def test_does_not_find_by_hash_string(self, ott_repo, saved_user):
        raw = "hash-lookup-test"
        token = make_one_time_token(user_id=saved_user.id, token_string=raw)
        await ott_repo.save(token)
        result = await ott_repo.get_by_string(hash_token(raw))
        assert result is None

    async def test_preserves_purpose_verify_email(self, ott_repo, saved_user):
        token = make_one_time_token(
            user_id=saved_user.id,
            token_string="ve-token",
            purpose=OneTimeTokenPurpose.VERIFY_EMAIL,
        )
        await ott_repo.save(token)
        fetched = await ott_repo.get_by_string("ve-token")
        assert fetched.purpose == OneTimeTokenPurpose.VERIFY_EMAIL

    async def test_preserves_purpose_recover_password(self, ott_repo, saved_user):
        token = make_one_time_token(
            user_id=saved_user.id,
            token_string="rp-token",
            purpose=OneTimeTokenPurpose.RECOVER_PASSWORD,
        )
        await ott_repo.save(token)
        fetched = await ott_repo.get_by_string("rp-token")
        assert fetched.purpose == OneTimeTokenPurpose.RECOVER_PASSWORD

    async def test_preserves_used_false(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id, token_string="unused-ott")
        await ott_repo.save(token)
        fetched = await ott_repo.get_by_string("unused-ott")
        assert fetched.used is False

    async def test_preserves_used_true(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id, token_string="used-ott", used=True)
        await ott_repo.save(token)
        fetched = await ott_repo.get_by_string("used-ott")
        assert fetched.used is True

    async def test_preserves_user_id(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id, token_string="uid-ott")
        await ott_repo.save(token)
        fetched = await ott_repo.get_by_string("uid-ott")
        assert fetched.user_id == saved_user.id

    async def test_sets_version_attribute_on_fetched_token(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id, token_string="ver-ott")
        await ott_repo.save(token)
        fetched = await ott_repo.get_by_string("ver-ott")
        assert getattr(fetched, "__version") == 1

    async def test_expired_token_is_still_retrievable(self, ott_repo, saved_user):
        token = make_one_time_token(
            user_id=saved_user.id,
            token_string="expired-ott",
            expires_in=timedelta(seconds=-1),
        )
        await ott_repo.save(token)
        fetched = await ott_repo.get_by_string("expired-ott")
        assert fetched is not None
        assert fetched.id == token.id

    async def test_returns_correct_token_when_multiple_exist(self, ott_repo, saved_user):
        t1 = make_one_time_token(user_id=saved_user.id, token_string="ott-one")
        t2 = make_one_time_token(user_id=saved_user.id, token_string="ott-two")
        await ott_repo.save(t1)
        await ott_repo.save(t2)
        fetched = await ott_repo.get_by_string("ott-two")
        assert fetched.id == t2.id

    async def test_two_tokens_different_purposes_same_user(self, ott_repo, saved_user):
        ve = make_one_time_token(
            user_id=saved_user.id,
            token_string="dual-ve",
            purpose=OneTimeTokenPurpose.VERIFY_EMAIL,
        )
        rp = make_one_time_token(
            user_id=saved_user.id,
            token_string="dual-rp",
            purpose=OneTimeTokenPurpose.RECOVER_PASSWORD,
        )
        await ott_repo.save(ve)
        await ott_repo.save(rp)
        assert (await ott_repo.get_by_string("dual-ve")).purpose == OneTimeTokenPurpose.VERIFY_EMAIL
        result = await ott_repo.get_by_string("dual-rp")
        assert result.purpose == OneTimeTokenPurpose.RECOVER_PASSWORD


class TestOneTimeTokenRepositoryDelete:
    async def test_delete_removes_token(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id, token_string="del-ott")
        await ott_repo.save(token)
        await ott_repo.delete(token)
        result = await ott_repo.get_by_string("del-ott")
        assert result is None

    async def test_delete_stale_version_raises_concurrency_error(self, ott_repo, saved_user):
        token = make_one_time_token(user_id=saved_user.id, token_string="stale-ott-del")
        await ott_repo.save(token)

        stale = await ott_repo.get_by_string("stale-ott-del")
        token.used = True
        await ott_repo.save(token)

        with pytest.raises(ConcurrencyError):
            await ott_repo.delete(stale)

    async def test_delete_nonexistent_raises_concurrency_error(self, ott_repo, saved_user):
        phantom = make_one_time_token(user_id=saved_user.id)
        setattr(phantom, "__version", 1)
        with pytest.raises(ConcurrencyError):
            await ott_repo.delete(phantom)

    async def test_delete_removes_only_target_token(self, ott_repo, saved_user):
        t1 = make_one_time_token(user_id=saved_user.id, token_string="keep-this")
        t2 = make_one_time_token(user_id=saved_user.id, token_string="delete-this")
        await ott_repo.save(t1)
        await ott_repo.save(t2)
        await ott_repo.delete(t2)
        assert await ott_repo.get_by_string("keep-this") is not None
        assert await ott_repo.get_by_string("delete-this") is None

    async def test_delete_user_with_tokens_raises_integrity_error(
        self, user_repo, ott_repo, saved_user
    ):
        # UserRepository.delete() uses raw SQL DELETE — no ORM cascade.
        # PostgreSQL FK constraint blocks deletion if child rows exist.
        from sqlalchemy.exc import IntegrityError
        token = make_one_time_token(user_id=saved_user.id, token_string="fk-ott")
        await ott_repo.save(token)
        with pytest.raises(IntegrityError):
            await user_repo.delete(saved_user)
