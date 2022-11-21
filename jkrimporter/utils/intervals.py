from datetime import date
from typing import Any, List, NamedTuple, Union


class Interval(NamedTuple):
    """Interval containing both ends"""

    lower: Union[None, int, date]
    upper: Union[None, int, date]

    def overlaps(self, other: "Interval") -> bool:
        return (
            self.lower is None or other.upper is None or self.lower <= other.upper
        ) and (other.lower is None or self.upper is None or other.lower <= self.upper)

    def adjacent(self, other: "Interval") -> bool:
        return other.left_upper == self.lower or self.upper == other.right_lower

    def contains(self, value: Union[Any, "Interval"]) -> bool:
        if isinstance(value, Interval):
            return (
                self.lower is None
                or (self.lower is None and value.lower is None)
                or (value.lower is not None and self.lower <= value.lower)
            ) and (
                self.upper is None
                or (self.upper is None and value.upper is None)
                or (value.upper is not None and value.upper <= self.upper)
            )

        return (value is None and (self.lower is None or self.upper is None)) or (
            value is not None
            and (self.lower is None or self.lower <= value)
            and (self.upper is None or value <= self.upper)
        )

    def union(self, other: "Interval"):
        if self.overlaps(other) or self.adjacent(other):
            lower = min(self.lower, other.lower) if self.lower and other.lower else None
            upper = max(self.upper, other.upper) if self.upper and other.upper else None

            return Interval(lower, upper)
        else:
            raise ValueError(
                "This and other Intervals dont overlap nor are adjacent. "
                "MultiIntervals are not supported."
            )


class IntervalCounter(List[Interval]):
    def count_containing(self, value) -> int:
        return len([1 for i in self if i.contains(value)])

    def count_overlapping(self, interval: "Interval") -> int:
        return len([1 for i in self if i.overlaps(interval)])


if __name__ == "__main__":
    v = IntervalCounter(
        [Interval(1, 4), Interval(2, 6), Interval(None, 2)]
    ).count_containing(3)
    print(v)
