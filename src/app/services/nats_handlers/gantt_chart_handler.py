from typing import Any, Dict

from src.app.services.gantt_chart_service import GanttChartApplicationService
from src.configs.logger import log
from src.domain.models.gantt_chart import ProjectConfigModel
from src.domain.models.nats.replies.gantt_chart_calculation import (
    GanttChartJiraIssueResult,
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
            log.info(f"[GANTT-NATS] Received Gantt chart calculation request for subject: {subject}")
            log.debug(f"[GANTT-NATS] Request message: {message}")

            # Validate request against our defined model
            request = GanttChartCalculationRequest.model_validate(message)
            log.info(f"[GANTT-NATS] Processing request for project: {request.project_key}, sprint: {request.sprint_id}")
            log.debug(
                f"[GANTT-NATS] Request contains {len(request.issues) if request.issues else 0} issues and {len(request.connections) if request.connections else 0} connections")

            # Create config if provided, otherwise use default
            config = request.config if request.config else ProjectConfigModel()
            log.debug(f"[GANTT-NATS] Using configuration: {config.model_dump()}")

            # Get Gantt chart with properly typed models
            log.info("[GANTT-NATS] Calling application service to calculate Gantt chart")
            gantt_chart = await self.gantt_chart_service.get_gantt_chart(
                project_key=request.project_key,
                sprint_id=request.sprint_id,
                config=config,
                workflow_id=request.workflow_id,
                issues=request.issues,
                connections=request.connections
            )
            log.info(f"[GANTT-NATS] Gantt chart calculation completed with {len(gantt_chart.tasks)} tasks")

            # Create client response directly from gantt chart tasks
            client_issues = [
                GanttChartJiraIssueResult(
                    node_id=task.node_id,
                    planned_start_time=task.plan_start_time,
                    planned_end_time=task.plan_end_time
                )
                for task in gantt_chart.tasks
            ]

            # Create the final response model
            # client_response = GanttChartCalculationResponse(issues=client_issues)
            log.info(f"[GANTT-NATS] Created client response with {len(client_issues)} issues")

            # Serialize với datetime xử lý đúng
            response_data = {}
            response_data["issues"] = [
                {
                    "node_id": issue.node_id,
                    "planned_start_time": issue.planned_start_time.isoformat(),
                    "planned_end_time": issue.planned_end_time.isoformat()
                }
                for issue in client_issues
            ]

            log.debug(f"[GANTT-NATS] Final response data structure: {response_data.keys()}")

            return {
                "success": True,
                "data": response_data
            }

        except Exception as e:
            log.error(f"[GANTT-NATS] Error handling Gantt chart calculation request: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": {}
            }
