from datetime import datetime
from typing import Any, Dict, Optional

from src.configs.logger import log
from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO


class JiraSprintWebhookMapper:
    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from Jira"""
        if not dt_str:
            return None
        try:
            if dt_str.endswith('Z'):
                dt_str = dt_str.replace('Z', '+00:00')
            return datetime.fromisoformat(dt_str)
        except Exception as e:
            log.error(f"Error parsing datetime {dt_str}: {str(e)}")
            return None

    @classmethod
    def extract_changes_from_changelog(cls, webhook_data: JiraWebhookResponseDTO) -> Dict[str, Any]:
        """Extract sprint changes from changelog in webhook data"""
        changes: Dict[str, Any] = {}

        try:
            if not hasattr(webhook_data, 'changelog') or not webhook_data.changelog:
                return changes

            for item in webhook_data.changelog.items:
                field = item.field

                if field == "status" or field == "state":
                    changes["state"] = item.toString
                elif field == "startDate":
                    changes["start_date"] = cls._parse_datetime(item.toString)
                elif field == "endDate":
                    changes["end_date"] = cls._parse_datetime(item.toString)
                elif field == "completeDate":
                    changes["complete_date"] = cls._parse_datetime(item.toString)
                elif field == "name":
                    changes["name"] = item.toString
                elif field == "goal":
                    changes["goal"] = item.toString

            return changes
        except Exception as e:
            log.error(f"Error extracting sprint changes from changelog: {str(e)}")
            return {}
