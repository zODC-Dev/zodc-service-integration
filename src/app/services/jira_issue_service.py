from datetime import datetime
from typing import List

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.schemas.responses.jira_issue import JiraIssueDescriptionDTO
from src.configs.logger import log
from src.domain.constants.jira import JiraActionType, JiraIssueStatus, JiraIssueType
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.exceptions.jira_exceptions import JiraIssueNotFoundError
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.apis.requests.jira_issue import JiraIssueAPICreateRequestDTO, JiraIssueAPIUpdateRequestDTO
from src.domain.models.nats.replies.jira_issue import JiraIssueSyncNATSReplyDTO
from src.domain.models.nats.requests.jira_issue import (
    JiraIssueBatchLinkNATSRequestDTO,
    JiraIssueBatchSyncNATSRequestDTO,
    JiraIssueSyncNATSRequestDTO,
)
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.nats_service import INATSService


class JiraIssueApplicationService:
    def __init__(
        self,
        jira_issue_db_service: IJiraIssueDatabaseService,
        jira_issue_api_service: IJiraIssueAPIService,
        issue_repository: IJiraIssueRepository,
        project_repository: IJiraProjectRepository,
        nats_service: INATSService,
        sync_log_repository: ISyncLogRepository
    ):
        self.jira_issue_db_service = jira_issue_db_service
        self.jira_issue_api_service = jira_issue_api_service
        self.jira_issue_repository = issue_repository
        self.project_repository = project_repository
        self.nats_service = nats_service
        self.sync_log_repository = sync_log_repository

    async def handle_sync_request(
        self,
        session: AsyncSession,
        request: JiraIssueBatchSyncNATSRequestDTO
    ) -> List[JiraIssueSyncNATSReplyDTO]:
        """Handle batch sync request"""
        results = []

        for issue_request in request.issues:
            result = await self._process_sync_issue(session, issue_request)
            results.append(result)

        return results

    async def _process_sync_issue(
        self,
        session: AsyncSession,
        request: JiraIssueSyncNATSRequestDTO
    ) -> JiraIssueSyncNATSReplyDTO:
        """Process single issue sync"""
        try:
            log.info(f"Processing issue sync request: {request.action_type}")
            if request.action_type == JiraActionType.CREATE:
                return await self._handle_create_issue(session, request)
            elif request.action_type == JiraActionType.UPDATE:
                return await self._handle_update_issue(session, request)

        except Exception as e:
            log.error(f"Error processing issue: {str(e)}")
            return JiraIssueSyncNATSReplyDTO(
                success=False,
                action_type=request.action_type,
                issue_id=request.issue_id,
                error_message=str(e)
            )

    async def _handle_create_issue(self, session: AsyncSession, request: JiraIssueSyncNATSRequestDTO) -> JiraIssueSyncNATSReplyDTO:
        try:
            # Validate required fields
            if not request.project_key:
                raise ValueError("project_key is required")
            if not request.summary:
                raise ValueError("summary is required")

            # Convert issue type
            issue_type = request.type
            if isinstance(issue_type, str):
                try:
                    issue_type = JiraIssueType(issue_type)
                except ValueError:
                    log.warning(f"Invalid issue type: {issue_type}, using TASK")
                    issue_type = JiraIssueType.TASK

            # Convert status
            status = request.status
            if isinstance(status, str):
                try:
                    status = JiraIssueStatus(status)
                except ValueError:
                    log.warning(f"Invalid status: {status}, using default")
                    status = None
            log.info(f"Creating issue with status: {status}")

            issue = await self.jira_issue_api_service.create_issue(
                session=session,
                user_id=request.user_id,
                issue_data=JiraIssueAPICreateRequestDTO(
                    jira_issue_id="",
                    description=request.description,
                    key="",
                    project_key=request.project_key,
                    summary=request.summary,
                    type=issue_type,
                    assignee_id=str(request.assignee_id) if request.assignee_id else None,
                    estimate_point=request.estimate_point,
                    status=status.value if status else None,
                    created_at=datetime.now(),
                    sprint_id=request.sprint_id,
                )
            )

            # Create sync log with the session
            await self.sync_log_repository.create_sync_log(
                session=session,
                sync_log=SyncLogDBCreateDTO(
                    entity_type=EntityType.ISSUE,
                    entity_id=str(issue.jira_issue_id),
                    operation=OperationType.CREATE,
                    request_payload=request.json(),
                    response_status=200,
                    response_body=issue.json(),
                    source=SourceType.ZODC,
                    sender="JiraIssueApplicationService",
                    error_message=None,
                )
            )
            return JiraIssueSyncNATSReplyDTO(
                success=True,
                action_type=JiraActionType.CREATE,
                issue_id=issue.jira_issue_id
            )
        except Exception as e:
            log.error(f"Error creating issue: {str(e)}")
            # Log error with session
            await self.sync_log_repository.create_sync_log(
                session=session,
                sync_log=SyncLogDBCreateDTO(
                    entity_type=EntityType.ISSUE,
                    entity_id=str(request.issue_id) if request.issue_id else "unknown",
                    operation=OperationType.CREATE,
                    request_payload=request.json(),
                    response_status=500,
                    response_body=None,
                    source=SourceType.ZODC,
                    sender="JiraIssueApplicationService",
                    error_message=str(e),
                )
            )
            return JiraIssueSyncNATSReplyDTO(
                success=False,
                action_type=JiraActionType.CREATE,
                error_message=str(e)
            )

    async def _handle_update_issue(self, session: AsyncSession, request: JiraIssueSyncNATSRequestDTO) -> JiraIssueSyncNATSReplyDTO:
        try:
            if not request.issue_id:
                raise ValueError("issue_id is required for update")

            issue = await self.jira_issue_api_service.update_issue(
                session=session,
                user_id=request.user_id,
                issue_id=request.issue_id,
                update=JiraIssueAPIUpdateRequestDTO(
                    summary=request.summary,
                    description=request.description,
                    status=request.status,
                    assignee_id=str(request.assignee_id) if request.assignee_id else None,
                    estimate_point=request.estimate_point,
                    actual_point=request.actual_point
                )
            )

            # Create sync log with the session
            await self.sync_log_repository.create_sync_log(
                session=session,
                sync_log=SyncLogDBCreateDTO(
                    entity_type=EntityType.ISSUE,
                    entity_id=str(issue.jira_issue_id),
                    operation=OperationType.UPDATE,
                    request_payload=request.json(),
                    response_status=200,
                    response_body=issue.json(),
                    source=SourceType.ZODC,
                    sender="JiraIssueApplicationService",
                    error_message=None,
                )
            )

            return JiraIssueSyncNATSReplyDTO(
                success=True,
                action_type=JiraActionType.UPDATE,
                issue_id=issue.jira_issue_id
            )
        except Exception as e:
            # Log error with session
            await self.sync_log_repository.create_sync_log(
                session=session,
                sync_log=SyncLogDBCreateDTO(
                    entity_type=EntityType.ISSUE,
                    entity_id=str(request.issue_id) if request.issue_id else "unknown",
                    operation=OperationType.UPDATE,
                    request_payload=request.json(),
                    response_status=500,
                    response_body=None,
                    source=SourceType.ZODC,
                    sender="JiraIssueApplicationService",
                    error_message=str(e),
                )
            )
            return JiraIssueSyncNATSReplyDTO(
                success=False,
                action_type=JiraActionType.UPDATE,
                issue_id=request.issue_id,
                error_message=str(e)
            )

    async def handle_link_request(
        self,
        session: AsyncSession,
        request: JiraIssueBatchLinkNATSRequestDTO
    ) -> List[JiraIssueSyncNATSReplyDTO]:
        """Handle multiple issue link request"""
        results = []

        for link in request.links:
            try:
                # Create link between two issues
                success = await self.jira_issue_api_service.create_issue_link(
                    session=session,
                    user_id=request.user_id,
                    source_issue_id=link.source_issue_id,
                    target_issue_id=link.target_issue_id,
                    relationship="Relates"  # Fixed relationship
                )

                if success:
                    # Log success with session
                    await self.sync_log_repository.create_sync_log(
                        session=session,
                        sync_log=SyncLogDBCreateDTO(
                            entity_type=EntityType.ISSUE,
                            entity_id=str(link.source_issue_id),
                            operation=OperationType.CREATE,
                            request_payload=request.model_dump(exclude={"links"}),
                            response_status=200,
                            response_body=None,
                            source=SourceType.ZODC,
                            sender="JiraIssueApplicationService",
                            error_message=None,
                        )
                    )

                    results.append(JiraIssueSyncNATSReplyDTO(
                        success=True,
                        action_type=JiraActionType.UPDATE,
                        issue_id=link.source_issue_id
                    ))
                else:
                    # Log failure with session
                    await self.sync_log_repository.create_sync_log(
                        session=session,
                        sync_log=SyncLogDBCreateDTO(
                            entity_type=EntityType.ISSUE,
                            entity_id=str(link.source_issue_id),
                            operation=OperationType.CREATE,
                            request_payload=request.model_dump(exclude={"links"}),
                            response_status=400,
                            response_body=None,
                            source=SourceType.ZODC,
                            sender="JiraIssueApplicationService",
                            error_message="Cannot create link",
                        )
                    )

                    results.append(JiraIssueSyncNATSReplyDTO(
                        success=False,
                        action_type=JiraActionType.UPDATE,
                        issue_id=link.source_issue_id,
                        error_message="Cannot create link"
                    ))
            except Exception as e:
                log.error(f"Error linking issue {link.source_issue_id} with {link.target_issue_id}: {str(e)}")

                # Log exception with session
                await self.sync_log_repository.create_sync_log(
                    session=session,
                    sync_log=SyncLogDBCreateDTO(
                        entity_type=EntityType.ISSUE,
                        entity_id=str(link.source_issue_id),
                        operation=OperationType.CREATE,
                        request_payload=request.model_dump(exclude={"links"}),
                        response_status=500,
                        response_body=None,
                        source=SourceType.ZODC,
                        sender="JiraIssueApplicationService",
                        error_message=str(e),
                    )
                )

                results.append(JiraIssueSyncNATSReplyDTO(
                    success=False,
                    action_type=JiraActionType.UPDATE,
                    issue_id=link.source_issue_id,
                    error_message=str(e)
                ))

        return results

    async def update_issue_assignee(self, session: AsyncSession, user_id: int, issue_key: str, assignee_account_id: str) -> bool:
        """Update the assignee of a Jira issue

        Args:
            session: AsyncSession
            user_id: ID of the user performing the action
            issue_key: The Jira issue key
            assignee_account_id: The Jira account ID of the new assignee

        Returns:
            bool: Whether the update was successful
        """
        try:
            # Call Jira API to update assignee
            result = await self.jira_issue_api_service.update_issue_assignee_with_admin_auth(
                issue_key=issue_key,
                assignee_account_id=assignee_account_id
            )

            # Create sync log entry
            await self.sync_log_repository.create_sync_log(
                session=session,
                sync_log=SyncLogDBCreateDTO(
                    entity_type=EntityType.ISSUE,
                    entity_id=issue_key,
                    operation=OperationType.UPDATE,
                    request_payload={
                        "assignee_account_id": assignee_account_id,
                    },
                    response_status=200 if result else 500,
                    response_body={
                        "success": result
                    },
                    source=SourceType.NATS,
                    sender=user_id,
                    error_message=None if result else "Failed to update assignee"
                )
            )

            return result

        except Exception as e:
            # Log error and create sync log entry
            log.error(f"Error updating assignee for issue {issue_key}: {str(e)}")

            # Record failed sync attempt
            await self.sync_log_repository.create_sync_log(
                session=session,
                sync_log=SyncLogDBCreateDTO(
                    entity_type=EntityType.ISSUE,
                    entity_id=issue_key,
                    operation=OperationType.UPDATE,
                    request_payload={
                        "assignee_account_id": assignee_account_id,
                    },
                    response_status=500,
                    response_body={},
                    source=SourceType.NATS,
                    sender=user_id,
                    error_message=str(e)
                )
            )

            raise

    async def remove_issue_link(self, session: AsyncSession, link_id: str) -> bool:
        """Remove a link between two issues

        Args:
            session: The database session
            link_id: ID of the link to remove

        Returns:
            bool: Whether the link was removed successfully
        """
        try:
            # Call Jira API to remove link
            result = await self.jira_issue_api_service.delete_issue_link_with_admin_auth(
                link_id=link_id
            )

            # Log the operation
            await self.sync_log_repository.create_sync_log(
                session=session,
                sync_log=SyncLogDBCreateDTO(
                    entity_type=EntityType.ISSUE,
                    entity_id=link_id,
                    operation=OperationType.DELETE,
                    request_payload={"link_id": link_id},
                    response_status=200 if result else 500,
                    response_body={"success": result},
                    source=SourceType.NATS,
                    sender="JiraIssueApplicationService",
                    error_message=None if result else "Failed to remove link"
                )
            )

            return result
        except Exception as e:
            log.error(f"Error removing link for issue {link_id}: {str(e)}")

            # Log the error
            await self.sync_log_repository.create_sync_log(
                session=session,
                sync_log=SyncLogDBCreateDTO(
                    entity_type=EntityType.ISSUE,
                    entity_id=link_id,
                    operation=OperationType.DELETE,
                    request_payload={"link_id": link_id},
                    response_status=500,
                    response_body=None,
                    source=SourceType.NATS,
                    sender="JiraIssueApplicationService",
                    error_message=str(e)
                )
            )

            return False

    async def get_issue_description_html(self, session: AsyncSession, issue_key: str) -> JiraIssueDescriptionDTO:
        """Lấy description dưới dạng HTML của một Jira issue

        Args:
            session: AsyncSession
            issue_key: Key của Jira issue

        Returns:
            DTO chứa key và HTML description
        """
        # Lấy issue từ database
        issue = await self.jira_issue_repository.get_by_jira_issue_key(session=session, jira_issue_key=issue_key)

        if not issue:
            raise JiraIssueNotFoundError(f"Issue with key {issue_key} not found")

        # Lấy raw ADF data từ Jira API nếu có thể

        description_html = f"{issue.description}" if issue.description else None

        return JiraIssueDescriptionDTO(
            key=issue_key,
            description=description_html
        )
