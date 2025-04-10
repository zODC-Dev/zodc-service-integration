from typing import Any, Dict, Optional

from pydantic import BaseModel


class NodeStatusSyncReply(BaseModel):
    success: bool
    error_message: Optional[str] = None
    data: Dict[str, Any] = {}
