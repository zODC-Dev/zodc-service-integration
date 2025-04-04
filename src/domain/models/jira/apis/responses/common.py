from .base import JiraAPIResponseBase


class JiraAPIIssuePriorityResponse(JiraAPIResponseBase):
    id: str
    name: str
    iconUrl: str

    class Config:
        extra = "allow"
