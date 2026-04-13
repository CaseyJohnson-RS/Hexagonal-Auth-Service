from . import DomainError


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class TokenError(DomainError):
    message = "Invalid email token"


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


class RefreshTokenReuse(TokenError):
    message = "Refresh token replaced by another token"


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class InvalidAccessToken(TokenError):
    message = "Invalid access token"


class AccessTokenExpired(TokenError):
    message = "Access token expired"
