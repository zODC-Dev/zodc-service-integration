
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NodeStatusSyncRequest(BaseModel):
    """Model đại diện cho request đồng bộ trạng thái của node từ hệ thống khác sang Jira

    Attributes:
        transaction_id: ID của transaction
        project_key: Project key của Jira
        jira_key: Key của issue trong Jira
        node_id: ID của node trong hệ thống
        status: Trạng thái mới của node
    """
    transaction_id: str
    project_key: str
    jira_key: str
    node_id: str
    status: str
    last_synced_at: Optional[datetime] = None
