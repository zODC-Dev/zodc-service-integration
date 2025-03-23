from datetime import datetime
from typing import Any, Dict, Optional

from src.configs.logger import log
from src.domain.constants.jira import JIRA_ISSUE_TYPE_ID_MAPPING, JIRA_STATUS_ID_MAPPING, JiraIssueStatus, JiraIssueType
from src.domain.models.jira_issue import JiraIssueCreateDTO
from src.domain.models.jira_webhook import JiraWebhookPayload


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
        "customfield_10017": "actual_point",    # Actual points
        "customfield_10020": "sprints",          # Sprint field
    }

    # Ngược lại để tìm kiếm theo tên field
    FIELD_NAME_MAPPING = {
        "Sprint": "sprints",
        "Story point estimate": "estimate_point",
        "Actual point": "actual_point",
    }

    @classmethod
    def map_to_create_dto(cls, webhook_data: JiraWebhookPayload) -> JiraIssueCreateDTO:
        """Map webhook data to JiraIssueCreateDTO"""
        try:
            issue = webhook_data.issue
            fields = issue.fields

            # Xử lý status theo mapping
            status = None
            if fields.status:
                status_id = getattr(fields.status, 'id', None)
                if status_id and str(status_id) in JIRA_STATUS_ID_MAPPING:
                    status = JIRA_STATUS_ID_MAPPING[str(status_id)]
                else:
                    try:
                        status = JiraIssueStatus(fields.status.name)
                    except ValueError:
                        status = JiraIssueStatus.TO_DO
            else:
                status = JiraIssueStatus.TO_DO

            # Xử lý issue type theo mapping
            issue_type = None
            if fields.issue_type:
                type_id = getattr(fields.issue_type, 'id', None)
                if type_id and str(type_id) in JIRA_ISSUE_TYPE_ID_MAPPING:
                    issue_type = JIRA_ISSUE_TYPE_ID_MAPPING[str(type_id)]
                else:
                    try:
                        issue_type = JiraIssueType(fields.issue_type.name)
                    except ValueError:
                        issue_type = JiraIssueType.TASK
            else:
                issue_type = JiraIssueType.TASK

            # Tạo link URL cho issue
            jira_base_url = cls._extract_jira_base_url(fields)
            link_url = f"{jira_base_url}/browse/{issue.key}" if jira_base_url else None

            return JiraIssueCreateDTO(
                jira_issue_id=issue.id,
                key=issue.key,
                project_key=fields.project.key,
                summary=fields.summary,
                description=fields.description,
                type=issue_type,
                status=status,
                assignee_id=fields.assignee.account_id if fields.assignee else None,
                reporter_id=fields.reporter.account_id if fields.reporter else None,
                created_at=cls._parse_datetime(fields.created),
                updated_at=cls._parse_datetime(fields.updated),
                estimate_point=fields.estimate_point,
                is_deleted=False,
                link_url=link_url
            )
        except Exception as e:
            log.error(f"Error mapping webhook data to create DTO: {str(e)}")
            raise

    @classmethod
    def map_to_update_dto(cls, webhook_data: JiraWebhookPayload) -> Dict[str, Any]:
        """Map webhook data to update dictionary based on changelog"""
        try:
            update_data: Dict[str, Any] = {}

            # Nếu có changelog, chỉ update các field đã thay đổi
            if webhook_data.changelog and webhook_data.changelog.items:
                for change in webhook_data.changelog.items:
                    log.info(f"change: {change}")
                    field_name = change.field
                    field_id = change.field_id

                    db_field = None
                    if field_id and field_id in cls.FIELD_ID_MAPPING:
                        db_field = cls.FIELD_ID_MAPPING[field_id]
                    elif field_name in cls.FIELD_NAME_MAPPING:
                        db_field = cls.FIELD_NAME_MAPPING[field_name]

                    if db_field:
                        # Sử dụng field_id nếu có, nếu không thì dùng field_name
                        source_field = field_id or field_name

                        # Ưu tiên dùng to_string cho status và issuetype
                        if field_name == "status" or field_name == "issuetype":
                            log.info(f"Processing {field_name} change: {change.to} (ID) -> {change.to_string} (Name)")

                            # Ưu tiên dùng ID nếu có trong mapping
                            if change.to and str(change.to) in (JIRA_STATUS_ID_MAPPING if field_name == "status" else JIRA_ISSUE_TYPE_ID_MAPPING):
                                value_to_transform = change.to
                            else:
                                # Nếu không có ID trong mapping, dùng tên hiển thị
                                value_to_transform = change.to_string
                        else:
                            value_to_transform = change.to or change.to_string

                        # Transform value
                        new_value = cls._transform_field_value(source_field, value_to_transform)

                        # Chỉ thêm vào update_data nếu giá trị không phải None
                        if new_value is not None:
                            update_data[db_field] = new_value
                            log.info(
                                f"Updating field {db_field} with value {new_value} (from {source_field}, original: {value_to_transform})")
                        else:
                            log.info(f"Skipping field {source_field} with None value")
                    else:
                        log.info(f"Unmapped field: {field_id or field_name}")

            # Luôn cập nhật updated_at
            fields = webhook_data.issue.fields
            update_data["updated_at"] = cls._parse_datetime(fields.updated)

            log.info(f"Mapped update data: {update_data}")
            return update_data

        except Exception as e:
            log.error(f"Error mapping webhook data to update dict: {str(e)}")
            raise

    @classmethod
    def _transform_field_value(cls, field_id_or_name: str, value: Any) -> Any:
        """Transform field value based on field type"""
        if value is None:
            return None

        try:
            # Xử lý các trường hợp dựa vào field_id hoặc field_name
            if field_id_or_name == "status":
                # Thử dùng ID mapping trước
                if isinstance(value, (str, int)) and str(value) in JIRA_STATUS_ID_MAPPING:
                    status = JIRA_STATUS_ID_MAPPING[str(value)]
                    log.info(f"Mapped status ID {value} to {status}")
                    return status

                # Nếu không có trong ID mapping, thử dùng tên
                try:
                    return JiraIssueStatus(value)
                except ValueError:
                    # Fallback: dùng from_str để tìm kiếm theo cách không phân biệt hoa thường
                    try:
                        log.info(f"Trying to map status name {value} using from_str")
                        return JiraIssueStatus.from_str(value)
                    except ValueError:
                        log.warning(f"Invalid status value: {value}, defaulting to TO_DO")
                        return JiraIssueStatus.TO_DO

            elif field_id_or_name == "issuetype":
                # Thử dùng ID mapping trước
                if isinstance(value, (str, int)) and str(value) in JIRA_ISSUE_TYPE_ID_MAPPING:
                    issue_type = JIRA_ISSUE_TYPE_ID_MAPPING[str(value)]
                    log.info(f"Mapped issue type ID {value} to {issue_type}")
                    return issue_type

                # Nếu không có trong ID mapping, thử dùng tên
                try:
                    return JiraIssueType(value)
                except ValueError:
                    log.warning(f"Invalid issue type value: {value}, defaulting to TASK")
                    return JiraIssueType.TASK

            elif field_id_or_name == "assignee":
                return value  # Assuming value is account_id

            elif field_id_or_name == "customfield_10016" or field_id_or_name == "Story point estimate":
                # Chuyển đổi story points sang float
                try:
                    return float(value) if value else 0
                except (ValueError, TypeError):
                    log.warning(f"Could not convert story point value '{value}' to float")
                    return 0

            elif field_id_or_name == "customfield_10017" or field_id_or_name == "Actual point":
                # Chuyển đổi actual points sang float
                try:
                    return float(value) if value else 0
                except (ValueError, TypeError):
                    log.warning(f"Could not convert actual point value '{value}' to float")
                    return 0

            elif field_id_or_name == "customfield_10020" or field_id_or_name == "Sprint":
                # Use the dedicated sprint mapper
                from src.app.mappers.jira_mapper import JiraSprintMapper
                return JiraSprintMapper.from_webhook_list(value)

            # Nếu không thuộc các trường hợp đặc biệt, trả về giá trị nguyên gốc
            return value

        except Exception as e:
            log.warning(f"Error transforming field {field_id_or_name}: {str(e)}")
            return None

    @staticmethod
    def _parse_datetime(dt_str: str) -> datetime:
        """Parse datetime string from Jira"""
        if dt_str.endswith('Z'):
            dt_str = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(dt_str)

    @staticmethod
    def _extract_jira_base_url(fields) -> Optional[str]:
        """Extract Jira base URL from fields"""
        if hasattr(fields, 'self') and fields.self:
            try:
                # Dạng của URL: https://your-jira-instance.com/rest/api/2/issue/123456
                parts = fields.self.split('/rest/api')
                if parts and len(parts) > 0:
                    return parts[0]  # Lấy phần base URL
            except Exception as e:
                log.warning(f"Could not extract Jira base URL: {str(e)}")
        return None
