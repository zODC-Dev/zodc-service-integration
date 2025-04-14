import asyncio
from contextlib import asynccontextmanager
import time
from typing import Any, Dict, List, Optional, Set, Union

from src.app.services.jira_issue_history_service import JiraIssueHistoryApplicationService
from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.database import AsyncSessionLocal
from src.configs.logger import log
from src.configs.redis import get_redis_client
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.models.jira.webhooks.jira_webhook import (
    BaseJiraWebhookDTO,
)
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.infrastructure.repositories.sqlalchemy_jira_issue_history_repository import (
    SQLAlchemyJiraIssueHistoryRepository,
)
from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository
from src.infrastructure.repositories.sqlalchemy_jira_project_repository import SQLAlchemyJiraProjectRepository
from src.infrastructure.repositories.sqlalchemy_jira_sprint_repository import SQLAlchemyJiraSprintRepository
from src.infrastructure.repositories.sqlalchemy_sync_log_repository import SQLAlchemySyncLogRepository
from src.infrastructure.services.jira_issue_history_database_service import JiraIssueHistoryDatabaseService
from src.infrastructure.services.jira_sprint_database_service import JiraSprintDatabaseService
from src.infrastructure.services.jira_webhook_service import JiraWebhookService
from src.infrastructure.services.redis_service import RedisService


