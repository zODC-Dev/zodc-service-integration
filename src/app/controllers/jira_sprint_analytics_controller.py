from typing import List

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.gantt_chart import GanttTaskResponse
from src.app.schemas.responses.jira_sprint_analytics import (
    BugReportDataResponse,
    SprintBurndownResponse,
    SprintBurnupResponse,
    SprintGoalResponse,
    WorkloadResponse,
)
from src.app.services.gantt_chart_service import GanttChartApplicationService
from src.app.services.jira_sprint_analytics_service import JiraSprintAnalyticsApplicationService
from src.configs.logger import log
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository


class JiraSprintAnalyticsController:
    """Controller for Sprint Analytics APIs"""

    def __init__(self, sprint_analytics_service: JiraSprintAnalyticsApplicationService, gantt_chart_service: GanttChartApplicationService = None, sprint_repository: IJiraSprintRepository = None):
        self.sprint_analytics_service = sprint_analytics_service
        self.gantt_chart_service = gantt_chart_service
        self.sprint_repository = sprint_repository

    async def get_sprint_burndown_chart(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> StandardResponse[SprintBurndownResponse]:
        """Get burndown chart data for a sprint"""
        try:
            result = await self.sprint_analytics_service.get_sprint_burndown_chart(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Sprint burndown chart data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting sprint burndown chart: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting sprint burndown chart: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_sprint_burnup_chart(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> StandardResponse[SprintBurnupResponse]:
        """Get burnup chart data for a sprint"""
        try:
            result = await self.sprint_analytics_service.get_sprint_burnup_chart(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Sprint burnup chart data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting sprint burnup chart: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting sprint burnup chart: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_sprint_goal(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> StandardResponse[SprintGoalResponse]:
        """Get sprint goal data for a sprint"""
        try:
            result = await self.sprint_analytics_service.get_sprint_goal(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Sprint goal data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting sprint goal: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting sprint goal: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_bug_report(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> StandardResponse[BugReportDataResponse]:
        """Get bug report data for a sprint"""
        try:
            result = await self.sprint_analytics_service.get_bug_report(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Bug report data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting bug report: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting bug report: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_team_workload(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> StandardResponse[List[WorkloadResponse]]:
        """Get workload data for team members in a sprint"""
        try:
            result = await self.sprint_analytics_service.get_team_workload(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Team workload data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting team workload: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting team workload: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_gantt_chart_data(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> StandardResponse[List[GanttTaskResponse]]:
        """Get Gantt chart data for a sprint"""
        try:
            result = await self.sprint_analytics_service.get_gantt_chart_data(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Gantt chart data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting Gantt chart data: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting Gantt chart data: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def test_gantt_chart_calculation(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> StandardResponse[List[GanttTaskResponse]]:
        """Test Gantt chart calculation with sample data"""
        try:
            from src.domain.models.gantt_chart import (
                GanttChartConnectionModel,
                GanttChartJiraIssueModel,
            )

            log.info(f"[TEST] Running Gantt chart test calculation for project {project_key}, sprint {sprint_id}")

            # Lấy thông tin sprint thực tế để có ngày bắt đầu/kết thúc
            sprint = await self.sprint_repository.get_sprint_by_id(
                session=session,
                sprint_id=sprint_id
            )

            if not sprint:
                raise ValueError(f"Sprint with ID {sprint_id} not found")

            log.info(f"[TEST] Using sprint period: {sprint.start_date} to {sprint.end_date}")

            # Tạo mẫu story và task
            story_a = GanttChartJiraIssueModel(node_id="story-a", jira_key="ZODC-403",
                                               title="Story A", type="Story", estimate_points=10)
            story_b = GanttChartJiraIssueModel(node_id="story-b", jira_key="ZODC-404",
                                               title="Story B", type="Story", estimate_points=12)

            task_a1 = GanttChartJiraIssueModel(node_id="task-a1", jira_key="ZODC-398",
                                               title="Task A1", type="Task", estimate_points=1)
            task_a2 = GanttChartJiraIssueModel(node_id="task-a2", jira_key="ZODC-399",
                                               title="Task A2", type="Task", estimate_points=2)

            task_b1 = GanttChartJiraIssueModel(node_id="task-b1", jira_key="ZODC-400",
                                               title="Task B1", type="Task", estimate_points=1)
            task_b2 = GanttChartJiraIssueModel(node_id="task-b2", jira_key="ZODC-401",
                                               title="Task B2", type="Task", estimate_points=1)

            # Tạo quan hệ: story-a -> story-b, task-a1 -> task-a2
            conn_a_to_b = GanttChartConnectionModel(from_node_id="story-a", to_node_id="story-b", type="relates to")
            conn_a1_to_a2 = GanttChartConnectionModel(from_node_id="task-a1", to_node_id="task-a2", type="relates to")

            # Tạo quan hệ contains (story chứa các task)
            contains_a_a1 = GanttChartConnectionModel(from_node_id="story-a", to_node_id="task-a1", type="contains")
            contains_a_a2 = GanttChartConnectionModel(from_node_id="story-a", to_node_id="task-a2", type="contains")
            contains_b_b1 = GanttChartConnectionModel(from_node_id="story-b", to_node_id="task-b1", type="contains")
            contains_b_b2 = GanttChartConnectionModel(from_node_id="story-b", to_node_id="task-b2", type="contains")

            # Gộp các danh sách
            issues = [story_a, story_b, task_a1, task_a2, task_b1, task_b2]
            connections = [conn_a_to_b, conn_a1_to_a2, contains_a_a1, contains_a_a2, contains_b_b1, contains_b_b2]

            log.info(f"[TEST] Created {len(issues)} sample issues and {len(connections)} connections")

            # Log connections for clarity
            log.info("[TEST] Original connections:")
            for conn in connections:
                log.info(f"[TEST]   {conn.from_node_id} -> {conn.to_node_id} ({conn.type})")

            # Gọi service để tính toán Gantt chart
            result = await self.gantt_chart_service.get_gantt_chart(
                session=session,
                project_key=project_key,
                sprint_id=sprint_id,
                issues=issues,
                connections=connections
            )

            # In kết quả ra log
            log.info("[TEST] Calculation result:")
            for task in result.tasks:
                log.info(
                    f"[TEST] Task: {task.jira_key} ({task.node_id}) - Start: {task.plan_start_time}, End: {task.plan_end_time}")
                log.info(f"[TEST]   Duration: {task.estimate_hours} hours, Predecessors: {task.predecessors}")

            return StandardResponse(
                data=result.model_dump(),
                message="Test Gantt chart calculation completed successfully"
            )
        except ValueError as e:
            log.error(f"Error in test Gantt chart calculation: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error in test Gantt chart calculation: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e
