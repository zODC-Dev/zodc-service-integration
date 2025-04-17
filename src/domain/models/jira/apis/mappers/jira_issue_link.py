from typing import List

from src.domain.models.jira.apis.responses.jira_issue_link import JiraIssueLinkDTO, JiraIssueLinksResponseDTO
from src.domain.models.jira_issue_link import IssueLinkType, JiraIssueLinkDirection, JiraIssueLinkModel, LinkedIssue


class JiraIssueLinkMapper:
    """Mapper class for converting Jira issue link DTO to domain model"""

    @staticmethod
    def to_domain(dto: JiraIssueLinkDTO) -> JiraIssueLinkModel:
        """Convert a single issue link DTO to domain model"""
        # Determine direction and get linked issue
        if dto.inward_issue:
            direction = JiraIssueLinkDirection.INWARD
            linked_issue_dto = dto.inward_issue
        else:
            direction = JiraIssueLinkDirection.OUTWARD
            linked_issue_dto = dto.outward_issue

        if not linked_issue_dto:
            raise ValueError("Issue link must have either inward or outward issue")

        # Map link type
        link_type = IssueLinkType(
            id=dto.type.id,
            name=dto.type.name,
            inward_description=dto.type.inward,
            outward_description=dto.type.outward
        )

        # Map linked issue
        linked_issue = LinkedIssue(
            id=linked_issue_dto.id,
            key=linked_issue_dto.key,
            summary=getattr(linked_issue_dto.fields, 'summary', None),
            status_name=getattr(linked_issue_dto.fields.status, 'name', None)
            if linked_issue_dto.fields.status else None,
            status_id=getattr(linked_issue_dto.fields.status, 'id', None)
            if linked_issue_dto.fields.status else None,
            priority_name=getattr(linked_issue_dto.fields.priority, 'name', None)
            if linked_issue_dto.fields.priority else None,
            issue_type_name=getattr(linked_issue_dto.fields.issuetype, 'name', None)
            if linked_issue_dto.fields.issuetype else None
        )

        # Create and return domain model
        return JiraIssueLinkModel(
            id=dto.id,
            link_type=link_type,
            direction=direction,
            linked_issue=linked_issue
        )

    @staticmethod
    def response_to_domain_list(response_dto: JiraIssueLinksResponseDTO) -> List[JiraIssueLinkModel]:
        """Convert response DTO to a list of domain models"""
        return [JiraIssueLinkMapper.to_domain(link) for link in response_dto.issue_links]
