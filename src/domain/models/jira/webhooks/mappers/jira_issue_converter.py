from datetime import datetime, timezone

from src.domain.models.database.jira_issue import JiraIssueDBCreateDTO, JiraIssueDBUpdateDTO
from src.domain.models.jira_issue import JiraIssueModel


class JiraIssueConverter:
    @staticmethod
    def _convert_to_create_dto(issue_data: JiraIssueModel) -> JiraIssueDBCreateDTO:
        """Convert JiraIssueModel to JiraIssueDBCreateDTO"""
        return JiraIssueDBCreateDTO(
            jira_issue_id=issue_data.jira_issue_id,
            key=issue_data.key,
            summary=issue_data.summary,
            description=issue_data.description,
            status=issue_data.status,
            type=issue_data.type,
            assignee_id=issue_data.assignee_id,
            reporter_id=issue_data.reporter_id,
            estimate_point=issue_data.estimate_point,
            actual_point=issue_data.actual_point,
            created_at=issue_data.created_at,
            updated_at=issue_data.updated_at,
            priority=issue_data.priority,
            link_url=issue_data.link_url,
            project_key=issue_data.project_key,
            sprints=issue_data.sprints,
            is_system_linked=issue_data.is_system_linked or False
        )

    @staticmethod
    def _convert_to_update_dto(issue_data: JiraIssueModel) -> JiraIssueDBUpdateDTO:
        """Convert JiraIssueModel to JiraIssueDBUpdateDTO"""
        return JiraIssueDBUpdateDTO(
            summary=issue_data.summary,
            description=issue_data.description,
            status=issue_data.status.value,
            type=issue_data.type,
            assignee_id=issue_data.assignee_id,
            reporter_id=issue_data.reporter_id,
            estimate_point=issue_data.estimate_point,
            actual_point=issue_data.actual_point,
            priority=issue_data.priority,
            updated_at=datetime.now(timezone.utc),
            last_synced_at=datetime.now(timezone.utc),
            link_url=issue_data.link_url,
            sprints=issue_data.sprints
        )
