from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.models.jira_sprint import JiraSprintCreateDTO, JiraSprintModel, JiraSprintUpdateDTO
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.infrastructure.entities.jira_sprint import JiraSprintEntity


class SQLAlchemyJiraSprintRepository(IJiraSprintRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _ensure_timezone(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime has timezone info"""
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _prepare_data(self, data: dict) -> dict:
        """Prepare data for database by ensuring all datetime fields have timezone info"""
        datetime_fields = ['start_date', 'end_date', 'complete_date', 'created_at', 'updated_at']
        for field in datetime_fields:
            if field in data and data[field]:
                data[field] = self._ensure_timezone(data[field])
        return data

    async def create_sprint(self, sprint_data: JiraSprintCreateDTO) -> JiraSprintModel:
        data = self._prepare_data(sprint_data.model_dump())
        sprint = JiraSprintEntity(**data)
        self.session.add(sprint)
        try:
            await self.session.commit()
            await self.session.refresh(sprint)
            return self._to_domain(sprint)
        except Exception as e:
            await self.session.rollback()
            log.error(f"Error creating sprint: {str(e)}")
            raise

    async def get_sprint_by_id(self, sprint_id: int) -> Optional[JiraSprintModel]:
        sprint = await self.session.get(JiraSprintEntity, sprint_id)
        return self._to_domain(sprint) if sprint else None

    async def get_sprints_by_project_id(self, project_id: int) -> List[JiraSprintModel]:
        result = await self.session.exec(select(JiraSprintEntity).where(JiraSprintEntity.project_id == project_id))
        sprints = result.all()
        return [self._to_domain(sprint) for sprint in sprints]

    async def update_sprint(self, sprint_id: int, sprint_data: JiraSprintUpdateDTO) -> Optional[JiraSprintModel]:
        try:
            sprint = await self.session.get(JiraSprintEntity, sprint_id)
            if not sprint:
                return None

            data = self._prepare_data(sprint_data.model_dump())
            for key, value in data.items():
                setattr(sprint, key, value)

            await self.session.commit()
            await self.session.refresh(sprint)
            return self._to_domain(sprint)
        except Exception as e:
            await self.session.rollback()
            log.error(f"Error updating sprint {sprint_id}: {str(e)}")
            raise

    async def get_by_jira_sprint_id(self, jira_sprint_id: str) -> Optional[JiraSprintModel]:
        result = await self.session.exec(select(JiraSprintEntity).where(JiraSprintEntity.jira_sprint_id == jira_sprint_id))
        sprint = result.first()
        return self._to_domain(sprint) if sprint else None

    async def get_project_sprints(self, project_key: str) -> List[JiraSprintModel]:
        """Get all sprints for a specific project"""
        log.info(f"Getting sprints for project {project_key}")
        result = await self.session.exec(
            select(JiraSprintEntity).where(
                JiraSprintEntity.project_key == project_key
            )
        )
        sprints = result.all()
        log.info(f"Found {len(sprints)} sprints for project {project_key}")
        return [self._to_domain(sprint) for sprint in sprints]

    def _to_domain(self, sprint: JiraSprintEntity) -> JiraSprintModel:
        return JiraSprintModel(
            jira_sprint_id=sprint.jira_sprint_id,
            name=sprint.name,
            state=sprint.state,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            complete_date=sprint.complete_date,
            created_at=sprint.created_at,
            updated_at=sprint.updated_at,
            id=sprint.id
        )
