from app.core.ports.config import ConfigPort
from app.config.settings import settings


class Config(ConfigPort):

    def email_token_exp(self):
        return settings.email_token_expiry

    def email_token_len(self):
        return settings.email_token_length

    def access_token_exp(self):
        return settings.access_token_expiry

    def refresh_token_len(self):
        return settings.refresh_token_length

    def refresh_token_exp(self):
        return settings.refresh_token_expiry

    def password_recover_token_len(self):
        return settings.password_recover_token_length

    def password_recover_token_exp(self):
        return settings.password_recover_token_expiry
