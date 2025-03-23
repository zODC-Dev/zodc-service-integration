from datetime import datetime, timezone
from typing import Any, Dict

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_issue import JiraIssueCreateDTO
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_webhook import JiraWebhookPayload


class JiraWebhookMapper:
    # Mapping từ field name trong Jira webhook sang field name trong database
    FIELD_MAPPING = {
        "summary": "summary",
        "description": "description",
        "issuetype": "type",
        "status": "status",
        "assignee": "assignee_id",
        "reporter": "reporter_id",
        "customfield_10016": "estimate_points",
        "customfield_10017": "actual_points",
        "Sprint": "sprints",
        # Thêm các mapping khác nếu cần
    }

    @classmethod
    def map_to_create_dto(cls, webhook_data: JiraWebhookPayload) -> JiraIssueCreateDTO:
        """Map webhook data to JiraIssueCreateDTO"""
        try:
            issue = webhook_data.issue
            fields = issue.fields

            return JiraIssueCreateDTO(
                jira_issue_id=issue.id,
                key=issue.key,
                project_key=fields.project.key,
                summary=fields.summary,
                description=fields.description,
                type=JiraIssueType(fields.issue_type.name),
                status=JiraIssueStatus(fields.status.name) if fields.status else JiraIssueStatus.TO_DO,
                assignee_id=fields.assignee.account_id if fields.assignee else None,
                reporter_id=fields.reporter.account_id if fields.reporter else None,
                created_at=cls._parse_datetime(fields.created),
                updated_at=cls._parse_datetime(fields.updated),
                estimate_points=fields.estimate_points,
                actual_points=fields.actual_points
            )
        except Exception as e:
            log.error(f"Error mapping webhook data to create DTO: {str(e)}")
            raise

    @classmethod
    def map_to_update_dto(cls, webhook_data: JiraWebhookPayload) -> Dict[str, Any]:
        """Map webhook data to update dictionary based on changelog"""
        try:
            update_data = {}

            # Nếu có changelog, chỉ update các field đã thay đổi
            if webhook_data.changelog and webhook_data.changelog.items:
                for change in webhook_data.changelog.items:
                    field_name = change.field
                    if field_name in cls.FIELD_MAPPING:
                        db_field = cls.FIELD_MAPPING[field_name]
                        new_value = cls._transform_field_value(field_name, change.to or change.to_string)
                        # Chỉ thêm vào update_data nếu giá trị không phải None
                        if new_value is not None:
                            update_data[db_field] = new_value
                        else:
                            log.debug(f"Skipping field {field_name} with None value")

            # Luôn cập nhật updated_at
            fields = webhook_data.issue.fields
            update_data["updated_at"] = cls._parse_datetime(fields.updated)

            log.debug(f"Mapped update data: {update_data}")
            return update_data

        except Exception as e:
            log.error(f"Error mapping webhook data to update dict: {str(e)}")
            raise

    @classmethod
    def _transform_field_value(cls, field_name: str, value: Any) -> Any:
        """Transform field value based on field type"""
        if value is None:
            return None

        try:
            if field_name == "status":
                return JiraIssueStatus(value)
            elif field_name == "issuetype":
                return JiraIssueType(value)
            elif field_name == "assignee":
                return value  # Assuming value is account_id
            elif field_name in ["customfield_10016", "customfield_10017"]:
                return float(value) if value else 0
            elif field_name == "Sprint":
                # Xử lý trường hợp sprint được gửi từ webhook
                if isinstance(value, str):
                    # Nếu là string (ví dụ: "Sprint 3"), tạm thời bỏ qua
                    log.debug(f"Received sprint update with value: {value}, skipping...")
                    return None
                elif isinstance(value, list):
                    # Nếu là list, xử lý theo định dạng của Jira
                    sprints = []
                    for sprint_data in value:
                        if isinstance(sprint_data, dict):
                            try:
                                sprints.append(JiraSprintModel(
                                    jira_sprint_id=sprint_data.get('id'),
                                    name=sprint_data.get('name'),
                                    state=sprint_data.get('state'),
                                    start_date=cls._parse_datetime(sprint_data.get(
                                        'startDate')) if sprint_data.get('startDate') else None,
                                    end_date=cls._parse_datetime(sprint_data.get(
                                        'endDate')) if sprint_data.get('endDate') else None,
                                    complete_date=cls._parse_datetime(sprint_data.get(
                                        'completeDate')) if sprint_data.get('completeDate') else None,
                                    goal=sprint_data.get('goal'),
                                    project_key=sprint_data.get('originBoardId'),  # hoặc trường phù hợp khác
                                    created_at=datetime.now(timezone.utc)
                                ))
                            except Exception as e:
                                log.warning(f"Error parsing sprint data: {str(e)}")
                                continue
                    return sprints if sprints else None
                return None
            return value
        except Exception as e:
            log.warning(f"Error transforming field {field_name}: {str(e)}")
            return None

    @staticmethod
    def _parse_datetime(dt_str: str) -> datetime:
        """Parse datetime string from Jira"""
        if dt_str.endswith('Z'):
            dt_str = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(dt_str)
