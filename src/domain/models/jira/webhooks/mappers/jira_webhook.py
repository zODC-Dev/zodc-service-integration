# from datetime import datetime
# from typing import Any, List

# from src.configs.logger import log
# from src.domain.constants.jira import JIRA_ISSUE_TYPE_ID_MAPPING, JIRA_STATUS_ID_MAPPING, JiraIssueStatus, JiraIssueType
# from src.domain.models.jira_sprint import JiraSprintModel


class JiraWebhookMapper:
    # Mapping từ field ID trong Jira webhook sang field name trong database
    FIELD_ID_MAPPING = {
        "summary": "summary",
        "description": "description",
        "issuetype": "type",
        "status": "status",
        "assignee": "assignee_id",
        "reporter": "reporter_id",
        "customfield_10016": "estimate_point",  # Story point estimate
        "customfield_10020": "sprints",          # Sprint field
    }

    # Ngược lại để tìm kiếm theo tên field
    FIELD_NAME_MAPPING = {
        "Sprint": "sprints",
        "Story point estimate": "estimate_point",
        "Actual point": "actual_point",
    }
