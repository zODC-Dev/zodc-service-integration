from enum import Enum


class SystemConfigConstants(str, Enum):
    ESTIMATE_POINT_TO_HOURS = "estimate_point_to_hours"
    WORKING_HOURS_PER_DAY = "working_hours_per_day"
    LUNCH_BREAK_MINUTES = "lunch_break_minutes"
    START_WORK_HOUR = "start_work_hour"
    END_WORK_HOUR = "end_work_hour"
