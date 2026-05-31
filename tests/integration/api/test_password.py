from tests.integration.api.conftest import EMAIL, PASSWORD, get_recover_token


class TestChangePassword:
    NEW_PASSWORD = "NewStrongPass99!"

    async def test_change_password_returns_200(self, client, tokens):
        resp = await client.post(
            "/auth/api/password/change",
            json={"old_password": PASSWORD, "new_password": self.NEW_PASSWORD},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200

    async def test_change_password_allows_login_with_new_password(self, client, tokens):
        await client.post(
            "/auth/api/password/change",
            json={"old_password": PASSWORD, "new_password": self.NEW_PASSWORD},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        resp = await client.post(
            "/auth/api/token", json={"email": EMAIL, "password": self.NEW_PASSWORD}
        )
        assert resp.status_code == 200

    async def test_change_password_blocks_old_password_login(self, client, tokens):
        await client.post(
            "/auth/api/password/change",
            json={"old_password": PASSWORD, "new_password": self.NEW_PASSWORD},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        resp = await client.post(
            "/auth/api/token", json={"email": EMAIL, "password": PASSWORD}
        )
        assert resp.status_code == 401

    async def test_change_password_wrong_old_password_returns_400(self, client, tokens):
        resp = await client.post(
            "/auth/api/password/change",
            json={"old_password": "WrongOldPass!", "new_password": self.NEW_PASSWORD},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 400

    async def test_change_password_same_password_returns_400(self, client, tokens):
        resp = await client.post(
            "/auth/api/password/change",
            json={"old_password": PASSWORD, "new_password": PASSWORD},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 400

    async def test_change_password_no_auth_header_returns_401(self, client, verified):
        resp = await client.post(
            "/auth/api/password/change",
            json={"old_password": PASSWORD, "new_password": self.NEW_PASSWORD},
        )
        assert resp.status_code == 401

    async def test_change_password_invalid_bearer_token_returns_400(self, client, verified):
        # InvalidAccessToken is a BaseError caught by domain_error() → 400.
        # Only a missing Authorization header triggers 401.
        resp = await client.post(
            "/auth/api/password/change",
            json={"old_password": PASSWORD, "new_password": self.NEW_PASSWORD},
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert resp.status_code == 400

    async def test_change_password_short_new_password_returns_400(self, client, tokens):
        resp = await client.post(
            "/auth/api/password/change",
            json={"old_password": PASSWORD, "new_password": "abc"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 400


class TestPasswordRecoverRequest:
    async def test_recover_request_returns_200_for_existing_user(
        self, client, verified, notification_queue
    ):
        resp = await client.post(
            "/auth/api/password/recover_request", json={"email": EMAIL}
        )
        assert resp.status_code == 200

    async def test_recover_request_emits_event_with_token(
        self, client, verified, notification_queue
    ):
        await client.post(
            "/auth/api/password/recover_request", json={"email": EMAIL}
        )
        token = get_recover_token(notification_queue)
        assert token

    async def test_recover_request_returns_200_for_nonexistent_user(self, client):
        # Silent to prevent user enumeration
        resp = await client.post(
            "/auth/api/password/recover_request",
            json={"email": "ghost@example.com"},
        )
        assert resp.status_code == 200

    async def test_recover_request_for_unverified_user_returns_200(
        self, client, registered
    ):
        # Silent – domain error swallowed at router level
        resp = await client.post(
            "/auth/api/password/recover_request", json={"email": EMAIL}
        )
        assert resp.status_code == 200


class TestPasswordRecover:
    NEW_PASSWORD = "RecoveredPass99!"

    async def _get_recover_token(self, client, notification_queue):
        await client.post(
            "/auth/api/password/recover_request", json={"email": EMAIL}
        )
        return get_recover_token(notification_queue)

    async def test_recover_returns_200(self, client, verified, notification_queue):
        token = await self._get_recover_token(client, notification_queue)
        resp = await client.post(
            "/auth/api/password/recover",
            json={"password_recover_token": token, "password": self.NEW_PASSWORD},
        )
        assert resp.status_code == 200

    async def test_recover_allows_login_with_new_password(
        self, client, verified, notification_queue
    ):
        token = await self._get_recover_token(client, notification_queue)
        await client.post(
            "/auth/api/password/recover",
            json={"password_recover_token": token, "password": self.NEW_PASSWORD},
        )
        resp = await client.post(
            "/auth/api/token", json={"email": EMAIL, "password": self.NEW_PASSWORD}
        )
        assert resp.status_code == 200

    async def test_recover_blocks_old_password(self, client, verified, notification_queue):
        token = await self._get_recover_token(client, notification_queue)
        await client.post(
            "/auth/api/password/recover",
            json={"password_recover_token": token, "password": self.NEW_PASSWORD},
        )
        resp = await client.post(
            "/auth/api/token", json={"email": EMAIL, "password": PASSWORD}
        )
        assert resp.status_code == 401

    async def test_recover_with_invalid_token_returns_400(self, client, verified):
        resp = await client.post(
            "/auth/api/password/recover",
            json={"password_recover_token": "bad-token", "password": self.NEW_PASSWORD},
        )
        assert resp.status_code == 400

    async def test_recover_with_short_password_returns_400(
        self, client, verified, notification_queue
    ):
        token = await self._get_recover_token(client, notification_queue)
        resp = await client.post(
            "/auth/api/password/recover",
            json={"password_recover_token": token, "password": "abc"},
        )
        assert resp.status_code == 400

    async def test_recover_token_cannot_be_reused(
        self, client, verified, notification_queue
    ):
        token = await self._get_recover_token(client, notification_queue)
        await client.post(
            "/auth/api/password/recover",
            json={"password_recover_token": token, "password": self.NEW_PASSWORD},
        )
        resp = await client.post(
            "/auth/api/password/recover",
            json={"password_recover_token": token, "password": "AnotherPass99!"},
        )
        assert resp.status_code == 400
