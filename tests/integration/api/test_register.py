from app.core.domain.events.user import UserEmailVerificationRequested
from tests.integration.api.conftest import EMAIL, PASSWORD, get_verify_token


class TestRegister:
    async def test_register_returns_200(self, client):
        resp = await client.post(
            "/auth/api/register", json={"email": EMAIL, "password": PASSWORD}
        )
        assert resp.status_code == 200

    async def test_register_emits_verification_event(self, client, notification_queue):
        await client.post(
            "/auth/api/register", json={"email": EMAIL, "password": PASSWORD}
        )
        events = [
            e for e in notification_queue.get_all()
            if isinstance(e, UserEmailVerificationRequested)
        ]
        assert len(events) == 1
        assert events[0].email == EMAIL
        assert events[0].token  # non-empty token string

    async def test_register_unverified_user_again_succeeds(self, client, notification_queue):
        await client.post("/auth/api/register", json={"email": EMAIL, "password": PASSWORD})
        notification_queue.clear()
        resp = await client.post(
            "/auth/api/register", json={"email": EMAIL, "password": PASSWORD}
        )
        assert resp.status_code == 200
        events = [
            e for e in notification_queue.get_all()
            if isinstance(e, UserEmailVerificationRequested)
        ]
        assert len(events) == 1

    async def test_register_verified_user_returns_400(self, client, verified):
        resp = await client.post(
            "/auth/api/register", json={"email": EMAIL, "password": PASSWORD}
        )
        assert resp.status_code == 400

    async def test_register_invalid_email_returns_400(self, client):
        resp = await client.post(
            "/auth/api/register", json={"email": "not-an-email", "password": PASSWORD}
        )
        assert resp.status_code == 400

    async def test_register_empty_email_returns_400(self, client):
        resp = await client.post(
            "/auth/api/register", json={"email": "", "password": PASSWORD}
        )
        assert resp.status_code == 400

    async def test_register_short_password_returns_400(self, client):
        resp = await client.post(
            "/auth/api/register", json={"email": EMAIL, "password": "abc"}
        )
        assert resp.status_code == 400

    async def test_two_different_emails_register_independently(self, client, notification_queue):
        r1 = await client.post(
            "/auth/api/register",
            json={"email": "user1@example.com", "password": PASSWORD},
        )
        r2 = await client.post(
            "/auth/api/register",
            json={"email": "user2@example.com", "password": PASSWORD},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        events = [
            e for e in notification_queue.get_all()
            if isinstance(e, UserEmailVerificationRequested)
        ]
        assert len(events) == 2
        tokens = {e.email: e.token for e in events}
        assert tokens["user1@example.com"] != tokens["user2@example.com"]


class TestVerifyEmail:
    async def test_verify_email_returns_200(self, client, registered):
        resp = await client.post(
            "/auth/api/verify_email", json={"one_time_token": registered}
        )
        assert resp.status_code == 200

    async def test_verify_email_with_invalid_token_returns_400(self, client):
        resp = await client.post(
            "/auth/api/verify_email", json={"one_time_token": "invalid-token"}
        )
        assert resp.status_code == 400

    async def test_verify_email_twice_returns_400(self, client, registered):
        await client.post("/auth/api/verify_email", json={"one_time_token": registered})
        resp = await client.post(
            "/auth/api/verify_email", json={"one_time_token": registered}
        )
        assert resp.status_code == 400

    async def test_verify_email_from_different_user_cannot_verify_another(
        self, client, notification_queue
    ):
        await client.post(
            "/auth/api/register", json={"email": "a@example.com", "password": PASSWORD}
        )
        token_a = get_verify_token(notification_queue)
        await client.post(
            "/auth/api/register", json={"email": "b@example.com", "password": PASSWORD}
        )

        # Try to verify b@example.com with a's token
        resp = await client.post(
            "/auth/api/verify_email", json={"one_time_token": token_a}
        )
        # Token a still valid — verifies user a, not b
        assert resp.status_code == 200
