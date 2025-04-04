from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.configs.logger import log
from src.domain.constants.jira import JiraSprintState
from src.domain.models.jira.apis.responses.jira_sprint import JiraSprintAPIGetResponseDTO
from src.domain.models.jira_sprint import JiraSprintModel


class JiraSprintMapper:
    """Mapper for converting between Sprint DTOs and domain models"""

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from Jira"""
        if dt_str is None:
            return None

        if dt_str.endswith('Z'):
            dt_str = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(dt_str)

    @classmethod
    def to_domain(cls, dto: JiraSprintAPIGetResponseDTO) -> JiraSprintModel:
        """Convert API response DTO to domain model"""
        try:
            now = datetime.now(timezone.utc)
            return JiraSprintModel(
                jira_sprint_id=dto.id,
                name=dto.name,
                state=dto.state,
                start_date=cls._parse_datetime(dto.start_date),
                end_date=cls._parse_datetime(dto.end_date),
                complete_date=cls._parse_datetime(dto.complete_date),
                created_at=now,
                board_id=dto.origin_board_id,
                goal=dto.goal
            )
        except Exception as e:
            log.error(f"Error converting sprint data to domain model: {str(e)}")
            raise

    @classmethod
    def from_domain(cls, model: JiraSprintModel) -> Dict[str, Any]:
        """Convert domain model to API request format"""
        return {
            "id": int(model.id),
            "name": model.name,
            "state": model.state,
            "startDate": model.start_date.isoformat() + 'Z' if model.start_date else None,
            "endDate": model.end_date.isoformat() + 'Z' if model.end_date else None,
            "completeDate": model.complete_date.isoformat() + 'Z' if model.complete_date else None,
            "goal": model.goal
        }

    @classmethod
    def from_webhook_list(cls, sprint_data: Any) -> Optional[List[JiraSprintModel]]:
        """Map sprint data from webhook to domain models"""
        sprints: List[JiraSprintModel] = []

        # Handle case when input is None
        if sprint_data is None:
            return None

        # Handle case when input is a string (sprint ID)
        if isinstance(sprint_data, str):
            try:
                sprint_id = int(sprint_data.strip())
                log.info(f"Converting sprint string ID {sprint_data} to sprint model")
                return [JiraSprintModel(
                    jira_sprint_id=sprint_id,
                    name=f"Sprint {sprint_id}",
                    state=JiraSprintState.ACTIVE.value,
                    created_at=datetime.now(timezone.utc)
                )]
            except (ValueError, TypeError):
                log.warning(f"Could not parse sprint ID from string: {sprint_data}")
                return None

        # Handle list of sprint data
        if isinstance(sprint_data, list):
            for item in sprint_data:
                sprint = cls._parse_sprint_item(item)
                if sprint:
                    sprints.append(sprint)

        # Handle single sprint object
        elif isinstance(sprint_data, dict):
            sprint = cls._parse_sprint_item(sprint_data)
            if sprint:
                sprints.append(sprint)

        return sprints

    @classmethod
    def _parse_sprint_item(cls, item: Any) -> Optional[JiraSprintModel]:
        """Parse a single sprint item from various formats"""
        try:
            # Handle string (ID only)
            if isinstance(item, str):
                try:
                    sprint_id = int(item.strip())
                    return JiraSprintModel(
                        jira_sprint_id=sprint_id,
                        name=f"Sprint {sprint_id}",
                        state=JiraSprintState.ACTIVE.value,
                        created_at=datetime.now(timezone.utc)
                    )
                except ValueError:
                    return None

            # Handle dictionary
            elif isinstance(item, dict):
                sprint_id = item.get('id')
                if not sprint_id:
                    return None

                return JiraSprintModel(
                    jira_sprint_id=sprint_id,
                    name=item.get('name', f"Sprint {sprint_id}"),
                    state=JiraSprintState.from_str(item.get('state', 'active')),
                    start_date=cls._parse_datetime(item.get('startDate')),
                    end_date=cls._parse_datetime(item.get('endDate')),
                    complete_date=cls._parse_datetime(item.get('completeDate')),
                    goal=item.get('goal'),
                    created_at=datetime.now(timezone.utc)
                )

            # Handle object with attributes
            elif hasattr(item, 'id'):
                sprint_id = item.id
                if not sprint_id:
                    return None

                return JiraSprintModel(
                    jira_sprint_id=sprint_id,
                    name=getattr(item, 'name', f"Sprint {sprint_id}"),
                    state=JiraSprintState.from_str(getattr(item, 'state', 'active')),
                    start_date=cls._parse_datetime(getattr(item, 'start_date', None)),
                    end_date=cls._parse_datetime(getattr(item, 'end_date', None)),
                    complete_date=cls._parse_datetime(getattr(item, 'complete_date', None)),
                    goal=getattr(item, 'goal', None),
                    created_at=datetime.now(timezone.utc)
                )

            return None
        except Exception as e:
            log.error(f"Error parsing sprint item: {str(e)}")
            return None

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string from Jira"""
        if not date_str:
            return None

        try:
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            return datetime.fromisoformat(date_str)
        except Exception as e:
            log.warning(f"Error parsing date '{date_str}': {str(e)}")
            return None
