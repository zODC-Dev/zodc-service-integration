from typing import Any, Dict

from src.configs.logger import log
from src.domain.models.jira_project import JiraProjectCreateDTO, JiraProjectUpdateDTO
from src.domain.models.nats_event import ProjectLinkEvent, ProjectUnlinkEvent
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.services.nats_message_handler import INATSMessageHandler


class ProjectMessageHandler(INATSMessageHandler):
    def __init__(self, project_repository: IJiraProjectRepository):
        self.project_repository = project_repository

    async def handle(self, subject: str, message: Dict[str, Any]) -> None:
        try:
            if subject.endswith(".linked"):
                await self._handle_project_link(message)
            elif subject.endswith(".unlinked"):
                await self._handle_project_unlink(message)
        except Exception as e:
            log.error(f"Error handling project event: {str(e)}")

    async def _handle_project_link(self, message: Dict[str, Any]) -> None:
        event = ProjectLinkEvent.model_validate(message)
        project = JiraProjectCreateDTO(
            project_id=event.project_id,
            jira_project_id=event.jira_project_id,
            name=event.name,
            key=event.key,
            avatar_url=event.avatar_url,
        )
        await self.project_repository.create_project(project)
        log.info(f"Project {event.name} ({event.key}) linked successfully")

    async def _handle_project_unlink(self, message: Dict[str, Any]) -> None:
        event = ProjectUnlinkEvent.model_validate(message)
        project = await self.project_repository.get_by_jira_project_id(event.jira_project_id)
        if project and project.id:
            await self.project_repository.update_project(
                project.id,
                JiraProjectUpdateDTO(is_jira_linked=False)
            )
            log.info(f"Project {project.name} unlinked successfully")
        else:
            log.warning(f"Project with Jira ID {event.jira_project_id} not found for unlinking")
