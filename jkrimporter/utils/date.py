import datetime
import re

finnish_date_pattern = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})")
iso_date_pattern = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

def parse_date_string(value: str):
    # Try ISO format first (YYYY-MM-DD)
    match = iso_date_pattern.fullmatch(value)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return datetime.date(year, month, day)

    # Try Finnish format (DD.MM.YYYY)
    match = finnish_date_pattern.fullmatch(value)
    if not match:
        raise ValueError("Date is not valid. Use format YYYY-MM-DD or DD.MM.YYYY")

    year = int(match.group(3))
    if year < 100:
        if 70 < year:
            year += 1900
        else:
            year += 2000

    return datetime.date(year, int(match.group(2)), int(match.group(1)))
