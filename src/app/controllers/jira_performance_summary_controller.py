from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.schemas.requests.jira_performance_summary import PerformanceSummaryRequest
from src.app.schemas.responses.jira_performance_summary import UserPerformanceSummaryResponse
from src.domain.models.jira_performance_summary import UserPerformanceSummaryModel
from src.domain.services.jira_performance_summary_service import IJiraPerformanceSummaryService


class JiraPerformanceSummaryController:
    """Controller xử lý các request liên quan đến performance summary"""

    def __init__(
        self,
        jira_performance_summary_service: IJiraPerformanceSummaryService
    ):
        self.jira_performance_summary_service = jira_performance_summary_service

    async def get_user_performance_summary(
        self,
        request: PerformanceSummaryRequest,
        session: AsyncSession
    ) -> UserPerformanceSummaryResponse:
        """Lấy thông tin hiệu suất của người dùng trong một quý"""
        # Lấy thông tin hiệu suất từ service

        assert request.user_id is not None, "User ID is required"

        performance_summary = await self.jira_performance_summary_service.get_user_performance_summary(
            session=session,
            user_id=request.user_id,
            quarter=request.quarter,
            year=request.year
        )

        # Chuyển đổi từ domain model sang response model
        return self._convert_to_response(performance_summary)

    def _convert_to_response(
        self,
        performance_summary: UserPerformanceSummaryModel
    ) -> UserPerformanceSummaryResponse:
        """Chuyển đổi từ domain model sang response model"""
        return UserPerformanceSummaryResponse(
            user_id=performance_summary.user_id,
            user_name=performance_summary.user_name,
            user_email=performance_summary.user_email,
            quarter=performance_summary.quarter,
            year=performance_summary.year,
            avatar_url=performance_summary.avatar_url,
            total_tasks=performance_summary.total_tasks,
            completed_tasks=performance_summary.completed_tasks,
            task_completion_rate=performance_summary.task_completion_rate,
            total_story_points=performance_summary.total_story_points,
            completed_story_points=performance_summary.completed_story_points,
            story_point_completion_rate=performance_summary.story_point_completion_rate,
            average_completion_time=performance_summary.average_completion_time,
            on_time_completion_rate=performance_summary.on_time_completion_rate,
            bug_fix_rate=performance_summary.bug_fix_rate,
            rework_rate=performance_summary.rework_rate,
            task_by_type=performance_summary.task_by_type,
            task_by_priority=performance_summary.task_by_priority,
            team_rank=performance_summary.team_rank,
            team_average_completion_rate=performance_summary.team_average_completion_rate,
            sprint_performance=performance_summary.sprint_performance,
            monthly_performance=performance_summary.monthly_performance
        )
