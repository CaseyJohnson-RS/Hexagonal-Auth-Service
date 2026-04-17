from typing import Optional
from fastapi import Request, Header

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/api/swagger_token")


def get_access_token(
    token: str = Depends(oauth2_scheme),
) -> str:
    return token


async def get_client_ip(request: Request) -> str:
    """Extract the client IP address"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"


async def get_user_agent(
    user_agent: Optional[str] = Header(None, alias="User-Agent")
) -> str:
    """Extract the User-Agent header"""
    return user_agent or "unknown"


async def get_location(
    cf_ipcountry: Optional[str] = Header(None, alias="CF-IPCountry"),  # Cloudflare
    x_country_code: Optional[str] = Header(None, alias="X-Country-Code"),  # Nginx GeoIP
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),  # Fallback
) -> Optional[str]:
    """
    Attempt to determine the client location from headers (no external requests).

    Works when behind:
    - Cloudflare (provides CF-IPCountry)
    - Nginx with GeoIP module (provides X-Country-Code)
    - Falls back to Accept-Language
    """
    # Cloudflare country code
    if cf_ipcountry and cf_ipcountry != "XX":
        return cf_ipcountry

    # Nginx GeoIP
    if x_country_code:
        return x_country_code

    # Accept-Language as a last resort
    if accept_language:
        # "en-US,en;q=0.9" -> "US"
        parts = accept_language.split(",")[0].split("-")
        if len(parts) > 1:
            return parts[1].upper()

    return None
