from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira.apis.responses.common import JiraAPIIssuePriorityResponse
from src.domain.models.jira.apis.responses.jira_issue import JiraIssueAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_sprint import JiraSprintAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO
from src.domain.models.jira_issue import JiraIssueModel, JiraIssuePriorityModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel


class JiraIssueMapper:
    """Mapper for Jira issue API responses to domain models"""

    @staticmethod
    def _map_user(user_response: JiraUserAPIGetResponseDTO) -> Optional[JiraUserModel]:
        try:
            avatar_url = ""
            if isinstance(user_response.avatar_urls, dict):
                avatar_url = user_response.avatar_urls.get("48x48", "")

            return JiraUserModel(
                jira_account_id=user_response.account_id,
                email=user_response.email_address or '',
                name=user_response.display_name,
                avatar_url=avatar_url,
                is_system_user=False,
                is_active=user_response.active
            )
        except Exception as e:
            log.error(f"Error mapping user response to domain: {str(e)}")
            # Return minimal valid model
            return JiraUserModel(
                jira_account_id=user_response.account_id,
                email='',
                name=user_response.display_name or '',
                avatar_url='',
                is_system_user=False
            )

    @staticmethod
    def _convert_adf_to_text(adf_data: Union[str, Dict[str, Any], None]) -> Optional[str]:
        """Convert Atlassian Document Format to plain text"""
        if adf_data is None:
            return None

        if isinstance(adf_data, str):
            return adf_data

        try:
            # Xử lý ADF object
            if isinstance(adf_data, dict):
                text_parts = []

                # Lấy text từ content
                if "content" in adf_data:
                    for content in adf_data["content"]:
                        if content.get("type") == "paragraph":
                            for text_node in content.get("content", []):
                                if text_node.get("type") == "text":
                                    text_parts.append(text_node.get("text", ""))

                return "\n".join(text_parts) if text_parts else None

            return str(adf_data)

        except Exception as e:
            log.error(f"Error converting ADF to text: {str(e)}")
            return None

    @staticmethod
    def to_domain(api_response: JiraIssueAPIGetResponseDTO) -> JiraIssueModel:
        try:
            fields = api_response.fields
            now = datetime.now(timezone.utc)

            # Đảm bảo truy cập các field từ fields object
            summary = fields.summary if hasattr(fields, 'summary') else ""
            description = JiraIssueMapper._convert_adf_to_text(fields.description)

            # Map user data
            assignee = None
            assignee_id = None
            reporter_id = None

            project_key = fields.project.key if hasattr(fields, 'project') and fields.project else ""

            if hasattr(fields, 'assignee') and fields.assignee:
                assignee_id = fields.assignee.account_id
                assignee = JiraIssueMapper._map_user(fields.assignee)

            if hasattr(fields, 'reporter') and fields.reporter:
                reporter_id = fields.reporter.account_id

            # Map sprints
            sprints: List[JiraSprintModel] = []
            if hasattr(fields, 'customfield_10020') and fields.customfield_10020:
                sprints = JiraIssueMapper._map_sprints(fields.customfield_10020, project_key)

            # Create link URL
            jira_base_url = settings.JIRA_DASHBOARD_URL
            # project_key = api_response.key.split("-")[0]
            current_sprint_id = sprints[0].board_id if sprints else 3
            current_sprint_id = 3
            link_url = f"{jira_base_url}/jira/software/projects/{project_key}/boards/{current_sprint_id}?selectedIssue={api_response.key}"

            return JiraIssueModel(
                jira_issue_id=api_response.id,
                key=api_response.key,
                project_key=project_key,
                summary=summary,
                description=description,
                type=JiraIssueType(fields.issuetype.name) if hasattr(fields, 'issuetype') else JiraIssueType.TASK,
                status=JiraIssueStatus(fields.status.name) if hasattr(fields, 'status') else JiraIssueStatus.TO_DO,
                assignee_id=assignee_id,
                reporter_id=reporter_id,
                estimate_point=fields.customfield_10016 or 0,
                actual_point=fields.customfield_10017 or 0,
                created_at=fields.created if hasattr(fields, 'created') else now,
                updated_at=fields.updated if hasattr(fields, 'updated') else now,
                sprints=sprints,
                link_url=link_url,
                last_synced_at=now,
                assignee=assignee
            )
        except Exception as e:
            log.error(f"Error mapping API response to domain issue: {str(e)}")
            raise

    @staticmethod
    def _map_priority(api_priority: JiraAPIIssuePriorityResponse) -> JiraIssuePriorityModel:
        return JiraIssuePriorityModel(
            id=api_priority.id,
            name=api_priority.name,
            icon_url=api_priority.iconUrl
        )

    @staticmethod
    def _map_sprint(api_sprint: JiraSprintAPIGetResponseDTO, project_key: str) -> Optional[JiraSprintModel]:
        try:
            now = datetime.now(timezone.utc)
            return JiraSprintModel(
                jira_sprint_id=api_sprint.id,
                name=api_sprint.name,
                state=api_sprint.state,
                start_date=JiraIssueMapper._parse_datetime(api_sprint.start_date),
                end_date=JiraIssueMapper._parse_datetime(api_sprint.end_date),
                complete_date=JiraIssueMapper._parse_datetime(api_sprint.complete_date),
                goal=api_sprint.goal,
                created_at=now,
                project_key=project_key
            )
        except Exception as e:
            log.error(f"Error mapping sprint: {str(e)}")
            return None

    @staticmethod
    def _map_sprints(api_sprints: List[JiraSprintAPIGetResponseDTO], project_key: str) -> List[JiraSprintModel]:
        if not api_sprints:
            return []
        return [JiraIssueMapper._map_sprint(sprint, project_key) for sprint in api_sprints if sprint]

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from Jira"""
        if dt_str is None:
            return None
        if dt_str.endswith('Z'):
            dt_str = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(dt_str)
