from datetime import timedelta
from typing import Tuple

from app.core.domain.entities.refresh_token import RefreshToken
from app.core.ports.services.access_token_issuer import AccessTokenIssuerPort


class RefreshTokenRotationService:
    """
    Stateless domain service for rotating refresh tokens and issuing access tokens.
    """

    @staticmethod
    def rotate(
        old_token: RefreshToken,
        refresh_token_length: int,
        refresh_token_expiry: timedelta,
        access_token_expiry: timedelta,
        access_token_issuer: AccessTokenIssuerPort,
    ) -> Tuple[RefreshToken, str, str]:
        """
        Rotate a refresh token and issue a new access token.

        Args:
            old_token (RefreshToken): The token to rotate.
            config (ConfigPort): Configuration provider for token lengths and expirations.
            access_token_issuer (AccessTokenIssuerPort): Service to issue access tokens.

        Returns:
            Tuple[RefreshToken, str, str]: New refresh token, raw refresh token string, and new access token.
        """
        # 1. Create new refresh token
        new_rt, new_rt_str = RefreshToken.create(
            user_id=old_token.user_id,
            token_length=refresh_token_length,
            expiry=refresh_token_expiry,
        )

        # 2. Mark old token as replaced
        old_token.mark_as_replaced_by(old_token.id)

        # 3. Issue new access token
        access_token = access_token_issuer.issue(
            old_token.user_id, access_token_expiry
        )

        return new_rt, new_rt_str, access_token
