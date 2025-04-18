from typing import Dict, List, Optional

from src.configs.logger import log
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
        config: Optional[ProjectConfigModel] = None,
        workflow_id: Optional[int] = None,
        issues: Optional[List[GanttChartJiraIssueModel]] = None,
        connections: Optional[List[GanttChartConnectionModel]] = None
    ) -> GanttChartModel:
        """Get Gantt chart for a sprint"""
        try:
            log.debug(f"[GANTT] Starting Gantt chart calculation for sprint: {sprint_id}, project: {project_key}")
            log.debug(f"[GANTT] Input issues count: {len(issues) if issues else 0}")
            log.debug(f"[GANTT] Input connections count: {len(connections) if connections else 0}")
            log.debug(f"[GANTT] Configuration: {config.model_dump() if config else 'default'}")

            # Use default config if not provided
            if not config:
                config = ProjectConfigModel()
                log.debug("[GANTT] Using default configuration")

            # Get sprint information
            log.debug(f"[GANTT] Fetching sprint information for ID: {sprint_id}")
            sprint = await self.sprint_repository.get_sprint_by_id(sprint_id)
            if not sprint:
                log.error(f"[GANTT] Sprint with ID {sprint_id} not found")
                raise ValueError(f"Sprint with ID {sprint_id} not found")

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
                db_issues = await self.issue_repository.get_issues_by_keys(jira_keys)
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

            # Flatten connections for dependency calculation
            flattened_connections = self._flatten_connections(connections_list, hierarchy_map)
            log.debug(f"[GANTT] Flattened connections: {len(flattened_connections)} connections")
            for conn in flattened_connections:
                log.debug(f"[GANTT] Flattened connection: {conn.from_node_id} -> {conn.to_node_id} ({conn.type})")

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
        stories = set()

        # First, identify all stories
        for parent in hierarchy_map:
            stories.add(parent)

        # Process all connections
        for connection in connections:
            conn_type = connection.type.lower()
            from_node = connection.from_node_id
            to_node = connection.to_node_id

            if conn_type == "relates to":
                # Direct dependency - keep as is
                flattened.append(GanttChartConnectionModel(
                    from_node_id=from_node,
                    to_node_id=to_node,
                    type="relates to"
                ))

                # If this is a story → story relationship, we need to add implicit dependencies
                # from the last tasks of first story to the first tasks of second story
                if from_node in stories and to_node in stories:
                    # Add dependencies between last tasks of first story and first tasks of second story
                    if from_node in hierarchy_map and to_node in hierarchy_map:
                        # Find terminal tasks (those with no outgoing relates_to connections)
                        terminal_tasks_from = self._find_terminal_tasks(
                            hierarchy_map[from_node], connections)

                        # Find initial tasks (those with no incoming relates_to connections)
                        initial_tasks_to = self._find_initial_tasks(
                            hierarchy_map[to_node], connections)

                        # Add dependencies between terminal and initial tasks
                        for term_task in terminal_tasks_from:
                            for init_task in initial_tasks_to:
                                flattened.append(GanttChartConnectionModel(
                                    from_node_id=term_task,
                                    to_node_id=init_task,
                                    type="relates to"
                                ))

            elif conn_type == "contains":
                # Parent-child relationship (story contains task)
                # 1. A child task can't start before its parent story
                flattened.append(GanttChartConnectionModel(
                    from_node_id=from_node,  # Story
                    to_node_id=to_node,      # Task
                    type="child_starts_after_parent"
                ))

                # 2. A parent story can't finish until all its children are done
                flattened.append(GanttChartConnectionModel(
                    from_node_id=to_node,    # Task
                    to_node_id=from_node,    # Story
                    type="parent_finishes_after_child"
                ))

        return flattened

    def _find_terminal_tasks(self, tasks: List[str], connections: List[GanttChartConnectionModel]) -> List[str]:
        """Find tasks that have no outgoing relates_to connections within their parent story"""
        # Get all tasks that are sources in relates_to connections
        source_tasks = set()
        for conn in connections:
            if conn.type.lower() == "relates to" and conn.from_node_id in tasks and conn.to_node_id in tasks:
                source_tasks.add(conn.from_node_id)

        # Terminal tasks are those that are not sources to other tasks in the same story
        terminal_tasks = [task for task in tasks if task not in source_tasks]

        # If no terminal tasks found, return all tasks
        return terminal_tasks if terminal_tasks else tasks

    def _find_initial_tasks(self, tasks: List[str], connections: List[GanttChartConnectionModel]) -> List[str]:
        """Find tasks that have no incoming relates_to connections within their parent story"""
        # Get all tasks that are targets in relates_to connections
        target_tasks = set()
        for conn in connections:
            if conn.type.lower() == "relates to" and conn.to_node_id in tasks and conn.from_node_id in tasks:
                target_tasks.add(conn.to_node_id)

        # Initial tasks are those that are not targets from other tasks in the same story
        initial_tasks = [task for task in tasks if task not in target_tasks]

        # If no initial tasks found, return all tasks
        return initial_tasks if initial_tasks else tasks

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
