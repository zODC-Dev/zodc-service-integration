from enum import Enum


class PermissionGroup(Enum):
    SYSTEM = "system"
    PROJECT = "project"
    MASTERFLOW = "masterflow"


class SystemPermissions(Enum):
    CREATE_ROLE = "system-role.create"
    VIEW_ROLE = "system-role.view"
    MANAGE_ROLE = "system-role.manage"
    MANAGE_USER = "system-user.manage"
    VIEW_USER = "system-user.view"
