class AuthenticationError(Exception):
    """Base authentication error"""
    pass

class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials provided"""
    pass

class UserNotFoundError(AuthenticationError):
    """User not found"""
    pass

class TokenError(AuthenticationError):
    """Base token error"""
    pass

class TokenExpiredError(TokenError):
    """Token has expired"""
    pass

class InvalidTokenError(TokenError):
    """Token is invalid"""
    pass

class SSOError(AuthenticationError):
    """Base SSO error"""
    pass
