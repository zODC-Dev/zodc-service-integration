# Remove duplicate JiraSprintAPIGetResponseDTO and JiraProjectAPIGetResponseDTO
# If this file is empty after removing duplicates, you can delete it

from typing import Dict, Optional, Union

from pydantic import BaseModel


class JiraProjectAPIGetResponseDTO(BaseModel):
    id: str
    key: str
    name: str
    description: Optional[str] = None
    avatarUrls: Union[Dict[str, str], str, None] = None  # Can be dict, string or None
    projectTypeKey: str
    simplified: bool = False
    style: str = ""
    isPrivate: bool = False
    properties: Dict[str, str] = {}
    entityId: Optional[str] = None
    uuid: Optional[str] = None

    class Config:
        extra = "allow"  # Cho phép các trường khác trong response mà không cần định nghĩa
