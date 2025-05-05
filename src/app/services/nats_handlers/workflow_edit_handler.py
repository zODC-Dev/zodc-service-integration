from typing import Any, Dict, List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.logger import log
from src.domain.constants.jira import JiraActionType, JiraIssueType
from src.domain.models.database.jira_issue import JiraIssueDBUpdateDTO
from src.domain.models.jira.apis.requests.jira_issue import JiraIssueAPICreateRequestDTO, JiraIssueAPIUpdateRequestDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.nats.replies.workflow_edit import WorkflowEditReply, WorkflowEditReplyIssue
from src.domain.models.nats.requests.workflow_edit import WorkflowEditConnection, WorkflowEditIssue, WorkflowEditRequest
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.nats_message_handler import INATSRequestHandler
from src.domain.services.redis_service import IRedisService
from src.utils.date_utils import is_db_timestamp_newer, convert_timestamp_to_timestamptz


class WorkflowEditRequestHandler(INATSRequestHandler):
    def __init__(
        self,
        jira_issue_service: JiraIssueApplicationService,
        user_repository: IJiraUserRepository,
        jira_sprint_repository: IJiraSprintRepository,
        redis_service: IRedisService,
        jira_issue_repository: IJiraIssueRepository
    ):
        self.jira_issue_service = jira_issue_service
        self.user_repository = user_repository
        self.jira_sprint_repository = jira_sprint_repository
        self.redis_service = redis_service
        self.jira_issue_repository = jira_issue_repository

    async def handle(self, subject: str, message: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
        """Handle workflow edit requests"""
        try:
            log.info(f"Received workflow edit request: {message}")
            # Convert raw message to DTO
            request = WorkflowEditRequest.model_validate(message)

            # Check last synced at
            issue_keys = [issue.jira_key for issue in request.issues if issue.jira_key]
            db_issues = await self.jira_issue_repository.get_issues_by_keys(session=session, keys=issue_keys)

            for issue in request.issues:
                log.info(f"Checking issue {issue.jira_key} with last synced at {issue.last_synced_at}")
                if issue.last_synced_at:
                    # Convert NATS timestamp to one with timezone info for proper comparison
                    nats_last_synced = convert_timestamp_to_timestamptz(issue.last_synced_at)

                    db_issue = next((db_issue for db_issue in db_issues if db_issue.key == issue.jira_key), None)
                    if db_issue and db_issue.last_synced_at:
                        log.debug(
                            f"DB last_synced_at: {db_issue.last_synced_at}, NATS last_synced_at (with tz): {nats_last_synced}")

                        if db_issue.last_synced_at > nats_last_synced:
                            log.info(f"Issue {issue.jira_key} was synced after {nats_last_synced}, skipping")
                            return {
                                "success": False,
                                "error": f"Issue {issue.jira_key} was synced after {nats_last_synced}, skipping",
                                "data": WorkflowEditReply(
                                    success=False,
                                    error_message=f"Issue {issue.jira_key} was synced after {nats_last_synced}, skipping",
                                    issues=[],
                                    removed_connections=0,
                                    added_connections=0
                                ).model_dump()
                            }

            # Tạo mapping ban đầu từ node_mappings nếu có
            node_to_jira_key_map: Dict[str, str] = {}
            for mapping in request.node_mappings:
                node_to_jira_key_map[mapping.node_id] = mapping.jira_key
                log.debug(f"Mapping from request: Node ID {mapping.node_id} -> Jira key {mapping.jira_key}")

            # Bổ sung mapping từ issues có sẵn jira_key
            for issue in request.issues:
                if issue.jira_key and issue.node_id not in node_to_jira_key_map:
                    node_to_jira_key_map[issue.node_id] = issue.jira_key
                    log.debug(f"Mapping from issues: Node ID {issue.node_id} -> Jira key {issue.jira_key}")

            # Bước 1: Xóa các connections cũ
            removed_count = await self._remove_connections(session=session, connections_to_remove=request.connections_to_remove, node_to_jira_key_map=node_to_jira_key_map)
            log.debug(f"Removed {removed_count} connections")

            # Bước 2: Xử lý các issues (tạo mới/cập nhật)
            created_issues = await self._process_issues(session=session, request=request)

            # Cập nhật mapping sau khi xử lý issues
            for result_issue in created_issues:
                node_to_jira_key_map[result_issue.node_id] = result_issue.jira_key
                log.debug(f"Updated mapping: Node ID {result_issue.node_id} -> Jira key {result_issue.jira_key}")

            # Bước 3: Tạo các connections mới
            added_count = 0
            if request.connections:
                added_count = await self._add_connections(request.connections, node_to_jira_key_map)
                log.debug(f"Added {added_count} connections")

            # Return response
            response = WorkflowEditReply(
                success=True,
                error_message=None,
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
                "data": WorkflowEditReply(success=False, error_message=str(e), issues=[], removed_connections=0, added_connections=0).model_dump()
            }

    async def _remove_connections(self, session: AsyncSession, connections_to_remove: List[WorkflowEditConnection], node_to_jira_key_map: Dict[str, str]) -> int:
        """Xóa các connections hiện có giữa các issues"""
        removed_count = 0

        for connection in connections_to_remove:
            try:
                # Lấy Jira key từ node ID hoặc dùng giá trị trực tiếp nếu là jira_key
                source_key = node_to_jira_key_map.get(connection.from_issue_key, connection.from_issue_key)
                target_key = node_to_jira_key_map.get(connection.to_issue_key, connection.to_issue_key)

                log.debug(f"Removing link between {source_key} and {target_key}")

                # Sử dụng hàm get_issue_links_with_admin_auth mới để lấy tất cả issue links của source_key
                issue_links = await self.jira_issue_service.jira_issue_api_service.get_issue_links_with_admin_auth(issue_key=source_key)

                if not issue_links:
                    log.debug(f"No links found for issue {source_key}")
                    continue

                # Tìm link với target issue
                link_id = None
                for link in issue_links:
                    if link.linked_issue.key == target_key:
                        link_id = link.id
                        log.debug(
                            f"Found link {link_id} between {source_key} and {target_key} with relationship: {link.relationship_description}")
                        break

                if not link_id:
                    log.warning(f"No link found between {source_key} and {target_key}")
                    continue

                # Xóa link bằng id
                success = await self.jira_issue_service.remove_issue_link(session=session, link_id=link_id)

                if success:
                    removed_count += 1
                    log.debug(f"Successfully removed link (id: {link_id}) between {source_key} and {target_key}")
                else:
                    log.error(f"Failed to remove link (id: {link_id}) between {source_key} and {target_key}")

            except Exception as e:
                log.error(
                    f"Error removing link between {connection.from_issue_key} and {connection.to_issue_key}: {str(e)}")

        return removed_count

    async def _process_issues(self, session: AsyncSession, request: WorkflowEditRequest) -> List[WorkflowEditReplyIssue]:
        """Process all issues in the request"""
        result_issues = []

        for issue in request.issues:
            try:
                # Check action type
                if issue.action.lower() == JiraActionType.CREATE.value:
                    # Create new issue
                    jira_issue = await self._create_issue(session=session, issue=issue, project_key=request.project_key, sprint_id=request.sprint_id)
                    if jira_issue:
                        result_issues.append(WorkflowEditReplyIssue(
                            node_id=issue.node_id,
                            jira_key=jira_issue.key,
                            jira_link_url=jira_issue.link_url
                        ))
                        log.info(f"Created Jira issue: {jira_issue.key} for node: {issue.node_id}")

                elif issue.action.lower() == JiraActionType.UPDATE.value:
                    # Update existing issue
                    if not issue.jira_key:
                        log.error(f"Cannot update issue without jira_key: {issue.node_id}")
                        continue

                    jira_issue = await self._update_issue(session=session, issue=issue, project_key=request.project_key, sprint_id=request.sprint_id)
                    if jira_issue:
                        result_issues.append(WorkflowEditReplyIssue(
                            node_id=issue.node_id,
                            jira_key=jira_issue.key,
                            jira_link_url=jira_issue.link_url
                        ))
                        log.debug(f"Updated Jira issue: {jira_issue.key} for node: {issue.node_id}")

            except Exception as e:
                log.error(f"Error processing issue {issue.node_id}: {str(e)}")

        return result_issues

    async def _create_issue(self, session: AsyncSession, issue: WorkflowEditIssue, project_key: str, sprint_id: Optional[int]) -> JiraIssueModel:
        """Create a new issue in Jira"""
        # Map issue type to Jira issue type
        issue_type = self._map_issue_type(issue.type)

        # Tìm Jira sprint ID tương ứng từ sprint ID của DB nếu có
        jira_sprint_id = await self._get_jira_sprint_id(session=session, project_key=project_key, sprint_id=sprint_id)
        if not jira_sprint_id:
            raise Exception(f"Jira sprint ID not found for sprint ID {sprint_id}")

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

        if issue.estimate_point:
            create_dto.estimate_point = issue.estimate_point

        # Sử dụng admin auth để tạo issue
        jira_issue = await self.jira_issue_service.jira_issue_api_service.create_issue_with_admin_auth(
            session=session,
            issue_data=create_dto
        )

        # Mark the issue for system linking IMMEDIATELY after creation
        if jira_issue and jira_issue.key:
            await self._mark_issue_for_system_linking(jira_issue.key)

        return jira_issue

    async def _update_issue(self, session: AsyncSession, issue: WorkflowEditIssue, project_key: str, sprint_id: Optional[int]) -> JiraIssueModel:
        """Update an existing issue in Jira"""
        if not issue.jira_key:
            raise Exception("Cannot update issue without jira_key")

        # Mark the issue for system linking BEFORE updating it
        await self._mark_issue_for_system_linking(issue.jira_key)

        # Tìm Jira sprint ID tương ứng từ sprint ID của DB nếu có
        jira_sprint_id = await self._get_jira_sprint_id(session=session, project_key=project_key, sprint_id=sprint_id)
        if not jira_sprint_id:
            raise Exception(f"Jira sprint ID not found for sprint ID {sprint_id}")

        # Create update data
        update_dto = JiraIssueAPIUpdateRequestDTO(
            summary=issue.title,
            assignee_id=str(issue.assignee_id),
            sprint_id=jira_sprint_id
        )

        if issue.estimate_point:
            update_dto.estimate_point = issue.estimate_point

        # Sử dụng admin auth để update issue
        jira_issue = await self.jira_issue_service.jira_issue_api_service.update_issue_with_admin_auth(
            session=session,
            issue_id=issue.jira_key,
            update=update_dto
        )

        # Sau khi update, đảm bảo issue được đánh dấu là system linked trong DB
        try:
            # Kiểm tra xem issue đã được đánh dấu là system linked chưa
            existing_issue = await self.jira_issue_repository.get_by_jira_issue_id(
                session=session,
                jira_issue_id=jira_issue.jira_issue_id
            )

            # Nếu chưa được đánh dấu là system linked
            if existing_issue and not existing_issue.is_system_linked:
                # Cập nhật flag is_system_linked
                update_db_dto = JiraIssueDBUpdateDTO(
                    is_system_linked=True
                )

                await self.jira_issue_repository.update(
                    session=session,
                    issue_id=jira_issue.jira_issue_id,
                    issue_update=update_db_dto
                )
                log.debug(f"Marked updated issue {jira_issue.key} as system linked in database")
        except Exception as e:
            log.error(f"Error updating system_linked flag for issue {jira_issue.key}: {str(e)}")
            # Không raise exception ở đây để không ảnh hưởng đến luồng chính
        return jira_issue

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

    async def _get_jira_sprint_id(self, session: AsyncSession, project_key: str, sprint_id: Optional[int]) -> Optional[int]:
        """Lấy Jira sprint ID từ sprint ID của DB"""
        try:
            if sprint_id is None:
                # Get current sprint
                current_sprint = await self.jira_sprint_repository.get_current_sprint(session=session, project_key=project_key)
                return current_sprint.jira_sprint_id if current_sprint else None

            sprint = await self.jira_sprint_repository.get_sprint_by_id(session=session, sprint_id=sprint_id)
            return sprint.jira_sprint_id if sprint else None
        except Exception as e:
            raise Exception(f"Error getting Jira sprint ID for sprint ID {sprint_id}: {str(e)}") from e
