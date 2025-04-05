from fastapi import Depends

from src.app.dependencies.base import get_issue_repository
from src.app.dependencies.common import get_nats_service
from src.app.dependencies.jira_sprint import get_jira_sprint_repository
from src.app.dependencies.workflow_mapping import get_workflow_mapping_repository
from src.app.services.gantt_chart_service import GanttChartApplicationService
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.workflow_mapping_repository import IWorkflowMappingRepository
from src.domain.services.gantt_chart_calculator_service import IGanttChartCalculatorService
from src.domain.services.nats_service import INATSService
from src.domain.services.workflow_service_client import IWorkflowServiceClient
from src.infrastructure.services.gantt_chart_calculator_service import GanttChartCalculatorService
from src.infrastructure.services.nats_workflow_service_client import NATSWorkflowServiceClient


async def get_gantt_chart_calculator_service() -> IGanttChartCalculatorService:
    """Get the Gantt chart calculator service"""
    return GanttChartCalculatorService()


async def get_workflow_service_client(
    nats_client: INATSService = Depends(get_nats_service)
) -> IWorkflowServiceClient:
    """Get the workflow service client"""
    return NATSWorkflowServiceClient(nats_client)


async def get_gantt_chart_service(
    issue_repository: IJiraIssueRepository = Depends(get_issue_repository),
    sprint_repository: IJiraSprintRepository = Depends(get_jira_sprint_repository),
    workflow_mapping_repository: IWorkflowMappingRepository = Depends(get_workflow_mapping_repository),
    gantt_calculator_service: IGanttChartCalculatorService = Depends(get_gantt_chart_calculator_service),
    workflow_service_client: IWorkflowServiceClient = Depends(get_workflow_service_client)
) -> GanttChartApplicationService:
    """Get the Gantt chart service"""
    return GanttChartApplicationService(issue_repository, sprint_repository, workflow_mapping_repository, gantt_calculator_service, workflow_service_client)
