class CalendarError(Exception):
    """Base class for exceptions in the calendar module."""
    pass


class CalendarFetchError(CalendarError):
    """Exception raised when there is an error fetching calendar events."""

    pass


class CalendarAPIError(CalendarError):
    """Exception raised when there is an error returned from the Microsoft Graph API."""

    pass


class CalendarTokenError(CalendarError):
    """Exception raised when there is an error fetching or refreshing the access token."""

    pass
