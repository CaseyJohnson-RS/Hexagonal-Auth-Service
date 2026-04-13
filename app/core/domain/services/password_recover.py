from datetime import timedelta
from typing import Tuple

from app.core.domain.entities.user import User
from app.core.domain.entities.one_time_token import OneTimeToken, OneTimeTokenPurpose


class PasswordRecoverService:

    @staticmethod
    def request_password_recover(
        user: User, token_length: int, token_expiry: timedelta
    ) -> Tuple[OneTimeToken, str]:
        # 1. Create the recover token
        token, token_string = OneTimeToken.create(
            user_id=user.id,
            token_length=token_length,
            expiry=token_expiry,
            purpose=OneTimeTokenPurpose.RECOVER_PASSWORD,
        )

        # 2. Notify the user aggregate about the new password recover request
        user.request_password_recover(token_string)

        return token, token_string
