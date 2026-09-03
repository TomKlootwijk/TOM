"""Closed exact rational intervals and outward-exact arithmetic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .rational import Q


@dataclass(frozen=True, slots=True)
class ClosedInterval:
    lower: Q
    upper: Q

    def __post_init__(self) -> None:
        lo = Q.from_value(self.lower)
        hi = Q.from_value(self.upper)
        if hi < lo:
            raise ValueError(f"interval upper {hi} is below lower {lo}")
        object.__setattr__(self, "lower", lo)
        object.__setattr__(self, "upper", hi)

    @classmethod
    def point(cls, value: Any) -> "ClosedInterval":
        q = Q.from_value(value)
        return cls(q, q)

    @classmethod
    def from_value(cls, value: Any) -> "ClosedInterval":
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(Q.from_value(value["lower"]), Q.from_value(value["upper"]))
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return cls(Q.from_value(value[0]), Q.from_value(value[1]))
        return cls.point(value)

    @classmethod
    def hull(cls, values: Iterable[Any]) -> "ClosedInterval":
        items = [Q.from_value(v) for v in values]
        if not items:
            raise ValueError("cannot form interval hull of an empty sequence")
        return cls(min(items), max(items))

    def to_record(self) -> dict[str, dict[str, int]]:
        return {"lower": self.lower.to_record(), "upper": self.upper.to_record()}

    def to_text(self) -> str:
        return f"[{self.lower.to_text()},{self.upper.to_text()}]"

    def width(self) -> Q:
        return self.upper - self.lower

    def midpoint(self) -> Q:
        return (self.lower + self.upper) / 2

    def contains(self, value: Any) -> bool:
        q = Q.from_value(value)
        return self.lower <= q <= self.upper

    def contains_zero(self) -> bool:
        return self.contains(0)

    def interior_contains_zero(self) -> bool:
        return self.lower < 0 < self.upper

    def is_point(self) -> bool:
        return self.lower == self.upper

    def sign_class(self) -> str:
        if self.upper < 0:
            return "negative"
        if self.lower > 0:
            return "positive"
        zero = Q(0)
        if self.lower == zero and self.upper == zero:
            return "zero"
        if self.lower == zero:
            return "nonnegative"
        if self.upper == zero:
            return "nonpositive"
        return "straddles-zero"

    def excludes_zero(self) -> bool:
        return self.upper < 0 or self.lower > 0

    def intersection(self, other: Any) -> "ClosedInterval | None":
        b = ClosedInterval.from_value(other)
        lo = max(self.lower, b.lower)
        hi = min(self.upper, b.upper)
        return None if hi < lo else ClosedInterval(lo, hi)

    def subset_of(self, other: Any) -> bool:
        b = ClosedInterval.from_value(other)
        return b.lower <= self.lower and self.upper <= b.upper

    def __neg__(self) -> "ClosedInterval":
        return ClosedInterval(-self.upper, -self.lower)

    def __add__(self, other: Any) -> "ClosedInterval":
        b = ClosedInterval.from_value(other)
        return ClosedInterval(self.lower + b.lower, self.upper + b.upper)

    def __radd__(self, other: Any) -> "ClosedInterval":
        return self + other

    def __sub__(self, other: Any) -> "ClosedInterval":
        return self + (-ClosedInterval.from_value(other))

    def __rsub__(self, other: Any) -> "ClosedInterval":
        return ClosedInterval.from_value(other) - self

    def __mul__(self, other: Any) -> "ClosedInterval":
        b = ClosedInterval.from_value(other)
        products = (
            self.lower * b.lower,
            self.lower * b.upper,
            self.upper * b.lower,
            self.upper * b.upper,
        )
        return ClosedInterval(min(products), max(products))

    def __rmul__(self, other: Any) -> "ClosedInterval":
        return self * other

    def reciprocal(self) -> "ClosedInterval":
        if self.contains_zero():
            raise ZeroDivisionError("interval reciprocal is undefined across zero")
        return ClosedInterval(1 / self.upper, 1 / self.lower)

    def __truediv__(self, other: Any) -> "ClosedInterval":
        return self * ClosedInterval.from_value(other).reciprocal()

    def __str__(self) -> str:
        return self.to_text()
