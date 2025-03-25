import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar

import aiohttp

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.refresh_tokens import TokenType
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraConnectionError, JiraRequestError
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_scheduler_service import ITokenSchedulerService

# Định nghĩa generic types cho mapper
T = TypeVar('T')  # Domain model
U = TypeVar('U')  # API response model


class JiraAPIClient:
    """Common client to interact with Jira API"""

    def __init__(
        self,
        redis_service: IRedisService,
        token_scheduler_service: ITokenSchedulerService,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.redis_service = redis_service
        self.token_scheduler_service = token_scheduler_service
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.base_url = settings.JIRA_BASE_URL

    async def _get_token(self, user_id: int) -> str:
        """Lấy Jira token từ cache hoặc refresh"""
        # Schedule token refresh check
        await self.token_scheduler_service.schedule_token_refresh(user_id)

        # Try to get token from cache first
        token = await self.redis_service.get_cached_jira_token(user_id)
        if token:
            return token

        # If not in cache, using refresh token to get new access token
        await self.token_scheduler_service.refresh_token_chain(user_id, TokenType.JIRA)

        # Try to get token from cache again
        token = await self.redis_service.get_cached_jira_token(user_id)
        if token:
            return token

        raise JiraAuthenticationError("Không thể lấy Jira token")

    def _get_headers(self, token: str) -> Dict[str, str]:
        """Tạo headers chuẩn cho request"""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def _handle_response(self, response: aiohttp.ClientResponse, error_msg: str = "Jira API error") -> Dict[str, Any]:
        """Xử lý HTTP response và ném exception nếu cần"""
        if response.status == 200 or response.status == 201:
            return await response.json()
        elif response.status == 204:
            return {}  # No content
        elif response.status == 401:
            raise JiraAuthenticationError("Token không hợp lệ hoặc đã hết hạn")
        elif response.status == 403:
            raise JiraAuthenticationError("Không có quyền thực hiện hành động này")
        elif response.status == 404:
            raise JiraRequestError(response.status, "Resource không tồn tại")
        elif response.status >= 500:
            error_text = await response.text()
            raise JiraConnectionError(f"Lỗi server Jira: {error_text}")
        else:
            error_text = await response.text()
            raise JiraRequestError(response.status, f"{error_msg}: {error_text}")

    async def request_with_retry(
        self,
        method: str,
        url: str,
        user_id: int,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "Jira API error"
    ) -> Dict[str, Any]:
        """Thực hiện HTTP request với cơ chế retry"""
        token = await self._get_token(user_id)
        headers = self._get_headers(token)

        retry_count = 0
        # last_error = None

        while retry_count < self.max_retries:
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    request_method = getattr(session, method.lower())
                    request_kwargs = {"headers": headers, "params": params}

                    if json_data is not None and method.lower() in ['post', 'put', 'patch']:
                        request_kwargs["json"] = json_data

                    async with request_method(url, **request_kwargs) as response:
                        return await self._handle_response(response, error_msg)

            except (JiraConnectionError, aiohttp.ClientError) as e:
                # Chỉ retry với lỗi kết nối
                retry_count += 1
                # last_error = e

                if retry_count >= self.max_retries:
                    log.error(f"Đã thử lại {retry_count} lần nhưng không thành công: {str(e)}")
                    raise

                # Exponential backoff
                wait_time = 0.5 * (2 ** retry_count)
                log.warning(f"Thử lại lần {retry_count} sau {wait_time}s. Lỗi: {str(e)}")
                await asyncio.sleep(wait_time)

            except (JiraAuthenticationError, JiraRequestError):
                # Không retry với lỗi xác thực hoặc request
                raise

        raise JiraRequestError(500, "Error fetching data from Jira")

    async def get(self, endpoint: str, user_id: int, params: Optional[Dict[str, Any]] = None, error_msg: str = "Lỗi khi lấy dữ liệu từ Jira") -> Dict[str, Any]:
        """Thực hiện HTTP GET request"""
        url = f"{self.base_url}{endpoint}"
        return await self.request_with_retry("GET", url, user_id, params=params, error_msg=error_msg)

    async def post(self, endpoint: str, user_id: int, data: Dict[str, Any], error_msg: str = "Lỗi khi tạo mới trên Jira") -> Dict[str, Any]:
        """Thực hiện HTTP POST request"""
        url = f"{self.base_url}{endpoint}"
        return await self.request_with_retry("POST", url, user_id, json_data=data, error_msg=error_msg)

    async def put(self, endpoint: str, user_id: int, data: Dict[str, Any], error_msg: str = "Lỗi khi cập nhật thông tin trên Jira") -> Dict[str, Any]:
        """Thực hiện HTTP PUT request"""
        url = f"{self.base_url}{endpoint}"
        return await self.request_with_retry("PUT", url, user_id, json_data=data, error_msg=error_msg)

    async def delete(self, endpoint: str, user_id: int, error_msg: str = "Lỗi khi xóa dữ liệu trên Jira") -> Dict[str, Any]:
        """Thực hiện HTTP DELETE request"""
        url = f"{self.base_url}{endpoint}"
        return await self.request_with_retry("DELETE", url, user_id, error_msg=error_msg)

    # Các phương thức tiện ích

    async def parse_response_with_model(self, response_data: Dict[str, Any], model_class: Type[U]) -> U:
        """Parse response data vào model class"""
        return model_class.model_validate(response_data)

    async def map_to_domain(self, response_data: Dict[str, Any], model_class: Type[U], mapper: Any) -> T:
        """Map API response to domain model"""
        api_model = await self.parse_response_with_model(response_data, model_class)
        domain_model = mapper.to_domain(api_model)
        return domain_model

    async def map_list_to_domain(self, response_data: List[Dict[str, Any]], model_class: Type[U], mapper: Any) -> List[T]:
        """Map list of API responses to domain models"""
        result = []
        for item in response_data:
            api_model = await self.parse_response_with_model(item, model_class)
            result.append(mapper.to_domain(api_model))
        return result
