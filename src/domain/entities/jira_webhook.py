from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class JiraWebhookEvent(BaseModel):
    """Entity representing a Jira webhook event"""
    webhook_event: str
    timestamp: datetime
    issue_id: Optional[str]
    issue_key: Optional[str]
    issue_summary: Optional[str]
    project_key: Optional[str]
    user_account_id: Optional[str]
    user_display_name: Optional[str]
    changelog: Optional[Dict[str, Any]]
    raw_data: Dict[str, Any]

    @classmethod
    def from_webhook_payload(cls, payload: Dict[str, Any]) -> "JiraWebhookEvent":
        """Create JiraWebhookEvent from raw webhook payload"""
        issue_data = payload.get("issue", {})
        user_data = payload.get("user", {})

        return cls(
            webhook_event=payload.get("webhookEvent", ""),
            timestamp=datetime.now(),
            issue_id=issue_data.get("id"),
            issue_key=issue_data.get("key"),
            issue_summary=issue_data.get("fields", {}).get("summary"),
            project_key=issue_data.get("fields", {}).get("project", {}).get("key"),
            user_account_id=user_data.get("accountId"),
            user_display_name=user_data.get("displayName"),
            changelog=payload.get("changelog"),
            raw_data=payload
        )
