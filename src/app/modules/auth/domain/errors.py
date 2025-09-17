class AuthError(Exception):
    pass

class InvalidCredentials(AuthError):
    pass

class TokenExpired(AuthError):
    pass

class TokenInvalid(AuthError):
    pass