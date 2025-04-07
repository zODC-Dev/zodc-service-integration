
from typing import List

from src.configs.logger import log
from src.domain.models.database.jira_issue_history import JiraIssueHistoryChangeDBCreateDTO, JiraIssueHistoryDBCreateDTO
from src.domain.models.jira.apis.responses.jira_changelog import JiraChangelogDetailAPIGetResponseDTO
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService


class JiraIssueHistorySyncService:
    """Service đồng bộ lịch sử thay đổi issue từ Jira API"""

    def __init__(
        self,
        jira_issue_api_service: IJiraIssueAPIService,
        issue_history_db_service: IJiraIssueHistoryDatabaseService
    ):
        self.jira_issue_api_service = jira_issue_api_service
        self.issue_history_db_service = issue_history_db_service

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
                await self._process_changelog(issue_id, changelog)

            log.info(f"Successfully synced {len(changelog_response.values)} changelog entries for issue {issue_id}")
            return True
        except Exception as e:
            log.error(f"Error syncing history for issue {issue_id}: {str(e)}")
            return False

    async def _process_changelog(self, issue_id: str, changelog: JiraChangelogDetailAPIGetResponseDTO) -> None:
        """Xử lý một changelog entry từ Jira API"""
        try:
            # Lấy thông tin cơ bản về changelog
            changelog_id = changelog.id
            author_id = changelog.author.accountId
            created_at = changelog.created  # Đây là datetime với timezone

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

            # Tạo event và lưu vào database
            if changes:
                event = JiraIssueHistoryDBCreateDTO(
                    jira_issue_id=issue_id,
                    jira_change_id=changelog_id,
                    author_id=author_id,
                    created_at=created_at,  # Giữ nguyên datetime với timezone
                    changes=changes
                )

                # Lưu vào database
                await self.issue_history_db_service.save_issue_history_event(event)
                log.info(f"Saved changelog {changelog_id} with {len(changes)} changes for issue {issue_id}")

        except Exception as e:
            log.error(f"Error processing changelog {changelog.id} for issue {issue_id}: {str(e)}")

    def _map_field_name(self, jira_field_name: str) -> str:
        """Map tên field từ Jira về tên field trong hệ thống của chúng ta"""
        field_mapping = {
            "status": "status",
            "Sprint": "sprint",
            "assignee": "assignee",
            "Story Points": "story_points",
            "Actual Point": "actual_point",
            # Thêm các mapping khác tùy theo nhu cầu
        }

        return field_mapping.get(jira_field_name, jira_field_name)
