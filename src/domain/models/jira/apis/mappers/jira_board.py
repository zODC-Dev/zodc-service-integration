from typing import Any, Dict

from src.domain.models.jira.apis.responses.jira_board import JiraBoardAPIGetResponseDTO
from src.domain.models.jira_board import JiraBoardModel


class JiraBoardMapper:
    """Mapper for converting between Board DTOs and domain models"""

    @classmethod
    def to_domain(cls, dto: JiraBoardAPIGetResponseDTO) -> JiraBoardModel:
        """Convert API response DTO to domain model"""
        project_key = None
        project_id = None

        if dto.location:
            project_key = dto.location.project_key
            project_id = dto.location.project_id

        return JiraBoardModel(
            id=dto.id,
            name=dto.name,
            type=dto.type,
            project_id=project_id,
            project_key=project_key
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JiraBoardModel:
        """Convert dictionary to domain model directly"""
        project_key = None
        project_id = None

        location = data.get("location", {})
        if location:
            project_key = location.get("projectKey")
            project_id = location.get("projectId")

        return JiraBoardModel(
            id=data.get("id"),
            name=data.get("name"),
            type=data.get("type"),
            project_id=project_id,
            project_key=project_key
        )
