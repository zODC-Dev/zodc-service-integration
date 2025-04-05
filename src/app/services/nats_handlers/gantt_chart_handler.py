from typing import Any, Dict

from src.app.services.gantt_chart_service import GanttChartApplicationService
from src.configs.logger import log
from src.domain.models.gantt_chart import ScheduleConfigModel
from src.domain.models.nats.replies.gantt_chart_calculation import (
    GanttChartCalculationReply,
)
from src.domain.models.nats.requests.gantt_chart_calculation import (
    GanttChartCalculationRequest,
)
from src.domain.services.nats_message_handler import INATSRequestHandler


class GanttChartRequestHandler(INATSRequestHandler):
    """Handler for Gantt chart calculation requests via NATS"""

    def __init__(self, gantt_chart_service: GanttChartApplicationService):
        self.gantt_chart_service = gantt_chart_service

    async def handle(self, subject: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Gantt chart calculation requests"""
        try:
            log.info(f"Received Gantt chart calculation request: {message}")

            # Validate request against our defined model
            request = GanttChartCalculationRequest.model_validate(message)

            # Create config if provided, otherwise use default
            config = request.config if request.config else ScheduleConfigModel()

            # Get Gantt chart with properly typed models
            gantt_chart = await self.gantt_chart_service.get_gantt_chart(
                project_key=request.project_key,
                sprint_id=request.sprint_id,
                config=config,
                workflow_id=request.workflow_id,
                issues=request.issues,
                connections=request.connections
            )

            # Prepare reply - using our model directly
            reply = GanttChartCalculationReply(
                transaction_id=request.transaction_id,
                project_key=request.project_key,
                sprint_id=request.sprint_id,
                sprint_start_date=gantt_chart.start_date,
                sprint_end_date=gantt_chart.end_date,
                tasks=gantt_chart.tasks,
                is_feasible=gantt_chart.is_feasible
            )

            return {
                "success": True,
                "data": reply.model_dump()
            }

        except Exception as e:
            log.error(f"Error handling Gantt chart calculation request: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {}
            }
