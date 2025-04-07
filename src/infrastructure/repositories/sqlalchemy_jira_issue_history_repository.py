from datetime import datetime
from typing import Any, List, Optional

from sqlmodel import and_, col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.models.database.jira_issue_history import JiraIssueHistoryDBCreateDTO
from src.domain.models.jira_issue_history import JiraIssueHistoryModel
from src.domain.repositories.jira_issue_history_repository import IJiraIssueHistoryRepository
from src.infrastructure.entities.jira_issue_history import JiraIssueHistoryEntity
from src.infrastructure.entities.jira_issue_sprint import JiraIssueSprintEntity


class SQLAlchemyJiraIssueHistoryRepository(IJiraIssueHistoryRepository):
    """Repository cho Jira issue history sử dụng SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_issue_history(
        self,
        jira_issue_id: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy toàn bộ lịch sử thay đổi của một issue"""
        try:
            stmt = select(JiraIssueHistoryEntity).where(
                col(JiraIssueHistoryEntity.jira_issue_id) == jira_issue_id
            ).order_by(col(JiraIssueHistoryEntity.created_at))

            result = await self.session.exec(stmt)
            history_items = result.all()

            return [self._entity_to_model(item) for item in history_items]
        except Exception as e:
            log.error(f"Error getting issue history: {str(e)}")
            return []

    async def get_issue_field_history(
        self,
        jira_issue_id: str,
        field_name: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của một trường cụ thể"""
        try:
            stmt = select(JiraIssueHistoryEntity).where(
                and_(
                    col(JiraIssueHistoryEntity.jira_issue_id) == jira_issue_id,
                    col(JiraIssueHistoryEntity.field_name) == field_name
                )
            ).order_by(col(JiraIssueHistoryEntity.created_at))

            result = await self.session.exec(stmt)
            history_items = result.all()

            return [self._entity_to_model(item) for item in history_items]
        except Exception as e:
            log.error(f"Error getting issue field history: {str(e)}")
            return []

    async def create(
        self,
        event: JiraIssueHistoryDBCreateDTO
    ) -> bool:
        """Lưu một sự kiện thay đổi issue bao gồm nhiều thay đổi"""
        try:
            if not event.changes:
                log.warning(f"No changes to save for event {event.jira_change_id}")
                return True

            saved_changes = 0

            # Xử lý từng thay đổi trong sự kiện
            for change in event.changes:
                # Kiểm tra xem đã tồn tại thay đổi này trong cơ sở dữ liệu chưa
                # Lấy thời gian thay đổi nhưng loại bỏ timezone để phù hợp với DB
                created_at_naive = event.created_at.replace(tzinfo=None)

                # Kiểm tra các bản ghi tương tự đã tồn tại
                try:
                    stmt = (
                        select(JiraIssueHistoryEntity)
                        .where(
                            col(JiraIssueHistoryEntity.jira_issue_id) == event.jira_issue_id,
                            col(JiraIssueHistoryEntity.jira_change_id) == event.jira_change_id,
                            col(JiraIssueHistoryEntity.field_name) == change.field
                        )
                    )

                    result = await self.session.exec(stmt)
                    existing_item = result.one_or_none()
                except Exception as e:
                    log.error(f"Error checking for existing history item: {str(e)}")
                    # Nếu lỗi khi kiểm tra, giả định không có trùng lặp
                    existing_item = None

                # Nếu đã có thay đổi tương tự gần đây, bỏ qua
                if existing_item:
                    log.info(
                        f"Skipping duplicate change for issue {event.jira_issue_id}, field '{change.field}' "
                        f"from '{change.from_value}' to '{change.to_value}' "
                        f"(existing change ID: {existing_item.jira_change_id}, created at: {existing_item.created_at})"
                    )
                    continue

                # Chuyển đổi các giá trị không phải string sang string
                old_value = str(change.from_value) if change.from_value is not None else None
                new_value = str(change.to_value) if change.to_value is not None else None

                # Tạo history item mới với created_at đã loại bỏ timezone
                history_item = JiraIssueHistoryEntity(
                    jira_issue_id=event.jira_issue_id,
                    field_name=change.field,
                    field_type=change.field_type,
                    old_value=old_value,
                    new_value=new_value,
                    old_string=change.from_string,
                    new_string=change.to_string,
                    author_id=event.author_id,
                    created_at=created_at_naive,  # Đã loại bỏ timezone
                    jira_change_id=event.jira_change_id
                )
                self.session.add(history_item)
                saved_changes += 1

            log.info(f"Saved {saved_changes} out of {len(event.changes)} changes for issue {event.jira_issue_id}")
            return True

        except Exception as e:
            log.error(f"Error saving history event: {str(e)}")
            return False

    async def get_sprint_issue_histories(
        self,
        sprint_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của tất cả issue trong một sprint"""
        try:
            # Lấy danh sách issue_id trong sprint
            sprint_issues_stmt = select(JiraIssueSprintEntity.jira_issue_id).where(
                JiraIssueSprintEntity.jira_sprint_id == sprint_id
            )
            result = await self.session.exec(sprint_issues_stmt)
            issue_ids = result.all()

            if not issue_ids:
                return []

            # Tạo query để lấy lịch sử của các issue
            conditions: List[Any] = [col(JiraIssueHistoryEntity.jira_issue_id).in_(issue_ids)]

            if from_date:
                conditions.append(col(JiraIssueHistoryEntity.created_at) >= from_date)
            if to_date:
                conditions.append(col(JiraIssueHistoryEntity.created_at) <= to_date)

            stmt = select(JiraIssueHistoryEntity).where(
                and_(*conditions)
            ).order_by(col(JiraIssueHistoryEntity.created_at))

            result = await self.session.exec(stmt)
            history_items = result.all()

            return [self._entity_to_model(item) for item in history_items]
        except Exception as e:
            log.error(f"Error getting sprint issue histories: {str(e)}")
            return []

    def _entity_to_model(self, entity: JiraIssueHistoryEntity) -> JiraIssueHistoryModel:
        """Chuyển đổi entity thành model"""
        return JiraIssueHistoryModel(
            id=entity.id,
            jira_issue_id=entity.jira_issue_id,
            field_name=entity.field_name,
            field_type=entity.field_type,
            old_value=entity.old_value,
            new_value=entity.new_value,
            old_string=entity.old_string,
            new_string=entity.new_string,
            author_id=entity.author_id,
            created_at=entity.created_at,
            jira_change_id=entity.jira_change_id
        )
