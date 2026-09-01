from __future__ import annotations

import csv
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Literal

from .model import LinearPoint, Vec3


@dataclass(frozen=True)
class VertexFaceQuery:
    p: LinearPoint
    a: LinearPoint
    b: LinearPoint
    c: LinearPoint
    label: bool
    source_index: int


@dataclass(frozen=True)
class EdgeEdgeQuery:
    a0: LinearPoint
    a1: LinearPoint
    b0: LinearPoint
    b1: LinearPoint
    label: bool
    source_index: int


def _row_point(row: list[int]) -> Vec3:
    if len(row) != 7:
        raise ValueError(f"expected 7 columns, got {len(row)}")
    coords = []
    for i in (0, 2, 4):
        numerator, denominator = row[i], row[i + 1]
        if denominator == 0:
            raise ValueError("zero rational denominator")
        coords.append(float(Fraction(numerator, denominator)))
    return Vec3(*coords)


def _load_rows(path: str | Path) -> list[list[int]]:
    rows: list[list[int]] = []
    with Path(path).open("r", newline="", encoding="utf-8") as f:
        for line_no, row in enumerate(csv.reader(f), start=1):
            if not row:
                continue
            if len(row) != 7:
                raise ValueError(f"{path}:{line_no}: expected 7 columns")
            try:
                rows.append([int(x) for x in row])
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: non-integer cell") from exc
    if len(rows) % 8 != 0:
        raise ValueError(f"{path}: row count {len(rows)} is not divisible by 8")
    return rows


def load_sample_queries(path: str | Path, query_type: Literal["vertex-face", "edge-edge"]):
    rows = _load_rows(path)
    out = []
    for index in range(0, len(rows), 8):
        block = rows[index:index + 8]
        labels = {r[6] for r in block}
        if not labels <= {0, 1} or len(labels) != 1:
            raise ValueError(f"{path}: block {index // 8} has inconsistent boolean labels")
        label = bool(next(iter(labels)))
        pts = [_row_point(r) for r in block]
        if query_type == "vertex-face":
            out.append(VertexFaceQuery(
                LinearPoint(pts[0], pts[4]),
                LinearPoint(pts[1], pts[5]),
                LinearPoint(pts[2], pts[6]),
                LinearPoint(pts[3], pts[7]),
                label,
                index // 8,
            ))
        else:
            out.append(EdgeEdgeQuery(
                LinearPoint(pts[0], pts[4]),
                LinearPoint(pts[1], pts[5]),
                LinearPoint(pts[2], pts[6]),
                LinearPoint(pts[3], pts[7]),
                label,
                index // 8,
            ))
    return out


def corpus_statistics(queries: Iterable[VertexFaceQuery | EdgeEdgeQuery]) -> dict[str, int]:
    q = list(queries)
    positives = sum(1 for x in q if x.label)
    return {"queries": len(q), "positive": positives, "negative": len(q) - positives}
