from config import CUSTOM_BLOCK_TIMES, CUSTOM_BLOCK_ORDERS, SPECIAL_UNIFORM_DATES, SCHEDULE_PATTERN, DAYS_OFF, CUSTOM_DAYS_OFF, TIME_SLOTS, SCHEDULE_START, ROOMS_FOR_COURSES
from datetime import datetime, timedelta
import numpy as np

# Helper function to determine if a day is a day off
def is_day_off(date):
    return date.weekday() in DAYS_OFF or date in CUSTOM_DAYS_OFF


def get_blocks_for_date(date):
    """Retrieve the block schedule for a specific date."""
    if date in CUSTOM_BLOCK_ORDERS:
        return CUSTOM_BLOCK_ORDERS[date]
    
    delta_week_days = np.busday_count(datetime(2024, 9, 4).date(), date)
    day_index = delta_week_days % len(SCHEDULE_PATTERN)
    
    if is_day_off(date) or date in CUSTOM_DAYS_OFF:
        return "No school"
    
    return SCHEDULE_PATTERN[day_index]

def get_block_times_for_date(date):
    if date in CUSTOM_BLOCK_TIMES:
        print("entered")
        return CUSTOM_BLOCK_TIMES[date]
    else:
        return TIME_SLOTS
