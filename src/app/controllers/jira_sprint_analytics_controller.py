
from src.app.schemas.responses.jira_sprint_analytics import SprintBurndownResponse, SprintBurnupResponse
from src.app.services.jira_sprint_analytics_service import JiraSprintAnalyticsApplicationService


class JiraSprintAnalyticsController:
    """Controller for Sprint Analytics APIs"""

    def __init__(self, sprint_analytics_service: JiraSprintAnalyticsApplicationService):
        self.sprint_analytics_service = sprint_analytics_service

    async def get_sprint_burndown_chart(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> SprintBurndownResponse:
        """Get burndown chart data for a sprint"""
        return await self.sprint_analytics_service.get_sprint_burndown_chart(
            user_id=user_id,
            project_key=project_key,
            sprint_id=sprint_id
        )

    async def get_sprint_burnup_chart(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> SprintBurnupResponse:
        """Get burnup chart data for a sprint"""
        return await self.sprint_analytics_service.get_sprint_burnup_chart(
            user_id=user_id,
            project_key=project_key,
            sprint_id=sprint_id
        )
