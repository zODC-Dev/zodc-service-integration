from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.controllers.jira_performance_summary_controller import JiraPerformanceSummaryController
from src.app.dependencies.controllers import get_jira_performance_summary_controller
from src.app.schemas.requests.jira_performance_summary import PerformanceSummaryRequest
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira_performance_summary import UserPerformanceSummaryResponse
from src.configs.database import get_db

router = APIRouter()


@router.get("/{user_id}/performance/summary", response_model=StandardResponse[UserPerformanceSummaryResponse])
async def get_user_performance_summary(
    user_id: int,
    quarter: int,
    year: int,
    controller: JiraPerformanceSummaryController = Depends(get_jira_performance_summary_controller),
    session: AsyncSession = Depends(get_db)
):
    """Lấy thông tin hiệu suất của người dùng trong một quý"""
    request = PerformanceSummaryRequest(user_id=user_id, quarter=quarter, year=year)
    result = await controller.get_user_performance_summary(session=session, request=request)
    return StandardResponse(data=result, message="Successfully fetched user performance summary")
