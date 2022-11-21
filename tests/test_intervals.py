import pytest

from jkrimporter.utils.intervals import Interval, IntervalCounter


@pytest.mark.parametrize(
    ["i1", "i2", "expected"],
    [
        (Interval(1, 2), Interval(3, 4), False),
        (Interval(1, 2), Interval(2, 3), True),
        (Interval(3, 5), Interval(4, 6), True),
        (Interval(None, 5), Interval(4, 6), True),
        (Interval(None, 5), Interval(4, None), True),
        (Interval(None, 5), Interval(6, None), False),
        (Interval(None, None), Interval(6, None), True),
        (Interval(None, None), Interval(None, None), True),
    ],
)
def test_range_overlap(i1: Interval, i2: Interval, expected):
    assert i1.overlaps(i2) == expected
    assert i2.overlaps(i1) == expected


@pytest.mark.parametrize(
    ["interval", "value", "expected"],
    [
        (Interval(1, 3), 2, True),
        (Interval(None, 3), 2, True),
        (Interval(1, None), 2, True),
        (Interval(None, None), 2, True),
        (Interval(1, 3), 4, False),
        (Interval(None, 3), 4, False),
        (Interval(1, 2), 0, False),
        (Interval(1, None), 0, False),
        (Interval(1, 2), 1, True),
        (Interval(1, 2), 2, True),
        (Interval(1, 2), None, False),
        (Interval(None, 2), None, True),
        (Interval(1, None), None, True),
        (Interval(3, 5), Interval(3, 5), True),
        (Interval(3, 5), Interval(3, None), False),
        (Interval(3, 5), Interval(None, 5), False),
        (Interval(3, 5), Interval(4, 6), False),
        (Interval(4, 6), Interval(3, 5), False),
        (Interval(4, 6), Interval(None, None), False),
    ],
)
def test_range_contains(interval: Interval, value, expected):
    assert interval.contains(value) == expected


@pytest.fixture
def interval_counter():
    return IntervalCounter([Interval(None, 2), Interval(1, 4), Interval(2, 6)])


@pytest.mark.parametrize(["value", "expected"], [(-4, 1), (1, 2), (2, 3), (4, 2)])
def test_interval_counter_containing(
    value, expected, interval_counter: IntervalCounter
):
    assert interval_counter.count_containing(value) == expected


@pytest.mark.parametrize(
    ["interval", "expected"],
    [(Interval(None, 0), 1), (Interval(1, 2), 3), (Interval(3, 4), 2)],
)
def test_interval_overlapping(interval, expected, interval_counter: IntervalCounter):
    assert interval_counter.count_overlapping(interval) == expected
