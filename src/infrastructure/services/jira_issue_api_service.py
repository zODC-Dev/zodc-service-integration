
import asyncio
from typing import Any, Dict, List, Optional, Union

from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.exceptions.jira_exceptions import JiraRequestError
from src.domain.models.jira.apis.mappers.jira_issue import JiraIssueMapper
from src.domain.models.jira.apis.mappers.jira_issue_comment import JiraIssueCommentMapper
from src.domain.models.jira.apis.mappers.jira_issue_link import JiraIssueLinkMapper
from src.domain.models.jira.apis.requests.jira_issue import JiraIssueAPICreateRequestDTO, JiraIssueAPIUpdateRequestDTO
from src.domain.models.jira.apis.responses.jira_changelog import (
    JiraIssueChangelogAPIGetResponseDTO,
    JiraIssueChangelogBulkFetchAPIGetResponseDTO,
)
from src.domain.models.jira.apis.responses.jira_issue import (
    JiraIssueAPIGetResponseDTO,
    JiraIssueBulkFetchAPIGetResponseDTO,
)
from src.domain.models.jira.apis.responses.jira_issue_comment import JiraIssueCommentAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_issue_link import JiraIssueLinksResponseDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_issue_comment import JiraIssueCommentModel
from src.domain.models.jira_issue_link import JiraIssueLinkModel
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.infrastructure.services.jira_service import JiraAPIClient
from src.utils.jira_utils import convert_html_to_adf


