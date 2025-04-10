from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class JiraChangelogItemDTO(BaseModel):
    """DTO đại diện cho một mục thay đổi trong changelog của Jira"""
    field: str = Field(..., description="Tên trường được thay đổi")
    fieldtype: str = Field(..., description="Loại trường được thay đổi")
    fieldId: Optional[str] = Field(None, description="ID của trường được thay đổi")
    from_value: Optional[str] = Field(None, alias="from", description="Giá trị trước khi thay đổi")
    to_value: Optional[str] = Field(None, alias="to", description="Giá trị sau khi thay đổi")
    fromString: Optional[str] = Field(None, description="Mô tả giá trị trước khi thay đổi")
    toString: Optional[str] = Field(None, description="Mô tả giá trị sau khi thay đổi")

    class Config:
        populate_by_name = True


class JiraChangelogAuthorDTO(BaseModel):
    """DTO đại diện cho tác giả của một changelog"""
    self: Optional[str] = Field(None, description="URL tự tham chiếu đến tác giả")
    accountId: str = Field(..., description="Account ID của tác giả trong Jira")
    displayName: str = Field(..., description="Tên hiển thị của tác giả")
    emailAddress: Optional[str] = Field(None, description="Địa chỉ email của tác giả")
    active: Optional[bool] = Field(None, description="Trạng thái hoạt động của tài khoản")
    timeZone: Optional[str] = Field(None, description="Múi giờ của tác giả")
    accountType: Optional[str] = Field(None, description="Loại tài khoản")

    # Thêm thuộc tính id không bắt buộc (optional)
    id: Optional[str] = Field(None, description="ID của tác giả (nếu có)")


class JiraChangelogDetailAPIGetResponseDTO(BaseModel):
    """DTO đại diện cho một changelog của Jira"""
    id: str = Field(..., description="ID của changelog")
    author: JiraChangelogAuthorDTO = Field(..., description="Tác giả thực hiện thay đổi")
    created: datetime = Field(..., description="Thời điểm thay đổi được tạo")
    items: List[JiraChangelogItemDTO] = Field(..., description="Danh sách các mục thay đổi")


class JiraIssueChangelogAPIGetResponseDTO(BaseModel):
    """DTO đại diện cho response của API changelog của Jira"""
    values: List[JiraChangelogDetailAPIGetResponseDTO] = Field(default=[], description="Danh sách các changelog")
    startAt: int = Field(..., description="Vị trí bắt đầu của kết quả trả về")
    maxResults: int = Field(..., description="Số lượng tối đa kết quả được trả về")
    total: int = Field(..., description="Tổng số changelog có sẵn")
    isLast: bool = Field(..., description="Có phải là trang cuối cùng không")
