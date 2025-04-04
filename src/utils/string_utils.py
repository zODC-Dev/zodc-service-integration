import uuid


def is_valid_uuid(uuid_str: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False
