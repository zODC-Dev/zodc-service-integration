from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.infrastructure.entities.jira_issue import JiraIssueEntity


class SQLAlchemyJiraIssueRepository(IJiraIssueRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_jira_issue_id(self, jira_issue_id: str) -> Optional[JiraIssueModel]:
        result = await self.session.exec(
            select(JiraIssueEntity).where(JiraIssueEntity.jira_issue_id == jira_issue_id)
        )
        entity = result.first()
        return self._to_domain(entity) if entity else None

    async def create(self, issue: JiraIssueModel) -> JiraIssueModel:
        entity = self._to_entity(issue)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return self._to_domain(entity)

    async def update(self, issue: JiraIssueModel) -> JiraIssueModel:
        entity = await self.get_by_jira_issue_id(issue.jira_issue_id)
        if not entity:
            raise ValueError(f"Issue with jira_issue_id {issue.jira_issue_id} not found")

        updated_entity = self._to_entity(issue)
        for key, value in updated_entity.model_dump(exclude_unset=True).items():
            setattr(entity, key, value)

        await self.session.commit()
        await self.session.refresh(entity)
        return self._to_domain(updated_entity)

    async def get_all(self) -> List[JiraIssueModel]:
        result = await self.session.exec(select(JiraIssueEntity))
        entities = result.all()
        return [self._to_domain(entity) for entity in entities]

    def _to_entity(self, model: JiraIssueModel) -> JiraIssueEntity:
        return JiraIssueEntity(
            jira_issue_id=model.jira_issue_id,
            key=model.key,
            summary=model.summary,
            description=model.description,
            status=model.status.value,
            type=model.type.value,
            assignee_id=model.assignee.id if model.assignee else None,
            priority_id=model.priority.id if model.priority else None,
            estimate_point=model.estimate_point,
            actual_point=model.actual_point,
            project_key=model.project_key,
            reporter_id=model.reporter_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_synced_at=model.last_synced_at,
            updated_locally=model.updated_locally
        )

    def _to_domain(self, entity: JiraIssueEntity) -> JiraIssueModel:
        return JiraIssueModel(
            key=entity.key,
            summary=entity.summary,
            description=entity.description,
            status=JiraIssueStatus(entity.status),
            type=JiraIssueType(entity.type),
            estimate_point=entity.estimate_point,
            actual_point=entity.actual_point,
            project_key=entity.project_key,
            reporter_id=entity.reporter_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            last_synced_at=entity.last_synced_at,
            jira_issue_id=entity.jira_issue_id,
            updated_locally=entity.updated_locally
        )
