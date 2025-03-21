from enum import Enum


class EntityType(str, Enum):
    ISSUE = "ISSUE"
    PROJECT = "PROJECT"
    SPRINT = "SPRINT"
    USER = "USER"


class OperationType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SYNC = "SYNC"


class SourceType(str, Enum):
    NATS = "NATS"
    WEBHOOK = "WEBHOOK"
    MANUAL = "MANUAL"
