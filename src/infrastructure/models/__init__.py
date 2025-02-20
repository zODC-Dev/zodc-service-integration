from .base import BaseModel, BaseModelWithTimestamps
from .permission import Permission
from .project import Project
from .refresh_token import RefreshToken
from .role import Role
from .user import User
from .user_project_role import UserProjectRole

# Update forward references
BaseModel.model_rebuild()
BaseModelWithTimestamps.model_rebuild()
RefreshToken.model_rebuild()
Permission.model_rebuild()
Project.model_rebuild()
Role.model_rebuild()
User.model_rebuild()
UserProjectRole.model_rebuild()
