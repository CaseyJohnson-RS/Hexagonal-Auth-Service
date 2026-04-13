from pydantic import BaseModel, Field


class RefreshTokenModel(BaseModel):
    refresh_token: str


class LoginUserModel(BaseModel):
    email: str = Field(default="example@gmail.com")
    password: str = Field(default="password")


class ChangePasswordModel(BaseModel):
    old_password: str = Field(default="old_password")
    new_password: str = Field(default="new_password")


class TokenResponse(BaseModel):
    refresh_token: str
    access_token: str
    token_type: str = Field(default="bearer")