from typing import Any, Dict, List, Optional, Union

from src.configs.logger import log
from src.domain.constants.jira import JIRA_ISSUE_TYPE_ID_MAPPING, JiraIssueStatus, JiraIssueType
from src.domain.models.jira.apis.mappers.jira_issue import JiraIssueMapper
from src.domain.models.jira.apis.requests.jira_issue import JiraIssueAPICreateRequestDTO, JiraIssueAPIUpdateRequestDTO
from src.domain.models.jira.apis.responses.jira_issue import JiraIssueAPIGetResponseDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.infrastructure.services.jira_service import JiraAPIClient


class JiraIssueAPIService(IJiraIssueAPIService):
    """Service to interact with Jira Issue API"""

    def __init__(
        self,
        jira_api_client: JiraAPIClient,
        user_repository: IJiraUserRepository
    ):
        self.client = jira_api_client
        self.user_repository = user_repository

    async def get_issue(self, user_id: int, issue_id: str) -> JiraIssueModel:
        """Get issue information from Jira API"""
        response_data = await self.client.get(
            f"/rest/api/3/issue/{issue_id}",
            user_id,
            params={"fields": "summary,description,status,assignee,reporter,priority,issuetype,created,updated,customfield_10016,customfield_10017,customfield_10020"},
            error_msg=f"Error when getting issue {issue_id}"
        )

        log.info(f"Issue response from Get Issue: {response_data}")

        return await self.client.map_to_domain(
            response_data,
            JiraIssueAPIGetResponseDTO,
            JiraIssueMapper
        )

    async def create_issue(self, user_id: int, issue_data: JiraIssueAPICreateRequestDTO) -> JiraIssueModel:
        """Create new issue in Jira"""
        log.info(f"Creating issue with data: {issue_data}")

        # Prepare payload
        payload = {
            "fields": {
                "project": {"key": issue_data.project_key},
                "summary": issue_data.summary,
                "description": issue_data.description,
                "issuetype": self._get_issue_type_payload(issue_data.type),
            }
        }

        # Add sprint if available
        if issue_data.sprint_id:
            # Jira expects customfield_10020 as a value of 1 active sprint
            payload["fields"]["customfield_10020"] = issue_data.sprint_id
            log.info(f"Adding issue to sprints: {issue_data.sprint_id}")

        # Add optional fields
        if issue_data.assignee_id:
            log.info(f"Updating assignee_id: {issue_data.assignee_id}")
            jira_user = await self.user_repository.get_user_by_id(int(issue_data.assignee_id))
            if jira_user and jira_user.jira_account_id:
                payload["fields"]["assignee"] = {"id": jira_user.jira_account_id}

        if issue_data.estimate_point is not None:
            payload["fields"]["customfield_10016"] = issue_data.estimate_point

        log.info(f"Creating issue with payload: {payload}")
        response_data = await self.client.post(
            "/rest/api/3/issue",
            user_id,
            payload,
            error_msg="Error when creating issue"
        )

        # Get new created issue
        created_issue_id: str = response_data.get("id")
        created_issue = await self.get_issue(user_id, created_issue_id)

        # Handle initial status if specified
        if issue_data.status:
            log.info(f"Setting initial status to {issue_data.status}")
            await self.transition_issue(user_id, created_issue_id, issue_data.status)
            created_issue = await self.get_issue(user_id, created_issue_id)

        return created_issue

    def _get_issue_type_payload(self, issue_type: Union[JiraIssueType, str]) -> Dict[str, Any]:
        """Get issue type payload for Jira API"""
        if isinstance(issue_type, str):
            try:
                issue_type = JiraIssueType(issue_type)
            except ValueError:
                log.warning(f"Invalid issue type: {issue_type}, using TASK")
                issue_type = JiraIssueType.TASK

        # Tìm ID từ mapping
        for type_id, mapped_type in JIRA_ISSUE_TYPE_ID_MAPPING.items():
            if mapped_type == issue_type:
                return {"id": type_id}

        # Fallback to using name if no ID mapping found
        return {"name": issue_type.value}

    async def update_issue(self, user_id: int, issue_id: str, update: JiraIssueAPIUpdateRequestDTO) -> JiraIssueModel:
        """Update issue in Jira"""
        # Prepare payload for fields
        payload: Dict[str, Any] = {"fields": {}}

        # Lưu lại thông tin status để xử lý riêng
        status_to_update = update.status
        update_result: Dict[str, Any] = {"success": True, "messages": []}

        # Đảm bảo không đưa status vào payload
        update.status = None

        # Thêm các trường khác vào payload
        if update.summary is not None:
            payload["fields"]["summary"] = update.summary

        if update.description is not None:
            payload["fields"]["description"] = self._text_to_adf(update.description)

        if update.assignee_id is not None:
            log.info(f"Updating assignee_id: {update.assignee_id}")
            jira_user = await self.user_repository.get_user_by_id(int(update.assignee_id))
            if jira_user and jira_user.jira_account_id:
                payload["fields"]["assignee"] = {"id": jira_user.jira_account_id}

        if update.estimate_point is not None:
            payload["fields"]["customfield_10016"] = update.estimate_point

        if update.actual_point is not None:
            payload["fields"]["customfield_10017"] = update.actual_point

        log.info(f"Updating issue {issue_id} with payload: {payload}")

        # Only send request if there is a field to update
        if payload["fields"]:
            try:
                await self.client.put(
                    f"/rest/api/3/issue/{issue_id}",
                    user_id,
                    payload,
                    error_msg=f"Error when updating issue {issue_id}"
                )
                update_result["messages"].append("Updated issue fields successfully")
            except Exception as e:
                log.error(f"Error updating issue fields: {str(e)}")
                update_result["success"] = False
                update_result["messages"].append(f"Failed to update issue fields: {str(e)}")

        # Update status if provided
        if status_to_update is not None:
            log.info(f"Attempting to update status to {status_to_update}")
            status_success = await self.transition_issue(user_id, issue_id, status_to_update)
            if status_success:
                update_result["messages"].append(f"Successfully transitioned to {status_to_update}")
            else:
                update_result["success"] = False
                update_result["messages"].append(f"Failed to transition to {status_to_update}")

        # Log kết quả cập nhật
        log.info(f"Update result for issue {issue_id}: {update_result}")

        # Return issue after update
        return await self.get_issue(user_id, issue_id)

    async def search_issues(
        self,
        user_id: int,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
        fields: Optional[List[str]] = None
    ) -> List[JiraIssueModel]:
        """Search issues by JQL"""
        if fields is None:
            fields = ["summary", "description", "status", "assignee", "issuetype", "created", "updated"]

        response_data = await self.client.post(
            "/rest/api/3/search",
            user_id,
            {
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": fields
            },
            error_msg="Error when searching issues"
        )

        issues = []
        for issue_data in response_data.get("issues", []):
            issue = await self.client.map_to_domain(
                issue_data,
                JiraIssueAPIGetResponseDTO,
                JiraIssueMapper
            )
            issues.append(issue)

        return issues

    async def get_issue_transitions(self, user_id: int, issue_id: str) -> List[Dict[str, Any]]:
        """Get list of possible transitions for issue"""
        response_data = await self.client.get(
            f"/rest/api/3/issue/{issue_id}/transitions",
            user_id,
            error_msg=f"Error when getting list of transitions for issue {issue_id}"
        )

        return response_data.get("transitions", [])

    async def transition_issue(self, user_id: int, issue_id: str, status: Union[JiraIssueStatus, str]) -> bool:
        """Chuyển trạng thái của issue

        Args:
            user_id: ID của người dùng thực hiện hành động
            issue_id: ID của issue cần chuyển trạng thái
            status: Trạng thái mới (JiraIssueStatus enum hoặc string)

        Returns:
            True nếu chuyển trạng thái thành công, False nếu không
        """
        # Chuyển đổi status từ chuỗi sang enum nếu cần
        if isinstance(status, str):
            try:
                status_enum = JiraIssueStatus(status)
            except ValueError:
                log.error(f"Invalid status string: {status}")
                return False
        else:
            status_enum = status

        # Lấy giá trị chuỗi của status để sử dụng trong so sánh
        status_value = status_enum.value

        # 1. Lấy danh sách transitions có thể thực hiện
        log.info(f"Getting transitions for issue {issue_id}")
        transitions = await self.get_issue_transitions(user_id, issue_id)

        # 2. Tìm transition ID tương ứng với status mong muốn
        transition_id = None
        matching_transitions = []

        # Log tất cả transitions có sẵn để debug
        for t in transitions:
            to_name = t.get('to', {}).get('name')
            transition_name = t.get('name')
            transition_id_str = t.get('id')

            log.info(f"Available transition: {transition_id_str} - {transition_name} -> {to_name}")

            # So sánh cả name và to.name với status value
            if (transition_name == status_value or to_name == status_value):
                matching_transitions.append(t)
                break

        if matching_transitions:
            # Lấy transition đầu tiên khớp
            transition_id = matching_transitions[0].get('id')
            log.info(f"Found matching transition: {transition_id} for status {status_value}")

        # 3. Nếu không tìm thấy transition phù hợp
        if not transition_id:
            log.warning(f"No transition found for status {status_value} of issue {issue_id}")

            # 3.1. Kiểm tra xem issue có đã ở trạng thái mong muốn chưa
            current_issue = await self.get_issue(user_id, issue_id)
            current_status_value = current_issue.status.value
            log.info(f"Current status of issue {issue_id} is {current_status_value}, wanted {status_value}")

            if current_issue.status == status_enum or current_status_value == status_value:
                log.info(f"Issue {issue_id} is already in status {status_value}")
                return True

            log.error(f"Cannot transition issue {issue_id} from {current_status_value} to {status_value}")
            return False

        # 4. Thực hiện transition nếu tìm thấy ID phù hợp
        try:
            log.info(f"Transitioning issue {issue_id} to {status_value} using transition ID {transition_id}")
            await self.client.post(
                f"/rest/api/3/issue/{issue_id}/transitions",
                user_id,
                {"transition": {"id": transition_id}},
                error_msg=f"Error when transitioning issue {issue_id} to {status_value}"
            )

            # 5. Kiểm tra lại trạng thái sau khi transition
            updated_issue = await self.get_issue(user_id, issue_id)
            log.info(f"After transition, issue {issue_id} is in status {updated_issue.status.value}")

            return updated_issue.status == status_enum or updated_issue.status.value == status_value

        except Exception as e:
            log.error(f"Error transitioning issue {issue_id} to {status_value}: {str(e)}")
            return False

    def _get_intermediate_statuses(self, current_status: JiraIssueStatus, target_status: JiraIssueStatus) -> List[JiraIssueStatus]:
        """Lấy danh sách các trạng thái trung gian để chuyển từ current_status -> target_status

        Ví dụ:
            - Từ TO_DO -> DONE: [IN_PROGRESS]
            - Từ TO_DO -> IN_PROGRESS: []
        """
        # Định nghĩa workflow tiêu chuẩn
        standard_workflow = {
            JiraIssueStatus.TO_DO: [JiraIssueStatus.IN_PROGRESS],
            JiraIssueStatus.IN_PROGRESS: [JiraIssueStatus.IN_REVIEW, JiraIssueStatus.DONE],
            JiraIssueStatus.IN_REVIEW: [JiraIssueStatus.DONE, JiraIssueStatus.IN_PROGRESS],
            JiraIssueStatus.DONE: [JiraIssueStatus.IN_PROGRESS]
        }

        # Xác định các đường dẫn có thể từ current_status -> target_status
        if current_status == target_status:
            return []

        # Direct path
        if target_status in standard_workflow.get(current_status, []):
            return []

        # One hop path
        for intermediate in standard_workflow.get(current_status, []):
            if target_status in standard_workflow.get(intermediate, []):
                return [intermediate]

        # Mặc định trả về rỗng nếu không tìm thấy đường dẫn
        return []

    async def add_comment(self, user_id: int, issue_id: str, comment: str) -> Dict[str, Any]:
        """Add comment to issue"""
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment
                            }
                        ]
                    }
                ]
            }
        }

        return await self.client.post(
            f"/rest/api/3/issue/{issue_id}/comment",
            user_id,
            payload,
            error_msg=f"Error when adding comment to issue {issue_id}"
        )

    async def get_issue_history(self, user_id: int, issue_id: str) -> List[Dict[str, Any]]:
        """Get issue history"""
        response_data = await self.client.get(
            f"/rest/api/3/issue/{issue_id}/changelog",
            user_id,
            error_msg=f"Error when getting issue history for issue {issue_id}"
        )

        return response_data.get("values", [])

    def _text_to_adf(self, text: str) -> Dict[str, Any]:
        """Convert plain text to Atlassian Document Format"""
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                }
            ]
        }
