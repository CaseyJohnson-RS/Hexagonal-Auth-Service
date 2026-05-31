from datetime import timedelta
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):

    # Postgres configuration
    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr
    postgres_host: str
    postgres_port: int
    postgres_echo: bool = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://"
            f"{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Service configuration
    trust_proxy: bool = False
    email_token_length: int = 32
    email_token_expiry_minutes: int = 720
    jwt_secret: str = "super_secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_length: int = 32
    refresh_token_expiry_hours: int = 336
    password_recover_token_length: int = 32
    password_recover_token_expiry_minutes: int = 15

    @property
    def email_token_expiry(self) -> timedelta:
        return timedelta(minutes=self.email_token_expiry_minutes)

    @property
    def access_token_expiry(self) -> timedelta:
        return timedelta(minutes=self.access_token_expire_minutes)

    @property
    def refresh_token_expiry(self) -> timedelta:
        return timedelta(hours=self.refresh_token_expiry_hours)

    @property
    def password_recover_token_expiry(self) -> timedelta:
        return timedelta(minutes=self.password_recover_token_expiry_minutes)

    # Redis configuration
    redis_url: str = "redis://localhost:6379/0"

    # General settings
    logging_level: str = "INFO"

    model_config = SettingsConfigDict(extra="ignore")


# MyPy is still stupid about pydantic settings
settings = Settings()  # type: ignore[call-arg]
