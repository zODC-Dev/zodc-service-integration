from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import and_, col, not_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.constants.jira import JiraSprintState
from src.domain.models.database.jira_sprint import JiraSprintDBCreateDTO, JiraSprintDBUpdateDTO
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.infrastructure.entities.jira_project import JiraProjectEntity
from src.infrastructure.entities.jira_sprint import JiraSprintEntity


class SQLAlchemyJiraSprintRepository(IJiraSprintRepository):
    def __init__(self):
        pass

    def _ensure_timezone(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime has timezone info"""
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _prepare_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for database by ensuring all datetime fields have timezone info"""
        datetime_fields = ['start_date', 'end_date', 'complete_date', 'created_at', 'updated_at']
        for field in datetime_fields:
            if field in data and data[field]:
                data[field] = self._ensure_timezone(data[field])
        return data

    async def create_sprint(self, session: AsyncSession, sprint_data: JiraSprintDBCreateDTO) -> JiraSprintModel:
        data = self._prepare_data(sprint_data.model_dump())

        sprint = JiraSprintEntity(**data)
        session.add(sprint)

        # check if project key is in the database
        project = await session.exec(select(JiraProjectEntity).where(col(JiraProjectEntity.key) == sprint.project_key))
        if not project:
            raise Exception(f"Project with key {sprint.project_key} not found")

        try:
            # Let the calling context handle the transaction
            await session.flush()
            await session.refresh(sprint)
            return self._to_domain(sprint)
        except Exception as e:
            log.error(f"Error creating sprint: {str(e)}")
            raise

    async def get_sprint_by_jira_sprint_id(self, session: AsyncSession, jira_sprint_id: int, include_deleted: bool = False) -> Optional[JiraSprintModel]:
        """Get sprint by Jira sprint ID"""
        query = select(JiraSprintEntity).where(col(JiraSprintEntity.jira_sprint_id) == jira_sprint_id)

        if not include_deleted:
            query = query.where(col(JiraSprintEntity.is_deleted) == False)  # noqa: E712

        result = await session.exec(query)
        sprint = result.first()
        return self._to_domain(sprint) if sprint else None

    async def get_sprint_by_id(self, session: AsyncSession, sprint_id: int, include_deleted: bool = False) -> Optional[JiraSprintModel]:
        """Get sprint by internal ID"""
        # Clear the session cache to force a fresh query to the database
        session.expire_all()

        query = select(JiraSprintEntity).where(JiraSprintEntity.id == sprint_id)

        if not include_deleted:
            query = query.where(col(JiraSprintEntity.is_deleted) == False)  # noqa: E712

        result = await session.exec(query)
        sprint = result.first()
        return self._to_domain(sprint) if sprint else None

    async def get_sprints_by_project_key(self, session: AsyncSession, project_key: str, include_deleted: bool = False) -> List[JiraSprintModel]:
        """Get all sprints for a project"""
        # Clear the session cache to force a fresh query to the database
        session.expire_all()

        query = select(JiraSprintEntity).where(col(JiraSprintEntity.project_key) == project_key)

        if not include_deleted:
            query = query.where(col(JiraSprintEntity.is_deleted) == False)  # noqa: E712

        result = await session.exec(query)
        sprints = result.all()
        return [self._to_domain(sprint) for sprint in sprints]

    async def update_sprint(self, session: AsyncSession, sprint_id: int, sprint_data: JiraSprintDBUpdateDTO) -> JiraSprintModel:
        try:
            sprint = await session.get(JiraSprintEntity, sprint_id)
            if not sprint:
                raise Exception(f"Sprint with ID {sprint_id} not found")

            data = self._prepare_data(sprint_data.model_dump())
            for key, value in data.items():
                setattr(sprint, key, value)

            session.add(sprint)
            # Let the calling context handle the transaction
            await session.flush()
            await session.refresh(sprint)
            return self._to_domain(sprint)
        except Exception as e:
            log.error(f"Error updating sprint {sprint_id}: {str(e)}")
            raise

    async def update_sprint_by_jira_sprint_id(self, session: AsyncSession, jira_sprint_id: int, sprint_data: JiraSprintDBUpdateDTO) -> JiraSprintModel:
        try:
            result = await session.exec(select(JiraSprintEntity).where(col(JiraSprintEntity.jira_sprint_id) == jira_sprint_id))
            sprint = result.first()
            if not sprint:
                raise Exception(f"Sprint with Jira ID {jira_sprint_id} not found")

            data = self._prepare_data(sprint_data.model_dump())
            for key, value in data.items():
                setattr(sprint, key, value)

            session.add(sprint)
            # Let the calling context handle the transaction
            await session.flush()
            await session.refresh(sprint)
            return self._to_domain(sprint)
        except Exception as e:
            log.error(f"Error updating sprint {jira_sprint_id}: {str(e)}")
            raise Exception(f"Error updating sprint {jira_sprint_id}: {str(e)}") from e

    async def get_project_sprints(self, session: AsyncSession, project_key: str, include_deleted: bool = False) -> List[JiraSprintModel]:
        """Get all sprints for a specific project"""
        log.info(f"Getting sprints for project {project_key}")

        # Clear the session cache to force a fresh query to the database
        # session.expire_all()

        query = select(JiraSprintEntity).where(
            and_(
                col(JiraSprintEntity.project_key) == project_key,
                not_(col(JiraSprintEntity.is_deleted)) if not include_deleted else True
            )
        )

        result = await session.exec(query)
        sprints = result.all()
        return [self._to_domain(sprint) for sprint in sprints]

    async def get_all_sprints(self, session: AsyncSession) -> List[JiraSprintModel]:
        """Get all sprints"""
        query = select(JiraSprintEntity).where(not_(col(JiraSprintEntity.is_deleted)))
        result = await session.exec(query)
        sprints = result.all()
        return [self._to_domain(sprint) for sprint in sprints]

    async def get_current_sprint(self, session: AsyncSession, project_key: str) -> Optional[JiraSprintModel]:
        """Get current active sprint for a project.

        If no active sprint exists:
        1. If there are future sprints, return the one with the earliest creation date
        2. Otherwise, return the most recently closed sprint
        """
        # First try to get an active sprint
        active_query = select(JiraSprintEntity).where(
            and_(
                col(JiraSprintEntity.project_key) == project_key,
                col(JiraSprintEntity.state) == JiraSprintState.ACTIVE.value,
                col(JiraSprintEntity.is_deleted) == False  # noqa: E712
            )
        )

        result = await session.exec(active_query)
        active_sprint = result.first()

        if active_sprint:
            return self._to_domain(active_sprint)

        # If no active sprint, try to get future sprints
        future_query = select(JiraSprintEntity).where(
            and_(
                col(JiraSprintEntity.project_key) == project_key,
                col(JiraSprintEntity.state) == JiraSprintState.FUTURE.value,
                col(JiraSprintEntity.is_deleted) == False  # noqa: E712
            )
        ).order_by(col(JiraSprintEntity.created_at))  # Get the earliest created future sprint

        result = await session.exec(future_query)
        future_sprint = result.first()

        if future_sprint:
            log.info(f"No active sprint found for project {project_key}. Using earliest future sprint.")
            return self._to_domain(future_sprint)

        # If no future sprint, get the most recently closed sprint
        closed_query = select(JiraSprintEntity).where(
            and_(
                col(JiraSprintEntity.project_key) == project_key,
                col(JiraSprintEntity.state) == JiraSprintState.CLOSED.value,
                col(JiraSprintEntity.is_deleted) == False  # noqa: E712
            )
        ).order_by(col(JiraSprintEntity.complete_date).desc())  # Get the most recently closed sprint

        result = await session.exec(closed_query)
        closed_sprint = result.first()

        if closed_sprint:
            log.info(f"No active or future sprint found for project {project_key}. Using most recently closed sprint.")
            return self._to_domain(closed_sprint)

        log.info(f"No sprint found for project {project_key}")
        return None

    def _to_domain(self, sprint: JiraSprintEntity) -> JiraSprintModel:
        return JiraSprintModel(
            jira_sprint_id=sprint.jira_sprint_id,
            name=sprint.name,
            state=sprint.state,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            complete_date=sprint.complete_date,
            project_key=sprint.project_key,
            created_at=sprint.created_at,
            updated_at=sprint.updated_at,
            goal=sprint.goal,
            board_id=sprint.board_id,
            id=sprint.id
        )
