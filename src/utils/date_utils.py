from datetime import datetime, timezone, timedelta
from typing import Optional


# Define Vietnam timezone (UTC+7)
VIETNAM_TZ = timezone(timedelta(hours=7))


def convert_timestamp_to_timestamptz(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert a timestamp without timezone (naive datetime) to timestamp with timezone (aware datetime).

    Assumes input datetime is in Vietnam timezone (UTC+7) if it doesn't have timezone info.

    Args:
        dt: A datetime object, potentially without timezone info

    Returns:
        A datetime object with timezone info (UTC+7)
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # If no timezone info, assume it's Vietnam time (UTC+7)
        return dt.replace(tzinfo=VIETNAM_TZ)

    # Already has timezone info
    return dt


def convert_timestamptz_to_timestamp(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert a timestamp with timezone (aware datetime) to timestamp without timezone (naive datetime).

    Converts to Vietnam time (UTC+7) first, then removes timezone info.

    Args:
        dt: A datetime object with timezone info

    Returns:
        A datetime object without timezone info, in Vietnam local time
    """
    if dt is None:
        return None

    if dt.tzinfo is not None:
        # Convert to Vietnam timezone first
        vietnam_time = dt.astimezone(VIETNAM_TZ)
        # Then remove timezone info
        return vietnam_time.replace(tzinfo=None)

    # Already without timezone info
    return dt


def is_db_timestamp_newer(db_timestamp: Optional[datetime], nats_timestamp: Optional[datetime]) -> bool:
    """
    Compare DB timestamp (with timezone) with NATS timestamp (without timezone).

    Args:
        db_timestamp: Timestamp from database, with timezone info
        nats_timestamp: Timestamp from NATS, without timezone info

    Returns:
        True if DB timestamp is newer than NATS timestamp, False otherwise
    """
    if not db_timestamp or not nats_timestamp:
        return False

    # Ensure NATS timestamp has timezone info for comparison
    nats_with_tz = convert_timestamp_to_timestamptz(nats_timestamp)

    return db_timestamp > nats_with_tz
