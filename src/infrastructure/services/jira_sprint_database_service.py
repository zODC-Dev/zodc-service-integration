from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.constants.jira import JiraSprintState
from src.domain.models.database.jira_sprint import JiraSprintDBCreateDTO, JiraSprintDBUpdateDTO
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class JiraSprintDatabaseService(IJiraSprintDatabaseService):
    def __init__(self, sprint_repository: IJiraSprintRepository):
        self.sprint_repository = sprint_repository

    async def create_sprint(self, session: AsyncSession, sprint_data: JiraSprintDBCreateDTO) -> JiraSprintModel:
        return await self.sprint_repository.create_sprint(session, sprint_data)

    async def update_sprint(self, session: AsyncSession, sprint_id: int, sprint_data: JiraSprintDBUpdateDTO) -> JiraSprintModel:
        return await self.sprint_repository.update_sprint(session, sprint_id, sprint_data)

    async def update_sprint_by_jira_sprint_id(self, session: AsyncSession, jira_sprint_id: int, sprint_data: JiraSprintDBUpdateDTO) -> JiraSprintModel:
        return await self.sprint_repository.update_sprint_by_jira_sprint_id(session, jira_sprint_id, sprint_data)

    async def get_sprint_by_id(self, session: AsyncSession, sprint_id: int, include_deleted: bool = False) -> Optional[JiraSprintModel]:
        return await self.sprint_repository.get_sprint_by_id(session, sprint_id, include_deleted)

    async def get_sprint_by_jira_sprint_id(self, session: AsyncSession, jira_sprint_id: int, include_deleted: bool = False) -> Optional[JiraSprintModel]:
        return await self.sprint_repository.get_sprint_by_jira_sprint_id(session, jira_sprint_id, include_deleted)

    async def get_project_sprints(self, session: AsyncSession, project_key: str, include_deleted: bool = False) -> List[JiraSprintModel]:
        """Get all sprints for a project and determine current sprint"""
        sprints = await self.sprint_repository.get_project_sprints(session, project_key, include_deleted)
        if not sprints:
            return []

        # Phân loại sprints theo state
        active_sprints = [s for s in sprints if s.state == JiraSprintState.ACTIVE.value]
        future_sprints = [s for s in sprints if s.state == JiraSprintState.FUTURE.value]
        closed_sprints = [s for s in sprints if s.state == JiraSprintState.CLOSED.value]

        current_sprint_id = None

        # Case 1: Có sprint active
        if active_sprints:
            current_sprint_id = active_sprints[0].id
        # Case 2: Không có active nhưng có future
        elif future_sprints:
            # Sắp xếp future sprints theo created_at giảm dần
            future_sprints.sort(key=lambda x: x.created_at, reverse=True)
            current_sprint_id = future_sprints[0].id
        # Case 3: Không có active và future, lấy closed gần nhất
        elif closed_sprints:
            # Sắp xếp closed sprints theo complete_date giảm dần
            latest_closed = max(
                (s for s in closed_sprints if s.complete_date is not None),
                key=lambda x: x.complete_date,
                default=None
            )
            if latest_closed:
                current_sprint_id = latest_closed.id

        # Đánh dấu is_current cho các sprints
        for sprint in sprints:
            sprint.is_current = sprint.id == current_sprint_id

        return sprints

    async def get_current_sprint(self, session: AsyncSession, project_key: str) -> Optional[JiraSprintModel]:
        return await self.sprint_repository.get_current_sprint(session, project_key)

    async def get_all_sprints(self, session: AsyncSession) -> List[JiraSprintModel]:
        return await self.sprint_repository.get_all_sprints(session)