class JiraIssueAPIService(IJiraIssueAPIService):
    """Service to interact with Jira Issue API"""

    def __init__(
        self,
        client: JiraAPIClient,
        user_repository: IJiraUserRepository,
        admin_client: Optional[JiraAPIClient] = None  # Thêm admin client
    ):
        self.client = client
        self.user_repository = user_repository
        self.admin_client = admin_client
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds

    async def get_issue_with_admin_auth(self, issue_id: str) -> Optional[JiraIssueModel]:
        """Get issue using admin auth"""
        # Sử dụng admin client hoặc client thường với admin auth
        client_to_use = self.admin_client or self.client

        # Gọi API với admin client
        for attempt in range(self.retry_attempts):
            try:
                response_data = await client_to_use.get(
                    session=None,
                    endpoint=f"/rest/api/3/issue/{issue_id}",
                    user_id=None,  # Không cần user_id
                    params={"expand": "renderedFields,transitions,changelog,names"},
                    error_msg=f"Error fetching issue {issue_id}"
                )

                # Map response to domain model
                issue: JiraIssueModel = await self.client.map_to_domain(
                    response_data,
                    JiraIssueAPIGetResponseDTO,
                    JiraIssueMapper
                )

                return issue

            except JiraRequestError as e:
                if e.status_code == 404:
                    log.warning(f"Issue {issue_id} not found in Jira")
                    return None
                elif attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # exponential backoff
                    log.warning(f"Retrying get_issue after {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                else:
                    log.error(f"Failed to fetch issue {issue_id} after {self.retry_attempts} attempts")
                    return None

            except Exception as e:
                log.error(f"Unexpected error fetching issue {issue_id}: {str(e)}")
                return None

        return None

    async def get_issue(self, session: AsyncSession, user_id: int, issue_id: str) -> Optional[JiraIssueModel]:
        """Get issue from Jira API with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                response_data = await self.client.get(
                    session=session,
                    endpoint=f"/rest/api/3/issue/{issue_id}",
                    user_id=user_id,
                    params={
                        "expand": "renderedFields",
                        "fields": [
                            "summary",
                            "description",
                            "status",
                            "assignee",
                            "reporter",
                            "project",
                            "priority",
                            "issuetype",
                            "created",
                            "updated",
                            "customfield_10016",  # story points
                            "customfield_10020",  # sprint
                            # Add any other needed fields
                        ]
                    },
                    error_msg=f"Error fetching issue {issue_id}"
                )

                log.debug(f"Response data when get issue: {response_data}")

                # Map response to domain model
                issue: JiraIssueModel = await self.client.map_to_domain(
                    response_data,
                    JiraIssueAPIGetResponseDTO,
                    JiraIssueMapper
                )

                return issue

            except JiraRequestError as e:
                if e.status_code == 404:
                    log.warning(f"Issue {issue_id} not found in Jira")
                    return None
                elif attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # exponential backoff
                    log.warning(f"Retrying get_issue after {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                else:
                    log.error(f"Failed to fetch issue {issue_id} after {self.retry_attempts} attempts")
                    return None

            except Exception as e:
                log.error(f"Unexpected error fetching issue {issue_id}: {str(e)}")
                return None

        return None

    async def create_issue(self, session: AsyncSession, user_id: int, issue_data: JiraIssueAPICreateRequestDTO) -> JiraIssueModel:
        """Create new issue in Jira"""
        log.debug(f"Creating issue with data: {issue_data}")

        # Prepare payload
        payload: Dict[str, Any] = {
            "fields": {
                "project": {"key": issue_data.project_key},
                "summary": issue_data.summary,
                "issuetype": self._get_issue_type_payload(issue_data.type),
            }
        }

        # Add description if available
        if issue_data.description:
            payload["fields"]["description"] = self._text_to_adf(issue_data.description)

        # Add sprint if available
        if issue_data.sprint_id:
            # Jira expects customfield_10020 as a value of 1 active sprint
            payload["fields"]["customfield_10020"] = issue_data.sprint_id
            log.debug(f"Adding issue to sprints: {issue_data.sprint_id}")

        # Add optional fields
        if issue_data.assignee_id:
            log.debug(f"Updating assignee_id: {issue_data.assignee_id}")
            jira_user = await self.user_repository.get_user_by_id(session=session, user_id=int(issue_data.assignee_id))
            if jira_user and jira_user.jira_account_id:
                payload["fields"]["assignee"] = {"id": jira_user.jira_account_id}

        if issue_data.estimate_point is not None:
            payload["fields"]["customfield_10016"] = issue_data.estimate_point

        log.debug(f"Creating issue with payload: {payload}")
        response_data = await self.client.post(
            session=session,
            endpoint="/rest/api/3/issue",
            user_id=user_id,
            data=payload,
            error_msg="Error when creating issue"
        )

        # Handle error
        if response_data.get("errorMessages"):
            log.error(f"Error when creating issue: {response_data.get('errorMessages')}")
            raise Exception(f"Error when creating issue: {response_data.get('errorMessages')}")

        # Get new created issue
        created_issue_id: str = response_data.get("id")
        created_issue = await self.get_issue(session=session, user_id=user_id, issue_id=created_issue_id)

        # Handle initial status if specified
        if issue_data.status:
            log.debug(f"Setting initial status to {issue_data.status}")
            await self.transition_issue(session=session, user_id=user_id, issue_id=created_issue_id, status=issue_data.status)
            created_issue = await self.get_issue(session=session, user_id=user_id, issue_id=created_issue_id)

        if created_issue:
            return created_issue
        else:
            log.error(f"Failed to get issue {created_issue_id} after create")
            raise Exception(f"Failed to get issue {created_issue_id} after create")

    def _get_issue_type_payload(self, issue_type: Union[JiraIssueType, str, None]) -> Dict[str, Any]:
        """Get issue type payload for Jira API"""
        converted_issue_type: JiraIssueType = JiraIssueType.TASK
        if issue_type is None:
            converted_issue_type = JiraIssueType.TASK

        if isinstance(issue_type, str):
            try:
                converted_issue_type = JiraIssueType(issue_type)
            except ValueError:
                log.warning(f"Invalid issue type: {issue_type}, using TASK")
                converted_issue_type = JiraIssueType.TASK
        elif isinstance(issue_type, JiraIssueType):
            converted_issue_type = issue_type
        else:
            log.warning(f"Invalid issue type: {issue_type}, using TASK")
            converted_issue_type = JiraIssueType.TASK

        # Using name
        return {"name": converted_issue_type.value}

    async def update_issue(self, session: AsyncSession, user_id: int, issue_id: str, update: JiraIssueAPIUpdateRequestDTO) -> JiraIssueModel:
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
            log.debug(f"Updating assignee_id: {update.assignee_id}")
            jira_user = await self.user_repository.get_user_by_id(session=session, user_id=int(update.assignee_id))
            if jira_user and jira_user.jira_account_id:
                payload["fields"]["assignee"] = {"id": jira_user.jira_account_id}

        if update.estimate_point is not None:
            payload["fields"]["customfield_10016"] = update.estimate_point

        log.debug(f"Updating issue {issue_id} with payload: {payload}")

        # Only send request if there is a field to update
        if payload["fields"]:
            try:
                await self.client.put(
                    session=session,
                    endpoint=f"/rest/api/3/issue/{issue_id}",
                    user_id=user_id,
                    data=payload,
                    error_msg=f"Error when updating issue {issue_id}"
                )
                update_result["messages"].append("Updated issue fields successfully")
            except Exception as e:
                log.error(f"Error updating issue fields: {str(e)}")
                update_result["success"] = False
                update_result["messages"].append(f"Failed to update issue fields: {str(e)}")

        # Update status if provided
        if status_to_update is not None:
            log.debug(f"Attempting to update status to {status_to_update}")
            status_success = await self.transition_issue(session=session, user_id=user_id, issue_id=issue_id, status=status_to_update)
            if status_success:
                update_result["messages"].append(f"Successfully transitioned to {status_to_update}")
            else:
                update_result["success"] = False
                update_result["messages"].append(f"Failed to transition to {status_to_update}")

        # Log kết quả cập nhật
        log.debug(f"Update result for issue {issue_id}: {update_result}")

        # Return issue after update
        updated_issue = await self.get_issue(session=session, user_id=user_id, issue_id=issue_id)
        if updated_issue:
            return updated_issue
        else:
            log.error(f"Failed to get issue {issue_id} after update")
            raise Exception(f"Failed to get issue {issue_id} after update")

    async def search_issues(
        self,
        session: AsyncSession,
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
            session=session,
            endpoint="/rest/api/3/search",
            user_id=user_id,
            data={
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": fields
            },
            error_msg="Error when searching issues"
        )

        issues: List[JiraIssueModel] = []
        for issue_data in response_data.get("issues", []):
            issue: JiraIssueModel = await self.client.map_to_domain(
                issue_data,
                JiraIssueAPIGetResponseDTO,
                JiraIssueMapper
            )
            issues.append(issue)

        return issues

    async def get_issue_transitions(self, session: AsyncSession, user_id: int, issue_id: str) -> List[Dict[str, Any]]:
        """Get list of possible transitions for issue"""
        response_data: Dict[str, List[Dict[str, Any]]] = await self.client.get(
            session=session,
            endpoint=f"/rest/api/3/issue/{issue_id}/transitions",
            user_id=user_id,
            error_msg=f"Error when getting list of transitions for issue {issue_id}"
        )

        return response_data.get("transitions", [])

    async def transition_issue(self, session: AsyncSession, user_id: int, issue_id: str, status: Union[JiraIssueStatus, str]) -> bool:
        """Chuyển trạng thái của issue

        Args:
            session: AsyncSession
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
        log.debug(f"Getting transitions for issue {issue_id}")
        transitions = await self.get_issue_transitions(session=session, user_id=user_id, issue_id=issue_id)

        # 2. Tìm transition ID tương ứng với status mong muốn
        transition_id = None
        matching_transitions = []

        # Log tất cả transitions có sẵn để debug
        for t in transitions:
            to_name = t.get('to', {}).get('name')
            transition_name = t.get('name')
            transition_id_str = t.get('id')

            log.debug(f"Available transition: {transition_id_str} - {transition_name} -> {to_name}")

            # So sánh cả name và to.name với status value
            if (transition_name == status_value or to_name == status_value):
                matching_transitions.append(t)
                break

        if matching_transitions:
            # Lấy transition đầu tiên khớp
            transition_id = matching_transitions[0].get('id')
            log.debug(f"Found matching transition: {transition_id} for status {status_value}")

        # 3. Nếu không tìm thấy transition phù hợp
        if not transition_id:
            log.warning(f"No transition found for status {status_value} of issue {issue_id}")

            # 3.1. Kiểm tra xem issue có đã ở trạng thái mong muốn chưa
            current_issue = await self.get_issue(session=session, user_id=user_id, issue_id=issue_id)
            if not current_issue:
                log.error(f"Issue {issue_id} not found")
                return False

            current_status_value = current_issue.status.value
            log.debug(f"Current status of issue {issue_id} is {current_status_value}, wanted {status_value}")

            if current_issue.status == status_enum or current_status_value == status_value:
                log.debug(f"Issue {issue_id} is already in status {status_value}")
                return True

            log.error(f"Cannot transition issue {issue_id} from {current_status_value} to {status_value}")
            return False

        # 4. Thực hiện transition nếu tìm thấy ID phù hợp
        try:
            log.debug(f"Transitioning issue {issue_id} to {status_value} using transition ID {transition_id}")
            await self.client.post(
                session=session,
                endpoint=f"/rest/api/3/issue/{issue_id}/transitions",
                user_id=user_id,
                data={"transition": {"id": transition_id}},
                error_msg=f"Error when transitioning issue {issue_id} to {status_value}"
            )

            # 5. Kiểm tra lại trạng thái sau khi transition
            updated_issue = await self.get_issue(session=session, user_id=user_id, issue_id=issue_id)
            log.debug(f"After transition, issue {issue_id} is in status {updated_issue.status.value}")

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
            JiraIssueStatus.IN_PROGRESS: [JiraIssueStatus.DONE],
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

    async def get_issue_history(self, session: AsyncSession, user_id: int, issue_id: str) -> List[Dict[str, Any]]:
        """Get issue history"""
        response_data = await self.client.get(
            session=session,
            endpoint=f"/rest/api/3/issue/{issue_id}/changelog",
            user_id=user_id,
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

    async def create_issue_link(self, session: AsyncSession, user_id: int, source_issue_id: str, target_issue_id: str, relationship: str) -> bool:
        """Create link between two issues in Jira

        Args:
            session: AsyncSession
            user_id: ID of the user performing the action
            source_issue_id: ID of the source issue
            target_issue_id: ID of the target issue
            relationship: Relationship type ("relates to")

        Returns:
            True if the link is created successfully, False otherwise
        """
        try:
            # Prepare payload for Jira API
            payload = {
                "type": {
                    "name": relationship
                },
                "inwardIssue": {
                    "key": source_issue_id
                },
                "outwardIssue": {
                    "key": target_issue_id
                }
            }

            log.debug(f"Creating link '{relationship}' between {source_issue_id} and {target_issue_id}")

            # Call Jira API to create link
            await self.client.post(
                session=session,
                endpoint="/rest/api/3/issueLink",
                user_id=user_id,
                data=payload,
                error_msg=f"Error creating link between {source_issue_id} and {target_issue_id}"
            )

            log.debug(f"Created link '{relationship}' between {source_issue_id} and {target_issue_id}")
            return True

        except Exception as e:
            log.error(f"Error creating issue link: {str(e)}")
            return False

    async def get_issue_changelog(self, session: AsyncSession, issue_id: str) -> JiraIssueChangelogAPIGetResponseDTO:
        """Lấy lịch sử thay đổi của issue từ Jira API"""
        try:
            # Endpoint cho changelog
            endpoint = f"/rest/api/3/issue/{issue_id}/changelog"

            client_to_use = self.admin_client or self.client

            # Tham số mở rộng để lấy tất cả changelog (mặc định Jira giới hạn số lượng)
            params = {
                "maxResults": 100,  # Có thể điều chỉnh số lượng tùy theo nhu cầu
                "startAt": 0
            }

            # Lấy tất cả changelog
            all_changelogs: List[Dict[str, Any]] = []
            start_at = 0
            max_results = 100
            total = None

            while True:
                params["startAt"] = start_at
                params["maxResults"] = max_results

                response_data = await client_to_use.get(
                    session=session,
                    endpoint=endpoint,
                    user_id=None,  # Không cần user_id
                    params=params,
                    error_msg=f"Error getting changelog for issue {issue_id}"
                )

                # log.debug(f"Response data when get changelog: {response_data}")

                if not response_data:
                    break

                # Debug: In ra cấu trúc của một changelog (chỉ in ra khi tìm thấy dữ liệu)
                values: List[Dict[str, Any]] = response_data.get("values", [])
                if values and len(values) > 0 and not all_changelogs:
                    # log.debug(f"Sample changelog structure: {values[0]}")
                    if 'author' in values[0]:
                        # log.debug(f"Sample author structure: {values[0]['author']}")
                        pass

                all_changelogs.extend(values)

                # Lấy thông tin phân trang
                total = response_data.get("total", 0) if total is None else total
                is_last = response_data.get("isLast", True)

                if is_last or len(values) < max_results:
                    break

                start_at += len(values)

            # Tạo response DTO
            changelog_response = {
                "values": all_changelogs,
                "startAt": 0,
                "maxResults": len(all_changelogs),
                "total": total or len(all_changelogs),
                "isLast": True
            }

            # Map kết quả sang DTO
            try:
                return JiraIssueChangelogAPIGetResponseDTO(**changelog_response)
            except Exception as validation_error:
                # Ghi log chi tiết về lỗi validation để debug
                log.error(f"DTO validation error: {str(validation_error)}")
                # Xem thử cấu trúc của dữ liệu author để phát hiện vấn đề
                if all_changelogs and len(all_changelogs) > 0 and 'author' in all_changelogs[0]:
                    log.error(f"Author structure: {all_changelogs[0]['author']}")
                raise

        except Exception as e:
            log.error(f"Error getting changelog for issue {issue_id}: {str(e)}")
            # Trả về DTO rỗng
            return JiraIssueChangelogAPIGetResponseDTO(values=[], startAt=0, maxResults=0, total=0, isLast=True)

    async def create_issue_with_admin_auth(self, session: AsyncSession, issue_data: JiraIssueAPICreateRequestDTO) -> JiraIssueModel:
        """Create new issue in Jira using admin auth"""
        log.debug(f"Creating issue with admin auth: {issue_data}")

        # Sử dụng admin client
        client_to_use = self.admin_client or self.client

        # Prepare payload
        payload = {
            "fields": {
                "project": {"key": issue_data.project_key},
                "summary": issue_data.summary,
                "issuetype": self._get_issue_type_payload(issue_data.type),
            }
        }

        # Add description if available
        if issue_data.description:
            payload["fields"]["description"] = self._text_to_adf(issue_data.description)

        # Add sprint if available
        if issue_data.sprint_id:
            # Jira expects customfield_10020 as a value of 1 active sprint
            payload["fields"]["customfield_10020"] = issue_data.sprint_id
            log.debug(f"Adding issue to sprints: {issue_data.sprint_id}")

        # Add optional fields
        if issue_data.assignee_id:
            log.debug(f"Updating assignee_id: {issue_data.assignee_id}")
            jira_user = await self.user_repository.get_user_by_id(session=session, user_id=int(issue_data.assignee_id))
            if jira_user and jira_user.jira_account_id:
                payload["fields"]["assignee"] = {"id": jira_user.jira_account_id}

        if issue_data.estimate_point is not None:
            payload["fields"]["customfield_10016"] = issue_data.estimate_point

        log.debug(f"Creating issue with admin auth and payload: {payload}")
        response_data = await client_to_use.post(
            session=None,
            endpoint="/rest/api/3/issue",
            user_id=None,  # Không cần user_id
            data=payload,
            error_msg="Error when creating issue"
        )

        # Handle error
        if response_data.get("errorMessages"):
            log.error(f"Error when creating issue: {response_data.get('errorMessages')}")
            raise Exception(f"Error when creating issue: {response_data.get('errorMessages')}")

        # Get new created issue
        created_issue_id: str = response_data.get("id")
        created_issue = await self.get_issue_with_admin_auth(created_issue_id)

        # Handle initial status if specified
        if issue_data.status:
            log.debug(f"Setting initial status to {issue_data.status}")
            await self.transition_issue_with_admin_auth(created_issue_id, issue_data.status)
            created_issue = await self.get_issue_with_admin_auth(created_issue_id)

        if created_issue:
            return created_issue
        else:
            log.error(f"Failed to get issue {created_issue_id} after create")
            raise Exception(f"Failed to get issue {created_issue_id} after create")

    async def update_issue_with_admin_auth(self, session: AsyncSession, issue_id: str, update: JiraIssueAPIUpdateRequestDTO) -> JiraIssueModel:
        """Update issue in Jira using admin auth"""
        # Sử dụng admin client
        client_to_use = self.admin_client or self.client

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
            log.debug(f"Updating assignee_id: {update.assignee_id}")
            jira_user = await self.user_repository.get_user_by_id(session=session, user_id=int(update.assignee_id))
            if jira_user and jira_user.jira_account_id:
                payload["fields"]["assignee"] = {"id": jira_user.jira_account_id}

        if update.estimate_point is not None:
            payload["fields"]["customfield_10016"] = update.estimate_point

        if update.sprint_id is not None:
            payload["fields"]["customfield_10020"] = update.sprint_id

        log.debug(f"Updating issue {issue_id} with admin auth, payload: {payload}")

        # Only send request if there is a field to update
        if payload["fields"]:
            try:
                await client_to_use.put(
                    session=None,
                    endpoint=f"/rest/api/3/issue/{issue_id}",
                    user_id=None,  # Không cần user_id
                    data=payload,
                    error_msg=f"Error when updating issue {issue_id}"
                )
                update_result["messages"].append("Updated issue fields successfully")
            except Exception as e:
                log.error(f"Error updating issue fields: {str(e)}")
                update_result["success"] = False
                update_result["messages"].append(f"Failed to update issue fields: {str(e)}")

        # Update status if provided
        if status_to_update is not None:
            log.debug(f"Attempting to update status to {status_to_update}")
            status_success = await self.transition_issue_with_admin_auth(issue_id, status_to_update)
            if status_success:
                update_result["messages"].append(f"Successfully transitioned to {status_to_update}")
            else:
                update_result["success"] = False
                update_result["messages"].append(f"Failed to transition to {status_to_update}")

        # Log kết quả cập nhật
        log.debug(f"Update result for issue {issue_id}: {update_result}")

        # Return issue after update
        updated_issue = await self.get_issue_with_admin_auth(issue_id)
        if updated_issue:
            return updated_issue
        else:
            log.error(f"Failed to get issue {issue_id} after update")
            raise Exception(f"Failed to get issue {issue_id} after update")

    async def create_issue_link_with_admin_auth(self, source_issue_id: str, target_issue_id: str, relationship: str) -> bool:
        """Create link between two issues in Jira using admin auth"""
        try:
            # Sử dụng admin client
            client_to_use = self.admin_client or self.client

            # Prepare payload for Jira API
            payload = {
                "type": {
                    "name": relationship
                },
                "inwardIssue": {
                    "key": source_issue_id
                },
                "outwardIssue": {
                    "key": target_issue_id
                }
            }

            log.debug(f"Creating link '{relationship}' between {source_issue_id} and {target_issue_id} with admin auth")

            # Call Jira API to create link
            await client_to_use.post(
                session=None,
                endpoint="/rest/api/3/issueLink",
                user_id=None,  # Không cần user_id
                data=payload,
                error_msg=f"Error creating link between {source_issue_id} and {target_issue_id}"
            )

            log.debug(f"Created link '{relationship}' between {source_issue_id} and {target_issue_id}")
            return True

        except Exception as e:
            log.error(f"Error creating issue link: {str(e)}")
            return False

    async def transition_issue_with_admin_auth(self, issue_id: str, status: Union[JiraIssueStatus, str]) -> bool:
        """Chuyển trạng thái của issue sử dụng admin auth"""
        # Sử dụng admin client
        client_to_use = self.admin_client or self.client

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
        log.debug(f"Getting transitions for issue {issue_id} with admin auth")
        transitions = await self.get_issue_transitions_with_admin_auth(issue_id)

        # 2. Tìm transition ID tương ứng với status mong muốn
        transition_id = None
        matching_transitions = []

        # Log tất cả transitions có sẵn để debug
        for t in transitions:
            to_name = t.get('to', {}).get('name')
            transition_name = t.get('name')
            transition_id_str = t.get('id')

            log.debug(f"Available transition: {transition_id_str} - {transition_name} -> {to_name}")

            # So sánh cả name và to.name với status value
            if (transition_name == status_value or to_name == status_value):
                matching_transitions.append(t)
                break

        if matching_transitions:
            # Lấy transition đầu tiên khớp
            transition_id = matching_transitions[0].get('id')
            log.debug(f"Found matching transition: {transition_id} for status {status_value}")

        # 3. Nếu không tìm thấy transition phù hợp
        if not transition_id:
            log.warning(f"No transition found for status {status_value} of issue {issue_id}")

            # 3.1. Kiểm tra xem issue có đã ở trạng thái mong muốn chưa
            current_issue = await self.get_issue_with_admin_auth(issue_id)
            if not current_issue:
                log.error(f"Issue {issue_id} not found")
                return False

            current_status_value = current_issue.status.value
            log.debug(f"Current status of issue {issue_id} is {current_status_value}, wanted {status_value}")

            if current_issue.status == status_enum or current_status_value == status_value:
                log.debug(f"Issue {issue_id} is already in status {status_value}")
                return True

            log.error(f"Cannot transition issue {issue_id} from {current_status_value} to {status_value}")
            return False

        # 4. Thực hiện transition nếu tìm thấy ID phù hợp
        try:
            log.debug(
                f"Transitioning issue {issue_id} to {status_value} using transition ID {transition_id} with admin auth")
            await client_to_use.post(
                session=None,
                endpoint=f"/rest/api/3/issue/{issue_id}/transitions",
                user_id=None,  # Không cần user_id
                data={"transition": {"id": transition_id}},
                error_msg=f"Error when transitioning issue {issue_id} to {status_value}"
            )

            # 5. Kiểm tra lại trạng thái sau khi transition
            updated_issue = await self.get_issue_with_admin_auth(issue_id)
            log.debug(f"After transition, issue {issue_id} is in status {updated_issue.status.value}")

            return updated_issue.status == status_enum or updated_issue.status.value == status_value

        except Exception as e:
            log.error(f"Error transitioning issue {issue_id} to {status_value}: {str(e)}")
            return False

    async def get_issue_transitions_with_admin_auth(self, issue_id: str) -> List[Dict[str, Any]]:
        """Get list of possible transitions for issue using admin auth"""
        # Sử dụng admin client
        client_to_use = self.admin_client or self.client

        response_data = await client_to_use.get(
            session=None,
            endpoint=f"/rest/api/3/issue/{issue_id}/transitions",
            user_id=None,  # Không cần user_id
            error_msg=f"Error when getting list of transitions for issue {issue_id}"
        )

        return response_data.get("transitions", [])

    async def delete_issue_link_with_admin_auth(self, link_id: str) -> bool:
        """Delete an issue link by its ID using admin authentication"""
        try:
            # Sử dụng admin client hoặc client thường với admin auth
            client_to_use = self.admin_client or self.client

            # Delete link bằng ID
            await client_to_use.delete(
                session=None,
                endpoint=f"/rest/api/3/issueLink/{link_id}",
                user_id=None,  # Không cần user_id khi sử dụng admin auth
                error_msg=f"Error deleting issue link with ID {link_id}"
            )

            log.debug(f"Successfully deleted issue link with ID {link_id}")
            return True
        except Exception as e:
            log.error(f"Error deleting issue link with ID {link_id}: {str(e)}")
            return False

    async def bulk_get_issue_changelog_with_admin_auth(self, issue_ids: List[str]) -> JiraIssueChangelogBulkFetchAPIGetResponseDTO:
        """Get changelog for multiple issues"""
        client_to_use = self.admin_client or self.client

        response_data = await client_to_use.post(
            session=None,
            endpoint="/rest/api/3/changelog/bulkfetch",
            user_id=None,  # Không cần user_id
            data={"issueIdsOrKeys": issue_ids},
            error_msg=f"Error when getting changelog for issues {issue_ids}"
        )

        return JiraIssueChangelogBulkFetchAPIGetResponseDTO.model_validate(response_data)

    async def bulk_get_issues_with_admin_auth(self, issue_ids: List[str]) -> List[JiraIssueModel]:
        """Bulk get issues with admin auth"""
        client_to_use = self.admin_client or self.client

        response_data = await client_to_use.post(
            session=None,
            endpoint="/rest/api/3/issue/bulkfetch",
            user_id=None,  # Không cần user_id
            data={"issueIdsOrKeys": issue_ids},
            error_msg=f"Error when getting issues {issue_ids}"
        )

        issues = JiraIssueBulkFetchAPIGetResponseDTO.model_validate(response_data)
        return [JiraIssueMapper.to_domain(issue) for issue in issues.issues]

    async def update_issue_assignee_with_admin_auth(self, issue_key: str, assignee_account_id: str) -> bool:
        """Update the assignee of a Jira issue

        Args:
            issue_key: The Jira issue key
            assignee_account_id: The Jira account ID of the new assignee

        Returns:
            bool: Whether the update was successful
        """
        try:
            url = f"/rest/api/3/issue/{issue_key}/assignee"

            payload = {
                "accountId": assignee_account_id
            }

            await self.client.put(
                session=None,
                endpoint=url,
                user_id=None,
                data=payload,
                error_msg=f"Error updating issue assignee {issue_key}"
            )
            return True
        except Exception as e:
            log.error(f"Error updating issue assignee: {str(e)}")
            raise JiraRequestError(500, f"Failed to update issue assignee: {str(e)}") from e

    async def get_issue_links_with_admin_auth(self, issue_key: str) -> List[JiraIssueLinkModel]:
        """Get links for an issue using admin auth

        Args:
            issue_key: The key of the issue to get links for

        Returns:
            List of issue link models
        """
        client = self.admin_client or self.client

        url = f"/rest/api/3/issue/{issue_key}"
        params = {
            "fields": "issuelinks"
        }

        try:
            response_data = await client.get(
                session=None,
                endpoint=url,
                user_id=None,  # Không cần user_id khi sử dụng admin client
                params=params,
                error_msg=f"Error when getting links for issue {issue_key}"
            )

            # Extract the part we care about
            fields_data = response_data.get("fields", {})

            # Create a response DTO with the issuelinks field
            response_dto = JiraIssueLinksResponseDTO(issuelinks=fields_data.get("issuelinks", []))

            # Convert to domain models
            issue_links = JiraIssueLinkMapper.response_to_domain_list(response_dto)

            return issue_links

        except Exception as e:
            log.error(f"Error getting issue links for {issue_key}: {str(e)}")
            return []

    async def get_issue_comments_with_admin_auth(self, issue_key: str) -> List[JiraIssueCommentModel]:
        """Get comments for an issue"""
        client = self.admin_client or self.client

        url = f"/rest/api/3/issue/{issue_key}/comment"

        params = {
            "expand": "renderedBody"
        }

        try:
            response_data = await client.get(
                session=None,
                endpoint=url,
                user_id=None,  # Không cần user_id khi sử dụng admin client
                params=params,
                error_msg=f"Error when getting comments for issue {issue_key}"
            )

            # Check if 'comments' key exists in response_data
            if 'comments' in response_data:
                # Convert to DTO
                response_dto = [JiraIssueCommentAPIGetResponseDTO(**comment)
                                for comment in response_data['comments']]

                # Convert to domain models
                comments = JiraIssueCommentMapper.response_to_domain_list(response_dto)
            else:
                log.warning(f"No comments found for issue {issue_key}")
                return []

            return comments

        except Exception as e:
            log.error(f"Error getting issue comments for {issue_key}: {str(e)}")
            return []

    async def create_issue_comment(self, session: AsyncSession, user_id: int, issue_key: str, comment: str) -> JiraIssueCommentModel:
        """Create a comment for an issue using admin auth"""
        client = self.admin_client or self.client

        url = f"/rest/api/3/issue/{issue_key}/comment?expand=renderedBody"

        payload = {
            "body": convert_html_to_adf(comment)
        }

        response_data = await client.post(
            session=session,
            endpoint=url,
            user_id=user_id,
            data=payload,
            error_msg=f"Error when creating comment for issue {issue_key}"
        )

        # Convert to DTO
        response_dto = JiraIssueCommentAPIGetResponseDTO(**response_data)

        # Convert to domain model
        return JiraIssueCommentMapper.response_to_domain(response_dto)
