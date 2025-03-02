class UserError(Exception):
    """Base exception for user-related errors"""
    pass

class UserNotFoundError(UserError):
    """Raised when a user is not found"""
    pass

class UserAlreadyExistsError(UserError):
    """Raised when trying to create a user that already exists"""
    pass

class UserInactiveError(UserError):
    """Raised when trying to access an inactive user"""
    pass

class InvalidUserDataError(UserError):
    """Raised when user data is invalid"""
    pass

class UserPermissionError(UserError):
    """Raised when user doesn't have required permissions"""
    pass

class UserUpdateError(UserError):
    """Raised when user update fails"""
    pass

class UserDeletionError(UserError):
    """Raised when user deletion fails"""
    pass

class UserCreationError(UserError):
    """Raised when user creation fails"""
    pass
