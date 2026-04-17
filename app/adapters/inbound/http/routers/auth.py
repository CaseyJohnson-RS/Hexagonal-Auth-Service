from fastapi import APIRouter, Depends, Form, HTTPException, status

from app.adapters.inbound.http.routers.schemas import (
    RefreshTokenModel,
    TokenResponse,
    ChangePasswordModel,
    LoginUserModel,
)
from app.application.cases.user import (
    ChangePasswordCase,
    PasswordRecoverCase,
    PasswordRecoverRequestCase,
    RegisterUserCase,
    VerifyEmailCase,
    LoginUserCase,
    RefreshTokenCase,
    RevokeTokenCase,
)
from app.application.dto.user import (
    ChangePasswordInputDTO,
    LoginUserInputDTO,
    PasswordRecoverInputDTO,
    PasswordRecoverRequestInputDTO,
    RefreshTokenInputDTO,
    RegisterUserInputDTO,
    RevokeRefreshTokenInputDTO,
    VerifyEmailInputDTO,
)
from app.core.domain.exceptions import BaseError

from .dependencies.cases import build_use_case
from .dependencies.security import (
    get_access_token,
    get_client_ip,
    get_location,
    get_user_agent,
)


router = APIRouter()


# Build use case factories at import time
get_register_use_case = build_use_case(RegisterUserCase)
get_verify_email_use_case = build_use_case(VerifyEmailCase)
get_login_use_case = build_use_case(LoginUserCase)
get_refresh_token_use_case = build_use_case(RefreshTokenCase)
get_revoke_token_use_case = build_use_case(RevokeTokenCase)
get_change_password_use_case = build_use_case(ChangePasswordCase)
get_password_recover_request_use_case = build_use_case(PasswordRecoverRequestCase)
get_password_recover_use_case = build_use_case(PasswordRecoverCase)


def domain_error(
    exc: BaseError,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> HTTPException:
    return HTTPException(status_code=status_code, detail=str(exc))


def token_response(result) -> TokenResponse:
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type="bearer",
    )


# ─────────────────────────── USER ───────────────────────────


@router.post("/register", tags=["register"])
async def register_user(
    data: RegisterUserInputDTO,
    use_case: RegisterUserCase = Depends(get_register_use_case),
):
    try:
        return await use_case.execute(data)
    except BaseError as e:
        raise domain_error(e)


@router.post("/verify_email", tags=["register"])
async def verify_email(
    data: VerifyEmailInputDTO,
    use_case: VerifyEmailCase = Depends(get_verify_email_use_case),
):
    try:
        return await use_case.execute(data)
    except BaseError as e:
        raise domain_error(e)


# ─────────────────────────── TOKEN ───────────────────────────


@router.post("/token", response_model=TokenResponse, tags=["token"])
async def login(
    data: LoginUserModel,
    client_ip: str | None = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
    location: str | None = Depends(get_location),
    use_case: LoginUserCase = Depends(get_login_use_case),
):
    case_data = LoginUserInputDTO(
        email=data.email,
        password=data.password,
        client_ip=client_ip,
        user_agent=user_agent,
        location=location,
    )
    try:
        return token_response(await use_case.execute(case_data))
    except BaseError as e:
        raise domain_error(e, status.HTTP_401_UNAUTHORIZED)


@router.post("/refresh", response_model=TokenResponse, tags=["token"])
async def refresh_token(
    data: RefreshTokenModel,
    client_ip: str | None = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
    location: str | None = Depends(get_location),
    use_case: RefreshTokenCase = Depends(get_refresh_token_use_case),
):
    case_data = RefreshTokenInputDTO(
        refresh_token=data.refresh_token,
        client_ip=client_ip,
        user_agent=user_agent,
        location=location,
    )
    try:
        return token_response(await use_case.execute(case_data))
    except BaseError as e:
        raise domain_error(e)


@router.post("/revoke", tags=["token"])
async def revoke_token(
    data: RefreshTokenModel,
    client_ip: str | None = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
    location: str | None = Depends(get_location),
    use_case: RevokeTokenCase = Depends(get_revoke_token_use_case),
):
    case_data = RevokeRefreshTokenInputDTO(
        refresh_token=data.refresh_token,
        client_ip=client_ip,
        user_agent=user_agent,
        location=location,
    )
    try:
        await use_case.execute(case_data)
    except BaseError as e:
        raise domain_error(e)


# ─────────────────────────── PASSWORD ───────────────────────────


@router.post("/password/change", tags=["password"])
async def change_password(
    data: ChangePasswordModel,
    access_token: str = Depends(get_access_token),
    use_case: ChangePasswordCase = Depends(get_change_password_use_case),
):
    case_data = ChangePasswordInputDTO(
        access_token=access_token,
        old_password=data.old_password,
        new_password=data.new_password,
    )
    try:
        await use_case.execute(case_data)
    except BaseError as e:
        raise domain_error(e)


@router.post("/password/recover_request", tags=["password"])
async def request_password_recover(
    data: PasswordRecoverRequestInputDTO,
    use_case: PasswordRecoverRequestCase = Depends(
        get_password_recover_request_use_case
    ),
):
    try:
        await use_case.execute(data)
    except BaseError:
        # intentionally silent to avoid user enumeration
        pass


@router.post("/password/recover", tags=["password"])
async def password_recover(
    data: PasswordRecoverInputDTO,
    use_case: PasswordRecoverCase = Depends(get_password_recover_use_case),
):
    try:
        await use_case.execute(data)
    except BaseError as e:
        raise domain_error(e)


# ─────────────────────────── SWAGGER ───────────────────────────


@router.post(
    "/swagger_token",
    response_model=TokenResponse,
    include_in_schema=False,
)
async def swagger_token(
    username: str = Form(default="example@gmail.com"),
    password: str = Form(default="password"),
    client_ip: str | None = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
    location: str | None = Depends(get_location),
    use_case: LoginUserCase = Depends(get_login_use_case),
):
    case_data = LoginUserInputDTO(
        email=username,
        password=password,
        client_ip=client_ip,
        user_agent=user_agent,
        location=location,
    )
    try:
        return token_response(await use_case.execute(case_data))
    except BaseError as e:
        raise domain_error(e, status.HTTP_401_UNAUTHORIZED)
