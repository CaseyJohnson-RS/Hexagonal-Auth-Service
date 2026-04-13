from datetime import timedelta
from typing import Protocol


class ConfigPort(Protocol):

    # Email token

    def email_token_len(self) -> int:
        pass

    def email_token_exp(self) -> timedelta:
        pass

    # Access token

    def access_token_exp(self) -> timedelta:
        pass

    # Refresh token

    def refresh_token_len(self) -> int:
        pass

    def refresh_token_exp(self) -> timedelta:
        pass

    # Password recover token

    def password_recover_token_len(self) -> int:
        pass

    def password_recover_token_exp(self) -> timedelta:
        pass
