import asyncio
import base64
import json
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
        max_retries: int = 3,
        use_admin_auth: bool = False  # Thêm flag cho admin auth
    ):
        self.redis_service = redis_service
        self.token_scheduler_service = token_scheduler_service
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.base_url = settings.JIRA_BASE_URL
        self.use_admin_auth = use_admin_auth

    async def _get_token(self, user_id: int) -> str:
        """Get Jira token from cache or refresh"""
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

        raise JiraAuthenticationError("Cannot get Jira token")

    def _get_headers(self, token: str) -> Dict[str, str]:
        """Create standard headers for request"""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def _get_admin_headers(self) -> Dict[str, str]:
        """Tạo headers cho admin auth với Basic Auth"""
        # Đổi sang định dạng base64 cho BasicAuth
        auth_str = f"{settings.JIRA_ADMIN_USERNAME}:{settings.JIRA_ADMIN_PASSWORD}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()

        return {
            "Authorization": f"Basic {encoded_auth}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    async def _get_headers_for_request(self, user_id: Optional[int] = None) -> Dict[str, str]:
        """Lấy headers cho request - hoặc từ admin hoặc từ user token"""
        if user_id is None:
            return self._get_admin_headers()
        else:
            token = await self._get_token(user_id)
            return self._get_headers(token)

    async def _handle_response(self, response: aiohttp.ClientResponse, error_msg: str = "Jira API error") -> Dict[str, Any]:
        """Handle HTTP response and throw exception if needed"""
        if response.status == 200 or response.status == 201:
            return await response.json()
        elif response.status == 204:
            return {}  # No content
        elif response.status == 401:
            error_text = await response.text()
            raise JiraAuthenticationError(f"Token is invalid or expired: {error_text}")
        elif response.status == 403:
            error_text = await response.text()
            raise JiraAuthenticationError(f"You do not have permission to perform this action: {error_text}")
        elif response.status == 404:
            error_text = await response.text()
            raise JiraRequestError(response.status, f"Resource not found: {error_text}")
        elif response.status >= 500:
            error_text = await response.text()
            raise JiraConnectionError(f"Jira server error: {error_text}")
        else:
            error_text = await response.text()
            raise JiraRequestError(response.status, f"{error_msg}: {error_text}")

    async def request_with_retry(
        self,
        method: str,
        url: str,
        user_id: Optional[int] = None,  # Đổi thành optional
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "Jira API error"
    ) -> Dict[str, Any]:
        """Perform HTTP request with retry mechanism"""
        headers = await self._get_headers_for_request(user_id)

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
                    log.error(f"Attempted {retry_count} times but failed: {str(e)}")
                    raise

                # Exponential backoff
                wait_time = 0.5 * (2 ** retry_count)
                log.warning(f"Retrying in {wait_time}s. Error: {str(e)}")
                await asyncio.sleep(wait_time)

            except (JiraAuthenticationError, JiraRequestError):
                # Không retry với lỗi xác thực hoặc request
                raise

        raise JiraRequestError(500, "Error fetching data from Jira")

    async def get(self, endpoint: str, user_id: Optional[int] = None, params: Optional[Dict[str, Any]] = None, error_msg: str = "Error fetching data from Jira") -> Dict[str, Any]:
        """Perform HTTP GET request"""
        url = f"{self.base_url}{endpoint}"
        return await self.request_with_retry("GET", url, user_id, params=params, error_msg=error_msg)

    async def post(self, endpoint: str, user_id: Optional[int] = None, data: Dict[str, Any] = None, error_msg: str = "Error creating new data on Jira") -> Dict[str, Any]:
        """Perform HTTP POST request"""
        url = f"{self.base_url}{endpoint}"
        return await self.request_with_retry("POST", url, user_id, json_data=data, error_msg=error_msg)

    async def put(self, endpoint: str, user_id: Optional[int] = None, data: Dict[str, Any] = None, error_msg: str = "Error updating data on Jira") -> Dict[str, Any]:
        """Perform HTTP PUT request"""
        url = f"{self.base_url}{endpoint}"
        return await self.request_with_retry("PUT", url, user_id, json_data=data, error_msg=error_msg)

    async def delete(self, endpoint: str, user_id: Optional[int] = None, error_msg: str = "Error deleting data on Jira") -> Dict[str, Any]:
        """Perform HTTP DELETE request"""
        url = f"{self.base_url}{endpoint}"
        return await self.request_with_retry("DELETE", url, user_id, error_msg=error_msg)

    # Các phương thức tiện ích

    async def parse_response_with_model(self, response_data: Dict[str, Any], model_class: Type[U]) -> U:
        """Parse response data into model class"""
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

    async def get_with_admin_auth(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "Error calling Jira API"
    ) -> Dict[str, Any]:
        """Call Jira API GET method with admin authentication

        Args:
            path: API path to call
            params: Query parameters
            error_msg: Error message to log if the request fails

        Returns:
            Response JSON data

        Raises:
            JiraRequestError: If the request fails
        """
        try:
            # Sử dụng admin credentials từ cấu hình
            admin_auth = self._get_admin_headers()

            # Build URL
            url = f"{self.base_url}{path}"

            # Log request (không bao gồm headers vì có thông tin nhạy cảm)
            log.info(f"GET {url} with admin auth")

            # Thực hiện request với admin auth
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    url,
                    headers=admin_auth,
                    params=params
                ) as response:
                    response_text = await response.text()
                    status_code = response.status

                    # Kiểm tra nếu request thành công
                    if status_code < 200 or status_code >= 300:
                        log.error(f"Jira API request failed with status {status_code}: {response_text}")
                        raise JiraRequestError(error_msg, status_code, response_text)

                    # Parse JSON response
                    try:
                        return json.loads(response_text) if response_text else {}
                    except json.JSONDecodeError:
                        log.error(f"Failed to parse JSON response: {response_text}")
                        return {"raw_response": response_text}

        except (aiohttp.ClientConnectorError, aiohttp.ClientTimeout) as e:
            log.error(f"Connection error when calling Jira API: {str(e)}")
            raise JiraRequestError(f"{error_msg}: Connection error", 0, str(e)) from e
        except JiraRequestError as e:
            # Re-throw JiraRequestError
            raise e
        except Exception as e:
            log.error(f"Unexpected error when calling Jira API: {str(e)}")
            raise JiraRequestError(f"{error_msg}: {str(e)}", 0, str(e)) from e
