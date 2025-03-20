from pydantic import BaseModel


class UserEventDTO(BaseModel):
    user_id: int
    event_type: str


class MicrosoftLoginEventDTO(BaseModel):
    user_id: int
    email: str
    access_token: str
    refresh_token: str
    expires_in: int


class JiraLoginEventDTO(BaseModel):
    user_id: int
    email: str
    access_token: str
    refresh_token: str
    cloud_id: str
    site_url: str
    account_id: str
    scope: str
