
from src.app.services.jira_issue_service import JiraIssueApplicationService


class JiraIssueController:
    def __init__(
        self,
        jira_issue_service: JiraIssueApplicationService,
    ):
        self.jira_issue_service = jira_issue_service
