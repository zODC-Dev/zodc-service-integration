from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.app.dtos.jira.jira_sync_dto import JiraBatchSyncRequestDTO, JiraIssueSyncRequestDTO, JiraIssueSyncResponseDTO
from src.configs.logger import log
from src.domain.constants.jira import JiraIssueType
from src.domain.constants.nats_events import NATSPublishTopic
from src.domain.models.jira_issue import JiraIssueCreateDTO, JiraIssueUpdateDTO
from src.domain.models.nats_event import JiraActionType
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.nats_service import INATSService


class JiraIssueApplicationService:
    def __init__(
        self,
        jira_issue_service: IJiraIssueDatabaseService,
        issue_repository: IJiraIssueRepository,
        project_repository: IJiraProjectRepository,
        nats_service: INATSService,
        sync_log_repository: ISyncLogRepository
    ):
        self.jira_issue_service = jira_issue_service
        self.jira_issue_repository = issue_repository
        self.project_repository = project_repository
        self.nats_service = nats_service
        self.sync_log_repository = sync_log_repository

    async def handle_sync_request(
        self,
        request: JiraBatchSyncRequestDTO
    ) -> List[JiraIssueSyncResponseDTO]:
        """Handle batch sync request"""
        results = []

        for issue_request in request.issues:
            result = await self._process_sync_issue(issue_request)
            results.append(result)

        return results

    async def _process_sync_issue(
        self,
        request: JiraIssueSyncRequestDTO
    ) -> JiraIssueSyncResponseDTO:
        """Process single issue sync"""
        try:
            if request.action_type == JiraActionType.CREATE:
                return await self._handle_create_issue(request)
            elif request.action_type == JiraActionType.UPDATE:
                return await self._handle_update_issue(request)

        except Exception as e:
            log.error(f"Error processing issue: {str(e)}")
            return JiraIssueSyncResponseDTO(
                success=False,
                action_type=request.action_type,
                issue_id=request.issue_id,
                error_message=str(e)
            )

    async def handle_update_request(self, data: Dict[str, Any]) -> None:
        issue_id = str(data.get("jira_issue_id", ""))
        user_id = int(data.get("user_id", 0))
        update_data = data.get("update_data", {})
        client_updated_at = data.get("updated_at", "")

        try:
            if not all([issue_id, user_id, update_data, client_updated_at]):
                raise ValueError("Missing required fields")

            validation_result = await self._validate_update_request(
                issue_id=issue_id,
                client_updated_at=client_updated_at
            )
            if not validation_result["is_valid"]:
                await self._publish_update_result(
                    issue_id=issue_id,
                    success=False,
                    error_message=validation_result["reason"]
                )
                return

            await self._process_update(
                user_id=user_id,
                issue_id=issue_id,
                update_data=update_data
            )

        except Exception as e:
            log.error(f"Error handling issue update request: {str(e)}")
            await self._publish_update_result(
                issue_id=issue_id,
                success=False,
                error_message=f"Internal error: {str(e)}"
            )

    # async def handle_webhook_update(self, webhook_data: JiraWebhookPayload) -> None:
    #     """Handle Jira webhook update"""
    #     try:
    #         issue_id = webhook_data.issue.id
    #         fields = webhook_data.issue.fields

    #         # Log the webhook sync
    #         await self.sync_log_repository.create_sync_log(
    #             SyncLogCreateDTO(
    #                 entity_type=EntityType.ISSUE,
    #                 entity_id=issue_id,
    #                 operation=OperationType.SYNC,
    #                 request_payload=webhook_data.to_json_serializable(),
    #                 response_status=200,
    #                 response_body={},
    #                 source=SourceType.WEBHOOK,
    #                 sender=None
    #             )
    #         )

    #         # Get existing issue
    #         issue = await self.jira_issue_repository.get_by_jira_issue_id(issue_id)
    #         if not issue:
    #             log.warning(f"Issue {issue_id} not found in database")
    #             return

    #         # Map webhook data to update dict
    #         update_data = JiraWebhookMapper.map_to_update_dto(webhook_data)

    #         # Check for conflicts
    #         if issue.updated_locally and update_data.get("updated_at") > issue.last_synced_at:
    #             await self._handle_conflict(
    #                 issue_id,
    #                 update_data["updated_at"],
    #                 issue.last_synced_at
    #             )

    #         # Update if there are changes
    #         if update_data:
    #             await self.jira_issue_repository.update(
    #                 issue_id,
    #                 JiraIssueUpdateDTO(**update_data)
    #             )

    #         # Update sync status
    #         await self._update_sync_status(
    #             issue_id=issue_id,
    #             updated_at=update_data["updated_at"]
    #         )

    #         log.info(f"Successfully processed issue update webhook for issue {issue_id}")

    #     except Exception as e:
    #         log.error(f"Error handling webhook update: {str(e)}")
    #         if 'issue_id' in locals():
    #             await self.sync_log_repository.create_sync_log(
    #                 SyncLogCreateDTO(
    #                     entity_type=EntityType.ISSUE,
    #                     entity_id=issue_id,
    #                     operation=OperationType.SYNC,
    #                     request_payload=webhook_data.to_json_serializable(),
    #                     response_status=500,
    #                     response_body={},
    #                     source=SourceType.WEBHOOK,
    #                     sender=None,
    #                     error_message=str(e)
    #                 )
    #             )
    #         raise

    # async def handle_webhook_create(self, webhook_data: JiraWebhookPayload) -> None:
    #     """Handle Jira issue creation webhook"""
    #     try:
    #         issue = webhook_data.issue

    #         # Log the webhook sync first
    #         await self.sync_log_repository.create_sync_log(
    #             SyncLogCreateDTO(
    #                 entity_type=EntityType.ISSUE,
    #                 entity_id=issue.id,
    #                 operation=OperationType.SYNC,
    #                 request_payload=webhook_data.to_json_serializable(),
    #                 response_status=200,
    #                 response_body={},
    #                 source=SourceType.WEBHOOK,
    #                 sender=None
    #             )
    #         )

    #         # Map webhook data to DTO
    #         issue_create = JiraWebhookMapper.map_to_create_dto(webhook_data)

    #         # Save to database
    #         await self.jira_issue_repository.create(issue_create)

    #         # Update sync status
    #         await self._update_sync_status(
    #             issue_id=issue.id,
    #             updated_at=issue_create.updated_at
    #         )

    #         log.info(f"Successfully processed issue creation webhook for issue {issue.id}")

    #     except Exception as e:
    #         log.error(f"Error handling issue creation webhook: {str(e)}")
    #         if hasattr(webhook_data, 'issue'):
    #             await self.sync_log_repository.create_sync_log(
    #                 SyncLogCreateDTO(
    #                     entity_type=EntityType.ISSUE,
    #                     entity_id=webhook_data.issue.id,
    #                     operation=OperationType.SYNC,
    #                     request_payload=webhook_data.to_json_serializable(),
    #                     response_status=500,
    #                     response_body={},
    #                     source=SourceType.WEBHOOK,
    #                     sender=None,
    #                     error_message=str(e)
    #                 )
    #             )
    #         raise

    async def _validate_update_request(
        self,
        issue_id: str,
        client_updated_at: str
    ) -> Dict[str, Any]:
        """Validate update request"""
        current_issue = await self.jira_issue_repository.get_by_jira_issue_id(issue_id)
        if not current_issue:
            return {
                "is_valid": False,
                "reason": "Issue not found in database"
            }

        if current_issue.updated_at > datetime.fromisoformat(client_updated_at):
            return {
                "is_valid": False,
                "reason": "Task has been updated on Jira after your last sync"
            }

        return {"is_valid": True}

    async def _process_update(
        self,
        user_id: int,
        issue_id: str,
        update_data: Dict[str, Any]
    ) -> None:
        """Process issue update"""
        update = JiraIssueUpdateDTO(**update_data)

        # Gọi Jira API để update
        await self.jira_issue_service.update_issue(user_id, issue_id, update)

        # Đánh dấu đã update locally
        issue = await self.jira_issue_repository.get_by_jira_issue_id(issue_id)
        if issue:
            issue.updated_locally = True
            await self.jira_issue_repository.update(issue_id, JiraIssueUpdateDTO._from_domain(issue))

    async def _handle_conflict(
        self,
        issue_id: str,
        jira_updated_at: datetime,
        local_updated_at: datetime
    ) -> None:
        """Handle update conflict"""
        await self.nats_service.publish(
            NATSPublishTopic.JIRA_ISSUE_SYNC_CONFLICT.value,
            {
                "issue_id": issue_id,
                "jira_updated_at": jira_updated_at.isoformat(),
                "local_updated_at": local_updated_at.isoformat()
            }
        )

    async def _update_sync_status(
        self,
        issue_id: str,
        updated_at: datetime
    ) -> None:
        """Update issue sync status"""
        issue = await self.jira_issue_repository.get_by_jira_issue_id(issue_id)
        if issue:
            issue.updated_at = updated_at
            issue.last_synced_at = datetime.now(timezone.utc)
            issue.updated_locally = False

            await self.jira_issue_repository.update(issue_id, JiraIssueUpdateDTO._from_domain(issue))

            # Thông báo đã sync thành công
            await self.nats_service.publish(
                NATSPublishTopic.JIRA_ISSUES_SYNC_RESULT.value,
                {
                    "jira_issue_id": issue_id,
                    "updated_at": updated_at.isoformat(),
                    "last_synced_at": issue.last_synced_at.isoformat()
                }
            )

    async def _publish_update_result(
        self,
        issue_id: str,
        success: bool,
        error_message: Optional[str] = None
    ) -> None:
        """Publish update result"""
        await self.nats_service.publish(
            NATSPublishTopic.JIRA_ISSUES_UPDATE_RESULT.value,
            {
                "success": success,
                "jira_issue_id": issue_id,
                "error_message": error_message
            }
        )

    async def handle_sync_conflict(self, message: Dict[str, Any]) -> None:
        """Handle sync conflicts"""
        # Move conflict handling logic here
        pass

    async def publish_update_error(self, issue_id: str, error: str) -> None:
        """Publish update error event"""
        await self.nats_service.publish(
            NATSPublishTopic.JIRA_ISSUE_UPDATE_ERROR.value,
            {
                "issue_id": issue_id,
                "error": error
            }
        )

    async def _handle_create_issue(self, request: JiraIssueSyncRequestDTO) -> JiraIssueSyncResponseDTO:
        try:
            issue = await self.jira_issue_service.create_issue(
                user_id=request.user_id,
                issue=JiraIssueCreateDTO(
                    project_key=request.project_key,
                    summary=request.summary or "",
                    description=request.description,
                    type=request.issue_type.value if request.issue_type else JiraIssueType.TASK.value,
                    assignee_id=request.assignee_id,
                    estimate_point=request.estimate_point,
                    status=request.status.value if request.status else None
                )
            )
            return JiraIssueSyncResponseDTO(
                success=True,
                action_type=JiraActionType.CREATE,
                issue_id=issue.jira_issue_id
            )
        except Exception as e:
            return JiraIssueSyncResponseDTO(
                success=False,
                action_type=JiraActionType.CREATE,
                error_message=str(e)
            )

    async def _handle_update_issue(self, request: JiraIssueSyncRequestDTO) -> JiraIssueSyncResponseDTO:
        try:
            if not request.issue_id:
                raise ValueError("issue_id is required for update")

            issue = await self.jira_issue_service.update_issue(
                user_id=request.user_id,
                issue_id=request.issue_id,
                update=JiraIssueUpdateDTO(
                    summary=request.summary,
                    description=request.description,
                    status=request.status,
                    assignee_id=request.assignee_id,
                    estimate_point=request.estimate_point,
                    actual_point=request.actual_point
                )
            )
            return JiraIssueSyncResponseDTO(
                success=True,
                action_type=JiraActionType.UPDATE,
                issue_id=issue.jira_issue_id
            )
        except Exception as e:
            return JiraIssueSyncResponseDTO(
                success=False,
                action_type=JiraActionType.UPDATE,
                issue_id=request.issue_id,
                error_message=str(e)
            )
