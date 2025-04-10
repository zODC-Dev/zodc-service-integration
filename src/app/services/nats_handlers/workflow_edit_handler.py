from typing import Any, Dict, List, Optional
import uuid

from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.logger import log
from src.domain.constants.jira import JiraActionType, JiraIssueType
from src.domain.models.jira.apis.requests.jira_issue import JiraIssueAPICreateRequestDTO, JiraIssueAPIUpdateRequestDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.nats.replies.workflow_edit import WorkflowEditReply, WorkflowEditReplyIssue
from src.domain.models.nats.requests.workflow_edit import WorkflowEditConnection, WorkflowEditIssue, WorkflowEditRequest
from src.domain.models.workflow_mapping import WorkflowMappingModel
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.workflow_mapping_repository import IWorkflowMappingRepository
from src.domain.services.nats_message_handler import INATSRequestHandler
from src.domain.services.redis_service import IRedisService


class WorkflowEditRequestHandler(INATSRequestHandler):
    def __init__(
        self,
        jira_issue_service: JiraIssueApplicationService,
        user_repository: IJiraUserRepository,
        jira_sprint_repository: IJiraSprintRepository,
        workflow_mapping_repository: IWorkflowMappingRepository,
        redis_service: IRedisService
    ):
        self.jira_issue_service = jira_issue_service
        self.user_repository = user_repository
        self.jira_sprint_repository = jira_sprint_repository
        self.workflow_mapping_repository = workflow_mapping_repository
        self.redis_service = redis_service

    async def handle(self, subject: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow edit requests"""
        try:
            log.info(f"Received workflow edit request: {message}")
            # Convert raw message to DTO
            request = WorkflowEditRequest.model_validate(message)

            # Lưu workflow mapping
            workflow_id = str(uuid.uuid4())
            workflow_mapping = WorkflowMappingModel(
                workflow_id=workflow_id,
                transaction_id=request.transaction_id,
                project_key=request.project_key,
                sprint_id=request.sprint_id,
                status="active"
            )
            await self.workflow_mapping_repository.create(workflow_mapping)
            log.info(f"Created workflow mapping with ID: {workflow_id}")

            # Tạo mapping ban đầu từ node_mappings nếu có
            node_to_jira_key_map = {}
            for mapping in request.node_mappings:
                node_to_jira_key_map[mapping.node_id] = mapping.jira_key
                log.info(f"Mapping from request: Node ID {mapping.node_id} -> Jira key {mapping.jira_key}")

            # Bổ sung mapping từ issues có sẵn jira_key
            for issue in request.issues:
                if issue.jira_key and issue.node_id not in node_to_jira_key_map:
                    node_to_jira_key_map[issue.node_id] = issue.jira_key
                    log.info(f"Mapping from issues: Node ID {issue.node_id} -> Jira key {issue.jira_key}")

            # Bước 1: Xóa các connections cũ
            removed_count = await self._remove_connections(request.connections_to_remove, node_to_jira_key_map)
            log.info(f"Removed {removed_count} connections")

            # Bước 2: Xử lý các issues (tạo mới/cập nhật)
            created_issues = await self._process_issues(request)

            # Cập nhật mapping sau khi xử lý issues
            for result_issue in created_issues:
                node_to_jira_key_map[result_issue.node_id] = result_issue.jira_key
                log.info(f"Updated mapping: Node ID {result_issue.node_id} -> Jira key {result_issue.jira_key}")

                # Lưu jira_key vào Redis để đánh dấu là system_linked khi webhook được gọi
                await self._mark_issue_for_system_linking(result_issue.jira_key)

            # Bước 3: Tạo các connections mới
            added_count = 0
            if request.connections:
                added_count = await self._add_connections(request.connections, node_to_jira_key_map)
                log.info(f"Added {added_count} connections")

            # Return response
            response = WorkflowEditReply(
                issues=created_issues,
                removed_connections=removed_count,
                added_connections=added_count
            )

            return {
                "success": True,
                "data": response.model_dump()
            }

        except Exception as e:
            log.error(f"Error handling workflow edit request: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": WorkflowEditReply(issues=[], removed_connections=0, added_connections=0).model_dump()
            }

    async def _remove_connections(self, connections_to_remove: List[WorkflowEditConnection], node_to_jira_key_map: Dict[str, str]) -> int:
        """Xóa các connections hiện có giữa các issues"""
        removed_count = 0

        for connection in connections_to_remove:
            try:
                # Lấy Jira key từ node ID hoặc dùng giá trị trực tiếp nếu là jira_key
                source_key = node_to_jira_key_map.get(connection.from_issue_key, connection.from_issue_key)
                target_key = node_to_jira_key_map.get(connection.to_issue_key, connection.to_issue_key)

                log.info(f"Removing link between {source_key} and {target_key}")

                # Lấy tất cả issuelinks của source issue
                issue_data = await self.jira_issue_service.jira_issue_api_service.get_issue_with_admin_auth(source_key)

                if not issue_data:
                    log.error(f"Source issue {source_key} not found")
                    continue

                # Kiểm tra nếu có issue links
                issue_links = issue_data.issue_links
                if not issue_links:
                    log.info(f"No links found for issue {source_key}")
                    continue

                # Tìm link với target issue
                link_id = None
                for link in issue_links:
                    if (link.inward_issue and link.inward_issue.key == target_key) or \
                       (link.outward_issue and link.outward_issue.key == target_key):
                        link_id = link.id
                        break

                if not link_id:
                    log.warning(f"No link found between {source_key} and {target_key}")
                    continue

                # Xóa link bằng id
                success = await self.jira_issue_service.jira_issue_api_service.delete_issue_link_with_admin_auth(link_id)

                if success:
                    removed_count += 1
                    log.info(f"Successfully removed link (id: {link_id}) between {source_key} and {target_key}")
                else:
                    log.error(f"Failed to remove link (id: {link_id}) between {source_key} and {target_key}")

            except Exception as e:
                log.error(
                    f"Error removing link between {connection.from_issue_key} and {connection.to_issue_key}: {str(e)}")

        return removed_count

    async def _process_issues(self, request: WorkflowEditRequest) -> List[WorkflowEditReplyIssue]:
        """Process all issues in the request"""
        result_issues = []

        for issue in request.issues:
            try:
                # Check action type
                if issue.action.lower() == JiraActionType.CREATE.value:
                    # Create new issue
                    jira_issue = await self._create_issue(issue, request.project_key, request.sprint_id)
                    if jira_issue:
                        result_issues.append(WorkflowEditReplyIssue(
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
                        result_issues.append(WorkflowEditReplyIssue(
                            node_id=issue.node_id,
                            jira_key=jira_issue.key
                        ))
                        log.info(f"Updated Jira issue: {jira_issue.key} for node: {issue.node_id}")

            except Exception as e:
                log.error(f"Error processing issue {issue.node_id}: {str(e)}")

        return result_issues

    async def _create_issue(self, issue: WorkflowEditIssue, project_key: str, sprint_id: Optional[int]) -> JiraIssueModel:
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
                log.error(f"Error mapping sprint ID {sprint_id} to Jira sprint ID: {str(e)}")

        # Create issue data
        create_dto = JiraIssueAPICreateRequestDTO(
            jira_issue_id="",
            key="",
            project_key=project_key,
            summary=issue.title,
            type=issue_type,
            assignee_id=str(issue.assignee_id),
            sprint_id=jira_sprint_id
        )

        # Sử dụng admin auth để tạo issue
        return await self.jira_issue_service.jira_issue_api_service.create_issue_with_admin_auth(
            issue_data=create_dto
        )

    async def _update_issue(self, issue: WorkflowEditIssue) -> JiraIssueModel:
        """Update an existing issue in Jira"""
        if not issue.jira_key:
            raise Exception("Cannot update issue without jira_key")

        # Create update data
        update_dto = JiraIssueAPIUpdateRequestDTO(
            summary=issue.title,
            assignee_id=str(issue.assignee_id)
        )

        # Sử dụng admin auth để update issue
        return await self.jira_issue_service.jira_issue_api_service.update_issue_with_admin_auth(
            issue_id=issue.jira_key,
            update=update_dto
        )

    async def _add_connections(
        self,
        connections: List[WorkflowEditConnection],
        node_to_jira_key_map: Dict[str, str]
    ) -> int:
        """Tạo các connections mới giữa các issues"""
        added_count = 0

        # Log mapping để dễ debug
        log.info(f"Node to Jira key mapping: {node_to_jira_key_map}")

        for connection in connections:
            try:
                # Lấy Jira key từ node ID
                source_key = node_to_jira_key_map.get(connection.from_issue_key, connection.from_issue_key)
                target_key = node_to_jira_key_map.get(connection.to_issue_key, connection.to_issue_key)

                # Kiểm tra xem đã có jira_key cho cả source và target chưa
                if not source_key:
                    log.error(f"Missing Jira key for source node ID: {connection.from_issue_key}")
                    continue

                if not target_key:
                    log.error(f"Missing Jira key for target node ID: {connection.to_issue_key}")
                    continue

                # Create "relates to" link between issues using admin auth
                success = await self.jira_issue_service.jira_issue_api_service.create_issue_link_with_admin_auth(
                    source_issue_id=source_key,
                    target_issue_id=target_key,
                    relationship="Relates"  # Always using "relates to" as requested
                )

                if success:
                    added_count += 1
                    log.info(f"Created link between {source_key} and {target_key}")
                else:
                    log.error(f"Failed to create link between {source_key} and {target_key}")

            except Exception as e:
                log.error(
                    f"Error creating link between {connection.from_issue_key} and {connection.to_issue_key}: {str(e)}")

        return added_count

    async def _mark_issue_for_system_linking(self, jira_key: str):
        """Đánh dấu issue cần được liên kết với hệ thống trong Redis"""
        try:
            # Tạo key Redis
            redis_key = f"system_linked:jira_issue:{jira_key}"

            # Lưu vào Redis với TTL 24 giờ (86400 giây)
            await self.redis_service.set(redis_key, "true", expiry=86400)
            log.info(f"Marked issue {jira_key} for system linking in Redis")
        except Exception as e:
            log.error(f"Error marking issue {jira_key} for system linking: {str(e)}")

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
