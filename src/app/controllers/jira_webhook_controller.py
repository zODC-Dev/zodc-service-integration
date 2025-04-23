from typing import Any, Dict

from fastapi import HTTPException

from src.app.services.jira_webhook_queue_service import JiraWebhookQueueService
from src.configs.logger import log
from src.domain.models.jira.webhooks.jira_webhook import BaseJiraWebhookDTO
from src.domain.services.jira_webhook_service import IJiraWebhookService


class JiraWebhookController:
    def __init__(self, jira_webhook_service: IJiraWebhookService, jira_webhook_queue_service: JiraWebhookQueueService):
        self.jira_webhook_service = jira_webhook_service
        self.jira_webhook_queue_service = jira_webhook_queue_service

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Handle incoming Jira webhook"""
        try:
            # Ghi log payload ban đầu để debug
            # log.debug(f"Received webhook payload: {payload}")

            # Sử dụng factory method từ BaseJiraWebhookDTO để tạo DTO phù hợp
            if "webhookEvent" in payload:
                log.info(f"Processing webhook event: {payload['webhookEvent']}")

            # Parse webhook data sử dụng factory method
            try:
                webhook_data = BaseJiraWebhookDTO.parse_webhook(payload)
                log.info(f"Webhook parsed successfully as {type(webhook_data).__name__}")

                # Thêm vào queue để xử lý bất đồng bộ
                await self.jira_webhook_queue_service.add_webhook_to_queue(webhook_data)

                return {"status": "queued", "event_type": webhook_data.webhook_event}
            except ValueError as ve:
                # Lỗi khi parse webhook, không thêm vào queue
                log.error(f"Error parsing webhook: {str(ve)}")

                # Vẫn cố thêm vào queue dù bị lỗi parse
                # try:
                #     # Chỉ thêm payload gốc nếu có event type
                #     if "webhookEvent" in payload:
                #         log.warning(f"Attempting to queue unparsed webhook with event {payload['webhookEvent']}")
                #         await self.jira_webhook_queue_service.add_webhook_to_queue(payload)
                #         return {"status": "queued_raw", "event_type": payload['webhookEvent']}
                # except Exception as inner_e:
                #     log.error(f"Failed to queue raw webhook: {str(inner_e)}")

                raise HTTPException(status_code=400, detail=f"Invalid webhook format: {str(ve)}") from ve

        except HTTPException:
            # Re-raise HTTPException để giữ nguyên status code
            raise
        except Exception as e:
            log.error(f"Error in webhook handler: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e
