import json
from typing import Dict, Any

from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.logger import log
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.exceptions.jira_exceptions import JiraRequestError
from src.domain.models.nats.requests.jira_issue_reassign import JiraIssueReassignNATSRequestDTO
from src.domain.models.nats.replies.jira_issue_reassign import JiraIssueReassignNATSReplyDTO
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.infrastructure.services.nats_service import NATSService


class JiraIssueReassignRequestHandler:
    def __init__(
        self,
        jira_issue_service: JiraIssueApplicationService,
        jira_user_repository: IJiraUserRepository,
    ):
        self.jira_issue_service = jira_issue_service
        self.jira_user_repository = jira_user_repository

    async def handle(self, data: Dict[str, Any], nats_service: NATSService) -> Dict[str, Any]:
        """
        Handle Jira issue reassign request

        Args:
            data: Request data from NATS
            nats_service: NATS service instance

        Returns:
            dict: Response data to be sent back through NATS
        """
        try:
            log.info(f"Received Jira issue reassign request: {data}")

            # Parse request
            request = JiraIssueReassignNATSRequestDTO(**data)

            # Find Jira account IDs for the users
            old_user = await self.jira_user_repository.get_user_by_id(request.old_user_id)
            new_user = await self.jira_user_repository.get_user_by_id(request.new_user_id)

            if not new_user or not new_user.jira_account_id:
                error_msg = f"New user with ID {request.new_user_id} not found or has no Jira account ID"
                log.error(error_msg)
                return JiraIssueReassignNATSReplyDTO(
                    success=False,
                    jira_key=request.jira_key,
                    node_id=request.node_id,
                    old_user_id=request.old_user_id,
                    new_user_id=request.new_user_id,
                    error_message=error_msg
                ).model_dump()

            # Call Jira API to update assignee
            # Assuming we need the authenticated user to make API call
            # Using the old_user as the authenticated user if available, otherwise use new_user
            user_id = old_user.id if old_user else new_user.id

            # Update assignee in Jira
            success = await self.jira_issue_service.update_issue_assignee(
                user_id=user_id,
                issue_key=request.jira_key,
                assignee_account_id=new_user.jira_account_id
            )

            # Prepare reply
            reply = JiraIssueReassignNATSReplyDTO(
                success=success,
                jira_key=request.jira_key,
                node_id=request.node_id,
                old_user_id=request.old_user_id,
                new_user_id=request.new_user_id,
            )

            return reply.model_dump()

        except JiraRequestError as e:
            log.error(f"Jira API error during issue reassign: {str(e)}")
            return JiraIssueReassignNATSReplyDTO(
                success=False,
                jira_key=request.jira_key if 'request' in locals() else data.get('jira_key', ''),
                node_id=request.node_id if 'request' in locals() else data.get('node_id', 0),
                old_user_id=request.old_user_id if 'request' in locals() else data.get('old_user_id', 0),
                new_user_id=request.new_user_id if 'request' in locals() else data.get('new_user_id', 0),
                error_message=str(e)
            ).model_dump()

        except Exception as e:
            log.error(f"Error handling Jira issue reassign request: {str(e)}", exc_info=True)
            return JiraIssueReassignNATSReplyDTO(
                success=False,
                jira_key=request.jira_key if 'request' in locals() else data.get('jira_key', ''),
                node_id=request.node_id if 'request' in locals() else data.get('node_id', 0),
                old_user_id=request.old_user_id if 'request' in locals() else data.get('old_user_id', 0),
                new_user_id=request.new_user_id if 'request' in locals() else data.get('new_user_id', 0),
                error_message=f"Internal error: {str(e)}"
            ).model_dump()
