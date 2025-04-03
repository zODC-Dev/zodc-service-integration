from datetime import datetime
from typing import List

from src.configs.logger import log
from src.domain.constants.jira import JiraActionType, JiraIssueStatus, JiraIssueType
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
        request: JiraIssueBatchSyncNATSRequestDTO
    ) -> List[JiraIssueSyncNATSReplyDTO]:
        """Handle batch sync request"""
        results = []

        for issue_request in request.issues:
            result = await self._process_sync_issue(issue_request)
            results.append(result)

        return results

    async def _process_sync_issue(
        self,
        request: JiraIssueSyncNATSRequestDTO
    ) -> JiraIssueSyncNATSReplyDTO:
        """Process single issue sync"""
        try:
            log.info(f"Processing issue sync request: {request.action_type}")
            if request.action_type == JiraActionType.CREATE:
                return await self._handle_create_issue(request)
            elif request.action_type == JiraActionType.UPDATE:
                return await self._handle_update_issue(request)

        except Exception as e:
            log.error(f"Error processing issue: {str(e)}")
            return JiraIssueSyncNATSReplyDTO(
                success=False,
                action_type=request.action_type,
                issue_id=request.issue_id,
                error_message=str(e)
            )

    async def _handle_create_issue(self, request: JiraIssueSyncNATSRequestDTO) -> JiraIssueSyncNATSReplyDTO:
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
            return JiraIssueSyncNATSReplyDTO(
                success=True,
                action_type=JiraActionType.CREATE,
                issue_id=issue.jira_issue_id
            )
        except Exception as e:
            log.error(f"Error creating issue: {str(e)}")
            return JiraIssueSyncNATSReplyDTO(
                success=False,
                action_type=JiraActionType.CREATE,
                error_message=str(e)
            )

    async def _handle_update_issue(self, request: JiraIssueSyncNATSRequestDTO) -> JiraIssueSyncNATSReplyDTO:
        try:
            if not request.issue_id:
                raise ValueError("issue_id is required for update")

            issue = await self.jira_issue_api_service.update_issue(
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
            return JiraIssueSyncNATSReplyDTO(
                success=True,
                action_type=JiraActionType.UPDATE,
                issue_id=issue.jira_issue_id
            )
        except Exception as e:
            return JiraIssueSyncNATSReplyDTO(
                success=False,
                action_type=JiraActionType.UPDATE,
                issue_id=request.issue_id,
                error_message=str(e)
            )

    async def handle_link_request(
        self,
        request: JiraIssueBatchLinkNATSRequestDTO
    ) -> List[JiraIssueSyncNATSReplyDTO]:
        """Handle multiple issue link request"""
        results = []

        for link in request.links:
            try:
                # Create link between two issues
                success = await self.jira_issue_api_service.create_issue_link(
                    user_id=request.user_id,
                    source_issue_id=link.source_issue_id,
                    target_issue_id=link.target_issue_id,
                    relationship="Relates"  # Fixed relationship
                )

                if success:
                    results.append(JiraIssueSyncNATSReplyDTO(
                        success=True,
                        action_type=JiraActionType.UPDATE,
                        issue_id=link.source_issue_id
                    ))
                else:
                    results.append(JiraIssueSyncNATSReplyDTO(
                        success=False,
                        action_type=JiraActionType.UPDATE,
                        issue_id=link.source_issue_id,
                        error_message="Cannot create link"
                    ))
            except Exception as e:
                log.error(f"Error linking issue {link.source_issue_id} with {link.target_issue_id}: {str(e)}")
                results.append(JiraIssueSyncNATSReplyDTO(
                    success=False,
                    action_type=JiraActionType.UPDATE,
                    issue_id=link.source_issue_id,
                    error_message=str(e)
                ))

        return results
