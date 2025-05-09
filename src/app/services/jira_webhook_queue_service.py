import asyncio
from contextlib import asynccontextmanager
import time
from typing import Dict, List, Optional, Set, Tuple

from src.app.dependencies.container import DependencyContainer
from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.database import AsyncSessionManager
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.models.jira.webhooks.jira_webhook import (
    BaseJiraWebhookDTO,
)
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.infrastructure.services.jira_webhook_service import JiraWebhookService


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
        self.queues: Dict[str, asyncio.PriorityQueue[Tuple[float, float, BaseJiraWebhookDTO]]] = {}
        self.processing: Set[str] = set()
        self.last_created_webhooks: Dict[str, float] = {}

        # Theo dõi tất cả task đang chạy
        self.running_tasks: Set[asyncio.Task[None]] = set()

        # Số lần retry tối đa cho webhook update khi không tìm thấy issue
        self.max_retries = 3

        # Queue cho các webhook cần retry
        self.retry_queue: asyncio.Queue[Tuple[float, float, BaseJiraWebhookDTO]] = asyncio.Queue()
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

    def _track_task(self, task: asyncio.Task[None]) -> None:
        """Theo dõi task để đảm bảo xử lý lỗi và dọn dẹp"""
        self.running_tasks.add(task)
        task.add_done_callback(lambda t: self.running_tasks.remove(t))

        # Xử lý exception nếu có
        task.add_done_callback(self._handle_task_exception)

    def _handle_task_exception(self, task: asyncio.Task[None]) -> None:
        """Xử lý exception từ task nếu có"""
        if not task.cancelled() and task.exception():
            log.error(f"Task failed with exception: {task.exception()}")

    async def add_webhook_to_queue(self, webhook_data: BaseJiraWebhookDTO) -> bool:
        """Thêm webhook vào hàng đợi và xử lý theo thứ tự ưu tiên"""
        try:
            # Đã là DTO, sử dụng trực tiếp
            parsed_webhook = webhook_data

            # Kiểm tra webhook có hợp lệ không
            if not hasattr(parsed_webhook, 'webhook_event'):
                log.error("Invalid webhook: missing webhook_event")
                return False

            # Xác định entity ID (issue, sprint hoặc user)
            entity_id: Optional[str] = None
            entity_type: Optional[str] = None

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
                log.warning(f"Cannot determine entity ID from webhook event {parsed_webhook.webhook_event}")
                return False

            log.debug(f"Determined entity type: {entity_type}, entity ID: {entity_id}")

            # Tính độ ưu tiên cho webhook này
            priority = self._calculate_priority(parsed_webhook)
            log.debug(f"Calculated priority {priority} for webhook {parsed_webhook.webhook_event}")

            assert entity_id is not None

            # Lấy hoặc tạo queue cho entity này
            if entity_id not in self.queues:
                self.queues[entity_id] = asyncio.PriorityQueue()

            # Thêm webhook vào hàng đợi
            await self.queues[entity_id].put((priority, time.time(), parsed_webhook))
            log.debug(f"Added webhook to queue for entity {entity_id}")

            # Khởi động worker mới nếu entity này chưa đang được xử lý
            if entity_id not in self.processing:
                entity_task: asyncio.Task[None] = asyncio.create_task(self._process_entity_queue(entity_id))
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

            webhooks: List[BaseJiraWebhookDTO] = []
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

            # Process with a new session to avoid session conflicts
            success = await self._process_webhook_with_new_session(last_webhook)

            if not success:
                log.warning(f"Failed to process webhook for entity {entity_id}")
                await self._handle_retry(webhooks, highest_priority)

        except Exception as e:
            log.error(f"Error processing entity queue {entity_id}: {str(e)}")
            # If we have webhooks, try to retry them
            if 'webhooks' in locals() and webhooks and 'highest_priority' in locals():
                await self._handle_retry(webhooks, highest_priority)
        finally:
            self.processing.remove(entity_id)
            if entity_id in self.queues and self.queues[entity_id].empty():
                del self.queues[entity_id]

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
                            # Process with new session
                            success = await self._process_webhook_with_new_session(webhook)

                            if success:
                                # Success - clear retry count
                                self.retry_counts.pop(webhook_key, None)
                                log.info(f"Successfully processed webhook {webhook_key} on retry #{retry_count + 1}")
                            else:
                                # Failed - schedule next retry
                                self.retry_counts[webhook_key] = retry_count + 1
                                delay = self.RETRY_DELAYS[min(retry_count, len(self.RETRY_DELAYS) - 1)]
                                await asyncio.sleep(delay)
                                await self.retry_queue.put((priority + 1, time.time(), webhook))
                                log.warning(
                                    f"Retry #{retry_count + 1} failed for {webhook_key}, scheduling next retry in {delay}s")

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
        """Create a new webhook service with an isolated database session"""
        redis_client = None

        # Use the centralized session manager
        async with AsyncSessionManager.session() as session:
            try:
                # Use factory to create handlers and services
                handlers, services = await DependencyContainer.create_webhook_handlers()

                # Store redis_client to close it later
                if 'redis_service' in services and hasattr(services['redis_service'], '_redis'):
                    redis_client = services['redis_service']._redis

                # Create webhook service with handlers
                webhook_service = JiraWebhookService(
                    jira_issue_repository=services['issue_repo'],
                    sync_log_repository=services['sync_log_repo'],
                    jira_issue_api_service=services['jira_issue_api_service'],
                    jira_sprint_api_service=services['jira_sprint_api_service'],
                    sprint_database_service=services['sprint_database_service'],
                    issue_history_sync_service=services['issue_history_sync_service'],
                    jira_project_repository=services['project_repo'],
                    redis_service=services['redis_service'],
                    jira_sprint_repository=services['sprint_repo'],
                    nats_application_service=services['nats_application_service'],
                    handlers=handlers
                )

                # Yield both the webhook service and session
                yield webhook_service, session

            finally:
                # Close Redis client if we have one
                if redis_client:
                    try:
                        await redis_client.close()
                    except Exception as redis_error:
                        log.warning(f"Error closing Redis client: {str(redis_error)}")

    async def _process_webhook_with_new_session(self, webhook_data: BaseJiraWebhookDTO) -> bool:
        """Xử lý webhook với một session database mới và độc lập"""
        try:
            # Sử dụng context manager để đảm bảo session được đóng đúng cách
            async with self._get_webhook_service() as (webhook_service, session):
                # Xử lý webhook, passing the session explicitly
                result = await webhook_service.handle_webhook(session, webhook_data)

                # Kiểm tra kết quả
                if result and "error" in result:
                    log.warning(f"Error in webhook processing: {result['error']}")
                    return False

                return True

        except Exception as e:
            log.error(f"Exception processing webhook: {str(e)}")
            # Don't try to close the session here as it's managed by the context manager
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

    async def stop(self) -> None:
        """Stop all running tasks and clean up resources"""
        for task in list(self.running_tasks):
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks, return_exceptions=True)
