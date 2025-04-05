from datetime import datetime, time, timedelta
from typing import Dict, List

from src.configs.logger import log
from src.domain.models.gantt_chart import (
    GanttChartConnectionModel,
    GanttChartJiraIssueModel,
    ScheduleConfigModel,
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
        config: ScheduleConfigModel
    ) -> List[TaskScheduleModel]:
        """Calculate schedule for tasks based on dependencies and constraints"""
        try:
            # Convert connections to dependency map
            dependency_map = self._build_dependency_map(connections)

            # Map issues by node_id for easy lookup
            issues_map = {issue.node_id: issue for issue in issues}

            # Get list of all node IDs
            node_ids = list(issues_map.keys())

            # Perform topological sort to find execution order
            sorted_tasks = self._topological_sort(node_ids, dependency_map)

            # Calculate start and end times for each task
            return self._calculate_task_times(
                sorted_tasks,
                issues_map,
                dependency_map,
                sprint_start_date,
                sprint_end_date,
                config
            )

        except Exception as e:
            log.error(f"Error calculating schedule: {str(e)}")
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

    def _build_dependency_map(self, connections: List[GanttChartConnectionModel]) -> Dict[str, List[str]]:
        """Build dependency map from connections"""
        dependency_map = {}

        for connection in connections:
            source = connection.from_issue_key
            target = connection.to_issue_key

            if target not in dependency_map:
                dependency_map[target] = []

            dependency_map[target].append(source)

            # Ensure source is in the map even if it has no dependencies
            if source not in dependency_map:
                dependency_map[source] = []

        return dependency_map

    def _topological_sort(self, nodes: List[str], dependency_map: Dict[str, List[str]]) -> List[str]:
        """Sort tasks based on dependencies using topological sort"""
        result = []
        visited = set()
        temp_visited = set()

        def visit(node: str):
            if node in temp_visited:
                # Cycle detected
                raise ValueError(f"Cycle detected in task dependencies for node {node}")

            if node not in visited:
                temp_visited.add(node)

                # Visit dependencies
                for dependency in dependency_map.get(node, []):
                    visit(dependency)

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
        dependency_map: Dict[str, List[str]],
        sprint_start: datetime,
        sprint_end: datetime,
        config: ScheduleConfigModel
    ) -> List[TaskScheduleModel]:
        """Calculate start and end times for each task"""
        result = []
        task_end_times = {}  # Map of node_id to end time

        # Set work day start and end times
        work_start = config.start_work_hour
        work_end = config.end_work_hour
        hours_per_day = config.working_hours_per_day

        for node_id in sorted_tasks:
            issue = issues_map.get(node_id)

            if not issue:
                continue

            # Get estimate points from issue
            estimate_points = issue.estimate_points
            estimate_hours = estimate_points * config.hours_per_point

            # Find latest end time of dependencies
            latest_dependency_end = sprint_start
            predecessors = dependency_map.get(node_id, [])

            for dep in predecessors:
                if dep in task_end_times and task_end_times[dep] > latest_dependency_end:
                    latest_dependency_end = task_end_times[dep]

            # Calculate start time (next available work time after dependencies)
            start_time = self._next_work_time(latest_dependency_end, work_start, work_end, config.include_weekends)

            # Calculate end time (start time + task duration, respecting work hours)
            end_time = self._add_work_hours(
                start_time,
                estimate_hours,
                work_start,
                work_end,
                hours_per_day,
                config.lunch_break_minutes,
                config.include_weekends
            )

            # Store end time for dependency calculations
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

        return result

    def _next_work_time(
        self,
        current_time: datetime,
        work_start: time,
        work_end: time,
        include_weekends: bool
    ) -> datetime:
        """Find next valid work time from current time"""
        # If weekend and we don't include weekends, move to Monday
        if not include_weekends and current_time.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
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
            # If next day is weekend and we don't include weekends, move to Monday
            if not include_weekends and next_day.weekday() >= 5:
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
        include_weekends: bool
    ) -> datetime:
        """Add work hours to start time, respecting work schedule"""
        remaining_hours = work_hours
        current_time = start_time

        while remaining_hours > 0:
            # Skip weekends if not included
            if not include_weekends and current_time.weekday() >= 5:
                current_time = self._next_work_day(current_time, work_start, include_weekends)
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
                current_time = self._next_work_day(current_time, work_start, include_weekends)
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
                current_time = self._next_work_day(current_time, work_start, include_weekends)

        return current_time

    def _next_work_day(self, current_time: datetime, work_start: time, include_weekends: bool) -> datetime:
        """Get the start of the next work day"""
        next_day = current_time + timedelta(days=1)

        # Skip weekends if not included
        if not include_weekends and next_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            days_to_add = 8 - next_day.weekday()  # Move to Monday
            next_day = next_day + timedelta(days=days_to_add)

        return next_day.replace(
            hour=work_start.hour,
            minute=work_start.minute,
            second=0,
            microsecond=0
        )
