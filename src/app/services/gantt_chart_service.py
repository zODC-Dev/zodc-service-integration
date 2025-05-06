from typing import Dict, List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.system_config_service import SystemConfigApplicationService
from src.configs.logger import log
from src.domain.models.database.jira_issue import JiraIssueDBUpdateDTO
from src.domain.models.gantt_chart import (
    GanttChartConnectionModel,
    GanttChartJiraIssueModel,
    GanttChartModel,
    ProjectConfigModel,
    TaskScheduleModel,
)
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.services.gantt_chart_calculator_service import IGanttChartCalculatorService
from src.domain.services.workflow_service_client import IWorkflowServiceClient


class GanttChartApplicationService:
    """Application service for Gantt chart operations"""

    def __init__(
        self,
        issue_repository: IJiraIssueRepository,
        sprint_repository: IJiraSprintRepository,
        gantt_calculator_service: IGanttChartCalculatorService,
        workflow_service_client: IWorkflowServiceClient,
        system_config_service: SystemConfigApplicationService
    ):
        self.issue_repository = issue_repository
        self.sprint_repository = sprint_repository
        self.gantt_calculator_service = gantt_calculator_service
        self.workflow_service_client = workflow_service_client
        self.system_config_service = system_config_service

    async def get_gantt_chart(
        self,
        session: AsyncSession,
        project_key: str,
        sprint_id: int,
        issues: Optional[List[GanttChartJiraIssueModel]] = None,
        connections: Optional[List[GanttChartConnectionModel]] = None
    ) -> GanttChartModel:
        """Get Gantt chart for a sprint"""
        try:
            log.debug(f"[GANTT] Starting Gantt chart calculation for sprint: {sprint_id}, project: {project_key}")
            log.debug(f"[GANTT] Input issues count: {len(issues) if issues else 0}")
            log.debug(f"[GANTT] Input connections count: {len(connections) if connections else 0}")

            # Lấy các cấu hình từ service
            hours_per_point = await self.system_config_service.get_estimate_point_to_hours(
                session=session, project_key=project_key
            )
            working_hours_per_day = await self.system_config_service.get_working_hours_per_day(session=session)
            lunch_break_minutes = await self.system_config_service.get_lunch_break_minutes(session=session)
            start_work_hour = await self.system_config_service.get_start_work_hour(session=session)
            end_work_hour = await self.system_config_service.get_end_work_hour(session=session)

            # Tạo config model từ các giá trị database
            config = ProjectConfigModel(
                estimate_point_to_hours=hours_per_point,
                working_hours_per_day=working_hours_per_day,
                lunch_break_minutes=lunch_break_minutes,
                start_work_hour=start_work_hour,
                end_work_hour=end_work_hour
            )
            log.debug(f"[GANTT] Created configuration from database: {config.model_dump()}")

            # Get sprint information
            log.debug(f"[GANTT] Fetching sprint information for ID: {sprint_id}")
            sprint = await self.sprint_repository.get_sprint_by_id(session=session, sprint_id=sprint_id)
            if not sprint:
                log.error(f"[GANTT] Sprint with ID {sprint_id} not found")
                raise ValueError(f"Sprint with ID {sprint_id} not found")

            assert sprint.start_date is not None, "Sprint start date is None"
            assert sprint.end_date is not None, "Sprint end date is None"
            log.debug(f"[GANTT] Sprint period: {sprint.start_date} to {sprint.end_date}")

            # Process issues from request
            gantt_chart_issues_list: List[GanttChartJiraIssueModel] = []
            if issues:
                # Create mapping of jira_key to issues for quicker lookup
                jira_keys = [issue.jira_key for issue in issues if issue.jira_key]
                log.debug(f"[GANTT] Jira keys to fetch from DB: {jira_keys}")

                # Fetch actual estimate points and other details from database
                db_issues_map: Dict[str, JiraIssueModel] = {}

                log.debug(f"[GANTT] Fetching {len(jira_keys)} issues from database")
                db_issues = await self.issue_repository.get_issues_by_keys(
                    session=session,
                    keys=jira_keys
                )
                log.debug(f"[GANTT] Found {len(db_issues)} issues in database")
                db_issues_map = {issue.key: issue for issue in db_issues}

                # Process each issue from request
                for req_issue in issues:
                    # Create a copy of the request issue
                    gantt_chart_issue_model = GanttChartJiraIssueModel(
                        node_id=req_issue.node_id,
                        jira_key=req_issue.jira_key,
                        type=req_issue.type,
                        # Use defaults initially
                        title="",
                        estimate_points=0,
                        assignee_id=None
                    )

                    # If we have this issue in database, update with DB data
                    if req_issue.jira_key and req_issue.jira_key in db_issues_map:
                        db_issue = db_issues_map[req_issue.jira_key]
                        gantt_chart_issue_model.title = db_issue.summary
                        gantt_chart_issue_model.estimate_points = db_issue.estimate_point
                        gantt_chart_issue_model.assignee_id = db_issue.assignee_id
                        log.debug(
                            f"[GANTT] Issue {req_issue.jira_key} found in DB: points={db_issue.estimate_point}, title={db_issue.summary}")
                    else:
                        # For issues not in DB, use node_id as title if none provided
                        gantt_chart_issue_model.title = f"Issue {req_issue.jira_key or req_issue.node_id}"
                        log.debug(
                            f"[GANTT] Issue {req_issue.jira_key or req_issue.node_id} not found in DB or has no key")

                    gantt_chart_issues_list.append(gantt_chart_issue_model)

                log.debug(f"[GANTT] Processed {len(gantt_chart_issues_list)} issues for calculation")
            else:
                log.warning("[GANTT] No issues provided in request")
                # Return empty Gantt chart
                return GanttChartModel(
                    sprint_id=sprint_id,
                    sprint_name=sprint.name or f"Sprint {sprint_id}",
                    project_key=project_key,
                    tasks=[],
                    start_date=sprint.start_date,
                    end_date=sprint.end_date,
                    config=config
                )

            # Process connections from request
            connections_list: List[GanttChartConnectionModel] = connections or []
            if connections:
                log.debug(f"[GANTT] Processing {len(connections)} connections")
                log.debug(f"[GANTT] Connection types: {[conn.type for conn in connections_list]}")

            # Build hierarchy map - parent to children relationships
            hierarchy_map = self._build_hierarchy_map(connections_list)
            log.debug(f"[GANTT] Hierarchy map created: {len(hierarchy_map)} parent nodes")
            for parent, children in hierarchy_map.items():
                log.debug(f"[GANTT] Parent {parent} has {len(children)} children: {children}")

            # Giữ nguyên các connection, không cần chuyển đổi phức tạp
            # Gang calculator mới sẽ xử lý propagation
            flattened_connections = self._flatten_connections(connections_list, hierarchy_map)
            log.debug(f"[GANTT] Flattened connections: {len(flattened_connections)} connections")

            # Calculate schedule
            log.debug(
                f"[GANTT] Calculating schedule for {len(gantt_chart_issues_list)} issues with {len(flattened_connections)} connections")
            tasks = await self.gantt_calculator_service.calculate_schedule(
                sprint_start_date=sprint.start_date,
                sprint_end_date=sprint.end_date,
                issues=gantt_chart_issues_list,
                connections=flattened_connections,
                hierarchy_map=hierarchy_map,
                config=config
            )
            log.debug(f"[GANTT] Schedule calculation completed: {len(tasks)} tasks scheduled")

            # Create a reverse hierarchy map for quicker lookup (child_id -> parent_id)
            reverse_hierarchy_map: Dict[str, str] = {}
            for parent, children in hierarchy_map.items():
                for child in children:
                    reverse_hierarchy_map[child] = parent

            for task in tasks:
                # Update issue with planned start and end times
                if task.jira_key:
                    update_dto = JiraIssueDBUpdateDTO(
                        planned_start_time=task.plan_start_time,
                        planned_end_time=task.plan_end_time
                    )

                    log.debug(
                        f"[GANTT] Updating task {task.jira_key} with planned times: start={task.plan_start_time}, end={task.plan_end_time}")

                    # If this task is a child of a story, update the story_id field
                    if task.node_id in reverse_hierarchy_map:
                        parent_node_id = reverse_hierarchy_map[task.node_id]
                        # Find the parent's jira_key
                        parent_task = next((t for t in tasks if t.node_id == parent_node_id), None)
                        if parent_task and parent_task.jira_key:
                            log.debug(f"[GANTT] Setting story_id for task {task.jira_key}: {parent_task.jira_key}")
                            update_dto.story_id = parent_task.jira_key
                            log.debug(f"[GANTT] Task {task.jira_key} is part of story {parent_task.jira_key}")

                    try:
                        log.debug(f"[GANTT] Calling issue_repository.update_by_key for {task.jira_key}")
                        updated_issue = await self.issue_repository.update_by_key(
                            session=session,
                            jira_issue_key=task.jira_key,
                            issue_update=update_dto
                        )
                        log.debug(f"[GANTT] Successfully updated issue {task.jira_key} in database")
                        log.debug(
                            f"[GANTT] Updated issue details: planned_start_time={updated_issue.planned_start_time}, planned_end_time={updated_issue.planned_end_time}, story_id={updated_issue.story_id}")
                    except Exception as e:
                        log.error(f"[GANTT] Failed to update issue {task.jira_key} in database: {str(e)}")
                else:
                    log.warning(f"[GANTT] Task {task.node_id} has no jira_key, skipping database update")

            # Check if schedule is feasible
            is_feasible = self.gantt_calculator_service.is_schedule_feasible(
                tasks=tasks,
                sprint_end_date=sprint.end_date
            )
            log.debug(f"[GANTT] Schedule feasibility: {is_feasible}")
            if not is_feasible:
                log.warning("[GANTT] Some tasks are scheduled to finish after sprint end date")
                # Log tasks that finish after sprint end
                for task in tasks:
                    if task.plan_end_time > sprint.end_date:
                        log.warning(
                            f"[GANTT] Task {task.jira_key or task.node_id} finishes after sprint end: {task.plan_end_time}")

            # Create Gantt chart model
            gantt_chart = GanttChartModel(
                sprint_id=sprint_id,
                sprint_name=sprint.name or f"Sprint {sprint_id}",
                project_key=project_key,
                tasks=tasks,
                start_date=sprint.start_date,
                end_date=sprint.end_date,
                is_feasible=is_feasible,
                config=config
            )

            return gantt_chart

        except Exception as e:
            log.error(f"[GANTT] Error getting Gantt chart: {str(e)}", exc_info=True)
            raise

    def _build_hierarchy_map(self, connections: List[GanttChartConnectionModel]) -> Dict[str, List[str]]:
        """Build a map of parent-child relationships from 'contains' connections"""
        hierarchy_map: Dict[str, List[str]] = {}

        for connection in connections:
            if connection.type.lower() == "contains":
                parent = connection.from_node_id
                child = connection.to_node_id

                if parent not in hierarchy_map:
                    hierarchy_map[parent] = []

                hierarchy_map[parent].append(child)

        return hierarchy_map

    def _flatten_connections(
        self,
        connections: List[GanttChartConnectionModel],
        hierarchy_map: Dict[str, List[str]]
    ) -> List[GanttChartConnectionModel]:
        """Convert all connections to flat dependency relationships for scheduling"""
        flattened = []

        # Process all connections, keep only "relates to" and "contains"
        for connection in connections:
            conn_type = connection.type.lower()

            # Keep "relates to" as is - these are direct dependencies
            if conn_type == "relates to":
                flattened.append(GanttChartConnectionModel(
                    from_node_id=connection.from_node_id,
                    to_node_id=connection.to_node_id,
                    type="relates to"
                ))

            # Keep "contains" as is - these define the hierarchy structure
            # Gantt calculator will use hierarchy_map for parent-child relationships
            elif conn_type == "contains":
                flattened.append(GanttChartConnectionModel(
                    from_node_id=connection.from_node_id,
                    to_node_id=connection.to_node_id,
                    type="contains"
                ))

        log.debug(f"[GANTT] Flattened connections: {len(flattened)} connections")
        return flattened

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
            return []

        except Exception as e:
            log.error(f"Error getting connections: {str(e)}")
            return []

    async def _populate_assignee_info(self, tasks: List[TaskScheduleModel]) -> None:
        """Populate assignee info for tasks"""
        # Implementation remains the same
        pass
