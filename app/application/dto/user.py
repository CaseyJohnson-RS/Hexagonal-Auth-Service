from pydantic import BaseModel, SkipValidation, Field
from app.core.domain.validators.password import min_password_len, max_password_len


# === INPUTS ==================================================================


class RegisterUserInputDTO(BaseModel):
    email: SkipValidation[str] = Field(default="example@gmail.com")
    password: SkipValidation[str] = Field(
        default="password",
        min_length=min_password_len,
        max_length=max_password_len,
    )


class VerifyEmailInputDTO(BaseModel):
    one_time_token: SkipValidation[str] = Field(default="one_time_token")


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class LoginUserInputDTO(BaseModel):
    email: SkipValidation[str] = Field(default="example@gmail.com")
    password: SkipValidation[str] = Field(
        default="password",
        min_length=min_password_len,
        max_length=max_password_len,
    )
    client_ip: SkipValidation[str | None] = Field(default=None)
    user_agent: SkipValidation[str | None] = Field(default=None)
    location: SkipValidation[str | None] = Field(default=None)


class RefreshTokenInputDTO(BaseModel):
    refresh_token: SkipValidation[str]
    client_ip: SkipValidation[str]
    user_agent: SkipValidation[str]
    location: SkipValidation[str | None]


class RevokeRefreshTokenInputDTO(BaseModel):
    refresh_token: SkipValidation[str]
    client_ip: SkipValidation[str | None]
    user_agent: SkipValidation[str | None]
    location: SkipValidation[str | None]


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class ChangePasswordInputDTO(BaseModel):
    access_token: SkipValidation[str]
    old_password: SkipValidation[str] = Field(
        default="password",
        min_length=min_password_len,
        max_length=max_password_len,
    )
    new_password: SkipValidation[str] = Field(
        default="new_password",
        min_length=min_password_len,
        max_length=max_password_len,
    )


class PasswordRecoverRequestInputDTO(BaseModel):
    email: SkipValidation[str] = Field(default="example@gmail.com")


class PasswordRecoverInputDTO(BaseModel):
    password_recover_token: SkipValidation[str]
    password: SkipValidation[str] = Field(
        default="new_password",
        min_length=min_password_len,
        max_length=max_password_len,
    )


# === OUTPUTS ==================================================================


class TokenPairDTO(BaseModel):
    access_token: str
    refresh_token: str


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
