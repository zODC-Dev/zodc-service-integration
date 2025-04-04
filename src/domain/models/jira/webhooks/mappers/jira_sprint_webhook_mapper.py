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

    # @classmethod
    # def map_to_update_dto(cls, webhook_data: JiraWebhookResponseDTO) -> JiraSprintDBUpdateDTO:
    #     """Map webhook data to JiraSprintDBUpdateDTO for update operations"""
    #     try:
    #         sprint = webhook_data.sprint
    #         update_dto = JiraSprintDBUpdateDTO(
    #             state=sprint.state,
    #             name=sprint.name,
    #             start_date=cls._parse_datetime(sprint.start_date if hasattr(sprint, 'start_date') else None),
    #             end_date=cls._parse_datetime(sprint.end_date if hasattr(sprint, 'end_date') else None),
    #             complete_date=cls._parse_datetime(sprint.complete_date if hasattr(sprint, 'complete_date') else None),
    #             goal=sprint.goal if hasattr(sprint, 'goal') else None,
    #             updated_at=datetime.now(timezone.utc)
    #         )

    #         return update_dto
    #     except Exception as e:
    #         log.error(f"Error mapping sprint update data: {str(e)}")
    #         raise

    @classmethod
    def extract_changes_from_changelog(cls, webhook_data: JiraWebhookResponseDTO) -> Dict[str, Any]:
        """Extract sprint changes from changelog in webhook data"""
        changes = {}

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
