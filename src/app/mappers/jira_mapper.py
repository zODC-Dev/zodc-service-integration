from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.configs.logger import log
from src.domain.models.jira_project import JiraProjectModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.infrastructure.dtos.jira.project_responses import JiraAPIProjectResponse
from src.infrastructure.dtos.jira.sprint_responses import JiraAPISprintResponse
from src.infrastructure.dtos.jira.user_responses import JiraAPIUserResponse


class JiraProjectMapper:
    @staticmethod
    def to_domain(api_response: JiraAPIProjectResponse) -> JiraProjectModel:
        return JiraProjectModel(
            project_id=api_response.id,
            key=api_response.key,
            name=api_response.name,
            jira_project_id=api_response.id,
            avatar_url=api_response.avatarUrls.get("48x48", "")
        )


class JiraUserMapper:
    @staticmethod
    def to_domain(api_response: JiraAPIUserResponse) -> JiraUserModel:
        return JiraUserModel(
            jira_account_id=api_response.accountId,
            email=api_response.emailAddress,
            name=api_response.displayName,
            is_active=api_response.active,
            avatar_url=api_response.avatarUrls.get("48x48", "")
        )


class JiraSprintMapper:
    @staticmethod
    def to_domain(api_response: JiraAPISprintResponse) -> JiraSprintModel:
        try:
            now = datetime.now(timezone.utc)
            return JiraSprintModel(
                jira_sprint_id=api_response.id,
                name=api_response.name,
                state=api_response.state,
                start_date=api_response.startDate and api_response.startDate.replace(tzinfo=timezone.utc),
                end_date=api_response.endDate and api_response.endDate.replace(tzinfo=timezone.utc),
                complete_date=api_response.completeDate and api_response.completeDate.replace(tzinfo=timezone.utc),
                goal=api_response.goal,
                created_at=now
            )
        except Exception as e:
            log.error(f"Error mapping sprint response to domain: {str(e)}")
            return JiraSprintModel(
                jira_sprint_id=api_response.id,
                name=api_response.name,
                state=api_response.state,
                created_at=datetime.now(timezone.utc)
            )

    @classmethod
    def from_webhook_list(cls, sprint_data: Any) -> Optional[List[JiraSprintModel]]:
        """Map sprint data from webhook to domain models"""
        sprints = []

        # Handle case when input is a string (sprint name)
        if isinstance(sprint_data, str):
            log.info(f"Received sprint as string: {sprint_data}")
            # Chỉ lấy tên sprint, không đủ thông tin để tạo model đầy đủ
            return None

        # Handle list of sprint data
        if isinstance(sprint_data, list):
            for item in sprint_data:
                sprint = cls.from_webhook_item(item)
                if sprint:
                    sprints.append(sprint)

        return sprints if sprints else None

    @classmethod
    def from_webhook_item(cls, sprint_item: Any) -> Optional[JiraSprintModel]:
        """Map a single sprint item from webhook"""
        try:
            if not sprint_item or not isinstance(sprint_item, dict):
                return None

            # Extract required fields
            sprint_id = sprint_item.get('id')
            if not sprint_id:
                log.warning("Sprint data missing required field 'id'")
                return None

            now = datetime.now(timezone.utc)

            # Parse dates
            start_date = cls._parse_date(sprint_item.get('startDate'))
            end_date = cls._parse_date(sprint_item.get('endDate'))
            complete_date = cls._parse_date(sprint_item.get('completeDate'))

            # Get project key from various possible fields
            project_key = cls._extract_project_key(sprint_item)

            return JiraSprintModel(
                jira_sprint_id=int(sprint_id),
                name=sprint_item.get('name', f"Sprint {sprint_id}"),
                state=sprint_item.get('state', 'active'),
                start_date=start_date,
                end_date=end_date,
                complete_date=complete_date,
                goal=sprint_item.get('goal'),
                project_key=project_key,
                created_at=now
            )

        except Exception as e:
            log.error(f"Error mapping sprint from webhook: {str(e)}")
            return None

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string from Jira webhook"""
        if not date_str:
            return None

        try:
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            return datetime.fromisoformat(date_str)
        except Exception as e:
            log.warning(f"Failed to parse date '{date_str}': {str(e)}")
            return None

    @staticmethod
    def _extract_project_key(sprint_data: Dict[str, Any]) -> Optional[str]:
        """Extract project key from sprint data"""
        # Thử các trường khác nhau có thể chứa project key
        for field in ['originBoardId', 'originBoardProjectKey', 'projectKey']:
            if field in sprint_data and sprint_data[field]:
                return str(sprint_data[field])

        # Nếu không tìm thấy project key, log cảnh báo
        log.warning(f"Could not extract project key from sprint data: {sprint_data}")
        return None
