import datetime
import re

date_pattern = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})")


def parse_date_string(value: str):
    match = date_pattern.fullmatch(value)
    if not match:
        raise ValueError("Date is not valid")

    year = int(match.group(3))
    if year < 100:
        if 70 < year:
            year += 1900
        else:
            year += 2000

    return datetime.date(year, int(match.group(2)), int(match.group(1)))
