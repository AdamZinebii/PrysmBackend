from datetime import timezone
import dateutil.parser
import re

def parse_custom_date(date_str):
    # Clean the timezone name (e.g., "UTC") after the offset (e.g., "+0000")
    cleaned = re.sub(r'(\+\d{4})\s+\w+$', r'\1', date_str.strip())
    # Parse the cleaned string and return UTC datetime
    return dateutil.parser.parse(cleaned).astimezone(timezone.utc)

test_date = '06/03/2025, 09:00 AM, +0000 UTC'
parsed = parse_custom_date(test_date)
print(parsed)

from datetime import datetime, timedelta, timezone

def is_within_last_24_hours(dt):
    now = datetime.now(timezone.utc)
    return now - dt <= timedelta(hours=24)

# Example usage
parsed_date = parse_custom_date('06/03/2025, 09:00 AM, +0000 UTC')
print(is_within_last_24_hours(parsed_date))  # Should print True or False
