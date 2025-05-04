from datetime import datetime, time, timedelta
from typing import Dict, List

from src.configs.logger import log
from src.domain.models.gantt_chart import (
    GanttChartConnectionModel,
    GanttChartJiraIssueModel,
    ProjectConfigModel,
    TaskScheduleModel,
)
from src.domain.services.gantt_chart_calculator_service import IGanttChartCalculatorService


class GanttChartCalculatorService(IGanttChartCalculatorService):
    """Service for calculating Gantt chart schedule"""

    async def calculate_schedule(
        self,
        sprint_start_date: datetime,
        sprint_end_date: datetime,
        issues: List[GanttChartJiraIssueModel],
        connections: List[GanttChartConnectionModel],
        hierarchy_map: Dict[str, List[str]],
        config: ProjectConfigModel
    ) -> List[TaskScheduleModel]:
        """Calculate schedule for tasks based on dependencies and constraints"""
        try:
            log.info(f"[GANTT-CALC] Starting schedule calculation for {len(issues)} issues")
            log.debug(f"[GANTT-CALC] Sprint period: {sprint_start_date} to {sprint_end_date}")
            log.debug(
                f"[GANTT-CALC] Configuration: hours_per_point={config.estimate_point_to_hours}, hours_per_day={config.working_hours_per_day}")

            # Convert flattened connections to dependency map
            dependency_map = self._build_dependency_map(connections)
            log.debug(f"[GANTT-CALC] Dependency map created with {len(dependency_map)} entries")

            # Log dependency details for debugging
            for target, deps in dependency_map.items():
                log.debug(f"[GANTT-CALC] Node {target} depends on: {deps}")

            # Map issues by node_id for easy lookup
            issues_map = {issue.node_id: issue for issue in issues}
            log.debug(f"[GANTT-CALC] Issues map created with {len(issues_map)} entries")

            # Get list of all node IDs
            node_ids = list(issues_map.keys())

            # Perform topological sort to find execution order
            log.debug("[GANTT-CALC] Performing topological sort")
            try:
                sorted_tasks = self._topological_sort(node_ids, dependency_map)
                log.debug(f"[GANTT-CALC] Topological sort result: {sorted_tasks}")
            except ValueError as e:
                log.error(f"[GANTT-CALC] Topological sort failed: {str(e)}")
                raise

            # Calculate start and end times for each task
            log.info("[GANTT-CALC] Calculating task times based on sorted order")
            scheduled_tasks = self._calculate_task_times(
                sorted_tasks,
                issues_map,
                dependency_map,
                sprint_start_date,
                sprint_end_date,
                hierarchy_map,
                config
            )

            # Log each scheduled task
            for task in scheduled_tasks:
                log.debug(f"[GANTT-CALC] Task {task.jira_key or task.node_id} ({task.type}): "
                          f"start={task.plan_start_time}, end={task.plan_end_time}, "
                          f"points={task.estimate_points}, hours={task.estimate_hours}")

            log.info(f"[GANTT-CALC] Schedule calculation completed: {len(scheduled_tasks)} tasks scheduled")
            return scheduled_tasks

        except Exception as e:
            log.error(f"[GANTT-CALC] Error calculating schedule: {str(e)}", exc_info=True)
            raise

    def is_schedule_feasible(
        self,
        tasks: List[TaskScheduleModel],
        sprint_end_date: datetime
    ) -> bool:
        """Check if the schedule is feasible"""
        for task in tasks:
            if task.plan_end_time > sprint_end_date:
                return False
        return True

    def _build_dependency_map(self, connections: List[GanttChartConnectionModel]) -> Dict[str, Dict[str, str]]:
        """Build dependency map from connections with dependency types"""
        dependency_map: Dict[str, Dict[str, str]] = {}

        for connection in connections:
            source = connection.from_node_id
            target = connection.to_node_id
            conn_type = connection.type.lower()

            if target not in dependency_map:
                dependency_map[target] = {}

            dependency_map[target][source] = conn_type

            # Ensure source is in the map even if it has no dependencies
            if source not in dependency_map:
                dependency_map[source] = {}

        return dependency_map

    def _topological_sort(self, nodes: List[str], dependency_map: Dict[str, Dict[str, str]]) -> List[str]:
        """Sort tasks based on dependencies using topological sort, ignoring parent_finishes_after_child dependencies"""
        result = []
        visited = set()
        temp_visited = set()

        def visit(node: str):
            if node in temp_visited:
                # Check if the cycle is only due to parent-child relationships
                cycle_is_safe = True
                for dep_node, dep_type in dependency_map.get(node, {}).items():
                    # If any dependency that creates a cycle is not a parent-child relationship, it's an error
                    if dep_node in temp_visited and dep_type != 'parent_finishes_after_child':
                        cycle_is_safe = False
                        break

                if not cycle_is_safe:
                    # This is a real cycle that cannot be resolved
                    raise ValueError(f"Cycle detected in task dependencies for node {node}")
                # Otherwise, we allow the cycle since it's just a parent-child relationship
                return

            if node not in visited:
                temp_visited.add(node)

                # Visit only certain types of dependencies for topological sort
                # Specifically, exclude parent_finishes_after_child from the sort
                for dep_node, dep_type in dependency_map.get(node, {}).items():
                    if dep_type != 'parent_finishes_after_child':
                        visit(dep_node)

                temp_visited.remove(node)
                visited.add(node)
                result.append(node)

        # Visit all nodes
        for node in nodes:
            if node not in visited:
                visit(node)

        # Reverse for correct order (dependencies first)
        return list(reversed(result))

    def _calculate_task_times(
        self,
        sorted_tasks: List[str],
        issues_map: Dict[str, GanttChartJiraIssueModel],
        dependency_map: Dict[str, Dict[str, str]],
        sprint_start: datetime,
        sprint_end: datetime,
        hierarchy_map: Dict[str, List[str]],
        config: ProjectConfigModel
    ) -> List[TaskScheduleModel]:
        """Calculate start and end times for each task"""
        log.debug(f"[GANTT-CALC] Calculating task times for {len(sorted_tasks)} tasks")
        result: List[TaskScheduleModel] = []
        task_end_times: Dict[str, datetime] = {}  # Map of node_id to end time
        task_start_times: Dict[str, datetime] = {}  # Map of node_id to start time

        # Set work day start and end times
        work_start = config.start_work_hour
        work_end = config.end_work_hour
        hours_per_day = config.working_hours_per_day
        log.debug(f"[GANTT-CALC] Work hours: {work_start} to {work_end}, {hours_per_day} hours per day")

        # Process tasks in order defined by topological sort
        for node_id in sorted_tasks:
            issue = issues_map.get(node_id)
            if not issue:
                log.warning(f"[GANTT-CALC] Node {node_id} not found in issues map, skipping")
                continue

            # Get estimate points from issue
            estimate_points = issue.estimate_points
            estimate_hours = estimate_points * config.estimate_point_to_hours

            # If it's a story with subtasks, calculate estimate as sum of subtasks
            if node_id in hierarchy_map:
                child_tasks = hierarchy_map[node_id]
                child_estimate: float = 0
                for child_id in child_tasks:
                    if child_id in issues_map:
                        child_estimate += issues_map[child_id].estimate_points

                # Use child estimate if it's greater than the story's estimate
                if child_estimate > estimate_points:
                    log.debug(
                        f"[GANTT-CALC] Story {node_id} estimate adjusted: {estimate_points} -> {child_estimate} points")
                    estimate_points = child_estimate
                    estimate_hours = estimate_points * config.estimate_point_to_hours

            # Find latest end time of dependencies
            latest_dependency_end = sprint_start
            predecessors = []

            # Process each dependency
            for dep_node, dep_type in dependency_map.get(node_id, {}).items():
                predecessors.append(dep_node)

                # "relates to" dependencies: successor starts after predecessor ends
                if dep_type == "relates to" and dep_node in task_end_times:
                    if task_end_times[dep_node] > latest_dependency_end:
                        latest_dependency_end = task_end_times[dep_node]
                        log.debug(
                            f"[GANTT-CALC] Task {node_id} depends on end of {dep_node} ({dep_type}): {latest_dependency_end}")

                # "child_starts_after_parent" dependencies: child starts after parent starts
                elif dep_type == "child_starts_after_parent" and dep_node in task_start_times:
                    if task_start_times[dep_node] > latest_dependency_end:
                        latest_dependency_end = task_start_times[dep_node]
                        log.debug(
                            f"[GANTT-CALC] Task {node_id} depends on start of {dep_node} ({dep_type}): {latest_dependency_end}")

            # Calculate start time
            start_time = self._next_work_time(latest_dependency_end, work_start, work_end)
            log.debug(f"[GANTT-CALC] Task {node_id} raw start time: {latest_dependency_end} -> adjusted: {start_time}")

            # Calculate end time
            end_time = self._add_work_hours(
                start_time,
                estimate_hours,
                work_start,
                work_end,
                hours_per_day,
                config.lunch_break_minutes
            )
            log.debug(f"[GANTT-CALC] Task {node_id} end time: {end_time} (duration: {estimate_hours} hours)")

            # Store times for dependency calculations
            task_start_times[node_id] = start_time
            task_end_times[node_id] = end_time

            # Create TaskSchedule object
            schedule = TaskScheduleModel(
                node_id=issue.node_id,
                jira_key=issue.jira_key,
                title=issue.title,
                type=issue.type,
                estimate_points=estimate_points,
                estimate_hours=estimate_hours,
                plan_start_time=start_time,
                plan_end_time=end_time,
                predecessors=predecessors,
                assignee_id=issue.assignee_id
            )

            result.append(schedule)

        # Process parent-child relationships to ensure parents finish after their children
        changed = True
        iterations = 0
        max_iterations = 5

        while changed and iterations < max_iterations:
            iterations += 1
            changed = False
            log.debug(f"[GANTT-CALC] Processing parent-child constraints, iteration {iterations}")

            # Check each dependency
            for node_id in sorted_tasks:
                # Get dependencies where this node is dependent on others
                for dep_node, dep_type in dependency_map.get(node_id, {}).items():
                    # For parent_finishes_after_child, ensure parent ends after child
                    if dep_type == "parent_finishes_after_child" and dep_node in task_end_times:
                        if task_end_times[node_id] < task_end_times[dep_node]:
                            old_end = task_end_times[node_id]
                            task_end_times[node_id] = task_end_times[dep_node]
                            log.debug(
                                f"[GANTT-CALC] Adjusting parent {node_id} end time: {old_end} -> {task_end_times[node_id]}")

                            # Update the task in the result list
                            for i, task in enumerate(result):
                                if task.node_id == node_id:
                                    result[i] = TaskScheduleModel(
                                        node_id=task.node_id,
                                        jira_key=task.jira_key,
                                        title=task.title,
                                        type=task.type,
                                        estimate_points=task.estimate_points,
                                        estimate_hours=task.estimate_hours,
                                        plan_start_time=task.plan_start_time,
                                        plan_end_time=task_end_times[node_id],
                                        predecessors=task.predecessors,
                                        assignee_id=task.assignee_id
                                    )
                                    changed = True
                                    break

        if iterations >= max_iterations:
            log.warning(f"[GANTT-CALC] Reached maximum iterations ({max_iterations}) for parent-child adjustments")

        # Log summary of schedule
        log.info("[GANTT-CALC] Schedule calculation summary:")
        log.info(f"[GANTT-CALC] - Total tasks: {len(result)}")
        earliest_start = min([task.plan_start_time for task in result]) if result else sprint_start
        latest_end = max([task.plan_end_time for task in result]) if result else sprint_start
        log.info(f"[GANTT-CALC] - Schedule span: {earliest_start} to {latest_end}")
        log.info(f"[GANTT-CALC] - Sprint span: {sprint_start} to {sprint_end}")

        return result

    def _next_work_time(
        self,
        current_time: datetime,
        work_start: time,
        work_end: time,
        include_weekends: bool = False  # Parameter kept for compatibility but ignored
    ) -> datetime:
        """Find next valid work time from current time"""
        # If weekend, move to Monday (weekends are always excluded)
        if current_time.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            days_to_add = 7 - current_time.weekday() + 1  # Move to Monday
            current_time = (current_time + timedelta(days=days_to_add)).replace(
                hour=work_start.hour,
                minute=work_start.minute,
                second=0,
                microsecond=0
            )
            return current_time

        # If before work hours, move to start of work day
        current_time_time = current_time.time()
        if current_time_time < work_start:
            return current_time.replace(
                hour=work_start.hour,
                minute=work_start.minute,
                second=0,
                microsecond=0
            )

        # If after work hours, move to next work day
        if current_time_time >= work_end:
            next_day = current_time + timedelta(days=1)
            # If next day is weekend, move to Monday
            if next_day.weekday() >= 5:
                days_to_add = 7 - next_day.weekday() + 1
                next_day = next_day + timedelta(days=days_to_add)

            return next_day.replace(
                hour=work_start.hour,
                minute=work_start.minute,
                second=0,
                microsecond=0
            )

        return current_time

    def _add_work_hours(
        self,
        start_time: datetime,
        work_hours: float,
        work_start: time,
        work_end: time,
        hours_per_day: int,
        lunch_break_minutes: int,
        include_weekends: bool = False  # Parameter kept for compatibility but ignored
    ) -> datetime:
        """Add work hours to start time, respecting work schedule"""
        remaining_hours = work_hours
        current_time = start_time

        while remaining_hours > 0:
            # Skip weekends (weekends are always excluded)
            if current_time.weekday() >= 5:
                current_time = self._next_work_day(current_time, work_start)
                continue

            # Calculate work hours left in current day
            current_time_time = current_time.time()

            # If current time is before work start, adjust to work start
            if current_time_time < work_start:
                current_time = current_time.replace(
                    hour=work_start.hour,
                    minute=work_start.minute,
                    second=0,
                    microsecond=0
                )
                current_time_time = current_time.time()

            # Calculate hours until end of work day
            work_end_datetime = datetime.combine(current_time.date(), work_end)
            current_datetime = datetime.combine(current_time.date(), current_time_time)
            hours_left_today = (work_end_datetime - current_datetime).total_seconds() / 3600

            # Handle lunch break
            lunch_break_start = time(12, 0)
            lunch_break_end = time(12, 0 + lunch_break_minutes)

            if current_time_time <= lunch_break_start and work_end > lunch_break_end:
                # Lunch break is still ahead or just starting
                hours_left_today -= lunch_break_minutes / 60  # Convert minutes to hours

            # If no time left today, move to next work day
            if hours_left_today <= 0:
                current_time = self._next_work_day(current_time, work_start)
                continue

            # Determine how many hours to add today
            hours_to_add_today = min(remaining_hours, hours_left_today)
            remaining_hours -= hours_to_add_today

            # Add hours to current time
            current_time = current_time + timedelta(hours=hours_to_add_today)

            # Handle lunch break crossing
            if (current_time_time < lunch_break_start and
                current_time.time() >= lunch_break_start and
                    remaining_hours > 0):
                current_time = current_time + timedelta(minutes=lunch_break_minutes)

            # If day is complete, move to next work day
            if current_time.time() >= work_end:
                current_time = self._next_work_day(current_time, work_start)

        return current_time

    def _next_work_day(self, current_time: datetime, work_start: time, include_weekends: bool = False) -> datetime:
        """Get the start of the next work day"""
        next_day = current_time + timedelta(days=1)

        # Skip weekends (weekends are always excluded)
        if next_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            days_to_add = 8 - next_day.weekday()  # Move to Monday
            next_day = next_day + timedelta(days=days_to_add)

        return next_day.replace(
            hour=work_start.hour,
            minute=work_start.minute,
            second=0,
            microsecond=0
        )
