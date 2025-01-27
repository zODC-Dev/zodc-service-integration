from enum import Enum


class SystemRoles(str, Enum):
    ADMIN = "admin"
    USER = "user"  # ODC Members
    PRODUCT_OWNER = "product_owner"
    ODC_MANAGER = "odc_manager"
