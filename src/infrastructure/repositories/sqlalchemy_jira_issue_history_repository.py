from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import and_, col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.models.database.jira_issue_history import JiraIssueHistoryDBCreateDTO
from src.domain.models.jira_issue_history import JiraIssueHistoryModel
from src.domain.repositories.jira_issue_history_repository import IJiraIssueHistoryRepository
from src.infrastructure.entities.jira_issue import JiraIssueEntity
from src.infrastructure.entities.jira_issue_history import JiraIssueHistoryEntity
from src.infrastructure.entities.jira_issue_sprint import JiraIssueSprintEntity


class SQLAlchemyJiraIssueHistoryRepository(IJiraIssueHistoryRepository):
    """Repository cho Jira issue history sử dụng SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_issues_field_history(
        self,
        jira_issue_ids: List[str],
        field_name: str
    ) -> Dict[str, List[JiraIssueHistoryModel]]:
        """Lấy lịch sử thay đổi của tất cả issue trong một sprint"""
        try:
            stmt = select(JiraIssueHistoryEntity).where(
                and_(
                    col(JiraIssueHistoryEntity.jira_issue_id).in_(jira_issue_ids),
                    col(JiraIssueHistoryEntity.field_name) == field_name
                )
            ).order_by(col(JiraIssueHistoryEntity.created_at))

            result = await self.session.exec(stmt)
            history_items = result.all()

            # Nhóm theo issue_id
            grouped_items: Dict[str, List[JiraIssueHistoryModel]] = {}
            for item in history_items:
                if item.jira_issue_id not in grouped_items:
                    grouped_items[item.jira_issue_id] = []
                grouped_items[item.jira_issue_id].append(self._entity_to_model(item))

            return grouped_items
        except Exception as e:
            log.error(f"Error getting multi issues field history: {str(e)}")
            return {}

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
            # Check if the issue id is already in the database
            stmt = select(JiraIssueEntity).where(
                col(JiraIssueEntity.jira_issue_id) == event.jira_issue_id
            )
            result = await self.session.exec(stmt)
            existing_issue = result.one_or_none()
            if not existing_issue:
                log.warning(f"Issue {event.jira_issue_id} does not exist in the database")
                return False

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

                # If the change already exists, skip
                if existing_item:
                    continue

                # Convert non-string values to string
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

            return True

        except Exception as e:
            log.error(f"Error saving history event: {str(e)}")
            return False

    async def bulk_create(
        self,
        events: List[JiraIssueHistoryDBCreateDTO]
    ) -> bool:
        """Bulk create issue history"""
        try:
            for event in events:
                await self.create(event)
            await self.session.commit()
            return True
        except Exception as e:
            log.error(f"Error bulk creating issue history: {str(e)}")
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

            log.info(f"Issue IDs: {issue_ids}")

            if not issue_ids:
                return []

            # Tạo query để lấy lịch sử của các issue
            conditions: List[Any] = [col(JiraIssueHistoryEntity.jira_issue_id).in_(issue_ids)]

            # Đảm bảo from_date và to_date có timezone nhất quán
            if from_date:
                # Chuyển đổi từ_date thành datetime không có timezone để so sánh với cột created_at
                from_date_naive = from_date.replace(tzinfo=None)
                conditions.append(col(JiraIssueHistoryEntity.created_at) >= from_date_naive)
                log.info(f"From date (naive): {from_date_naive}")

            if to_date:
                # Chuyển đổi to_date thành datetime không có timezone để so sánh với cột created_at
                to_date_naive = to_date.replace(tzinfo=None)
                conditions.append(col(JiraIssueHistoryEntity.created_at) <= to_date_naive)
                log.info(f"To date (naive): {to_date_naive}")

            stmt = select(JiraIssueHistoryEntity).where(
                and_(*conditions)
            ).order_by(col(JiraIssueHistoryEntity.created_at))

            history_result = await self.session.exec(stmt)
            history_items = history_result.all()

            # log.info(f"History items: {history_items}")

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
            created_at=entity.created_at.replace(tzinfo=timezone.utc),
            jira_change_id=entity.jira_change_id
        )
