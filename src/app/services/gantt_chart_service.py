from typing import List, Optional

from src.configs.logger import log
from src.domain.models.gantt_chart import (
    GanttChartConnectionModel,
    GanttChartJiraIssueModel,
    GanttChartModel,
    ScheduleConfigModel,
    TaskScheduleModel,
)
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.workflow_mapping_repository import IWorkflowMappingRepository
from src.domain.services.gantt_chart_calculator_service import IGanttChartCalculatorService
from src.domain.services.workflow_service_client import IWorkflowServiceClient


class GanttChartApplicationService:
    """Application service for Gantt chart operations"""

    def __init__(
        self,
        issue_repository: IJiraIssueRepository,
        sprint_repository: IJiraSprintRepository,
        workflow_mapping_repository: IWorkflowMappingRepository,
        gantt_calculator_service: IGanttChartCalculatorService,
        workflow_service_client: IWorkflowServiceClient
    ):
        self.issue_repository = issue_repository
        self.sprint_repository = sprint_repository
        self.workflow_mapping_repository = workflow_mapping_repository
        self.gantt_calculator_service = gantt_calculator_service
        self.workflow_service_client = workflow_service_client

    async def get_gantt_chart(
        self,
        project_key: str,
        sprint_id: int,
        config: Optional[ScheduleConfigModel] = None,
        workflow_id: Optional[str] = None,
        issues: Optional[List[GanttChartJiraIssueModel]] = None,
        connections: Optional[List[GanttChartConnectionModel]] = None
    ) -> GanttChartModel:
        """Get Gantt chart for a sprint"""
        try:
            # Use default config if not provided
            if not config:
                config = ScheduleConfigModel()

            # Get sprint information
            sprint = await self.sprint_repository.get_sprint_by_id(sprint_id)
            if not sprint:
                raise ValueError(f"Sprint with ID {sprint_id} not found")

            # Use provided issues or get from database
            issues_list: List[GanttChartJiraIssueModel] = []
            if issues:
                # Use provided issues
                issues_list = issues
            else:
                # Get issues from database
                db_issues = await self.issue_repository.get_project_issues(
                    project_key=project_key,
                    sprint_id=sprint.jira_sprint_id
                )

                if not db_issues:
                    log.warning(f"No issues found for sprint {sprint_id} in project {project_key}")
                    # Return empty Gantt chart
                    return GanttChartModel(
                        sprint_id=sprint_id,
                        sprint_name=sprint.name,
                        project_key=project_key,
                        tasks=[],
                        start_date=sprint.start_date,
                        end_date=sprint.end_date,
                        config=config
                    )

                # Convert DB issues to JiraIssueModel
                for issue in db_issues:
                    issue_model = GanttChartJiraIssueModel(
                        node_id=issue.jira_issue_id,
                        jira_key=issue.key,
                        title=issue.summary,
                        type=issue.type,
                        estimate_points=issue.estimate_point,
                        assignee_id=issue.assignee_id
                    )
                    issues_list.append(issue_model)

            # Use provided connections or get from workflow
            connections_list: List[GanttChartConnectionModel] = []
            if connections:
                # Use provided connections
                connections_list = connections
            else:
                # Get connections based on workflow
                connections_list = await self._get_connections(project_key, sprint_id, workflow_id)

            # Calculate schedule
            tasks = await self.gantt_calculator_service.calculate_schedule(
                sprint_start_date=sprint.start_date,
                sprint_end_date=sprint.end_date,
                issues=issues_list,
                connections=connections_list,
                config=config
            )

            # Check if schedule is feasible
            is_feasible = self.gantt_calculator_service.is_schedule_feasible(
                tasks=tasks,
                sprint_end_date=sprint.end_date
            )

            # Add assignee info if available
            await self._populate_assignee_info(tasks)

            # Create Gantt chart model
            gantt_chart = GanttChartModel(
                sprint_id=sprint_id,
                sprint_name=sprint.name,
                project_key=project_key,
                tasks=tasks,
                start_date=sprint.start_date,
                end_date=sprint.end_date,
                is_feasible=is_feasible,
                config=config
            )

            return gantt_chart

        except Exception as e:
            log.error(f"Error getting Gantt chart: {str(e)}")
            raise

    async def _get_connections(
        self,
        project_key: str,
        sprint_id: int,
        workflow_id: Optional[str] = None
    ) -> List[GanttChartConnectionModel]:
        """Get connections for a sprint or workflow"""
        try:
            # If workflow_id is provided, get connections from that workflow
            if workflow_id:
                connections = await self.workflow_service_client.get_workflow_connections(workflow_id)
                if connections:
                    return connections

            # Otherwise, get all active workflows for this sprint and get connections
            workflow_mappings = await self.workflow_mapping_repository.get_by_sprint(sprint_id)

            all_connections = []
            for mapping in workflow_mappings:
                if mapping.status == "active":
                    connections = await self.workflow_service_client.get_workflow_connections(
                        mapping.workflow_id
                    )
                    all_connections.extend(connections)

            return all_connections

        except Exception as e:
            log.error(f"Error getting connections: {str(e)}")
            return []

    async def _populate_assignee_info(self, tasks: List[TaskScheduleModel]) -> None:
        """Populate assignee info for tasks"""
        # Implementation remains the same
        pass
