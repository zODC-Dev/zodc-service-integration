from datetime import datetime, time, timedelta
from typing import Dict, List, Tuple

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

            # Tách các connection theo loại
            relates_to_connections = [c for c in connections if c.type.lower() == "relates to"]
            log.debug(f"[GANTT-CALC] Found {len(relates_to_connections)} 'relates to' connections")

            # Lan truyền dependencies từ story xuống task con
            propagated_connections = self._propagate_dependencies(relates_to_connections, hierarchy_map)
            log.debug(f"[GANTT-CALC] After propagation: {len(propagated_connections)} 'relates to' connections")

            # Convert connections to dependency map
            dependency_map = self._build_dependency_map(propagated_connections)
            log.debug(f"[GANTT-CALC] Dependency map created with {len(dependency_map)} entries")

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
                config
            )

            # Điều chỉnh thời gian cho story dựa trên task con
            log.info("[GANTT-CALC] Adjusting story times based on child tasks")
            scheduled_tasks = self._adjust_story_times(scheduled_tasks, hierarchy_map)

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

    def _propagate_dependencies(
        self,
        relates_to_connections: List[GanttChartConnectionModel],
        hierarchy_map: Dict[str, List[str]]
    ) -> List[GanttChartConnectionModel]:
        """Lan truyền dependencies từ story xuống tasks con.

        Nếu story A depends on story B, thì tất cả các task con cuối của story A
        sẽ depends on tất cả các task con đầu của story B
        """
        result = relates_to_connections.copy()
        story_ids = set(hierarchy_map.keys())

        log.info(
            f"[GANTT-CALC] Starting dependency propagation with {len(relates_to_connections)} original connections")
        log.info(f"[GANTT-CALC] Found {len(story_ids)} stories in hierarchy map")

        # Tạo map ngược từ task con đến story cha
        reverse_hierarchy: Dict[str, str] = {}
        for story_id, child_ids in hierarchy_map.items():
            for child_id in child_ids:
                reverse_hierarchy[child_id] = story_id

        log.debug(f"[GANTT-CALC] Created reverse hierarchy map with {len(reverse_hierarchy)} child->parent mappings")

        # Đảm bảo quan hệ phụ thuộc giữa các task trong cùng một story
        # Tách theo story, xử lý liên kết trong từng story riêng biệt
        story_internal_dependencies: Dict[str, List[GanttChartConnectionModel]] = {}

        # Tạo các liên kết giữa các task con đảm bảo thứ tự đúng
        task_connections = [
            conn for conn in relates_to_connections if conn.from_node_id in reverse_hierarchy or conn.to_node_id in reverse_hierarchy]

        for conn in task_connections:
            from_node = conn.from_node_id
            to_node = conn.to_node_id

            # Nếu cả hai task đều nằm trong cùng một story
            if from_node in reverse_hierarchy and to_node in reverse_hierarchy:
                from_story = reverse_hierarchy[from_node]
                to_story = reverse_hierarchy[to_node]

                if from_story == to_story:
                    story_id = from_story
                    if story_id not in story_internal_dependencies:
                        story_internal_dependencies[story_id] = []
                    story_internal_dependencies[story_id].append(conn)

        log.debug(f"[GANTT-CALC] Found internal dependencies in {len(story_internal_dependencies)} stories")

        # Tìm các cặp story có quan hệ relates_to
        story_dependencies: List[Tuple[str, str]] = []
        for conn in relates_to_connections:
            if conn.from_node_id in story_ids and conn.to_node_id in story_ids:
                story_dependencies.append((conn.from_node_id, conn.to_node_id))
                log.debug(f"[GANTT-CALC] Found story dependency: {conn.from_node_id} -> {conn.to_node_id}")

        log.info(f"[GANTT-CALC] Found {len(story_dependencies)} story-to-story dependencies to propagate")

        # Lan truyền dependencies cho mỗi cặp story
        propagated_count = 0
        for src_story, dst_story in story_dependencies:
            log.debug(f"[GANTT-CALC] Processing story dependency: {src_story} -> {dst_story}")

            # Tìm task cuối cùng của story nguồn
            if src_story in hierarchy_map:
                src_children = hierarchy_map[src_story]
                if not src_children:
                    log.debug(f"[GANTT-CALC] Source story {src_story} has no children, skipping")
                    continue

                # Lấy task cuối trong story nguồn (không có depends đến task khác trong cùng story)
                src_story_connections = story_internal_dependencies.get(src_story, [])
                terminal_tasks = self._find_terminal_tasks(src_children, src_story_connections)

                log.debug(f"[GANTT-CALC] Terminal tasks for story {src_story}: {terminal_tasks}")

                # Nếu không tìm thấy terminal tasks, sử dụng tất cả task con
                if not terminal_tasks:
                    log.debug(
                        f"[GANTT-CALC] No terminal tasks found for story {src_story}, using all {len(src_children)} children")
                    terminal_tasks = src_children
                else:
                    log.debug(f"[GANTT-CALC] Found {len(terminal_tasks)} terminal tasks for story {src_story}")

                # Tìm task đầu tiên của story đích
                if dst_story in hierarchy_map:
                    dst_children = hierarchy_map[dst_story]
                    if not dst_children:
                        log.debug(f"[GANTT-CALC] Destination story {dst_story} has no children, skipping")
                        continue

                    # Lấy task đầu trong story đích (không có task khác trong cùng story depends đến nó)
                    dst_story_connections = story_internal_dependencies.get(dst_story, [])
                    initial_tasks = self._find_initial_tasks(dst_children, dst_story_connections)

                    log.debug(f"[GANTT-CALC] Initial tasks for story {dst_story}: {initial_tasks}")
                    # Nếu không tìm thấy initial tasks, sử dụng tất cả task con
                    if not initial_tasks:
                        log.debug(
                            f"[GANTT-CALC] No initial tasks found for story {dst_story}, using all {len(dst_children)} children")
                        initial_tasks = dst_children
                    else:
                        log.debug(f"[GANTT-CALC] Found {len(initial_tasks)} initial tasks for story {dst_story}")

                    # Tạo connections mới
                    story_propagated_count = 0
                    for term_task in terminal_tasks:
                        for init_task in initial_tasks:
                            # Kiểm tra connection này đã tồn tại chưa
                            existing = False
                            for conn in result:
                                if conn.from_node_id == term_task and conn.to_node_id == init_task:
                                    existing = True
                                    break

                            if not existing:
                                log.debug(f"[GANTT-CALC] Creating propagated dependency: {term_task} -> {init_task}")
                                result.append(GanttChartConnectionModel(
                                    from_node_id=term_task,
                                    to_node_id=init_task,
                                    type="relates to"
                                ))
                                propagated_count += 1
                                story_propagated_count += 1

                    log.debug(
                        f"[GANTT-CALC] Created {story_propagated_count} new dependencies for story pair {src_story}->{dst_story}")
                    log.debug(f"[GANTT-CALC] Current result: {result}")
                else:
                    log.debug(f"[GANTT-CALC] Destination story {dst_story} not found in hierarchy map")
            else:
                log.debug(f"[GANTT-CALC] Source story {src_story} not found in hierarchy map")

        log.info(f"[GANTT-CALC] Propagated {propagated_count} new dependencies between tasks")
        log.info(f"[GANTT-CALC] Final connection count: {len(result)}")
        return result

    def _find_terminal_tasks(self, tasks: List[str], connections: List[GanttChartConnectionModel]) -> List[str]:
        """Find tasks that have no outgoing relates_to connections within their parent story"""
        # Get all tasks that are sources in relates_to connections within this list of tasks
        source_tasks = set()
        target_tasks = set()

        for conn in connections:
            if conn.type.lower() == "relates to":
                # Chỉ xem xét các connections giữa các task trong danh sách này
                if conn.from_node_id in tasks:
                    source_tasks.add(conn.from_node_id)
                if conn.to_node_id in tasks:
                    target_tasks.add(conn.to_node_id)

        # Terminal tasks là những task có trong tasks mà không có outgoing connections đến task khác trong cùng danh sách
        # Hoặc có outgoing nhưng không đến task nào trong danh sách này
        terminal_tasks = []
        for task in tasks:
            # Nếu task không phải là source hoặc là source nhưng không có target nào trong danh sách tasks
            if task not in source_tasks or all(conn.to_node_id not in tasks for conn in connections if conn.from_node_id == task):
                terminal_tasks.append(task)

        # If no terminal tasks found, return all tasks
        if not terminal_tasks:
            log.debug("[GANTT-CALC] No terminal tasks found, using all tasks")
            terminal_tasks = tasks.copy()

        log.debug(f"[GANTT-CALC] Found {len(terminal_tasks)} terminal tasks out of {len(tasks)}")
        return terminal_tasks

    def _find_initial_tasks(self, tasks: List[str], connections: List[GanttChartConnectionModel]) -> List[str]:
        """Find tasks that have no incoming relates_to connections within their parent story"""
        # Get all tasks that are targets in relates_to connections within this list of tasks
        target_tasks = set()
        source_tasks = set()

        for conn in connections:
            if conn.type.lower() == "relates to":
                # Chỉ xem xét các connections giữa các task trong danh sách này
                if conn.to_node_id in tasks:
                    target_tasks.add(conn.to_node_id)
                if conn.from_node_id in tasks:
                    source_tasks.add(conn.from_node_id)

        # Initial tasks là những task có trong tasks mà không có incoming connections từ task khác trong cùng danh sách
        # Hoặc có incoming nhưng không từ task nào trong danh sách này
        initial_tasks = []
        for task in tasks:
            # Nếu task không phải là target hoặc là target nhưng không có source nào trong danh sách tasks
            if task not in target_tasks or all(conn.from_node_id not in tasks for conn in connections if conn.to_node_id == task):
                initial_tasks.append(task)

        # If no initial tasks found, return all tasks
        if not initial_tasks:
            log.debug("[GANTT-CALC] No initial tasks found, using all tasks")
            initial_tasks = tasks.copy()

        log.debug(f"[GANTT-CALC] Found {len(initial_tasks)} initial tasks out of {len(tasks)}")
        return initial_tasks

    def _build_dependency_map(self, connections: List[GanttChartConnectionModel]) -> Dict[str, Dict[str, str]]:
        """Build dependency map from connections with dependency types

        Args:
            connections: List of connections between tasks

        Returns:
            Dictionary mapping tasks to their dependencies
        """
        dependency_map: Dict[str, Dict[str, str]] = {}

        # Log the connections we're using to build the dependency map
        log.debug(f"[GANTT-CALC] Building dependency map from {len(connections)} connections:")
        for conn in connections:
            log.debug(f"[GANTT-CALC]   {conn.from_node_id} -> {conn.to_node_id} ({conn.type})")

        # Process all relates_to connections to build the dependency map
        for connection in connections:
            source = connection.from_node_id
            target = connection.to_node_id
            conn_type = connection.type.lower()

            # For 'relates to' connections, the target depends on the source
            # This means source must be completed before target can start
            if conn_type == "relates to":
                # Add target -> source dependency (target depends on source)
                if target not in dependency_map:
                    dependency_map[target] = {}

                dependency_map[target][source] = conn_type

                log.debug(f"[GANTT-CALC] Added dependency: {target} depends on {source}")

            # Add nodes to the map even if they have no dependencies
            # This ensures isolated nodes are still scheduled
            if source not in dependency_map:
                dependency_map[source] = {}

            if target not in dependency_map:
                dependency_map[target] = {}

        # Log the resulting dependency map for debugging
        log.debug("[GANTT-CALC] Resulting dependency map:")
        for node, deps in dependency_map.items():
            if deps:
                log.debug(f"[GANTT-CALC]   {node} depends on: {list(deps.keys())}")
            else:
                log.debug(f"[GANTT-CALC]   {node} has no dependencies")

        return dependency_map

    def _topological_sort(self, nodes: List[str], dependency_map: Dict[str, Dict[str, str]]) -> List[str]:
        """Sort tasks based on dependencies using Kahn's algorithm for topological sort

        Args:
            nodes: List of all task nodes
            dependency_map: Dictionary mapping tasks to their dependencies
                Format: {node: {dependency_node: relationship_type}}

        Returns:
            List of tasks in topological order where dependencies come before dependent tasks
        """
        log.debug(f"[GANTT-CALC] Starting Kahn's topological sort with nodes: {nodes}")
        log.debug(f"[GANTT-CALC] Dependency map: {dependency_map}")

        # Xây dựng đồ thị và đếm in-degree (số lượng node mà mỗi node phụ thuộc vào)
        graph = {node: [] for node in nodes}
        in_degree = {node: 0 for node in nodes}

        for node, dependencies in dependency_map.items():
            for dep_node in dependencies:
                # node phụ thuộc vào dep_node
                # Vì vậy trong đồ thị, dep_node --> node
                graph[dep_node].append(node)
                in_degree[node] += 1

        log.debug(f"[GANTT-CALC] Constructed graph: {graph}")
        log.debug(f"[GANTT-CALC] In-degree of each node: {in_degree}")

        # Khởi tạo hàng đợi với các node có in-degree = 0 (không phụ thuộc vào node nào)
        queue = [node for node in nodes if in_degree[node] == 0]
        log.debug(f"[GANTT-CALC] Initial queue (nodes with no dependencies): {queue}")

        result = []

        # Xử lý từng node trong hàng đợi
        while queue:
            current = queue.pop(0)
            result.append(current)
            log.debug(f"[GANTT-CALC] Processed node {current}, current result: {result}")

            # Giảm in-degree của các node bị ảnh hưởng bởi current
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                log.debug(f"[GANTT-CALC] Reduced in-degree of {neighbor} to {in_degree[neighbor]}")

                # Nếu in-degree = 0, thêm vào hàng đợi
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    log.debug(f"[GANTT-CALC] Added {neighbor} to queue, current queue: {queue}")

        # Kiểm tra chu trình
        if len(result) != len(nodes):
            log.error(f"[GANTT-CALC] Cycle detected! Only processed {len(result)} out of {len(nodes)} nodes.")
            raise ValueError("Cycle detected in task dependencies")

        log.debug(f"[GANTT-CALC] Final topological sort result: {result}")

        # Kiểm tra tính đúng đắn của kết quả
        for node, dependencies in dependency_map.items():
            for dep_node in dependencies:
                if result.index(node) < result.index(dep_node):
                    log.error(f"[GANTT-CALC] Invalid order: {node} depends on {dep_node} but appears before it!")

        return result

    def _calculate_task_times(
        self,
        sorted_tasks: List[str],
        issues_map: Dict[str, GanttChartJiraIssueModel],
        dependency_map: Dict[str, Dict[str, str]],
        sprint_start: datetime,
        sprint_end: datetime,
        config: ProjectConfigModel
    ) -> List[TaskScheduleModel]:
        """Calculate start and end times for each task based on their dependencies

        Args:
            sorted_tasks: List of tasks in topological order
            issues_map: Dictionary mapping node_id to issue data
            dependency_map: Dictionary mapping node_id to dependencies
            sprint_start: Sprint start datetime
            sprint_end: Sprint end datetime
            config: Project configuration parameters

        Returns:
            List of TaskScheduleModel objects with calculated times
        """
        log.debug(f"[GANTT-CALC] Calculating task times for {len(sorted_tasks)} tasks")
        result: List[TaskScheduleModel] = []
        task_end_times: Dict[str, datetime] = {}  # Map of node_id to end time
        task_start_times: Dict[str, datetime] = {}  # Map of node_id to start time

        # Set work day start and end times
        work_start = config.start_work_hour
        work_end = config.end_work_hour
        hours_per_day = config.working_hours_per_day
        hours_per_point = config.estimate_point_to_hours
        lunch_break_minutes = config.lunch_break_minutes

        # Define minimum task duration (30 minutes for tasks with zero estimate)
        min_task_duration_hours = 0.5  # 30 minutes

        log.info(
            f"[GANTT-CALC] Work configuration: {work_start} to {work_end}, {hours_per_day} hours/day, {hours_per_point} hours/point, {lunch_break_minutes} min lunch")
        log.info(f"[GANTT-CALC] Sprint period: {sprint_start} to {sprint_end}")

        task_count = 0
        zero_estimate_count = 0

        # Log the order of task processing for debugging
        log.info(f"[GANTT-CALC] Processing tasks in order: {sorted_tasks}")

        # First, let's verify our dependency map is correct
        for node_id in sorted_tasks:
            if node_id in dependency_map:
                deps = dependency_map[node_id]
                if deps:
                    log.debug(f"[GANTT-CALC] Task {node_id} depends on: {list(deps.keys())}")
                else:
                    log.debug(f"[GANTT-CALC] Task {node_id} has no dependencies")
            else:
                log.warning(f"[GANTT-CALC] Task {node_id} not found in dependency map!")

        # Process tasks in topological order
        for node_id in sorted_tasks:
            task_count += 1
            log.debug(f"[GANTT-CALC] Processing task {task_count}/{len(sorted_tasks)}: {node_id}")

            issue = issues_map.get(node_id)
            if not issue:
                log.warning(f"[GANTT-CALC] Node {node_id} not found in issues map, skipping")
                continue

            # Get estimate points from issue
            estimate_points = issue.estimate_points
            estimate_hours = estimate_points * hours_per_point

            # Ensure all tasks have at least the minimum duration
            if estimate_hours < min_task_duration_hours:
                zero_estimate_count += 1
                log.debug(
                    f"[GANTT-CALC] Task {node_id} ({issue.jira_key or 'no key'}) has insufficient estimate, assigning minimum duration")
                estimate_hours = min_task_duration_hours

            # Find latest end time of dependencies
            latest_dependency_end = sprint_start
            latest_dependency_node = None
            predecessors = []
            dep_count = 0

            # Process each dependency
            if node_id in dependency_map:
                dependencies = dependency_map[node_id].keys()
                if dependencies:
                    log.debug(f"[GANTT-CALC] Task {node_id} depends on: {list(dependencies)}")

                for dep_node in dependencies:
                    dep_count += 1
                    predecessors.append(dep_node)

                    # Task can only start after all dependencies end
                    if dep_node in task_end_times:
                        dep_end_time = task_end_times[dep_node]
                        log.debug(f"[GANTT-CALC] Dependency {dep_node} ends at {dep_end_time}")

                        if dep_end_time > latest_dependency_end:
                            latest_dependency_end = dep_end_time
                            latest_dependency_node = dep_node
                            log.debug(
                                f"[GANTT-CALC] Task {node_id} latest dependency is now {dep_node}: {latest_dependency_end}")
                    else:
                        # Should not happen if topological sort is correct
                        log.warning(
                            f"[GANTT-CALC] Dependency {dep_node} for task {node_id} has no end time yet - this should not happen with correct topological sort!")
                        # Use sprint start as fallback
                        log.warning("[GANTT-CALC] Using sprint start time as fallback!")
            else:
                log.debug(f"[GANTT-CALC] Task {node_id} not found in dependency map, assuming no dependencies")

            if dep_count > 0:
                log.debug(
                    f"[GANTT-CALC] Task {node_id} has {dep_count} dependencies, latest from {latest_dependency_node or 'none'}")
            else:
                log.debug(f"[GANTT-CALC] Task {node_id} has no dependencies, starting at sprint start time")

            # Calculate start time - must be valid work time
            start_time = self._next_work_time(latest_dependency_end, work_start, work_end)
            log.debug(f"[GANTT-CALC] Task {node_id} raw start time: {latest_dependency_end} -> adjusted: {start_time}")

            # Calculate end time
            end_time = self._add_work_hours(
                start_time,
                estimate_hours,
                work_start,
                work_end,
                hours_per_day,
                lunch_break_minutes
            )
            log.debug(f"[GANTT-CALC] Task {node_id} end time: {end_time} (duration: {estimate_hours} hours)")

            # Double-check that end_time is always after start_time
            if end_time <= start_time:
                log.warning(f"[GANTT-CALC] Task {node_id} end time <= start time, adjusting end time")
                # Add minimum duration
                end_time = self._add_work_hours(
                    start_time,
                    min_task_duration_hours,
                    work_start,
                    work_end,
                    hours_per_day,
                    lunch_break_minutes
                )
                log.debug(f"[GANTT-CALC] Task {node_id} adjusted end time: {end_time}")

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
                estimate_hours=max(estimate_hours, min_task_duration_hours),  # Use at least minimum duration
                plan_start_time=start_time,
                plan_end_time=end_time,
                predecessors=predecessors,
                assignee_id=issue.assignee_id
            )

            result.append(schedule)

        log.info(f"[GANTT-CALC] Calculated times for {len(result)} tasks")
        log.info(f"[GANTT-CALC] Found {zero_estimate_count} tasks with zero or minimal estimate")

        if result:
            earliest_start = min([task.plan_start_time for task in result])
            latest_end = max([task.plan_end_time for task in result])
            log.info(f"[GANTT-CALC] Schedule span: {earliest_start} to {latest_end}")

        return result

    def _adjust_story_times(
        self,
        tasks: List[TaskScheduleModel],
        hierarchy_map: Dict[str, List[str]]
    ) -> List[TaskScheduleModel]:
        """Adjust story times based on child tasks"""
        # Build a map for easier lookup
        task_map = {task.node_id: task for task in tasks}

        log.info(f"[GANTT-CALC] Adjusting story times for {len(hierarchy_map)} stories")
        adjusted_count = 0

        # For each story, adjust times based on child tasks
        for story_id, child_ids in hierarchy_map.items():
            if not child_ids or story_id not in task_map:
                log.debug(f"[GANTT-CALC] Story {story_id} has no children or is not in task map, skipping")
                continue

            # Get the story task
            story_task = task_map[story_id]

            # Find earliest start and latest end among children
            earliest_start = None
            latest_end = None
            valid_children = 0

            for child_id in child_ids:
                if child_id in task_map:
                    valid_children += 1
                    child_task = task_map[child_id]

                    if earliest_start is None or child_task.plan_start_time < earliest_start:
                        earliest_start = child_task.plan_start_time

                    if latest_end is None or child_task.plan_end_time > latest_end:
                        latest_end = child_task.plan_end_time

            # Update story times if children were found
            if earliest_start is not None and latest_end is not None:
                log.debug(f"[GANTT-CALC] Adjusting story {story_id} times based on {valid_children} children")
                log.debug(
                    f"[GANTT-CALC] Story {story_id} before: start={story_task.plan_start_time}, end={story_task.plan_end_time}")

                # Create a new task with updated times
                updated_story = TaskScheduleModel(
                    node_id=story_task.node_id,
                    jira_key=story_task.jira_key,
                    title=story_task.title,
                    type=story_task.type,
                    estimate_points=story_task.estimate_points,
                    estimate_hours=story_task.estimate_hours,
                    plan_start_time=earliest_start,
                    plan_end_time=latest_end,
                    predecessors=story_task.predecessors,
                    assignee_id=story_task.assignee_id
                )

                # Replace the story in the list
                for i, task in enumerate(tasks):
                    if task.node_id == story_id:
                        tasks[i] = updated_story
                        adjusted_count += 1
                        break

                log.debug(
                    f"[GANTT-CALC] Story {story_id} after: start={updated_story.plan_start_time}, end={updated_story.plan_end_time}")

        log.info(f"[GANTT-CALC] Adjusted {adjusted_count} stories based on child tasks")
        return tasks

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
