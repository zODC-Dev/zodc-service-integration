from typing import Any, Dict

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.logger import log
from src.domain.exceptions.jira_exceptions import JiraRequestError
from src.domain.models.nats.replies.jira_issue_reassign import JiraIssueReassignNATSReplyDTO
from src.domain.models.nats.requests.jira_issue_reassign import JiraIssueReassignNATSRequestDTO
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.nats_message_handler import INATSRequestHandler


class JiraIssueReassignRequestHandler(INATSRequestHandler):
    def __init__(
        self,
        jira_issue_service: JiraIssueApplicationService,
        jira_user_repository: IJiraUserRepository,
        jira_issue_repository: IJiraIssueRepository
    ):
        self.jira_issue_service = jira_issue_service
        self.jira_user_repository = jira_user_repository
        self.jira_issue_repository = jira_issue_repository

    async def handle(self, subject: str, message: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
        """Handle Jira issue reassign request

        Args:
            subject: Subject of the NATS message
            message: Request data from NATS
            session: AsyncSession
        Returns:
            dict: Response data to be sent back through NATS
        """
        try:
            log.info(f"Received Jira issue reassign request: {message}")

            # Parse request
            request = JiraIssueReassignNATSRequestDTO(**message)

            # Find Jira account IDs for the users
            old_user = await self.jira_user_repository.get_user_by_id(session=session, user_id=request.old_user_id)
            new_user = await self.jira_user_repository.get_user_by_id(session=session, user_id=request.new_user_id)

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
            user_id = request.old_user_id or request.new_user_id

            assert user_id is not None, "user_id is not None"

            # # Check last synced at
            # if request.last_synced_at:
            #     issue = await self.jira_issue_repository.get_by_jira_issue_key(session=session, jira_issue_key=request.jira_key)
            #     if issue and issue.last_synced_at and issue.last_synced_at > request.last_synced_at:
            #         log.info(f"Issue {request.jira_key} was synced after {request.last_synced_at}, skipping")
            #         return JiraIssueReassignNATSReplyDTO(
            #             success=False,
            #             jira_key=request.jira_key,
            #             node_id=request.node_id,
            #             old_user_id=request.old_user_id,
            #             new_user_id=request.new_user_id,
            #             error_message=f"Issue {request.jira_key} was synced after {request.last_synced_at}, skipping"
            #         ).model_dump()

            # Update assignee in Jira
            success = await self.jira_issue_service.update_issue_assignee(
                session=session,
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
                jira_key=request.jira_key if 'request' in locals() else message.get('jira_key', ''),
                node_id=request.node_id if 'request' in locals() else message.get('node_id', 0),
                old_user_id=request.old_user_id if 'request' in locals() else message.get('old_user_id', 0),
                new_user_id=request.new_user_id if 'request' in locals() else message.get('new_user_id', 0),
                error_message=str(e)
            ).model_dump()

        except Exception as e:
            log.error(f"Error handling Jira issue reassign request: {str(e)}", exc_info=True)
            return JiraIssueReassignNATSReplyDTO(
                success=False,
                jira_key=request.jira_key if 'request' in locals() else message.get('jira_key', ''),
                node_id=request.node_id if 'request' in locals() else message.get('node_id', 0),
                old_user_id=request.old_user_id if 'request' in locals() else message.get('old_user_id', 0),
                new_user_id=request.new_user_id if 'request' in locals() else message.get('new_user_id', 0),
                error_message=f"Internal error: {str(e)}"
            ).model_dump()
