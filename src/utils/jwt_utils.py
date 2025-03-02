from datetime import datetime, timezone

import jwt

from src.configs.logger import log


def get_jwt_expiry(token: str) -> datetime | None:
    """Get expiry from JWT token without verification

    Args:
        token (str): JWT token string

    Returns:
        datetime: Expiry datetime in UTC timezone
        None: If token cannot be decoded or no exp claim
    """
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded.get('exp')
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    except Exception as e:
        log.warning(f"Failed to decode JWT token: {str(e)}")
    return None
