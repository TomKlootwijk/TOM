from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import random
import statistics
import time

from nhdf_ccd import Body, CCDConfig, CCDStatus, LinearMotion, Sphere, StaticMotion, Vec3
from nhdf_ccd.conservative import conservative_advancement
from nhdf_ccd.exact import exact_sphere_sphere
from nhdf_ccd.oracles import SphereSphereOracle


ROOT = Path(__file__).resolve().parent


def make_queries(count: int, seed: int = 20260831) -> list[tuple[Body, Body]]:
    rng = random.Random(seed)
    queries: list[tuple[Body, Body]] = []
    for i in range(count):
        r1 = rng.uniform(0.1, 1.5)
        r2 = rng.uniform(0.1, 1.5)
        a = Body(f"a{i}", Sphere(r1), StaticMotion(Vec3(0.0, 0.0, 0.0)))
        angle = rng.uniform(-math.pi, math.pi)
        distance = rng.uniform(r1 + r2 + 0.05, 20.0)
        p0 = Vec3(distance * math.cos(angle), distance * math.sin(angle), rng.uniform(-0.25, 0.25))
        if i % 2 == 0:
            # Aim through the target with enough travel to pass it within the step.
            speed = rng.uniform(distance + r1 + r2 + 0.2, 2.5 * distance + 4.0)
            direction = (-p0).normalized()
            velocity = direction * speed
        else:
            # Mostly tangential or receding traffic.
            tangent = Vec3(-p0.y, p0.x, 0.0).normalized()
            velocity = tangent * rng.uniform(0.0, 8.0) + p0.normalized() * rng.uniform(-1.0, 3.0)
        b = Body(f"b{i}", Sphere(r2), LinearMotion(p0, velocity))
        queries.append((a, b))
    return queries


def endpoint_discrete_hit(a: Body, b: Body) -> bool:
    r = a.shape.radius + b.shape.radius  # type: ignore[attr-defined]
    return any((b.motion.position(t) - a.motion.position(t)).norm() <= r for t in (0.0, 1.0))


def benchmark(count: int = 5000) -> dict[str, object]:
    config = CCDConfig(distance_tolerance=1e-8, max_iterations=256, use_nhdf_hints=False)
    queries = make_queries(count)

    t0 = time.perf_counter()
    exact = [exact_sphere_sphere(a, b, config) for a, b in queries]
    exact_seconds = time.perf_counter() - t0
    assert all(c is not None for c in exact)

    t0 = time.perf_counter()
    ca = [conservative_advancement(SphereSphereOracle(a, b), config) for a, b in queries]
    ca_seconds = time.perf_counter() - t0

    exact_hits = [c.status == CCDStatus.HIT for c in exact if c is not None]
    ca_hits = [c.status == CCDStatus.HIT for c in ca]
    false_negatives = sum(gt and not pred for gt, pred in zip(exact_hits, ca_hits))
    false_positives = sum((not gt) and pred for gt, pred in zip(exact_hits, ca_hits))
    inconclusive = sum(c.status == CCDStatus.INCONCLUSIVE for c in ca)
    endpoint_misses = sum(gt and not endpoint_discrete_hit(a, b) for gt, (a, b) in zip(exact_hits, queries))
    hit_toi_errors = [
        abs((pred.toi_upper or 0.0) - (gt.toi_upper or 0.0))
        for gt, pred in zip(exact, ca)
        if gt is not None and gt.status == CCDStatus.HIT and pred.status == CCDStatus.HIT
    ]
    iterations = [c.iterations for c in ca]

    summary = {
        "query_count": count,
        "seed": 20260831,
        "exact_hit_count": sum(exact_hits),
        "endpoint_discrete_missed_hit_count": endpoint_misses,
        "ca_false_negatives": false_negatives,
        "ca_false_positives": false_positives,
        "ca_inconclusive": inconclusive,
        "exact_seconds": exact_seconds,
        "ca_seconds": ca_seconds,
        "exact_queries_per_second": count / exact_seconds,
        "ca_queries_per_second": count / ca_seconds,
        "ca_mean_iterations": statistics.fmean(iterations),
        "ca_max_iterations": max(iterations),
        "ca_max_toi_upper_error": max(hit_toi_errors, default=0.0),
        "ca_mean_toi_upper_error": statistics.fmean(hit_toi_errors) if hit_toi_errors else 0.0,
        "environment": "CPython reference; timings are machine-specific and are not product claims",
    }

    (ROOT / "benchmark_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    with (ROOT / "benchmark_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        for key, value in summary.items():
            writer.writerow([key, value])
    return summary


if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2, sort_keys=True))
