
import pytz
from datetime import datetime, timezone

def make_timezone_aware(dt):
    """Convert naive datetime to timezone-aware"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume UTC if naive
        return dt.replace(tzinfo=timezone.utc)
    return dt

def make_timezone_naive(dt):
    """Convert timezone-aware datetime to naive UTC"""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def safe_datetime_subtract(dt1, dt2):
    """Safely subtract datetimes handling timezone issues"""
    # Make both timezone-aware or both naive
    if dt1.tzinfo is None and dt2.tzinfo is None:
        return dt1 - dt2
    elif dt1.tzinfo is not None and dt2.tzinfo is not None:
        return dt1 - dt2
    else:
        # Mixed - convert both to UTC naive
        dt1_naive = make_timezone_naive(dt1)
        dt2_naive = make_timezone_naive(dt2)
        return dt1_naive - dt2_naive
