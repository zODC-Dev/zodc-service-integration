from typing import List

from src.domain.models.jira.apis.mappers.jira_user import JiraUserMapper
from src.domain.models.jira.apis.responses.jira_issue_comment import JiraIssueCommentAPIGetResponseDTO
from src.domain.models.jira_issue_comment import JiraIssueCommentModel
from src.utils.jira_utils import convert_adf_to_text


class JiraIssueCommentMapper:
    @staticmethod
    def response_to_domain_list(response_data: List[JiraIssueCommentAPIGetResponseDTO]) -> List[JiraIssueCommentModel]:
        """Convert API response to domain models"""
        return [JiraIssueCommentModel(
            id=item.id,
            assignee=JiraUserMapper.to_domain(item.author),
            content=item.rendered_body if item.rendered_body else convert_adf_to_text(item.body),
            created_at=item.created
        ) for item in response_data]

    @staticmethod
    def response_to_domain(response_data: JiraIssueCommentAPIGetResponseDTO) -> JiraIssueCommentModel:
        """Convert API response to domain model"""
        return JiraIssueCommentModel(
            id=response_data.id,
            assignee=JiraUserMapper.to_domain(response_data.author),
            content=response_data.rendered_body if response_data.rendered_body else convert_adf_to_text(
                response_data.body),
            created_at=response_data.created
        )
