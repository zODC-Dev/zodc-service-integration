from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PerformanceSummaryRequest(BaseModel):
    """Request schema cho API lấy thông tin hiệu suất của người dùng"""
    user_id: Optional[int] = Field(None, alias="userId")
    quarter: int
    year: int

    @field_validator("quarter")
    @classmethod
    def validate_quarter(cls, v):
        if v < 1 or v > 4:
            raise ValueError("Quarter must be between 1 and 4")
        return v

    @field_validator("year")
    @classmethod
    def validate_year(cls, v):
        if v < 2000 or v > 2100:
            raise ValueError("Year must be between 2000 and 2100")
        return v

    class Config:
        populate_by_name = True
