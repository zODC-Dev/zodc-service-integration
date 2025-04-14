from typing import List, Optional

from src.configs.logger import log
from src.domain.exceptions.jira_exceptions import JiraIssueNotFoundError
from src.domain.models.apis.jira_issue_history import (
    JiraIssueChangelogAPIGetDTO,
    JiraIssueChangelogAuthorAPIGetDTO,
    JiraIssueChangelogDataAPIGetDTO,
    JiraIssueFieldId,
    JiraIssueHistoryAPIGetDTO,
)
from src.domain.models.database.jira_issue_history import JiraIssueHistoryChangeDBCreateDTO, JiraIssueHistoryDBCreateDTO
from src.domain.models.jira.apis.responses.jira_changelog import JiraChangelogDetailAPIGetResponseDTO
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService
from src.domain.services.jira_user_database_service import IJiraUserDatabaseService


class JiraIssueHistoryApplicationService:
    """Service đồng bộ lịch sử thay đổi issue từ Jira API"""

    def __init__(
        self,
        jira_issue_api_service: IJiraIssueAPIService,
        issue_history_db_service: IJiraIssueHistoryDatabaseService,
        jira_issue_db_service: IJiraIssueDatabaseService,
        jira_user_db_service: IJiraUserDatabaseService
    ):
        self.jira_issue_api_service = jira_issue_api_service
        self.issue_history_db_service = issue_history_db_service
        self.jira_user_db_service = jira_user_db_service
        self.jira_issue_db_service = jira_issue_db_service

    async def sync_issue_history(self, issue_id: str) -> bool:
        """Đồng bộ toàn bộ lịch sử của một issue"""
        try:
            # Lấy changelog từ Jira API
            changelog_response = await self.jira_issue_api_service.get_issue_changelog(issue_id)
            if not changelog_response.values:
                log.warning(f"No changelog found for issue {issue_id}")
                return False

            # Xử lý và lưu từng changelog
            for changelog in changelog_response.values:
                changes = await self.convert_api_changelog_to_db_changelog(issue_id, changelog)
                # Tạo event và lưu vào database
                if changes:
                    event = JiraIssueHistoryDBCreateDTO(
                        jira_issue_id=issue_id,
                        jira_change_id=changelog.id,
                        author_id=changelog.author.accountId,
                        created_at=changelog.created,  # Giữ nguyên datetime với timezone
                        changes=changes
                    )

                    # Lưu vào database
                    await self.issue_history_db_service.save_issue_history_event(event)

            log.info(f"Successfully synced {len(changelog_response.values)} changelog entries for issue {issue_id}")
            return True
        except Exception as e:
            log.error(f"Error syncing history for issue {issue_id}: {str(e)}")
            return False

    async def convert_api_changelog_to_db_changelog(self, issue_id: str, changelog: JiraChangelogDetailAPIGetResponseDTO) -> List[JiraIssueHistoryChangeDBCreateDTO]:
        """Convert changelog from Jira API to database changelog"""
        try:
            # Lấy các thay đổi từ changelog
            items = changelog.items
            if not items:
                return

            # Chuyển đổi sang các đối tượng IssueHistoryChangeModel
            changes: List[JiraIssueHistoryChangeDBCreateDTO] = []
            for item in items:
                field = item.field
                field_type = item.fieldtype
                from_value = item.from_value
                to_value = item.to_value
                from_string = item.fromString or ""
                to_string = item.toString or ""

                # Mapping field name nếu cần
                mapped_field = self._map_field_name(field)

                changes.append(JiraIssueHistoryChangeDBCreateDTO(
                    field=mapped_field,
                    field_type=field_type,
                    from_value=from_value,
                    to_value=to_value,
                    from_string=from_string,
                    to_string=to_string
                ))

            return changes

        except Exception as e:
            log.error(f"Error processing changelog {changelog.id} for issue {issue_id}: {str(e)}")
            return []

    def _map_field_name(self, jira_field_name: str) -> str:
        """Map tên field từ Jira về tên field trong hệ thống của chúng ta"""
        field_mapping = {
            "status": "status",
            "Sprint": "sprint",
            "assignee": "assignee",
            "Story point estimate": "story_points",
            "Actual point": "actual_point",
            "description": "description",
            "summary": "summary",
            "reporter": "reporter",
        }

        return field_mapping.get(jira_field_name, jira_field_name)

    async def get_issue_changelogs(self, issue_key: str) -> JiraIssueHistoryAPIGetDTO:
        """Lấy changelog của một Jira Issue

        Args:
            issue_key: Key của Jira Issue

        Returns:
            Lịch sử thay đổi của issue
        """
        try:
            issue = await self.jira_issue_db_service.get_issue_by_key(issue_key)
            if not issue:
                raise JiraIssueNotFoundError(f"Issue {issue_key} not found")

            # Lấy tất cả các changelog từ database
            history_events = await self.issue_history_db_service.get_issue_history(issue.jira_issue_id)

            # Chuyển đổi sang định dạng DTO
            changelogs = []
            for event in history_events:
                changelog = await self._convert_to_changelog_dto(event)
                if changelog:
                    changelogs.append(changelog)

            # Tạo response
            return JiraIssueHistoryAPIGetDTO(
                key=issue_key,
                created_at=issue.created_at.isoformat(),
                changelogs=changelogs
            )
        except Exception as e:
            log.error(f"Error getting changelogs for issue {issue_key}: {str(e)}")
            raise e

    async def _convert_to_changelog_dto(self, event) -> Optional[JiraIssueChangelogAPIGetDTO]:
        """Chuyển đổi dữ liệu từ database sang DTO"""
        try:
            # Chuyển đổi field name sang fieldId enum
            field_id = self._map_field_to_enum(event.field_name)
            if not field_id:
                return None

            # Lấy thông tin tác giả
            author = await self._get_author_info(event.author_id)
            if not author:
                return None

            # If field id is assignee, we need to get the avatar url from the user
            avatar_url = None
            if field_id == JiraIssueFieldId.ASSIGNEE:
                avatar_url = await self._get_assignee_avatar_url(event.new_value)

            # Tạo đối tượng DTO
            return JiraIssueChangelogAPIGetDTO(
                field_id=field_id,
                created_at=event.created_at.isoformat(),
                author=author,
                from_=self._create_changelog_data(event.old_string, event.old_value, avatar_url),
                to=self._create_changelog_data(event.new_string, event.new_value, avatar_url)
            )
        except Exception as e:
            log.error(f"Error converting changelog to DTO: {str(e)}")
            return None

    def _map_field_to_enum(self, field_name: str) -> Optional[JiraIssueFieldId]:
        """Map tên field từ database sang enum"""
        field_mapping = {
            "status": JiraIssueFieldId.STATUS,
            "sprint": JiraIssueFieldId.SPRINT,
            "assignee": JiraIssueFieldId.ASSIGNEE,
            "story_points": JiraIssueFieldId.STORY_POINTS,
            "summary": JiraIssueFieldId.SUMMARY,
            "description": JiraIssueFieldId.DESCRIPTION,
            "reporter": JiraIssueFieldId.REPORTER,
        }

        return field_mapping.get(field_name)

    def _create_changelog_data(self, display_value: str, value: str, avatar_url: Optional[str] = None) -> Optional[JiraIssueChangelogDataAPIGetDTO]:
        """Tạo đối tượng JiraIssueChangelogData"""
        if not display_value and not value:
            return None

        return JiraIssueChangelogDataAPIGetDTO(
            display_value=display_value,
            value=value,
            avatar_url=avatar_url
        )

    async def _get_author_info(self, author_id: str) -> Optional[JiraIssueChangelogAuthorAPIGetDTO]:
        """Lấy thông tin tác giả từ database"""
        try:
            user = await self.jira_user_db_service.get_user_by_jira_account_id(author_id)
            if not user:
                return None

            return JiraIssueChangelogAuthorAPIGetDTO.from_domain(user)

        except Exception as e:
            log.error(f"Error getting author info for {author_id}: {str(e)}")
            return None

    async def _get_assignee_avatar_url(self, assignee_id: str) -> Optional[str]:
        """Lấy avatar url của assignee"""
        user = await self.jira_user_db_service.get_user_by_jira_account_id(assignee_id)
        if not user:
            return None
        return user.avatar_url
