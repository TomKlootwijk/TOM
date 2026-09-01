from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from .ccd import edge_edge_ccd, vertex_face_ccd
from .corpus import EdgeEdgeQuery, VertexFaceQuery
from .model import Status


@dataclass
class EvaluationSummary:
    total: int
    positives: int
    negatives: int
    status_counts: dict[str, int]
    true_positive: int
    true_negative: int
    false_positive: int
    false_negative: int
    inconclusive: int

    @property
    def conclusive(self) -> int:
        return self.true_positive + self.true_negative + self.false_positive + self.false_negative

    @property
    def conclusive_accuracy(self) -> float | None:
        return None if self.conclusive == 0 else (self.true_positive + self.true_negative) / self.conclusive

    def to_dict(self) -> dict:
        return {
            **self.__dict__,
            "conclusive": self.conclusive,
            "conclusive_accuracy": self.conclusive_accuracy,
        }


def evaluate_queries(queries, *, geom_tol: float = 1e-8, time_tol: float = 1e-9, max_intervals: int = 50_000, limit: int | None = None):
    selected = queries if limit is None else queries[:limit]
    counts: Counter[str] = Counter()
    tp = tn = fp = fn = inc = 0
    records = []
    for q in selected:
        if isinstance(q, VertexFaceQuery):
            cert = vertex_face_ccd(q.p, q.a, q.b, q.c, geom_tol=geom_tol, time_tol=time_tol, max_intervals=max_intervals, pair_id=f"vf:{q.source_index}")
        elif isinstance(q, EdgeEdgeQuery):
            cert = edge_edge_ccd(q.a0, q.a1, q.b0, q.b1, geom_tol=geom_tol, time_tol=time_tol, max_intervals=max_intervals, pair_id=f"ee:{q.source_index}")
        else:
            raise TypeError(type(q))
        counts[cert.status.value] += 1
        predicted = cert.status in {Status.HIT, Status.INITIAL_OVERLAP}
        if not cert.conclusive:
            inc += 1
        elif predicted and q.label:
            tp += 1
        elif predicted and not q.label:
            fp += 1
        elif not predicted and q.label:
            fn += 1
        else:
            tn += 1
        records.append({
            "index": q.source_index,
            "label": int(q.label),
            "status": cert.status.value,
            "toi_lower": cert.toi_lower,
            "toi_upper": cert.toi_upper,
            "method": cert.method,
            "condition_indicator": cert.condition_indicator,
            "digest": cert.digest(),
        })
    summary = EvaluationSummary(
        total=len(selected), positives=sum(q.label for q in selected), negatives=sum(not q.label for q in selected),
        status_counts=dict(counts), true_positive=tp, true_negative=tn,
        false_positive=fp, false_negative=fn, inconclusive=inc,
    )
    return summary, records
