from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira.apis.responses.jira_issue import JiraIssueAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_sprint import JiraSprintAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel


class JiraIssueMapper:
    """Mapper for Jira issue API responses to domain models"""

    @staticmethod
    def _map_user(user_response: JiraUserAPIGetResponseDTO) -> Optional[JiraUserModel]:
        try:
            avatar_url = ""
            if isinstance(user_response.avatar_urls, dict):
                avatar_url = user_response.avatar_urls.get("48x48", "")

            return JiraUserModel(
                jira_account_id=user_response.account_id,
                email=user_response.email_address or '',
                name=user_response.display_name,
                avatar_url=avatar_url,
                is_system_user=False,
                is_active=user_response.active
            )
        except Exception as e:
            log.error(f"Error mapping user response to domain: {str(e)}")
            # Return minimal valid model
            return JiraUserModel(
                jira_account_id=user_response.account_id,
                email='',
                name=user_response.display_name or '',
                avatar_url='',
                is_system_user=False
            )

    @staticmethod
    def _convert_adf_to_text(adf_data: Union[str, Dict[str, Any], None]) -> Optional[str]:
        """Convert Atlassian Document Format to plain text"""
        if adf_data is None:
            return None

        if isinstance(adf_data, str):
            return adf_data

        try:
            # Xử lý ADF object
            if isinstance(adf_data, dict):
                text_parts = []

                # Lấy text từ content
                if "content" in adf_data:
                    for content in adf_data["content"]:
                        if content.get("type") == "paragraph":
                            for text_node in content.get("content", []):
                                if text_node.get("type") == "text":
                                    text_parts.append(text_node.get("text", ""))

                return "\n".join(text_parts) if text_parts else None

            return str(adf_data)

        except Exception as e:
            log.error(f"Error converting ADF to text: {str(e)}")
            return None

    @staticmethod
    def _convert_adf_to_html(adf_data: Union[str, Dict[str, Any], None]) -> Optional[str]:
        """Convert Atlassian Document Format to HTML"""
        if adf_data is None:
            return None

        if isinstance(adf_data, str):
            return f"<p>{adf_data}</p>"

        try:
            # Xử lý ADF object
            if isinstance(adf_data, dict):
                html_parts = []

                # Xử lý từng phần tử trong content
                if "content" in adf_data:
                    for content in adf_data["content"]:
                        content_type = content.get("type")

                        if content_type == "paragraph":
                            paragraph_html = "<p>"
                            for text_node in content.get("content", []):
                                if text_node.get("type") == "text":
                                    text = text_node.get("text", "")
                                    marks = text_node.get("marks", [])

                                    # Áp dụng định dạng từ marks
                                    for mark in marks:
                                        mark_type = mark.get("type")
                                        if mark_type == "strong":
                                            text = f"<strong>{text}</strong>"
                                        elif mark_type == "em":
                                            text = f"<em>{text}</em>"
                                        elif mark_type == "code":
                                            text = f"<code>{text}</code>"
                                        elif mark_type == "underline":
                                            text = f"<u>{text}</u>"
                                        elif mark_type == "strike":
                                            text = f"<s>{text}</s>"

                                    paragraph_html += text
                                elif text_node.get("type") == "hardBreak":
                                    paragraph_html += "<br/>"
                                elif text_node.get("type") == "mention":
                                    user = text_node.get("attrs", {}).get("text", "")
                                    paragraph_html += f"<span class='mention'>@{user}</span>"
                                elif text_node.get("type") == "emoji":
                                    emoji = text_node.get("attrs", {}).get("shortName", "")
                                    paragraph_html += f":{emoji}:"
                                elif text_node.get("type") == "inlineCard":
                                    url = text_node.get("attrs", {}).get("url", "")
                                    paragraph_html += f"<a href='{url}' class='inline-card'>{url}</a>"

                            paragraph_html += "</p>"
                            html_parts.append(paragraph_html)

                        elif content_type == "heading":
                            level = content.get("attrs", {}).get("level", 1)
                            heading_html = f"<h{level}>"
                            for text_node in content.get("content", []):
                                if text_node.get("type") == "text":
                                    heading_html += text_node.get("text", "")
                            heading_html += f"</h{level}>"
                            html_parts.append(heading_html)

                        elif content_type == "bulletList":
                            list_html = "<ul>"
                            for list_item in content.get("content", []):
                                if list_item.get("type") == "listItem":
                                    list_html += "<li>"
                                    for item_content in list_item.get("content", []):
                                        if item_content.get("type") == "paragraph":
                                            for text_node in item_content.get("content", []):
                                                if text_node.get("type") == "text":
                                                    list_html += text_node.get("text", "")
                                    list_html += "</li>"
                            list_html += "</ul>"
                            html_parts.append(list_html)

                        elif content_type == "orderedList":
                            list_html = "<ol>"
                            for list_item in content.get("content", []):
                                if list_item.get("type") == "listItem":
                                    list_html += "<li>"
                                    for item_content in list_item.get("content", []):
                                        if item_content.get("type") == "paragraph":
                                            for text_node in item_content.get("content", []):
                                                if text_node.get("type") == "text":
                                                    list_html += text_node.get("text", "")
                                    list_html += "</li>"
                            list_html += "</ol>"
                            html_parts.append(list_html)

                        elif content_type == "codeBlock":
                            language = content.get("attrs", {}).get("language", "")
                            code_html = f"<pre><code class='language-{language}'>"
                            for text_node in content.get("content", []):
                                if text_node.get("type") == "text":
                                    code_html += text_node.get("text", "")
                            code_html += "</code></pre>"
                            html_parts.append(code_html)

                        elif content_type == "blockquote":
                            quote_html = "<blockquote>"
                            for quote_content in content.get("content", []):
                                if quote_content.get("type") == "paragraph":
                                    for text_node in quote_content.get("content", []):
                                        if text_node.get("type") == "text":
                                            quote_html += text_node.get("text", "")
                            quote_html += "</blockquote>"
                            html_parts.append(quote_html)

                        elif content_type == "panel":
                            panel_type = content.get("attrs", {}).get("panelType", "info")
                            panel_html = f"<div class='panel panel-{panel_type}'>"
                            for panel_content in content.get("content", []):
                                if panel_content.get("type") == "paragraph":
                                    for text_node in panel_content.get("content", []):
                                        if text_node.get("type") == "text":
                                            panel_html += text_node.get("text", "")
                            panel_html += "</div>"
                            html_parts.append(panel_html)

                        elif content_type == "table":
                            table_html = "<table border='1'>"
                            for row in content.get("content", []):
                                if row.get("type") == "tableRow":
                                    table_html += "<tr>"
                                    for cell in row.get("content", []):
                                        if cell.get("type") == "tableCell":
                                            table_html += "<td>"
                                            for cell_content in cell.get("content", []):
                                                if cell_content.get("type") == "paragraph":
                                                    for text_node in cell_content.get("content", []):
                                                        if text_node.get("type") == "text":
                                                            table_html += text_node.get("text", "")
                                            table_html += "</td>"
                                    table_html += "</tr>"
                            table_html += "</table>"
                            html_parts.append(table_html)

                return "".join(html_parts) if html_parts else None

            return f"<p>{str(adf_data)}</p>"

        except Exception as e:
            log.error(f"Error converting ADF to HTML: {str(e)}")
            return None

    @staticmethod
    def to_domain(api_response: JiraIssueAPIGetResponseDTO) -> JiraIssueModel:
        try:
            fields = api_response.fields
            now = datetime.now(timezone.utc)

            # Đảm bảo truy cập các field từ fields object
            summary = fields.summary if hasattr(fields, 'summary') else ""
            description: Optional[str] = api_response.rendered_fields.get(
                "description", None) if api_response.rendered_fields else None
            if description is None:
                description = JiraIssueMapper._convert_adf_to_html(fields.description)

            # Map user data
            assignee = None
            assignee_id = None
            reporter_id = None

            project_key = fields.project.key if hasattr(fields, 'project') and fields.project else ""

            if hasattr(fields, 'assignee') and fields.assignee:
                assignee_id = fields.assignee.account_id
                assignee = JiraIssueMapper._map_user(fields.assignee)

            if hasattr(fields, 'reporter') and fields.reporter:
                reporter_id = fields.reporter.account_id

            # Map sprints
            sprints: List[JiraSprintModel] = []
            if hasattr(fields, 'customfield_10020') and fields.customfield_10020:
                sprints = JiraIssueMapper._map_sprints(fields.customfield_10020, project_key)

            # Create link URL
            # project_key = api_response.key.split("-")[0]
            board_id = sprints[0].board_id if sprints else None
            link_url: Optional[str] = None
            if board_id:
                link_url = f"{settings.JIRA_DASHBOARD_URL}/jira/software/projects/{project_key}/boards/{board_id}?selectedIssue={api_response.key}"

            return JiraIssueModel(
                jira_issue_id=api_response.id,
                key=api_response.key,
                project_key=project_key,
                summary=summary,
                description=description,
                type=JiraIssueType(fields.issuetype.name) if hasattr(fields, 'issuetype') else JiraIssueType.TASK,
                status=JiraIssueStatus(fields.status.name) if hasattr(fields, 'status') else JiraIssueStatus.TO_DO,
                assignee_id=assignee_id,
                priority=fields.priority.name if hasattr(fields, 'priority') else None,
                reporter_id=reporter_id,
                estimate_point=fields.customfield_10016 or 0,
                actual_point=fields.customfield_10017 or 0,
                created_at=fields.created if hasattr(fields, 'created') else now,
                updated_at=fields.updated if hasattr(fields, 'updated') else now,
                sprints=sprints,
                link_url=link_url,
                last_synced_at=now,
                assignee=assignee
            )
        except Exception as e:
            log.error(f"Error mapping API response to domain issue: {str(e)}")
            raise

    @staticmethod
    def _map_sprint(api_sprint: JiraSprintAPIGetResponseDTO, project_key: str) -> Optional[JiraSprintModel]:
        try:
            now = datetime.now(timezone.utc)
            return JiraSprintModel(
                jira_sprint_id=api_sprint.id,
                name=api_sprint.name,
                state=api_sprint.state,
                start_date=JiraIssueMapper._parse_datetime(api_sprint.start_date),
                end_date=JiraIssueMapper._parse_datetime(api_sprint.end_date),
                complete_date=JiraIssueMapper._parse_datetime(api_sprint.complete_date),
                goal=api_sprint.goal,
                board_id=api_sprint.origin_board_id or api_sprint.board_id,
                created_at=now,
                project_key=project_key
            )
        except Exception as e:
            log.error(f"Error mapping sprint: {str(e)}")
            return None

    @staticmethod
    def _map_sprints(api_sprints: List[JiraSprintAPIGetResponseDTO], project_key: str) -> List[JiraSprintModel]:
        if not api_sprints:
            return []
        return [JiraIssueMapper._map_sprint(sprint, project_key) for sprint in api_sprints if sprint]

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from Jira"""
        if dt_str is None:
            return None
        if dt_str.endswith('Z'):
            dt_str = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(dt_str)
