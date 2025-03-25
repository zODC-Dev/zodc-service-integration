import asyncio
from contextlib import asynccontextmanager
import time
from typing import Dict, List, Optional, Set

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.database import AsyncSessionLocal
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository
from src.infrastructure.repositories.sqlalchemy_sync_log_repository import SQLAlchemySyncLogRepository
from src.infrastructure.services.jira_webhook_service import JiraWebhookService


class JiraWebhookQueueService:
    """Service xử lý hàng đợi webhook từ Jira với isolate sessions"""

    def __init__(
        self,
        jira_issue_api_service: IJiraIssueAPIService,
        webhook_handlers: List[JiraWebhookHandler]
    ):
        # Dùng PriorityQueue để đảm bảo xử lý theo thứ tự ưu tiên
        self.queues: Dict[str, asyncio.PriorityQueue] = {}
        self.processing: Set[str] = set()
        self.last_created_webhooks: Dict[str, float] = {}

        # Theo dõi tất cả task đang chạy
        self.running_tasks: Set[asyncio.Task] = set()

        # Số lần retry tối đa cho webhook update khi không tìm thấy issue
        self.max_retries = 3

        # Queue cho các webhook cần retry
        self.retry_queue: asyncio.Queue = asyncio.Queue()
        self.RETRY_INTERVAL = 1  # 1s

        # Bắt đầu worker xử lý retry
        self._start_retry_worker()

        # Thêm các thuộc tính mới
        self.jira_issue_api_service = jira_issue_api_service
        self.DEBOUNCE_TIME = 0.5  # 500ms để gom nhóm các webhooks
        self.webhook_handlers = webhook_handlers

    def _start_retry_worker(self) -> None:
        """Khởi động worker xử lý retry queue"""
        retry_task = asyncio.create_task(self._process_retry_queue())
        self._track_task(retry_task)

    def _track_task(self, task: asyncio.Task) -> None:
        """Theo dõi task để đảm bảo xử lý lỗi và dọn dẹp"""
        self.running_tasks.add(task)
        task.add_done_callback(lambda t: self.running_tasks.remove(t))

        # Xử lý exception nếu có
        task.add_done_callback(self._handle_task_exception)

    def _handle_task_exception(self, task: asyncio.Task) -> None:
        """Xử lý exception từ task nếu có"""
        if not task.cancelled() and task.exception():
            log.error(f"Task failed with exception: {task.exception()}")

    async def add_webhook_to_queue(self, webhook_data: JiraWebhookResponseDTO) -> bool:
        """Thêm webhook vào hàng đợi và xử lý theo thứ tự ưu tiên"""
        try:
            issue_id = webhook_data.issue.id

            # Tạo queue cho issue nếu chưa có
            if issue_id not in self.queues:
                self.queues[issue_id] = asyncio.PriorityQueue()
                log.info(f"Created new priority queue for issue {issue_id}")

            # Tính toán độ ưu tiên (số thấp = ưu tiên cao)
            priority = self._calculate_priority(webhook_data)

            # Thêm timestamp để giữ thứ tự FIFO khi cùng ưu tiên
            timestamp = time.time()

            # Thêm webhook vào queue với (ưu tiên, timestamp, webhook)
            await self.queues[issue_id].put((priority, timestamp, webhook_data))

            log.info(
                f"Added webhook event {webhook_data.webhook_event} for issue {issue_id} to queue with priority {priority}")

            # Bắt đầu xử lý queue nếu chưa có worker nào đang xử lý
            if issue_id not in self.processing:
                process_task = asyncio.create_task(self._process_issue_queue(issue_id))
                self._track_task(process_task)

            return True
        except Exception as e:
            log.error(f"Error adding webhook to queue: {str(e)}")
            return False

    def _calculate_priority(self, webhook_data: JiraWebhookResponseDTO) -> int:
        """Tính toán độ ưu tiên của webhook (thấp = ưu tiên cao)"""
        event = webhook_data.webhook_event

        # Lưu thời gian của webhook created
        if event == JiraWebhookEvent.ISSUE_CREATED:
            self.last_created_webhooks[webhook_data.issue.id] = time.time()
            return 0  # Ưu tiên cao nhất
        elif event == JiraWebhookEvent.ISSUE_UPDATED:
            return 1
        elif event == JiraWebhookEvent.ISSUE_DELETED:
            return 2
        else:
            return 3

    async def _process_issue_queue(self, issue_id: str) -> None:
        """Process issue queue with appropriate handler"""
        self.processing.add(issue_id)

        try:
            queue = self.queues[issue_id]
            await asyncio.sleep(self.DEBOUNCE_TIME)

            webhooks = []
            highest_priority = float('inf')

            while not queue.empty():
                priority, _, webhook = await queue.get()
                webhooks.append(webhook)
                highest_priority = min(highest_priority, priority)
                queue.task_done()

            if not webhooks:
                return

            handler = await self._get_handler(webhooks[-1].webhook_event)
            if not handler:
                log.error(f"No handler found for event {webhooks[-1].webhook_event}")
                return

            try:
                result = await handler.handle(webhooks[-1])
                if result and "error" in result:
                    await self._handle_retry(webhooks, highest_priority)
            except Exception as e:
                log.error(f"Error processing webhooks: {str(e)}")
                await self._handle_retry(webhooks, highest_priority)

        finally:
            self.processing.remove(issue_id)
            if issue_id in self.queues and self.queues[issue_id].empty():
                del self.queues[issue_id]

    async def _get_handler(self, webhook_event: str) -> Optional[JiraWebhookHandler]:
        """Get appropriate handler for webhook event"""
        for handler in self.webhook_handlers:
            if await handler.can_handle(webhook_event):
                return handler
        return None

    async def _get_latest_issue_data(self, issue_id: str) -> Optional[JiraIssueModel]:
        """Lấy data mới nhất của issue từ Jira API"""
        try:
            # Lấy issue từ Jira API
            issue = await self.jira_issue_api_service.get_issue_with_system_user(issue_id)
            return issue
        except Exception as e:
            log.error(f"Error fetching issue {issue_id} from Jira API: {str(e)}")
            return None

    # async def _update_database_with_issue_data(
    #     self,
    #     webhook_service: JiraWebhookService,
    #     issue_data: JiraIssueModel,
    #     original_webhook: JiraWebhookResponseDTO
    # ):
    #     """Cập nhật database với data mới nhất"""
    #     # Kiểm tra issue có tồn tại trong DB không
    #     existing_issue = await webhook_service.jira_issue_repository.get_by_jira_issue_id(issue_data.jira_issue_id)

    #     if not existing_issue:
    #         # Tạo mới nếu chưa tồn tại
    #         create_dto = JiraIssueConverter._convert_to_create_dto(issue_data)
    #         await webhook_service.jira_issue_repository.create(create_dto)
    #     else:
    #         # Cập nhật nếu đã tồn tại
    #         update_dto = JiraIssueConverter._convert_to_update_dto(issue_data)
    #         await webhook_service.jira_issue_repository.update(issue_data.jira_issue_id, update_dto)

    #     # Log webhook sync
    #     await webhook_service.sync_log_repository.create_sync_log(
    #         SyncLogDBCreateDTO(
    #             entity_type=EntityType.ISSUE,
    #             entity_id=issue_data.jira_issue_id,
    #             operation=OperationType.SYNC,
    #             request_payload=original_webhook.to_json_serializable(),
    #             response_status=200,
    #             response_body={},
    #             source=SourceType.WEBHOOK,
    #             sender=None
    #         )
    #     )

    async def _maybe_add_to_retry_queue(self, webhook: JiraWebhookResponseDTO, retry_count: int) -> None:
        """Đưa một webhook vào retry queue nếu chưa vượt quá số lần retry tối đa"""
        if retry_count < self.max_retries:
            # Tăng thời gian chờ theo số lần retry (exponential backoff)
            delay = 2 ** retry_count  # 1s, 2s, 4s, ...
            process_time = time.time() + delay

            log.info(
                f"Scheduling retry #{retry_count+1} for {webhook.webhook_event} "
                f"on issue {webhook.issue.id} after {delay}s"
            )

            # Đặt vào retry queue với (thời gian xử lý, webhook, số lần retry)
            await self.retry_queue.put((process_time, webhook, retry_count + 1))
        else:
            log.warning(
                f"Abandoning {webhook.webhook_event} for issue {webhook.issue.id} "
                f"after {retry_count} retries"
            )

    async def _process_retry_queue(self):
        """Process the retry queue"""
        while True:
            try:
                # Kiểm tra nếu queue rỗng
                if self.retry_queue.empty():
                    await asyncio.sleep(self.RETRY_INTERVAL)
                    continue

                # Lấy webhook từ queue
                process_time, webhook_data, retry_count = await self.retry_queue.get()
                current_time = time.time()

                # Kiểm tra xem đã đến thời gian xử lý chưa
                if current_time < process_time:
                    # Nếu chưa đến thời gian, đưa lại vào queue và đợi
                    await self.retry_queue.put((process_time, webhook_data, retry_count))
                    await asyncio.sleep(min(process_time - current_time, self.RETRY_INTERVAL))
                    continue

                try:
                    # Xử lý webhook với session mới
                    async with self._get_webhook_service() as webhook_service:
                        result = await webhook_service.handle_webhook(webhook_data)

                        if result and "error" in result:
                            error_msg = result.get("error", "Unknown error")
                            if "Issue not found" in error_msg:
                                # Nếu vẫn chưa tìm thấy issue và chưa vượt quá số lần retry
                                await self._maybe_add_to_retry_queue(webhook_data, retry_count)
                            else:
                                log.error(f"Failed to process webhook after {retry_count} retries: {error_msg}")
                        else:
                            log.info(
                                f"Successfully processed webhook for issue {webhook_data.issue.id} on retry #{retry_count}")

                except Exception as e:
                    log.error(f"Error processing webhook in retry queue: {str(e)}")
                    # Thử lại nếu chưa vượt quá số lần retry
                    await self._maybe_add_to_retry_queue(webhook_data, retry_count)

                finally:
                    # Đánh dấu task này đã được xử lý
                    self.retry_queue.task_done()

            except Exception as e:
                log.error(f"Error in retry queue processor: {str(e)}")
                await asyncio.sleep(self.RETRY_INTERVAL)

    @asynccontextmanager
    async def _get_webhook_service(self):
        """Tạo webhook service mới với session database mới"""
        async with AsyncSessionLocal() as session:
            # Tạo repositories với session mới
            issue_repo = SQLAlchemyJiraIssueRepository(session)
            sync_log_repo = SQLAlchemySyncLogRepository(session)

            # Tạo webhook service
            webhook_service = JiraWebhookService(issue_repo, sync_log_repo, self.jira_issue_api_service)

            try:
                yield webhook_service
                # Session sẽ được commit khi kết thúc context nếu không có exception
            except Exception as e:
                # Session sẽ được rollback tự động bởi get_db_session khi có exception
                log.error(f"Error in webhook service: {str(e)}")
                raise
            finally:
                await session.close()

    async def _process_webhook_with_new_session(self, webhook_data: JiraWebhookResponseDTO) -> bool:
        """Xử lý webhook với một session database mới và độc lập"""
        try:
            # Sử dụng context manager để đảm bảo session được đóng đúng cách
            async with self._get_webhook_service() as webhook_service:
                # Xử lý webhook
                result = await webhook_service.handle_webhook(webhook_data)

                # Kiểm tra kết quả
                if result and "error" in result:
                    error_msg = result.get("error", "Unknown error")
                    if "Issue not found" in error_msg and webhook_data.webhook_event == JiraWebhookEvent.ISSUE_UPDATED:
                        # Đây là lỗi có thể retry
                        log.warning(
                            f"Issue not found for update webhook (issue_id={webhook_data.issue.id}), will retry")
                        return False
                    else:
                        # Lỗi khác
                        log.error(f"Error processing webhook: {error_msg}")
                        return False

                log.info(f"Successfully processed {webhook_data.webhook_event} for issue {webhook_data.issue.id}")
                return True

        except Exception as e:
            log.error(f"Exception processing webhook: {str(e)}")
            return False

    async def _handle_retry(self, webhooks: List[JiraWebhookResponseDTO], highest_priority: int) -> None:
        """Xử lý retry cho các webhooks thất bại"""
        for webhook in webhooks:
            # Chỉ retry cho các webhook update, vì create và delete không cần retry
            if webhook.webhook_event == JiraWebhookEvent.ISSUE_UPDATED:
                log.info(f"Adding webhook for issue {webhook.issue.id} to retry queue")
                await self._maybe_add_to_retry_queue(webhook, 0)
            else:
                log.warning(
                    f"Skipping retry for {webhook.webhook_event} webhook on issue {webhook.issue.id}"
                )

        # Nếu có webhook create trong danh sách, log cảnh báo
        if any(w.webhook_event == JiraWebhookEvent.ISSUE_CREATED for w in webhooks):
            log.warning(
                f"Failed to process create webhook for issue {webhooks[0].issue.id}. "
                "This might cause issues with subsequent updates."
            )

    # async def _handle_delete_webhook(self, webhook_service: JiraWebhookService, webhooks: List[JiraWebhookResponseDTO]) -> None:
    #     """Handle delete webhooks for an issue"""
    #     try:
    #         # Get the issue ID from the first webhook
    #         issue_id = webhooks[0].issue.id

    #         # Check if the issue exists in the database
    #         existing_issue = await webhook_service.jira_issue_repository.get_by_jira_issue_id(issue_id)

    #         if existing_issue:
    #             # Mark the issue as deleted in the database
    #             await webhook_service.jira_issue_repository.update(
    #                 issue_id,
    #                 JiraIssueDBUpdateDTO(is_deleted=True)
    #             )

    #             # Log the delete operation
    #             await webhook_service.sync_log_repository.create_sync_log(
    #                 SyncLogDBCreateDTO(
    #                     entity_type=EntityType.ISSUE,
    #                     entity_id=issue_id,
    #                     operation=OperationType.DELETE,
    #                     request_payload=webhooks[0].to_json_serializable(),
    #                     response_status=200,
    #                     response_body={},
    #                     source=SourceType.WEBHOOK,
    #                     sender=None
    #                 )
    #             )

    #             log.info(f"Successfully marked issue {issue_id} as deleted")
    #         else:
    #             log.warning(f"Attempted to delete non-existent issue {issue_id}")

    #     except Exception as e:
    #         log.error(f"Error handling delete webhook: {str(e)}")
    #         raise
