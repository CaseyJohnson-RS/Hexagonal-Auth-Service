from datetime import timedelta
from typing import Tuple

from app.core.domain.entities.user import User
from app.core.domain.entities.one_time_token import OneTimeToken, OneTimeTokenPurpose


class EmailVerificationService:
    """
    Domain service responsible for coordinating email verification
    for User aggregates.
    """

    @staticmethod
    def request_verification(
        user: User, token_length: int, token_expiry: timedelta
    ) -> Tuple[OneTimeToken, str]:
        """
        Generate a one-time email verification token and notify the user aggregate.

        Args:
            user (User): The user to verify.
            token_length (int): Length of the token string to generate.
            token_expiry (timedelta): Expiration duration for the token.

        Returns:
            Tuple[OneTimeToken, str]: The created token and the raw token string.
        """
        # 1. Create the verification token
        token, token_string = OneTimeToken.create(
            user_id=user.id,
            token_length=token_length,
            expiry=token_expiry,
            purpose=OneTimeTokenPurpose.VERIFY_EMAIL,
        )

        # 2. Notify the user aggregate about the new verification request
        user.request_email_verification(token_string)

        return token, token_string
