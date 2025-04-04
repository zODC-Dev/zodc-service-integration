from typing import Any, Dict, List, Optional

from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.jira import JiraActionType, JiraIssueType
from src.domain.models.jira.apis.requests.jira_issue import JiraIssueAPICreateRequestDTO, JiraIssueAPIUpdateRequestDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.nats.replies.workflow_sync import WorkflowSyncReply, WorkflowSyncReplyIssue
from src.domain.models.nats.requests.workflow_sync import WorkflowSyncConnection, WorkflowSyncIssue, WorkflowSyncRequest
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.nats_message_handler import INATSRequestHandler


class WorkflowSyncRequestHandler(INATSRequestHandler):
    def __init__(
        self,
        jira_issue_service: JiraIssueApplicationService,
        user_repository: IJiraUserRepository,
        jira_sprint_repository: IJiraSprintRepository
    ):
        self.jira_issue_service = jira_issue_service
        self.user_repository = user_repository
        self.jira_sprint_repository = jira_sprint_repository

    async def handle(self, subject: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow sync requests"""
        try:
            log.info(f"Received workflow sync request: {message}")
            # Convert raw message to DTO
            request = WorkflowSyncRequest.model_validate(message)

            # Tạo mapping ban đầu từ các issue đã có Jira key
            node_to_jira_key_map = {}
            for issue in request.issues:
                if issue.jira_key:
                    node_to_jira_key_map[issue.node_id] = issue.jira_key
                    log.info(f"Initial mapping: Node ID {issue.node_id} -> Jira key {issue.jira_key}")

            # Process issues (create/update)
            created_issues = await self._process_issues(request)

            # Cập nhật mapping sau khi xử lý issues
            for result_issue in created_issues:
                node_to_jira_key_map[result_issue.node_id] = result_issue.jira_key
                log.info(f"Updated mapping: Node ID {result_issue.node_id} -> Jira key {result_issue.jira_key}")

            # Process connections between issues - chỉ xử lý sau khi đã có đủ mapping
            if request.connections:
                await self._process_connections(request.connections, node_to_jira_key_map)

            # Return response with created issues
            response = WorkflowSyncReply(issues=created_issues)

            # Check if we processed any issues successfully
            if not created_issues and (request.issues or request.connections):
                # Nếu có issues/connections để xử lý nhưng không có issue nào thành công
                # thì trả về error
                return {
                    "success": False,
                    "error": "Failed to process workflow sync request - no issues were created/updated",
                    "data": response.model_dump()
                }

            return {
                "success": True,
                "data": response.model_dump()
            }

        except Exception as e:
            log.error(f"Error handling workflow sync request: {str(e)}")
            # Return error response
            return {
                "success": False,
                "error": str(e),
                "data": WorkflowSyncReply(issues=[]).model_dump()
            }

    async def _process_issues(self, request: WorkflowSyncRequest) -> List[WorkflowSyncReplyIssue]:
        """Process all issues in the request"""
        result_issues = []

        for issue in request.issues:
            try:
                # Check action type
                if issue.action.lower() == JiraActionType.CREATE.value:
                    # Create new issue
                    jira_issue = await self._create_issue(issue, request.project_key, request.sprint_id)
                    if jira_issue:
                        result_issues.append(WorkflowSyncReplyIssue(
                            node_id=issue.node_id,
                            jira_key=jira_issue.key
                        ))
                        log.info(f"Created Jira issue: {jira_issue.key} for node: {issue.node_id}")

                elif issue.action.lower() == JiraActionType.UPDATE.value:
                    # Update existing issue
                    if not issue.jira_key:
                        log.error(f"Cannot update issue without jira_key: {issue.node_id}")
                        continue

                    jira_issue = await self._update_issue(issue)
                    if jira_issue:
                        result_issues.append(WorkflowSyncReplyIssue(
                            node_id=issue.node_id,
                            jira_key=jira_issue.key
                        ))
                        log.info(f"Updated Jira issue: {jira_issue.key} for node: {issue.node_id}")

            except Exception as e:
                raise Exception(f"Error processing issue {issue.node_id}: {str(e)}") from e

        return result_issues

    async def _create_issue(self, issue: WorkflowSyncIssue, project_key: str, sprint_id: Optional[int]) -> JiraIssueModel:
        """Create a new issue in Jira"""
        # Map issue type to Jira issue type
        issue_type = self._map_issue_type(issue.type)

        # Tìm Jira sprint ID tương ứng từ sprint ID của DB nếu có
        jira_sprint_id = None
        if sprint_id:
            try:
                # Lấy sprint từ repository
                sprint = await self.jira_sprint_repository.get_sprint_by_id(sprint_id)
                if sprint and sprint.jira_sprint_id:
                    jira_sprint_id = sprint.jira_sprint_id
                    log.info(f"Mapped sprint ID {sprint_id} to Jira sprint ID {jira_sprint_id}")
                else:
                    log.warning(f"Could not find Jira sprint ID for sprint ID {sprint_id}")
            except Exception as e:
                raise Exception(f"Error mapping sprint ID {sprint_id} to Jira sprint ID: {str(e)}") from e

        # Create issue data
        create_dto = JiraIssueAPICreateRequestDTO(
            jira_issue_id="",
            key="",
            project_key=project_key,
            summary=issue.title,
            type=issue_type,
            assignee_id=str(issue.assignee_id),
            sprint_id=jira_sprint_id  # Sử dụng Jira sprint ID đã được map
        )

        # Use system user or first available user with Jira access
        user_id = await self._get_valid_user_id()

        # Create issue via Jira API
        return await self.jira_issue_service.jira_issue_api_service.create_issue(
            user_id=user_id,
            issue_data=create_dto
        )

    async def _update_issue(self, issue: WorkflowSyncIssue) -> JiraIssueModel:
        """Update an existing issue in Jira"""
        # Map assignee_id to Jira account ID if provided

        # Create update data
        update_dto = JiraIssueAPIUpdateRequestDTO(
            summary=issue.title,
            assignee_id=str(issue.assignee_id)
        )

        # Use system user or first available user with Jira access
        user_id = await self._get_valid_user_id()

        # Update issue via Jira API
        return await self.jira_issue_service.jira_issue_api_service.update_issue(
            user_id=user_id,
            issue_id=issue.jira_key,
            update=update_dto
        )

    async def _process_connections(
        self,
        connections: List[WorkflowSyncConnection],
        node_to_jira_key_map: Dict[str, str]
    ):
        """Process all connections between issues"""
        user_id = await self._get_valid_user_id()
        connection_results = []

        # Log mapping để dễ debug
        log.info(f"Node to Jira key mapping: {node_to_jira_key_map}")

        for connection in connections:
            try:
                # Lấy Jira key từ node ID
                source_key = node_to_jira_key_map.get(connection.from_issue_key)
                target_key = node_to_jira_key_map.get(connection.to_issue_key)

                # Kiểm tra xem đã có jira_key cho cả source và target chưa
                if not source_key:
                    log.error(f"Missing Jira key for source node ID: {connection.from_issue_key}")
                    connection_results.append(False)
                    continue

                if not target_key:
                    log.error(f"Missing Jira key for target node ID: {connection.to_issue_key}")
                    connection_results.append(False)
                    continue

                # Create "relates to" link between issues
                success = await self.jira_issue_service.jira_issue_api_service.create_issue_link(
                    user_id=user_id,
                    source_issue_id=source_key,
                    target_issue_id=target_key,
                    relationship="Relates"  # Always using "relates to" as requested
                )

                if success:
                    log.info(f"Created link between {source_key} and {target_key}")
                    connection_results.append(True)
                else:
                    log.error(f"Failed to create link between {source_key} and {target_key}")
                    connection_results.append(False)

            except Exception as e:
                log.error(
                    f"Error creating link between {connection.from_issue_key} and {connection.to_issue_key}: {str(e)}")
                connection_results.append(False)

        # Nếu không có connection nào thành công, raise exception
        if connections and not any(connection_results):
            raise Exception("Failed to create any connections between issues")

    async def _get_valid_user_id(self) -> int:
        """Get a valid user ID for Jira API calls"""
        # In a real implementation, you might want to use a system user or
        # get the first user with Jira access from the repository
        # For now, returning a placeholder value
        return settings.JIRA_SYSTEM_USER_ID

    def _map_issue_type(self, issue_type: str) -> str:
        """Map issue type to Jira issue type"""
        # Normalize to uppercase for comparison
        normalized_type = issue_type.upper()

        if normalized_type == "STORY":
            return JiraIssueType.STORY.value
        elif normalized_type == "TASK":
            return JiraIssueType.TASK.value
        elif normalized_type == "BUG":
            return JiraIssueType.BUG.value
        elif normalized_type == "EPIC":
            return JiraIssueType.EPIC.value
        else:
            # Default to Task if unknown type
            log.warning(f"Unknown issue type: {issue_type}, defaulting to Task")
            return JiraIssueType.TASK.value