class JiraWebhookQueueService:
    """Service xử lý hàng đợi webhook từ Jira với isolate sessions"""

    def __init__(
        self,
        jira_issue_api_service: IJiraIssueAPIService,
        jira_sprint_api_service: IJiraSprintAPIService,
        jira_issue_history_service: IJiraIssueHistoryDatabaseService,
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
        self.jira_sprint_api_service = jira_sprint_api_service
        self.DEBOUNCE_TIME = 1.0  # seconds
        self.webhook_handlers = webhook_handlers
        self.retry_counts: Dict[str, int] = {}
        self.RETRY_DELAYS = [5, 30, 300]  # Retry delays in seconds: 5s, 30s, 5min
        self.jira_issue_history_service = jira_issue_history_service

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

    async def add_webhook_to_queue(self, webhook_data: Union[Dict[str, Any], BaseJiraWebhookDTO]) -> bool:
        """Thêm webhook vào hàng đợi và xử lý theo thứ tự ưu tiên"""
        try:
            # Kiểm tra kiểu dữ liệu và phân tích nếu cần
            parsed_webhook = None

            # Nếu dữ liệu là dictionary (dữ liệu thô), thử phân tích
            if isinstance(webhook_data, dict):
                log.debug("Received raw webhook data, parsing...")
                try:
                    parsed_webhook = BaseJiraWebhookDTO.parse_webhook(webhook_data)
                    log.debug(f"Successfully parsed raw webhook as {type(parsed_webhook).__name__}")
                except Exception as e:
                    log.error(f"Failed to parse webhook: {str(e)}")
                    return False
            else:
                # Đã là DTO, sử dụng trực tiếp
                parsed_webhook = webhook_data

            # Kiểm tra webhook có hợp lệ không
            if not parsed_webhook or not hasattr(parsed_webhook, 'webhook_event'):
                log.error("Invalid webhook: missing webhook_event")
                return False

            # Xác định entity ID (issue, sprint hoặc user)
            entity_id = None
            entity_type = None

            # Kiểm tra nếu là issue webhook
            if hasattr(parsed_webhook, 'issue') and parsed_webhook.issue and hasattr(parsed_webhook.issue, 'id'):
                entity_id = str(parsed_webhook.issue.id)
                entity_type = 'issue'
            # Kiểm tra nếu là sprint webhook
            elif hasattr(parsed_webhook, 'sprint') and parsed_webhook.sprint and hasattr(parsed_webhook.sprint, 'id'):
                entity_id = str(parsed_webhook.sprint.id)
                entity_type = 'sprint'
            # Kiểm tra nếu là user webhook
            elif hasattr(parsed_webhook, 'user') and parsed_webhook.user and hasattr(parsed_webhook.user, 'account_id'):
                entity_id = parsed_webhook.user.account_id
                entity_type = 'user'
            else:
                log.error(f"Cannot determine entity ID from webhook event {parsed_webhook.webhook_event}")
                return False

            log.info(f"Determined entity type: {entity_type}, entity ID: {entity_id}")

            # Tính độ ưu tiên cho webhook này
            priority = self._calculate_priority(parsed_webhook)
            log.info(f"Calculated priority {priority} for webhook {parsed_webhook.webhook_event}")

            # Lấy hoặc tạo queue cho entity này
            if entity_id not in self.queues:
                self.queues[entity_id] = asyncio.PriorityQueue()

            # Thêm webhook vào hàng đợi
            await self.queues[entity_id].put((priority, time.time(), parsed_webhook))
            log.debug(f"Added webhook to queue for entity {entity_id}")

            # Khởi động worker mới nếu entity này chưa đang được xử lý
            if entity_id not in self.processing:
                entity_task = asyncio.create_task(self._process_entity_queue(entity_id))
                self._track_task(entity_task)
                log.debug(f"Started processing task for entity {entity_id}")

            return True

        except Exception as e:
            log.error(f"Error adding webhook to queue: {str(e)}")
            return False

    def _calculate_priority(self, webhook_data: BaseJiraWebhookDTO) -> int:
        """Tính toán độ ưu tiên của webhook (thấp = ưu tiên cao)"""
        # Sử dụng normalized_event để đảm bảo nhất quán
        event = webhook_data.normalized_event

        # Ưu tiên cho issue events
        if event == JiraWebhookEvent.ISSUE_CREATED:
            if hasattr(webhook_data, 'issue') and webhook_data.issue:
                self.last_created_webhooks[webhook_data.issue.id] = time.time()
            return 0  # Ưu tiên cao nhất
        elif event == JiraWebhookEvent.ISSUE_UPDATED:
            return 1
        elif event == JiraWebhookEvent.ISSUE_DELETED:
            return 2

        # Ưu tiên cho sprint events
        elif event in [JiraWebhookEvent.SPRINT_CREATED, JiraWebhookEvent.SPRINT_STARTED]:
            return 1  # Ưu tiên cao
        elif event in [JiraWebhookEvent.SPRINT_UPDATED, JiraWebhookEvent.SPRINT_CLOSED]:
            return 2

        # Ưu tiên cho user events
        elif event == JiraWebhookEvent.USER_CREATED:
            return 1  # Ưu tiên cao cho việc tạo user
        elif event == JiraWebhookEvent.USER_UPDATED:
            return 2
        elif event == JiraWebhookEvent.USER_DELETED:
            return 3  # Ưu tiên thấp cho delete

        # Default priority
        else:
            return 5

    async def _process_entity_queue(self, entity_id: str) -> None:
        """Process entity queue with appropriate handler"""
        self.processing.add(entity_id)

        try:
            queue = self.queues[entity_id]
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

            # Get the last webhook
            last_webhook = webhooks[-1]

            # Tìm handler phù hợp
            handler = await self._get_handler(last_webhook.normalized_event)

            if not handler:
                log.error(f"No handler found for event {last_webhook.webhook_event}")
                await self._handle_retry(webhooks, highest_priority)
                return

            try:
                # Xử lý với session mới
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        result = await handler.process(last_webhook)
                        if result and "error" in result:
                            log.warning(f"Error processing webhook: {result['error']}")
                            await self._handle_retry(webhooks, highest_priority)
            except Exception as e:
                log.error(f"Error processing webhooks: {str(e)}")
                await self._handle_retry(webhooks, highest_priority)

        finally:
            self.processing.remove(entity_id)
            if entity_id in self.queues and self.queues[entity_id].empty():
                del self.queues[entity_id]

    async def _get_handler(self, webhook_event: str) -> Optional[JiraWebhookHandler]:
        """Get appropriate handler for webhook event"""
        # Dùng đúng tên event đã được chuẩn hóa
        log.info(f"Finding handler for event: {webhook_event}")

        for handler in self.webhook_handlers:
            if await handler.can_handle(webhook_event):
                log.info(f"Found handler {handler.__class__.__name__} for event {webhook_event}")
                return handler

        log.warning(f"No handler found for event {webhook_event}")
        return None

    async def _get_latest_issue_data(self, issue_id: str) -> Optional[JiraIssueModel]:
        """Lấy data mới nhất của issue từ Jira API"""
        try:
            # Lấy issue từ Jira API
            issue = await self.jira_issue_api_service.get_issue_with_admin_auth(issue_id)
            return issue
        except Exception as e:
            log.error(f"Error fetching issue {issue_id} from Jira API: {str(e)}")
            return None

    async def _process_retry_queue(self) -> None:
        """Process the retry queue periodically"""
        while True:
            try:
                if not self.retry_queue.empty():
                    priority, timestamp, webhook = await self.retry_queue.get()

                    # Get retry count for this webhook
                    webhook_key = self._get_webhook_key(webhook)
                    retry_count = self.retry_counts.get(webhook_key, 0)

                    if retry_count < self.max_retries:
                        try:
                            # Find appropriate handler
                            handler = await self._get_handler(webhook.normalized_event)
                            if handler:
                                result = await handler.process(webhook)
                                if result and "error" not in result:
                                    # Success - clear retry count
                                    self.retry_counts.pop(webhook_key, None)
                                    log.info(
                                        f"Successfully processed webhook {webhook_key} on retry #{retry_count + 1}")
                                else:
                                    # Failed - schedule next retry
                                    self.retry_counts[webhook_key] = retry_count + 1
                                    delay = self.RETRY_DELAYS[min(retry_count, len(self.RETRY_DELAYS) - 1)]
                                    await asyncio.sleep(delay)
                                    await self.retry_queue.put((priority + 1, time.time(), webhook))
                                    log.warning(
                                        f"Retry #{retry_count + 1} failed for {webhook_key}, scheduling next retry in {delay}s")
                            else:
                                log.error(f"No handler found for webhook {webhook_key}")
                                self.retry_counts[webhook_key] = retry_count + 1
                        except Exception as e:
                            log.error(f"Error processing webhook {webhook_key}: {str(e)}")
                            # Schedule next retry
                            self.retry_counts[webhook_key] = retry_count + 1
                            if retry_count < self.max_retries - 1:
                                delay = self.RETRY_DELAYS[retry_count]
                                await asyncio.sleep(delay)
                                await self.retry_queue.put((priority + 1, time.time(), webhook))
                                log.warning(f"Scheduled retry #{retry_count + 2} for {webhook_key} in {delay}s")
                    else:
                        log.error(f"Failed to process webhook after {self.max_retries} retries: {webhook}")
                        # Clear retry count for failed webhook
                        self.retry_counts.pop(webhook_key, None)

                    self.retry_queue.task_done()

                # Sleep before checking queue again
                await asyncio.sleep(self.RETRY_INTERVAL)

            except Exception as e:
                log.error(f"Error in retry queue processing: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying

    def _get_webhook_key(self, webhook: BaseJiraWebhookDTO) -> str:
        """Generate a unique key for webhook to track retry counts"""
        try:
            components = []

            # Add basic webhook info
            if hasattr(webhook, 'webhook_event'):
                components.append(str(webhook.webhook_event))

            if hasattr(webhook, 'timestamp'):
                components.append(str(webhook.timestamp))

            # Add entity specific info
            if hasattr(webhook, 'issue') and webhook.issue and webhook.issue.id:
                components.append(f"issue_{webhook.issue.id}")
            elif hasattr(webhook, 'sprint') and webhook.sprint and webhook.sprint.id:
                components.append(f"sprint_{webhook.sprint.id}")

            # Fallback if no components
            if not components:
                components.append(str(time.time()))

            return "_".join(components)
        except Exception as e:
            log.error(f"Error generating webhook key: {str(e)}")
            # Fallback to timestamp if error
            return str(time.time())

    async def _handle_retry(self, webhooks: List[BaseJiraWebhookDTO], priority: float) -> None:
        """Handle retry with fixed delays"""
        for webhook in webhooks:
            try:
                webhook_key = self._get_webhook_key(webhook)
                retry_count = self.retry_counts.get(webhook_key, 0)

                if retry_count < self.max_retries:
                    # Use predefined delay
                    delay = self.RETRY_DELAYS[min(retry_count, len(self.RETRY_DELAYS) - 1)]

                    # Increment retry count
                    self.retry_counts[webhook_key] = retry_count + 1

                    # Add to retry queue with increased priority
                    new_priority = priority + retry_count + 1

                    # Schedule retry after delay
                    await asyncio.sleep(delay)
                    await self.retry_queue.put((new_priority, time.time(), webhook))

                    log.info(f"Scheduled retry #{retry_count + 1} for webhook {webhook_key} after {delay}s")
                else:
                    log.error(f"Failed to process webhook {webhook_key} after {self.max_retries} retries")
                    # Clear retry count
                    self.retry_counts.pop(webhook_key, None)
            except Exception as e:
                log.error(f"Error handling retry for webhook: {str(e)}")

    @asynccontextmanager
    async def _get_webhook_service(self):
        """Tạo webhook service mới với session database mới"""
        async with AsyncSessionLocal() as session:
            # Tạo repositories với session mới
            issue_repo = SQLAlchemyJiraIssueRepository(session)
            sync_log_repo = SQLAlchemySyncLogRepository(session)
            sprint_repo = SQLAlchemyJiraSprintRepository(session)
            sprint_database_service = JiraSprintDatabaseService(sprint_repo)
            issue_history_repo = SQLAlchemyJiraIssueHistoryRepository(session)
            issue_history_db_service = JiraIssueHistoryDatabaseService(issue_history_repo)
            issue_history_sync_service = JiraIssueHistoryApplicationService(
                self.jira_issue_api_service, issue_history_db_service)
            jira_project_repository = SQLAlchemyJiraProjectRepository(session)
            redis_client = await get_redis_client()
            redis_service = RedisService(redis_client)
            # Tạo webhook service
            webhook_service = JiraWebhookService(
                issue_repo, sync_log_repo, self.jira_issue_api_service, self.jira_sprint_api_service, sprint_database_service, issue_history_sync_service, jira_project_repository, redis_service)

            try:
                yield webhook_service
                # Session sẽ được commit khi kết thúc context nếu không có exception
            except Exception as e:
                # Session sẽ được rollback tự động bởi get_db_session khi có exception
                log.error(f"Error in webhook service: {str(e)}")
                raise
            finally:
                await session.close()

    async def _process_webhook_with_new_session(self, webhook_data: BaseJiraWebhookDTO) -> bool:
        """Xử lý webhook với một session database mới và độc lập"""
        try:
            # Sử dụng context manager để đảm bảo session được đóng đúng cách
            async with self._get_webhook_service() as webhook_service:
                # Xử lý webhook
                result = await webhook_service.handle_webhook(webhook_data)

                # Kiểm tra kết quả
                if result and "error" in result:
                    return False

                log.info(f"Successfully processed {webhook_data.webhook_event} for issue {webhook_data}")
                return True

        except Exception as e:
            log.error(f"Exception processing webhook: {str(e)}")
            return False

    # Cleanup method để xóa các retry counts cũ
    async def cleanup_retry_counts(self) -> None:
        """Clean up old retry counts periodically"""
        while True:
            await asyncio.sleep(3600)  # Run every hour
            current_webhooks = set()

            # Collect all current webhook keys
            for queue in self.queues.values():
                while not queue.empty():
                    _, _, webhook = queue.get_nowait()
                    current_webhooks.add(self._get_webhook_key(webhook))

            # Remove retry counts for webhooks that are no longer in any queue
            keys_to_remove = []
            for webhook_key in self.retry_counts:
                if webhook_key not in current_webhooks:
                    keys_to_remove.append(webhook_key)

            for key in keys_to_remove:
                self.retry_counts.pop(key, None)
