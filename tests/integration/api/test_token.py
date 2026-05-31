from tests.integration.api.conftest import EMAIL, PASSWORD


class TestRefreshToken:
    async def test_refresh_returns_new_token_pair(self, client, tokens):
        resp = await client.post(
            "/auth/api/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        new_tokens = resp.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

    async def test_refresh_returns_different_refresh_token(self, client, tokens):
        resp = await client.post(
            "/auth/api/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        new_tokens = resp.json()
        # Refresh token is random — always differs.
        # Access token may match if both are issued within the same second
        # (same JWT payload + same secret → same signature).
        assert new_tokens["refresh_token"] != tokens["refresh_token"]

    async def test_reuse_original_token_after_refresh_returns_400(self, client, tokens):
        original = tokens["refresh_token"]
        await client.post("/auth/api/refresh", json={"refresh_token": original})
        resp = await client.post("/auth/api/refresh", json={"refresh_token": original})
        assert resp.status_code == 400

    async def test_reuse_already_refreshed_token_returns_400(self, client, tokens):
        first = await client.post(
            "/auth/api/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        rotated = first.json()["refresh_token"]
        await client.post("/auth/api/refresh", json={"refresh_token": rotated})
        resp = await client.post("/auth/api/refresh", json={"refresh_token": rotated})
        assert resp.status_code == 400

    async def test_refresh_with_invalid_token_returns_400(self, client, verified):
        resp = await client.post(
            "/auth/api/refresh", json={"refresh_token": "completely-invalid"}
        )
        assert resp.status_code == 400

    async def test_refresh_chain_works_multiple_times(self, client, tokens):
        token = tokens["refresh_token"]
        for _ in range(3):
            resp = await client.post("/auth/api/refresh", json={"refresh_token": token})
            assert resp.status_code == 200
            token = resp.json()["refresh_token"]

    async def test_new_refresh_token_is_usable_for_another_refresh(self, client, tokens):
        first_refresh = await client.post(
            "/auth/api/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        new_token = first_refresh.json()["refresh_token"]
        second_refresh = await client.post(
            "/auth/api/refresh", json={"refresh_token": new_token}
        )
        assert second_refresh.status_code == 200


class TestRevokeToken:
    async def test_revoke_returns_200(self, client, tokens):
        resp = await client.post(
            "/auth/api/revoke", json={"refresh_token": tokens["refresh_token"]}
        )
        assert resp.status_code == 200

    async def test_revoked_token_cannot_be_refreshed(self, client, tokens):
        rt = tokens["refresh_token"]
        await client.post("/auth/api/revoke", json={"refresh_token": rt})
        resp = await client.post("/auth/api/refresh", json={"refresh_token": rt})
        assert resp.status_code == 400

    async def test_revoke_same_token_twice_returns_400(self, client, tokens):
        rt = tokens["refresh_token"]
        await client.post("/auth/api/revoke", json={"refresh_token": rt})
        resp = await client.post("/auth/api/revoke", json={"refresh_token": rt})
        assert resp.status_code == 400

    async def test_revoke_invalid_token_returns_400(self, client, verified):
        resp = await client.post(
            "/auth/api/revoke", json={"refresh_token": "no-such-token"}
        )
        assert resp.status_code == 400

    async def test_revoke_one_token_does_not_affect_another(self, client, verified):
        r1 = await client.post("/auth/api/token", json={"email": EMAIL, "password": PASSWORD})
        r2 = await client.post("/auth/api/token", json={"email": EMAIL, "password": PASSWORD})
        t1 = r1.json()["refresh_token"]
        t2 = r2.json()["refresh_token"]

        await client.post("/auth/api/revoke", json={"refresh_token": t1})

        resp = await client.post("/auth/api/refresh", json={"refresh_token": t2})
        assert resp.status_code == 200
