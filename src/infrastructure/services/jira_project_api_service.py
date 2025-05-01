from typing import List, Optional

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.jira import JiraIssueType
from src.domain.models.jira.apis.mappers.jira_issue import JiraIssueMapper
from src.domain.models.jira.apis.mappers.jira_project import JiraProjectMapper
from src.domain.models.jira.apis.mappers.jira_sprint import JiraSprintMapper
from src.domain.models.jira.apis.mappers.jira_user import JiraUserMapper
from src.domain.models.jira.apis.responses.jira_issue import JiraIssueAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_project import JiraProjectAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_sprint import JiraSprintAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_project import JiraProjectModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.infrastructure.services.jira_service import JiraAPIClient


class JiraProjectAPIService(IJiraProjectAPIService):
    """Service để tương tác với Jira Project API"""

    def __init__(
        self,
        jira_api_client: JiraAPIClient,
        user_repository: IJiraUserRepository
    ):
        self.client = jira_api_client
        self.user_repository = user_repository
        self.base_url = settings.JIRA_BASE_URL

    async def get_project_details(self, user_id: int, project_key: str) -> JiraProjectModel:
        """Lấy thông tin chi tiết dự án từ Jira API"""
        response_data = await self.client.get(
            f"/rest/api/3/project/{project_key}",
            user_id,
            error_msg=f"Lỗi khi lấy thông tin dự án {project_key}"
        )

        return await self.client.map_to_domain(
            response_data,
            JiraProjectAPIGetResponseDTO,
            JiraProjectMapper
        )

    async def get_project_users(self, user_id: int, project_key: str) -> List[JiraUserModel]:
        """Get all users in a project from Jira API"""
        response_data = await self.client.get(
            "/rest/api/3/user/assignable/search",
            user_id,
            params={"project": project_key},
            error_msg=f"Error fetching users for project {project_key}"
        )

        # log.info(f"Response data via get_project_users: {response_data}")

        users: List[JiraUserModel] = []
        for user_data in response_data:
            user: JiraUserModel = await self.client.map_to_domain(
                user_data,
                JiraUserAPIGetResponseDTO,
                JiraUserMapper
            )
            users.append(user)

        return users

    async def get_project_sprints(self, user_id: int, project_key: str) -> List[JiraSprintModel]:
        """Get all sprints for a project from Jira API"""
        # First get board ID for the project
        board_response = await self.client.get(
            "/rest/agile/1.0/board",
            user_id,
            params={"projectKeyOrId": project_key},
            error_msg=f"Error fetching board for project {project_key}"
        )

        if not board_response.get("values"):
            return []

        board_id = board_response["values"][0]["id"]

        # Sau đó lấy sprints cho board
        sprint_response = await self.client.get(
            f"/rest/agile/1.0/board/{board_id}/sprint",
            user_id,
            error_msg=f"Error fetching sprints for board {board_id}"
        )

        sprints: List[JiraSprintModel] = []
        for sprint_data in sprint_response.get("values", []):
            sprint: JiraSprintModel = await self.client.map_to_domain(
                sprint_data,
                JiraSprintAPIGetResponseDTO,
                JiraSprintMapper
            )
            sprints.append(sprint)

        return sprints

    async def get_accessible_projects(self, user_id: int) -> List[JiraProjectModel]:
        """Get all projects that the user has access to"""
        response_data = await self.client.get(
            "/rest/api/3/project",
            user_id,
            error_msg="Error fetching projects"
        )

        projects: List[JiraProjectModel] = []
        for project_data in response_data:
            project: JiraProjectModel = await self.client.map_to_domain(
                project_data,
                JiraProjectAPIGetResponseDTO,
                JiraProjectMapper
            )
            projects.append(project)

        return projects

    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50,
        start_at: int = 0
    ) -> List[JiraIssueModel]:
        """Get all issues for a project from Jira API with pagination"""
        # # Build JQL query
        # jql_parts = [f"project = {project_key}"]
        # if sprint_id:
        #     jql_parts.append(f"sprint = {sprint_id}")
        # if is_backlog is not None:
        #     jql_parts.append("sprint is EMPTY" if is_backlog else "sprint is not EMPTY")
        # if issue_type:
        #     jql_parts.append(f"issuetype = {issue_type.value}")
        # if search:
        #     jql_parts.append(f'(summary ~ "{search}" OR description ~ "{search}")')

        # jql = " AND ".join(jql_parts)

        # Build JQL query
        jql_conditions = [f"project = {project_key}"]

        # Handle sprint/backlog filter
        if sprint_id:
            jql_conditions.append(f"sprint = {sprint_id}")
        elif is_backlog:
            jql_conditions.append("sprint is EMPTY")

        # Handle issue type filter
        if issue_type:
            jql_conditions.append(f"issuetype = '{issue_type.value}'")

        # Handle search - only using trailing wildcard
        if search:
            # Escape special characters in search term
            escaped_search = search.replace('"', '\\"')
            search_condition = f'(summary ~ "{escaped_search}*" OR description ~ "{escaped_search}*")'
            jql_conditions.append(search_condition)

        jql = " AND ".join(jql_conditions)

        response_data = await self.client.post(
            "/rest/api/3/search",
            user_id,
            {
                "jql": jql,
                # "startAt": start_at,
                "maxResults": limit,
                # "fields": "summary,description,status,assignee,priority,issuetype,created,updated,customfield_10016,customfield_10017,customfield_10020"
            },
            error_msg=f"Error searching issues for project {project_key}"
        )

        issues: List[JiraIssueModel] = []
        for issue_data in response_data.get("issues", []):
            issue: Optional[JiraIssueModel] = await self.client.map_to_domain(
                issue_data,
                JiraIssueAPIGetResponseDTO,
                JiraIssueMapper
            )
            if issue:
                issues.append(issue)

        return issues

    async def get_sprint_issues(
        self,
        user_id: int,
        sprint_id: str,
        issue_type: Optional[JiraIssueType] = None,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        """Get all issues in a specific sprint"""
        # Build JQL query
        jql_parts = [f"sprint = {sprint_id}"]
        if issue_type:
            jql_parts.append(f"issuetype = {issue_type.value}")

        jql = " AND ".join(jql_parts)

        return await self.search_issues(user_id, jql, limit=limit)

    async def search_issues(
        self,
        user_id: int,
        jql: str,
        start_at: int = 0,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        """Search issues with JQL"""
        response_data = await self.client.post(
            "/rest/api/3/search",
            user_id,
            {
                "jql": jql,
                "startAt": start_at,
                "maxResults": limit,
                "fields": "summary,description,status,assignee,priority,issuetype,created,updated,customfield_10016,customfield_10017,customfield_10020"
            },
            error_msg="Error searching issues with JQL"
        )

        issues: List[JiraIssueModel] = []
        for issue_data in response_data.get("issues", []):
            issue: JiraIssueModel = await self.client.map_to_domain(
                issue_data,
                JiraIssueAPIGetResponseDTO,
                JiraIssueMapper
            )
            issues.append(issue)

        return issues

    async def get_sprint_by_id(self, user_id: int, sprint_id: int) -> Optional[JiraSprintModel]:
        """Lấy thông tin chi tiết về một sprint cụ thể"""
        try:
            response_data = await self.client.get(
                f"/rest/agile/1.0/sprint/{sprint_id}",
                user_id,
                error_msg=f"Lỗi khi lấy thông tin sprint {sprint_id}"
            )

            sprint: JiraSprintModel = await self.client.map_to_domain(
                response_data,
                JiraSprintAPIGetResponseDTO,
                JiraSprintMapper
            )

            return sprint
        except Exception as e:
            log.error(f"Lỗi khi lấy sprint {sprint_id}: {str(e)}")
            return None
