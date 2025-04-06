from typing import List

from src.configs.logger import log
from src.domain.models.gantt_chart import GanttChartConnectionModel, GanttChartJiraIssueModel
from src.domain.services.nats_service import INATSService
from src.domain.services.workflow_service_client import IWorkflowServiceClient


class NATSWorkflowServiceClient(IWorkflowServiceClient):
    """NATS client for workflow service"""

    def __init__(self, nats_client: INATSService):
        self.nats_client = nats_client

    async def get_workflow_connections(self, workflow_id: str) -> List[GanttChartConnectionModel]:
        """Get connections for a workflow from workflow service"""
        try:
            # Prepare request
            request = {
                "workflow_id": workflow_id
            }

            # Send request to NATS
            response = await self.nats_client.request(
                "workflow.get_connections",
                request
            )

            if not response.get("success", False):
                log.error(f"Failed to get workflow connections: {response.get('error')}")
                return []

            # Parse connections from response
            connections_data = response.get("data", {}).get("connections", [])
            connections = []

            for conn_data in connections_data:
                try:
                    connection = GanttChartConnectionModel(
                        from_issue_key=conn_data.get("from_issue_key"),
                        to_issue_key=conn_data.get("to_issue_key"),
                        type=conn_data.get("type", "relates to")
                    )
                    connections.append(connection)
                except Exception as e:
                    log.error(f"Error parsing connection data: {str(e)}")

            return connections

        except Exception as e:
            log.error(f"Error fetching workflow connections: {str(e)}")
            return []

    async def get_workflow_issues(self, workflow_id: str) -> List[GanttChartJiraIssueModel]:
        """Get issues for a workflow from workflow service"""
        try:
            # Prepare request
            request = {
                "workflow_id": workflow_id
            }

            # Send request to NATS
            response = await self.nats_client.request(
                "workflow.get_issues",
                request
            )

            if not response.get("success", False):
                log.error(f"Failed to get workflow issues: {response.get('error')}")
                return []

            # Parse issues from response
            issues_data = response.get("data", {}).get("issues", [])
            issues = []

            for issue_data in issues_data:
                try:
                    issue = GanttChartJiraIssueModel(
                        node_id=issue_data.get("node_id"),
                        jira_key=issue_data.get("jira_key"),
                        title=issue_data.get("title", ""),
                        type=issue_data.get("type", "TASK"),
                        estimate_points=float(issue_data.get("estimate_points", 0)),
                        assignee_id=issue_data.get("assignee_id")
                    )
                    issues.append(issue)
                except Exception as e:
                    log.error(f"Error parsing issue data: {str(e)}")

            return issues

        except Exception as e:
            log.error(f"Error fetching workflow issues: {str(e)}")
            return []
