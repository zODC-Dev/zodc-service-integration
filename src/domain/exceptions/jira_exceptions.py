class JiraError(Exception):
    """Base exception for Jira-related errors"""
    pass

class JiraConnectionError(JiraError):
    """Failed to connect to Jira API"""
    pass

class JiraAuthenticationError(JiraError):
    """Authentication failed with Jira API"""
    pass

class JiraRequestError(JiraError):
    """Error occurred during Jira API request"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Jira API request failed with status {status_code}: {message}") 