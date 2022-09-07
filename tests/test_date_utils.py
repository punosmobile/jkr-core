from datetime import date

import pytest

from jkrimporter.utils.date import parse_date_string


@pytest.mark.parametrize(
    "date_str, expected",
    [
        ("12.12.2021", date(2021, 12, 12)),
        ("12.12.21", date(2021, 12, 12)),
        ("12.12.99", date(1999, 12, 12)),
        ("12.12.80", date(1980, 12, 12)),
    ],
)
def test_parse_date(date_str, expected):
    assert parse_date_string(date_str) == expected


@pytest.mark.parametrize(
    "date_str",
    [
        "12.12.1",
        "34.12.21",
        "12.14.99",
    ],
)
def test_invalid_date_should_raise(date_str):
    with pytest.raises(Exception):
        parse_date_string(date_str)
