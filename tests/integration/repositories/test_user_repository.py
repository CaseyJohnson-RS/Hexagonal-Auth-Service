import pytest
from uuid import uuid4

from app.application.exceptions.concurrency import ConcurrencyError
from tests.integration.repositories.conftest import make_user


class TestUserRepositorySave:
    async def test_insert_new_user(self, user_repo):
        user = make_user(email="a@example.com")
        await user_repo.save(user)
        fetched = await user_repo.get_by_id(user.id)
        assert fetched is not None
        assert fetched.email == "a@example.com"

    async def test_insert_sets_version_attribute_to_one(self, user_repo):
        user = make_user()
        assert not hasattr(user, "__version")
        await user_repo.save(user)
        assert getattr(user, "__version") == 1

    async def test_update_persists_mutated_fields(self, user_repo, saved_user):
        saved_user.active = False
        await user_repo.save(saved_user)
        fetched = await user_repo.get_by_id(saved_user.id)
        assert fetched.active is False

    async def test_update_increments_version_in_db(self, user_repo, saved_user):
        assert getattr(saved_user, "__version") == 1
        saved_user.active = False
        await user_repo.save(saved_user)
        assert getattr(saved_user, "__version") == 2

    async def test_successive_updates_increment_version_each_time(self, user_repo, saved_user):
        saved_user.active = False
        await user_repo.save(saved_user)
        saved_user.active = True
        await user_repo.save(saved_user)
        assert getattr(saved_user, "__version") == 3
        fetched = await user_repo.get_by_id(saved_user.id)
        assert fetched.active is True

    async def test_update_all_mutable_fields(self, user_repo, saved_user):
        saved_user.email = "changed@example.com"
        saved_user.password_hash = "new-hash"
        saved_user.active = False
        saved_user.is_email_verified = False
        await user_repo.save(saved_user)
        fetched = await user_repo.get_by_id(saved_user.id)
        assert fetched.email == "changed@example.com"
        assert fetched.password_hash == "new-hash"
        assert fetched.active is False
        assert fetched.is_email_verified is False

    async def test_optimistic_lock_conflict_raises_concurrency_error(self, user_repo):
        user = make_user(email="race@example.com")
        await user_repo.save(user)

        copy_a = await user_repo.get_by_id(user.id)
        copy_b = await user_repo.get_by_id(user.id)

        copy_a.active = False
        await user_repo.save(copy_a)

        copy_b.active = True
        with pytest.raises(ConcurrencyError):
            await user_repo.save(copy_b)

    async def test_update_with_no_matching_version_raises(self, user_repo):
        user = make_user()
        setattr(user, "__version", 99)
        with pytest.raises(ConcurrencyError):
            await user_repo.save(user)


class TestUserRepositoryGet:
    async def test_get_by_email_returns_saved_user(self, user_repo):
        user = make_user(email="find-by-email@example.com")
        await user_repo.save(user)
        fetched = await user_repo.get_by_email("find-by-email@example.com")
        assert fetched is not None
        assert fetched.id == user.id

    async def test_get_by_id_returns_saved_user(self, user_repo, saved_user):
        fetched = await user_repo.get_by_id(saved_user.id)
        assert fetched is not None
        assert fetched.id == saved_user.id

    async def test_get_by_email_returns_none_for_unknown_email(self, user_repo):
        result = await user_repo.get_by_email("nobody@example.com")
        assert result is None

    async def test_get_by_id_returns_none_for_unknown_id(self, user_repo):
        result = await user_repo.get_by_id(uuid4())
        assert result is None

    async def test_get_preserves_all_fields(self, user_repo):
        user = make_user(
            email="full@example.com",
            password_hash="ph123",
            active=False,
            is_email_verified=False,
        )
        await user_repo.save(user)
        fetched = await user_repo.get_by_id(user.id)
        assert fetched.email == "full@example.com"
        assert fetched.password_hash == "ph123"
        assert fetched.active is False
        assert fetched.is_email_verified is False
        assert fetched.created_at == user.created_at

    async def test_get_by_id_sets_version_attribute(self, user_repo, saved_user):
        fetched = await user_repo.get_by_id(saved_user.id)
        assert getattr(fetched, "__version") == 1

    async def test_get_by_email_sets_version_attribute(self, user_repo):
        user = make_user(email="ver@example.com")
        await user_repo.save(user)
        fetched = await user_repo.get_by_email("ver@example.com")
        assert getattr(fetched, "__version") == 1

    async def test_get_by_email_is_exact_match(self, user_repo):
        await user_repo.save(make_user(email="exact@example.com"))
        result = await user_repo.get_by_email("EXACT@example.com")
        assert result is None

    async def test_two_users_dont_collide(self, user_repo):
        u1 = make_user(email="u1@example.com")
        u2 = make_user(email="u2@example.com")
        await user_repo.save(u1)
        await user_repo.save(u2)
        r1 = await user_repo.get_by_id(u1.id)
        r2 = await user_repo.get_by_id(u2.id)
        assert r1.id != r2.id
        assert r1.email == "u1@example.com"
        assert r2.email == "u2@example.com"


class TestUserRepositoryDelete:
    async def test_delete_removes_user_from_db(self, user_repo, saved_user):
        await user_repo.delete(saved_user)
        result = await user_repo.get_by_id(saved_user.id)
        assert result is None

    async def test_delete_with_stale_version_raises_concurrency_error(self, user_repo):
        user = make_user(email="stale-del@example.com")
        await user_repo.save(user)

        stale_copy = await user_repo.get_by_id(user.id)
        user.active = False
        await user_repo.save(user)

        with pytest.raises(ConcurrencyError):
            await user_repo.delete(stale_copy)

    async def test_delete_nonexistent_user_raises_concurrency_error(self, user_repo):
        phantom = make_user()
        setattr(phantom, "__version", 1)
        with pytest.raises(ConcurrencyError):
            await user_repo.delete(phantom)

    async def test_delete_removes_only_target_user(self, user_repo):
        u1 = make_user(email="del1@example.com")
        u2 = make_user(email="del2@example.com")
        await user_repo.save(u1)
        await user_repo.save(u2)
        await user_repo.delete(u1)
        assert await user_repo.get_by_id(u1.id) is None
        assert await user_repo.get_by_id(u2.id) is not None
