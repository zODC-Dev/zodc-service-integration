from datetime import datetime, timezone
from typing import Any, List, Optional

from src.configs.logger import log
from src.domain.constants.jira import JiraSprintState
from src.domain.models.jira.apis.responses.jira_project import JiraProjectAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_sprint import JiraSprintAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO
from src.domain.models.jira_project import JiraProjectModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel


class JiraProjectMapper:
    @staticmethod
    def to_domain(api_response: JiraProjectAPIGetResponseDTO) -> JiraProjectModel:
        return JiraProjectModel(
            project_id=api_response.id,
            key=api_response.key,
            name=api_response.name,
            jira_project_id=api_response.id,
            avatar_url=api_response.avatarUrls.get("48x48", "")
        )


class JiraUserMapper:
    @staticmethod
    def to_domain(api_response: JiraUserAPIGetResponseDTO) -> JiraUserModel:
        return JiraUserModel(
            jira_account_id=api_response.accountId,
            email=api_response.emailAddress,
            name=api_response.displayName,
            avatar_url=api_response.avatarUrls.get("48x48", "")
        )


class JiraSprintMapper:
    @staticmethod
    def to_domain(api_response: JiraSprintAPIGetResponseDTO) -> JiraSprintModel:
        try:
            now = datetime.now(timezone.utc)
            return JiraSprintModel(
                jira_sprint_id=api_response.id,
                name=api_response.name,
                state=api_response.state,
                start_date=api_response.startDate and api_response.startDate.replace(tzinfo=timezone.utc),
                end_date=api_response.endDate and api_response.endDate.replace(tzinfo=timezone.utc),
                complete_date=api_response.completeDate and api_response.completeDate.replace(tzinfo=timezone.utc),
                goal=api_response.goal,
                created_at=now
            )
        except Exception as e:
            log.error(f"Error mapping sprint response to domain: {str(e)}")
            return JiraSprintModel(
                jira_sprint_id=api_response.id,
                name=api_response.name,
                state=api_response.state,
                created_at=datetime.now(timezone.utc)
            )

    @classmethod
    def from_webhook_list(cls, sprint_data: Any) -> Optional[List[JiraSprintModel]]:
        """Map sprint data from webhook to domain models"""
        sprints = []

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
                    state=JiraSprintState.ACTIVE,
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

        return sprints if sprints else None

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
                        state=JiraSprintState.ACTIVE,
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
                    start_date=cls._parse_date(item.get('startDate')),
                    end_date=cls._parse_date(item.get('endDate')),
                    complete_date=cls._parse_date(item.get('completeDate')),
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
                    start_date=cls._parse_date(getattr(item, 'startDate', None)),
                    end_date=cls._parse_date(getattr(item, 'endDate', None)),
                    complete_date=cls._parse_date(getattr(item, 'completeDate', None)),
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
