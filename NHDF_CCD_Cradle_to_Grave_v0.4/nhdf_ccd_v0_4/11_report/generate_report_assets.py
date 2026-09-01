from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
REPORT = Path(__file__).resolve().parent
FIG = REPORT / "figures"
SUMMARY_PATH = ROOT / "05_benchmarks" / "benchmark_summary.json"


def comma_int(value: float | int) -> str:
    return f"{int(round(float(value))):,}"


def sci(value: float | int) -> str:
    return f"{float(value):.3e}"


def write_macros(data: dict[str, object]) -> None:
    macros = [
        "% generated from 05_benchmarks/benchmark_summary.json",
        f"\\newcommand{{\\BenchQueries}}{{{comma_int(data['query_count'])}}}",
        f"\\newcommand{{\\BenchHits}}{{{comma_int(data['exact_hit_count'])}}}",
        f"\\newcommand{{\\BenchEndpointMisses}}{{{comma_int(data['endpoint_discrete_missed_hit_count'])}}}",
        f"\\newcommand{{\\BenchFalseNegatives}}{{{comma_int(data['ca_false_negatives'])}}}",
        f"\\newcommand{{\\BenchFalsePositives}}{{{comma_int(data['ca_false_positives'])}}}",
        f"\\newcommand{{\\BenchInconclusive}}{{{comma_int(data['ca_inconclusive'])}}}",
        f"\\newcommand{{\\BenchMaxIterations}}{{{comma_int(data['ca_max_iterations'])}}}",
        f"\\newcommand{{\\BenchMeanIterations}}{{{float(data['ca_mean_iterations']):.3f}}}",
        f"\\newcommand{{\\BenchMaxToiError}}{{{sci(data['ca_max_toi_upper_error'])}}}",
        f"\\newcommand{{\\BenchMeanToiError}}{{{sci(data['ca_mean_toi_upper_error'])}}}",
        f"\\newcommand{{\\BenchExactQps}}{{{comma_int(data['exact_queries_per_second'])}}}",
        f"\\newcommand{{\\BenchCaQps}}{{{comma_int(data['ca_queries_per_second'])}}}",
        "",
    ]
    (REPORT / "results_macros.tex").write_text("\n".join(macros), encoding="utf-8")


def save_correctness(data: dict[str, object]) -> None:
    labels = ["Exact hits", "Endpoint\nmisses", "CA false\nnegatives", "CA false\npositives"]
    values = [
        int(data["exact_hit_count"]),
        int(data["endpoint_discrete_missed_hit_count"]),
        int(data["ca_false_negatives"]),
        int(data["ca_false_positives"]),
    ]
    fig, ax = plt.subplots(figsize=(8.3, 4.9))
    bars = ax.bar(labels, values)
    ax.set_title("Generated sphere-sphere validation counts")
    ax.set_ylabel("query count")
    ax.set_ylim(0, max(values) * 1.17 if max(values) else 1)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, max(value, 0) + max(values) * 0.025,
                f"{value:,}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(FIG / "benchmark_correctness.png", dpi=180)
    plt.close(fig)


def save_throughput(data: dict[str, object]) -> None:
    labels = ["Exact quadratic", "Conservative advancement"]
    values = [float(data["exact_queries_per_second"]), float(data["ca_queries_per_second"])]
    fig, ax = plt.subplots(figsize=(8.3, 4.9))
    bars = ax.bar(labels, values)
    ax.set_title("Reference CPython microbenchmark (machine-specific)")
    ax.set_ylabel("queries per second")
    ax.set_ylim(0, max(values) * 1.16 if max(values) else 1)
    ax.tick_params(axis="x", labelrotation=10)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + max(values) * 0.025,
                f"{value:,.0f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(FIG / "benchmark_throughput.png", dpi=180)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    data = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    write_macros(data)
    save_correctness(data)
    save_throughput(data)
    print(f"updated report macros and benchmark figures from {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
