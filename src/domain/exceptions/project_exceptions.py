class ProjectError(Exception):
    """Base exception for project-related errors."""
    pass


class ProjectNotFoundError(ProjectError):
    """Exception raised when a project is not found."""
    pass


class ProjectKeyAlreadyExistsError(ProjectError):
    """Exception raised when trying to create a project with an existing key."""
    pass
