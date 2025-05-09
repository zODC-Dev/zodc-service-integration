from abc import ABC, abstractmethod

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.models.jira_performance_summary import UserPerformanceSummaryModel


class IJiraPerformanceSummaryService(ABC):
    """Interface cho service xử lý thông tin hiệu suất của người dùng"""

    @abstractmethod
    async def get_user_performance_summary(
        self,
        session: AsyncSession,
        user_id: int,
        quarter: int,
        year: int
    ) -> UserPerformanceSummaryModel:
        """Lấy thông tin hiệu suất của người dùng trong một quý"""
        pass
