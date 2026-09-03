"""Small deterministic knowledge operators used by the included source-derived demo."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


def active_bit_positions(value: int) -> list[int]:
    if value < 0:
        raise ValueError("active-bit projection expects a non-negative integer")
    return [k for k in range(value.bit_length()) if (value >> k) & 1]


def popcount(value: int) -> int:
    return len(active_bit_positions(value))


def regular_pulse_geometry(count: int, radius: float = 1.0, phase: float = 0.0) -> dict[str, Any]:
    if count < 0:
        raise ValueError("pulse count must be non-negative")
    if count == 0:
        return {"kind": "empty", "points": []}
    if count == 1:
        return {"kind": "point", "points": [[radius * math.cos(phase), radius * math.sin(phase)]]}
    if count == 2:
        return {
            "kind": "segment",
            "points": [[radius * math.cos(phase), radius * math.sin(phase)],
                       [-radius * math.cos(phase), -radius * math.sin(phase)]],
        }
    points = [
        [radius * math.cos(phase + 2.0 * math.pi * j / count),
         radius * math.sin(phase + 2.0 * math.pi * j / count)]
        for j in range(count)
    ]
    return {"kind": "triangle" if count == 3 else "regular_polygon", "points": points}


@dataclass(slots=True)
class KnowledgeResult:
    output: dict[str, Any]
    trace: list[dict[str, Any]]


def nineteen_demo() -> KnowledgeResult:
    value = 19
    segments = ["ne", "gen", "tien"]
    active = active_bit_positions(value)
    trace: list[dict[str, Any]] = [
        {"operator": "TOM.ACTIVE", "input": value, "output": active},
        {"operator": "TOM.POPCOUNT", "input": active, "output": len(active)},
        {"operator": "TOM.PULSE", "input": segments, "output": len(segments)},
    ]
    equal = len(active) == len(segments)
    trace.append({"operator": "TOM.EQ", "left": len(active), "right": len(segments), "output": equal})
    geometry = regular_pulse_geometry(len(segments))
    trace.append({"operator": "TOM.PROJECT", "input": len(segments), "output": geometry["kind"]})
    output = {
        "value": value,
        "binary": format(value, "b"),
        "active_bit_positions": active,
        "active_bit_count": len(active),
        "profile_segments": segments,
        "pulse_count": len(segments),
        "equal_feature_counts": equal,
        "projection": geometry,
    }
    return KnowledgeResult(output=output, trace=trace)
