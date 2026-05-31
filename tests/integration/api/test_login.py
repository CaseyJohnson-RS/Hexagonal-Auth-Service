from tests.integration.api.conftest import EMAIL, PASSWORD


class TestLogin:
    async def test_login_returns_token_pair(self, client, tokens):
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

    async def test_login_access_token_is_non_empty(self, client, tokens):
        assert tokens["access_token"]

    async def test_login_refresh_token_is_non_empty(self, client, tokens):
        assert tokens["refresh_token"]

    async def test_login_before_verify_returns_401(self, client, registered):
        resp = await client.post(
            "/auth/api/token", json={"email": EMAIL, "password": PASSWORD}
        )
        assert resp.status_code == 401

    async def test_login_wrong_password_returns_401(self, client, verified):
        resp = await client.post(
            "/auth/api/token", json={"email": EMAIL, "password": "WrongPassword!"}
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user_returns_401(self, client):
        resp = await client.post(
            "/auth/api/token",
            json={"email": "nobody@example.com", "password": "SomePass123!"},
        )
        assert resp.status_code == 401

    async def test_login_wrong_password_does_not_reveal_user_existence(self, client, verified):
        wrong_pass = await client.post(
            "/auth/api/token", json={"email": EMAIL, "password": "WrongPass!"}
        )
        no_user = await client.post(
            "/auth/api/token",
            json={"email": "ghost@example.com", "password": "WrongPass!"},
        )
        assert wrong_pass.status_code == no_user.status_code == 401

    async def test_login_twice_returns_different_refresh_tokens(self, client, verified):
        r1 = await client.post("/auth/api/token", json={"email": EMAIL, "password": PASSWORD})
        r2 = await client.post("/auth/api/token", json={"email": EMAIL, "password": PASSWORD})
        assert r1.json()["refresh_token"] != r2.json()["refresh_token"]

    async def test_login_case_sensitive_email(self, client, verified):
        resp = await client.post(
            "/auth/api/token",
            json={"email": EMAIL.upper(), "password": PASSWORD},
        )
        assert resp.status_code == 401
