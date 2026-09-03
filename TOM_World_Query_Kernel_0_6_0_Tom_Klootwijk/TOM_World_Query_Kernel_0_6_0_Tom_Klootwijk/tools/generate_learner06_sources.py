from __future__ import annotations

"""Generate the finite Learner 0.2 registry, fixtures and formal authorities.

The generated JSON files are the authority.  This generator is deterministic
and remains in the package so a clean source replay can reproduce every byte.
Candidate spaces are explicit, finite, content-addressed and independent of all
observation targets.
"""

from fractions import Fraction
import itertools
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples/learner06"
DATASETS = OUT / "datasets"

from tomagi.canonical import attach_hash, canonical_bytes, content_hash
from tomagi.formal import Limits, attach_program_hash, run_program

SEED_HASH = "sha256:d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
REPAIR_ARTIFACT_HASH = "sha256:f2637bea677cfd83daa2435d16d495556f7a28608ca0af15c19f9e2a2f34fe60"
REPAIR_PROOF_HASH = "sha256:88f1b383fbedfdc15e22001940d65cbc0b518ce3a9f8d9aa27447a9f44f44f3d"
PRIOR_AUTHORITY_HASH = "sha256:2d2b021ca8ced2cf612d58739269f826dda9c3812168cc4dc61dbc251e1a33d5"
PARTITION_POLICY_HASH = "sha256:6463102eca543f58fc8616721e9f67cea69a3aca4b0b00bd16737d76cbd808ff"
FAMILY_IDS = [
    "family:polynomial:0.2",
    "family:piecewise-affine:0.2",
    "family:transition-table:0.2",
    "family:expression-tree:0.2",
]
PRIOR_RESULT = ROOT / "validation/learner052/promotion_authority.materialized.json"


def q(value: int | Fraction, den: int = 1) -> dict[str, int]:
    f = value if isinstance(value, Fraction) else Fraction(value, den)
    return {"num": f.numerator, "den": f.denominator}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def addressed(body: Mapping[str, Any]) -> dict[str, Any]:
    return attach_hash(dict(body))


def candidate(body: Mapping[str, Any]) -> dict[str, Any]:
    return addressed({"schema": "TOM-LEARNER-0.2-CANDIDATE-1.0", **body})


def expression_candidates() -> list[dict[str, Any]]:
    trees: list[tuple[str, dict[str, Any], int]] = []
    x = {"op": "x"}
    trees.append(("x", x, 1))
    for c in range(-2, 3):
        trees.append((f"const:{c}", {"op": "const", "value": q(c)}, 1))
    trees.extend([
        ("neg:x", {"op": "neg", "arg": x}, 2),
        ("abs:x", {"op": "abs", "arg": x}, 2),
        ("square:x", {"op": "square", "arg": x}, 2),
    ])
    # Canonical finite affine and quadratic-like expression forms.
    for a in range(-2, 3):
        for b in range(-2, 3):
            tree = {
                "op": "add",
                "left": {"op": "mul", "left": {"op": "const", "value": q(a)}, "right": x},
                "right": {"op": "const", "value": q(b)},
            }
            trees.append((f"affine:{a}:{b}", tree, 5))
    for b in range(-2, 3):
        tree = {
            "op": "add",
            "left": {"op": "square", "arg": x},
            "right": {"op": "const", "value": q(b)},
        }
        trees.append((f"square-plus:{b}", tree, 4))
    # Deduplicate exact syntax only; semantic duplicates deliberately survive and
    # must produce ambiguity rather than a hidden tie-break.
    seen: set[bytes] = set()
    result: list[dict[str, Any]] = []
    for name, tree, complexity in trees:
        key = canonical_bytes(tree)
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate({
            "id": f"candidate:expression:{name}",
            "family_id": "family:expression-tree:0.2",
            "complexity": complexity,
            "tree": tree,
        }))
    return result


def build_registry() -> tuple[dict[str, Any], dict[str, Any]]:
    partition_policy = addressed({
        "schema": "TOM-LEARNER-0.2-PARTITION-POLICY-1.0",
        "id": "partition:explicit-id-lists:0.2",
        "rule": "partition membership is an explicit ordered observation-ID list; target values are excluded",
        "required_partitions": ["train", "validation", "holdout"],
    })

    poly_specs = list(itertools.product((-1, 0, 1), repeat=3))
    poly_specs.extend([
        (1, -3, 2),   # canonical quadratic fixture
        (1, 2, 0),    # accepted supersession of prior affine authority
        (-2, 0, 0),   # constant fixture
        (2, 2, 0),    # regression-impact rejection fixture
        (0, 2, 0), (0, -2, 0), (2, 0, 0),
    ])
    poly = []
    for c0, c1, c2 in sorted(set(poly_specs)):
        highest = 2 if c2 else 1 if c1 else 0
        poly.append(candidate({
            "id": f"candidate:polynomial:{c0}:{c1}:{c2}",
            "family_id": "family:polynomial:0.2",
            "complexity": highest + 1,
            "coefficients": [q(c0), q(c1), q(c2)],
        }))

    piecewise_specs = [
        # Two accepted benchmark relations.
        (1, 1, 0, -1, 2),
        (1, 0, 1, 2, -1),
        # The same global affine relation at three breakpoints is deliberate
        # semantic ambiguity and must not be tie-broken.
        (-1, 1, 0, 1, 0),
        (1, 1, 0, 1, 0),
        (3, 1, 0, 1, 0),
        # Finite decoys make search nontrivial while remaining explicitly
        # reviewable in the content-addressed family registry.
        (-1, 0, 0, 1, 0), (1, 0, 0, 1, 0), (3, 0, 0, 1, 0),
        (-1, 1, 1, -1, 1), (1, 1, 1, -1, 1), (3, 1, 1, -1, 1),
        (-1, -1, 2, 1, -2), (1, -1, 2, 1, -2), (3, -1, 2, 1, -2),
        (-1, 2, -1, 0, 1), (1, 2, -1, 0, 1), (3, 2, -1, 0, 1),
        (-1, 0, 1, 2, -1), (3, 0, 1, 2, -1),
        (-1, 1, 0, -1, 2), (3, 1, 0, -1, 2),
    ]
    piecewise = []
    for breakpoint, ls, li, rs, ri in piecewise_specs:
        piecewise.append(candidate({
            "id": f"candidate:piecewise:{breakpoint}:{ls}:{li}:{rs}:{ri}",
            "family_id": "family:piecewise-affine:0.2",
            "complexity": 5,
            "breakpoint": q(breakpoint),
            "left": {"slope": q(ls), "intercept": q(li)},
            "right": {"slope": q(rs), "intercept": q(ri)},
        }))

    table = []
    alphabet = ["A", "B", "C"]
    outputs = ["red", "green", "blue"]
    for values in itertools.product(outputs, repeat=len(alphabet)):
        entries = [{"input": key, "output": value} for key, value in zip(alphabet, values)]
        table.append(candidate({
            "id": "candidate:table:" + ":".join(values),
            "family_id": "family:transition-table:0.2",
            "complexity": len(entries),
            "entries": entries,
        }))

    expression = expression_candidates()

    families = [
        addressed({
            "schema": "TOM-LEARNER-0.2-HYPOTHESIS-FAMILY-1.0",
            "id": "family:polynomial:0.2",
            "semantic_version": "0.2.0",
            "kind": "bounded-exact-polynomial",
            "domain": "exact-rational-scalar",
            "codomain": "exact-rational-scalar",
            "search_budget": {"max_candidates": len(poly), "max_degree": 2},
            "candidate_order": "literal-registry-order",
            "candidates": poly,
        }),
        addressed({
            "schema": "TOM-LEARNER-0.2-HYPOTHESIS-FAMILY-1.0",
            "id": "family:piecewise-affine:0.2",
            "semantic_version": "0.2.0",
            "kind": "bounded-piecewise-affine",
            "domain": "exact-rational-scalar",
            "codomain": "exact-rational-scalar",
            "search_budget": {"max_candidates": len(piecewise), "max_segments": 2},
            "candidate_order": "literal-registry-order",
            "candidates": piecewise,
        }),
        addressed({
            "schema": "TOM-LEARNER-0.2-HYPOTHESIS-FAMILY-1.0",
            "id": "family:transition-table:0.2",
            "semantic_version": "0.2.0",
            "kind": "finite-transition-table",
            "domain": "symbol:A|B|C",
            "codomain": "symbol:red|green|blue",
            "search_budget": {"max_candidates": len(table), "complete_inputs": 3},
            "candidate_order": "literal-registry-order",
            "candidates": table,
        }),
        addressed({
            "schema": "TOM-LEARNER-0.2-HYPOTHESIS-FAMILY-1.0",
            "id": "family:expression-tree:0.2",
            "semantic_version": "0.2.0",
            "kind": "bounded-expression-tree",
            "domain": "exact-rational-scalar",
            "codomain": "exact-rational-scalar",
            "operation_registry": ["x", "const", "neg", "abs", "square", "add", "sub", "mul"],
            "search_budget": {"max_candidates": len(expression), "max_depth": 2, "max_complexity": 5},
            "candidate_order": "literal-registry-order",
            "candidates": expression,
        }),
    ]
    registry = addressed({
        "schema": "TOM-LEARNER-0.2-FAMILY-REGISTRY-1.0",
        "id": "registry:learner-family:0.2",
        "seed_sha256": SEED_HASH,
        "partition_policy_hash": partition_policy["content_hash"],
        "family_order": [family["id"] for family in families],
        "families": families,
    })
    return registry, partition_policy


def observation(dataset_id: str, index: int, input_value: Any, target: Any) -> dict[str, Any]:
    return addressed({
        "schema": "TOM-LEARNER-0.2-OBSERVATION-1.0",
        "id": f"observation:{dataset_id}:{index:02d}",
        "input": input_value,
        "target": target,
        "source": "literal-benchmark",
    })


def dataset(dataset_id: str, eligible: list[str], values: list[tuple[Any, Any]],
            train: list[int], validation: list[int], holdout: list[int],
            partition_policy: Mapping[str, Any], *, supersedes: str | None = None) -> dict[str, Any]:
    observations = [observation(dataset_id, i, x, y) for i, (x, y) in enumerate(values)]
    ids = [row["id"] for row in observations]
    parts = {
        "train": [ids[i] for i in train],
        "validation": [ids[i] for i in validation],
        "holdout": [ids[i] for i in holdout],
    }
    assignment_basis = addressed({
        "schema": "TOM-LEARNER-0.2-PARTITION-ASSIGNMENT-1.0",
        "dataset_id": dataset_id,
        "partition_policy_hash": partition_policy["content_hash"],
        "partitions": parts,
    })
    body: dict[str, Any] = {
        "schema": "TOM-LEARNER-0.2-DATASET-1.0",
        "id": dataset_id,
        "eligible_families": eligible,
        "partition_policy_hash": partition_policy["content_hash"],
        "assignment_basis": assignment_basis,
        "observations": observations,
        "partitions": parts,
    }
    if supersedes is not None:
        body["supersedes"] = supersedes
    return addressed(body)


def numeric_values(xs: list[int], fn) -> list[tuple[Any, Any]]:
    return [(q(x), q(fn(Fraction(x)))) for x in xs]


def build_prior_authority() -> dict[str, Any]:
    source = json.loads(PRIOR_RESULT.read_text(encoding="utf-8"))["value"]
    relations = []
    for publication in source["publication_plan"]["publications"]:
        for write in publication["writes"]:
            record = write["record"]
            if record.get("schema") != "TOMAGI-FORMAL-SDF0-RELATION-1.0":
                continue
            a = record["coefficients"]["a"]
            b = record["coefficients"]["b"]
            cases = []
            af, bf = Fraction(a["num"], a["den"]), Fraction(b["num"], b["den"])
            for index, x in enumerate((-3, -1, 0, 2, 5)):
                cases.append({
                    "id": f"case:{record['content_hash'][7:15]}:{index}",
                    "input": q(x),
                    "expected": q(af * x + bf),
                })
            relations.append({
                "content_hash": record["content_hash"],
                "source_id": record["id"],
                "model": candidate({
                    "id": f"prior-model:{record['content_hash'][7:19]}",
                    "family_id": "family:polynomial:0.2",
                    "complexity": 2 if af else 1,
                    "coefficients": [b, a, q(0)],
                }),
                "regression_cases": cases,
            })
    relations.sort(key=lambda item: item["content_hash"])
    if len(relations) != 12:
        raise RuntimeError(f"expected 12 prior relations, found {len(relations)}")
    return addressed({
        "schema": "TOM-LEARNER-0.2-PRIOR-AUTHORITY-1.0",
        "seed_sha256": SEED_HASH,
        "prior_release": "0.5.2",
        "prior_terminal_head": source["terminal_head"],
        "prior_terminal_snapshot_hash": source["terminal_snapshot_hash"],
        "prior_publication_plan_hash": source["publication_plan"]["content_hash"],
        "base_records": _terminal_base_records(source["publication_plan"]),
        "definitions": relations,
    })


def _terminal_base_records(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    terminal = plan["terminal_head"]
    final_pub = plan["publications"][-1]
    records: list[dict[str, Any]] = []
    for write in final_pub["writes"]:
        if write["record"]["content_hash"] in {terminal} or write["namespace"] == "snapshots":
            records.append({"namespace": write["namespace"], "record": write["record"]})
    if not any(item["namespace"] == "commits" and item["record"]["content_hash"] == terminal for item in records):
        raise RuntimeError("prior terminal commit not found")
    return records


def build_datasets(partition_policy: Mapping[str, Any], prior: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    xs9 = [-3, -2, -1, 0, 1, 2, 3, 4, 5]
    ptrain, pval, phold = [0, 1, 3, 5, 7], [2, 6], [4, 8]
    wtrain, wval, whold = [0, 2, 3, 4, 5, 7], [1, 6], [8]
    xs7 = [-3, -2, -1, 0, 1, 2, 3]
    etrain, eval_, ehold = [0, 1, 3, 5, 6], [2], [4]
    first_prior = next(item for item in prior["definitions"] if item["model"]["coefficients"] == [q(1), q(2), q(0)])

    datasets: list[dict[str, Any]] = []
    expected: dict[str, dict[str, Any]] = {}

    def add(record: dict[str, Any], accepted: bool, reason: str, family: str | None = None) -> None:
        datasets.append(record)
        expected[record["id"]] = {"accepted": accepted, "reason": reason, "selected_family": family}

    add(dataset(
        "dataset:poly-quadratic", ["family:polynomial:0.2"],
        numeric_values(xs9, lambda x: 2*x*x - 3*x + 1), ptrain, pval, phold, partition_policy,
    ), True, "accepted", "family:polynomial:0.2")
    add(dataset(
        "dataset:poly-affine-supersession", ["family:polynomial:0.2"],
        numeric_values(xs9, lambda x: 2*x + 1), ptrain, pval, phold, partition_policy,
        supersedes=first_prior["content_hash"],
    ), True, "accepted", "family:polynomial:0.2")
    add(dataset(
        "dataset:poly-constant", ["family:polynomial:0.2"],
        numeric_values(xs9, lambda x: Fraction(-2)), ptrain, pval, phold, partition_policy,
    ), True, "accepted", "family:polynomial:0.2")

    add(dataset(
        "dataset:piecewise-v", ["family:piecewise-affine:0.2"],
        numeric_values(xs9, lambda x: x if x <= 1 else -x + 2), wtrain, wval, whold, partition_policy,
    ), True, "accepted", "family:piecewise-affine:0.2")
    add(dataset(
        "dataset:piecewise-ramp", ["family:piecewise-affine:0.2"],
        numeric_values(xs9, lambda x: Fraction(1) if x <= 1 else 2*x - 1), wtrain, wval, whold, partition_policy,
    ), True, "accepted", "family:piecewise-affine:0.2")

    table_values1 = [("A", "red"), ("B", "green"), ("C", "blue"), ("A", "red"), ("B", "green"), ("C", "blue")]
    table_values2 = [("A", "red"), ("B", "red"), ("C", "blue"), ("A", "red"), ("B", "red"), ("C", "blue")]
    add(dataset("dataset:table-colours", ["family:transition-table:0.2"], table_values1, [0,1,2], [3,4], [5], partition_policy), True, "accepted", "family:transition-table:0.2")
    add(dataset("dataset:table-shared", ["family:transition-table:0.2"], table_values2, [0,1,2], [3,4], [5], partition_policy), True, "accepted", "family:transition-table:0.2")

    add(dataset(
        "dataset:expr-abs", ["family:expression-tree:0.2"],
        numeric_values(xs7, lambda x: abs(x)), etrain, eval_, ehold, partition_policy,
    ), True, "accepted", "family:expression-tree:0.2")
    add(dataset(
        "dataset:expr-square-plus-one", ["family:expression-tree:0.2"],
        numeric_values(xs7, lambda x: x*x + 1), etrain, eval_, ehold, partition_policy,
    ), True, "accepted", "family:expression-tree:0.2")

    # Validation-only outlier: training still selects x^2, then validation rejects.
    values = numeric_values(xs9, lambda x: x*x)
    values[2] = (values[2][0], q(99))
    add(dataset("dataset:poly-validation-outlier", ["family:polynomial:0.2"], values, ptrain, pval, phold, partition_policy), False, "validation-counterexample")

    add(dataset(
        "dataset:piecewise-ambiguity", ["family:piecewise-affine:0.2"],
        numeric_values(xs9, lambda x: x), wtrain, wval, whold, partition_policy,
    ), False, "ambiguous-train-survivors")

    table_bad = [("A", "red"), ("A", "blue"), ("B", "green"), ("C", "blue"), ("B", "green"), ("C", "blue")]
    add(dataset("dataset:table-contradiction", ["family:transition-table:0.2"], table_bad, [0,1,2,3], [4], [5], partition_policy), False, "no-exact-train-candidate")

    add(dataset(
        "dataset:expr-identity-ambiguity", ["family:expression-tree:0.2"],
        numeric_values(xs7, lambda x: x), etrain, eval_, ehold, partition_policy,
    ), False, "ambiguous-train-survivors")

    add(dataset(
        "dataset:cross-family-ambiguity", ["family:polynomial:0.2", "family:expression-tree:0.2"],
        numeric_values(xs7, lambda x: x*x + 1), etrain, eval_, ehold, partition_policy,
    ), False, "ambiguous-train-survivors")

    add(dataset(
        "dataset:supersession-regression-failure", ["family:polynomial:0.2"],
        numeric_values(xs9, lambda x: 2*x + 2), ptrain, pval, phold, partition_policy,
        supersedes=first_prior["content_hash"],
    ), False, "regression-impact")

    add(dataset(
        "dataset:poly-outside-search-space", ["family:polynomial:0.2"],
        numeric_values(xs9, lambda x: 4*x), ptrain, pval, phold, partition_policy,
    ), False, "no-exact-train-candidate")

    oracle = addressed({
        "schema": "TOM-LEARNER-0.2-BENCHMARK-ORACLE-1.0",
        "dataset_count": len(datasets),
        "expected": expected,
        "claim_boundary": "validation-only expected outcomes; not an input to the formal authority",
    })
    return datasets, oracle


# ---------------------------------------------------------------------------
# Formal AST helpers

_counter = itertools.count()


def L(value: Any) -> dict[str, Any]: return {"op": "lit", "value": value}
def R(name: str) -> dict[str, Any]: return {"op": "ref", "name": name}
def G(target: Any, key: Any) -> dict[str, Any]: return {"op": "get", "target": target, "key": key if isinstance(key, dict) else L(key)}
def EQ(a: Any, b: Any) -> dict[str, Any]: return {"op": "eq", "left": a, "right": b}
def NE(a: Any, b: Any) -> dict[str, Any]: return {"op": "ne", "left": a, "right": b}
def LE(a: Any, b: Any) -> dict[str, Any]: return {"op": "le", "left": a, "right": b}
def GT(a: Any, b: Any) -> dict[str, Any]: return {"op": "gt", "left": a, "right": b}
def ADD(a: Any, b: Any) -> dict[str, Any]: return {"op": "add", "left": a, "right": b}
def SUB(a: Any, b: Any) -> dict[str, Any]: return {"op": "sub", "left": a, "right": b}
def MUL(a: Any, b: Any) -> dict[str, Any]: return {"op": "mul", "left": a, "right": b}
def DIV(a: Any, b: Any) -> dict[str, Any]: return {"op": "div", "left": a, "right": b}
def AND(*values: Any) -> dict[str, Any]: return {"op": "and", "values": list(values)}
def OR(*values: Any) -> dict[str, Any]: return {"op": "or", "values": list(values)}
def NOT(value: Any) -> dict[str, Any]: return {"op": "not", "value": value}
def IF(c: Any, t: Any, f: Any) -> dict[str, Any]: return {"op": "if", "condition": c, "then": t, "else": f}
def LIST(items: list[Any]) -> dict[str, Any]: return {"op": "list", "items": items}
def RECORD(fields: Mapping[str, Any]) -> dict[str, Any]: return {"op": "record", "fields": dict(fields)}
def LEN(value: Any) -> dict[str, Any]: return {"op": "len", "value": value}
def IS_STRING(value: Any) -> dict[str, Any]: return {"op": "is_string", "value": value}
def HASH(value: Any) -> dict[str, Any]: return {"op": "hash", "value": value}
def HAS(target: Any, key: str) -> dict[str, Any]: return {"op": "has", "target": target, "key": L(key)}
def KEYS(target: Any) -> dict[str, Any]: return {"op": "keys", "target": target}
def PUT(target: Any, key: str, value: Any) -> dict[str, Any]: return {"op": "put", "target": target, "key": L(key), "value": value}
def CONCAT(left: Any, right: Any) -> dict[str, Any]: return {"op": "concat", "left": left, "right": right}
def APPEND(source: Any, value: Any) -> dict[str, Any]: return {"op": "append", "source": source, "value": value}
def UNIQUE(source: Any) -> dict[str, Any]: return {"op": "unique", "source": source}
def SORT(source: Any, item: str, key: Any) -> dict[str, Any]: return {"op": "sort", "source": source, "item": item, "key": key}
def MAP(source: Any, item: str, body: Any, index: str | None = None) -> dict[str, Any]:
    out = {"op": "map", "source": source, "item": item, "body": body}
    if index: out["index"] = index
    return out
def FILTER(source: Any, item: str, predicate: Any) -> dict[str, Any]: return {"op": "filter", "source": source, "item": item, "predicate": predicate}
def FOLD(source: Any, item: str, acc: str, initial: Any, body: Any) -> dict[str, Any]: return {"op": "fold", "source": source, "item": item, "accumulator": acc, "initial": initial, "body": body}
def LET(bindings: list[tuple[str, Any]], body: Any) -> dict[str, Any]: return {"op": "let", "bindings": [{"name": n, "value": v} for n,v in bindings], "body": body}
def ASSERT(condition: Any, message: str, value: Any) -> dict[str, Any]: return {"op": "assert", "condition": condition, "message": message, "value": value}


def fresh(prefix: str) -> str:
    return f"{prefix}_{next(_counter)}"


def addressed_expr(fields: Mapping[str, Any], prefix: str = "body") -> dict[str, Any]:
    name = fresh(prefix)
    body = RECORD(fields)
    return LET([(name, body)], PUT(R(name), "content_hash", HASH(R(name))))


def contains(source: Any, value: Any, prefix: str = "contains") -> dict[str, Any]:
    item, acc = fresh(prefix+"_item"), fresh(prefix+"_acc")
    return FOLD(source, item, acc, L(False), OR(R(acc), EQ(R(item), value)))


def all_true(source: Any, item: str, predicate: Any, prefix: str = "all") -> dict[str, Any]:
    acc = fresh(prefix+"_acc")
    return FOLD(source, item, acc, L(True), AND(R(acc), predicate))


def exact_keys(record: Any, fields: list[str]) -> dict[str, Any]:
    return EQ(KEYS(record), L(sorted(fields)))


def unique_values(source: Any) -> dict[str, Any]:
    return EQ(LEN(source), LEN(UNIQUE(source)))


def rational_valid(value: Any) -> dict[str, Any]:
    """Recognize the one canonical reduced positive-denominator rational form."""

    numerator = G(value, "num")
    denominator = G(value, "den")
    return AND(
        exact_keys(value, ["den", "num"]),
        GT(denominator, L(0)),
        # div normalizes through Fraction; comparing hashes rather than formal
        # numeric equality rejects unreduced encodings such as 2/2.
        EQ(HASH(value), HASH(DIV(numerator, denominator))),
    )


def addressed_valid(
    record: Any,
    fields: list[str],
    *,
    optional_field: str | None = None,
) -> dict[str, Any]:
    """Return a formal content-address check without trusting a nested hash."""

    body = RECORD({field: G(record, field) for field in fields})
    if optional_field is not None:
        body_with_optional = RECORD({
            **{field: G(record, field) for field in fields},
            optional_field: G(record, optional_field),
        })
        body = IF(HAS(record, optional_field), body_with_optional, body)
    return EQ(G(record, "content_hash"), HASH(body))


def assert_chain(value: Any, checks: list[tuple[Any, str]]) -> dict[str, Any]:
    """Nest assertions so the first declared guard is evaluated first."""

    result = value
    for condition, message in reversed(checks):
        result = ASSERT(condition, message, result)
    return result


def valid_tree(node: Any, depth: int, operations: Any) -> dict[str, Any]:
    """Validate the complete declared expression grammar to a fixed depth."""

    op = G(node, "op")
    leaf = OR(
        AND(EQ(op, L("x")), exact_keys(node, ["op"])),
        AND(
            EQ(op, L("const")),
            exact_keys(node, ["op", "value"]),
            rational_valid(G(node, "value")),
        ),
    )
    if depth == 0:
        return AND(contains(operations, op, "tree_op"), leaf)
    unary = AND(
        contains(L(["neg", "abs", "square"]), op, "tree_unary"),
        exact_keys(node, ["arg", "op"]),
        valid_tree(G(node, "arg"), depth - 1, operations),
    )
    binary = AND(
        contains(L(["add", "sub", "mul"]), op, "tree_binary"),
        exact_keys(node, ["left", "op", "right"]),
        valid_tree(G(node, "left"), depth - 1, operations),
        valid_tree(G(node, "right"), depth - 1, operations),
    )
    return AND(contains(operations, op, "tree_op"), OR(leaf, unary, binary))


def tree_size(node: Any, depth: int) -> dict[str, Any]:
    op = G(node, "op")
    if depth == 0:
        return L(1)
    return IF(
        OR(EQ(op, L("x")), EQ(op, L("const"))),
        L(1),
        IF(
            contains(L(["neg", "abs", "square"]), op, "tree_size_unary"),
            ADD(L(1), tree_size(G(node, "arg"), depth - 1)),
            ADD(
                L(1),
                ADD(
                    tree_size(G(node, "left"), depth - 1),
                    tree_size(G(node, "right"), depth - 1),
                ),
            ),
        ),
    )


def candidate_valid(candidate_expr: Any, family_expr: Any) -> dict[str, Any]:
    family_id = G(candidate_expr, "family_id")
    coefficients = G(candidate_expr, "coefficients")
    entries = G(candidate_expr, "entries")
    tree = G(candidate_expr, "tree")

    poly_fields = ["schema", "id", "family_id", "complexity", "coefficients"]
    piecewise_fields = [
        "schema", "id", "family_id", "complexity", "breakpoint", "left", "right",
    ]
    table_fields = ["schema", "id", "family_id", "complexity", "entries"]
    expression_fields = ["schema", "id", "family_id", "complexity", "tree"]
    candidate_body = IF(
        EQ(family_id, L(FAMILY_IDS[0])),
        RECORD({field: G(candidate_expr, field) for field in poly_fields}),
        IF(
            EQ(family_id, L(FAMILY_IDS[1])),
            RECORD({field: G(candidate_expr, field) for field in piecewise_fields}),
            IF(
                EQ(family_id, L(FAMILY_IDS[2])),
                RECORD({field: G(candidate_expr, field) for field in table_fields}),
                RECORD({field: G(candidate_expr, field) for field in expression_fields}),
            ),
        ),
    )
    candidate_keys = IF(
        EQ(family_id, L(FAMILY_IDS[0])),
        L(sorted(poly_fields + ["content_hash"])),
        IF(
            EQ(family_id, L(FAMILY_IDS[1])),
            L(sorted(piecewise_fields + ["content_hash"])),
            IF(
                EQ(family_id, L(FAMILY_IDS[2])),
                L(sorted(table_fields + ["content_hash"])),
                L(sorted(expression_fields + ["content_hash"])),
            ),
        ),
    )

    expected_poly_complexity = IF(
        NE(G(coefficients, 2), L(q(0))),
        L(3),
        IF(NE(G(coefficients, 1), L(q(0))), L(2), L(1)),
    )
    coefficient = fresh("polynomial_coefficient")
    poly_rationals_valid = all_true(
        coefficients, coefficient, rational_valid(R(coefficient)), "polynomial_coefficients",
    )
    table_entry = fresh("table_contract_entry")
    table_inputs = MAP(entries, table_entry, G(R(table_entry), "input"))
    table_outputs_valid = all_true(
        entries,
        table_entry,
        AND(
            exact_keys(R(table_entry), ["input", "output"]),
            contains(L(["red", "green", "blue"]), G(R(table_entry), "output"), "table_output"),
        ),
        "table_entries",
    )
    expression_operations = G(family_expr, "operation_registry")
    profile_valid = OR(
        AND(
            EQ(family_id, L(FAMILY_IDS[0])),
            EQ(LEN(coefficients), L(3)),
            poly_rationals_valid,
            EQ(G(candidate_expr, "complexity"), expected_poly_complexity),
        ),
        AND(
            EQ(family_id, L(FAMILY_IDS[1])),
            EQ(G(candidate_expr, "complexity"), L(5)),
            rational_valid(G(candidate_expr, "breakpoint")),
            exact_keys(G(candidate_expr, "left"), ["intercept", "slope"]),
            exact_keys(G(candidate_expr, "right"), ["intercept", "slope"]),
            rational_valid(G(G(candidate_expr, "left"), "slope")),
            rational_valid(G(G(candidate_expr, "left"), "intercept")),
            rational_valid(G(G(candidate_expr, "right"), "slope")),
            rational_valid(G(G(candidate_expr, "right"), "intercept")),
        ),
        AND(
            EQ(family_id, L(FAMILY_IDS[2])),
            EQ(LEN(entries), L(3)),
            EQ(G(candidate_expr, "complexity"), LEN(entries)),
            EQ(table_inputs, L(["A", "B", "C"])),
            table_outputs_valid,
        ),
        AND(
            EQ(family_id, L(FAMILY_IDS[3])),
            valid_tree(tree, 2, expression_operations),
            EQ(G(candidate_expr, "complexity"), tree_size(tree, 2)),
            LE(G(candidate_expr, "complexity"), G(G(family_expr, "search_budget"), "max_complexity")),
        ),
    )
    return AND(
        contains(L(FAMILY_IDS), family_id, "candidate_family"),
        EQ(family_id, G(family_expr, "id")),
        EQ(G(candidate_expr, "schema"), L("TOM-LEARNER-0.2-CANDIDATE-1.0")),
        IS_STRING(G(candidate_expr, "id")),
        GT(LEN(G(candidate_expr, "id")), L(0)),
        EQ(KEYS(candidate_expr), candidate_keys),
        profile_valid,
        EQ(G(candidate_expr, "content_hash"), HASH(candidate_body)),
    )


def family_valid(family_expr: Any) -> dict[str, Any]:
    family_id = G(family_expr, "id")
    candidates = G(family_expr, "candidates")
    budget = G(family_expr, "search_budget")
    candidate_item = fresh("family_candidate")
    candidate_id = fresh("family_candidate_id")
    candidate_hash = fresh("family_candidate_hash")

    base_fields = [
        "schema", "id", "semantic_version", "kind", "domain", "codomain",
        "search_budget", "candidate_order", "candidates",
    ]
    expression_fields = base_fields + ["operation_registry"]
    family_body = IF(
        EQ(family_id, L(FAMILY_IDS[3])),
        RECORD({field: G(family_expr, field) for field in expression_fields}),
        RECORD({field: G(family_expr, field) for field in base_fields}),
    )
    expected_keys = IF(
        EQ(family_id, L(FAMILY_IDS[3])),
        L(sorted(expression_fields + ["content_hash"])),
        L(sorted(base_fields + ["content_hash"])),
    )
    profile_valid = OR(
        AND(
            EQ(family_id, L(FAMILY_IDS[0])),
            EQ(G(family_expr, "kind"), L("bounded-exact-polynomial")),
            EQ(G(family_expr, "domain"), L("exact-rational-scalar")),
            EQ(G(family_expr, "codomain"), L("exact-rational-scalar")),
            EQ(KEYS(budget), L(["max_candidates", "max_degree"])),
            EQ(G(budget, "max_degree"), L(2)),
            EQ(G(family_expr, "candidate_order"), L("literal-registry-order")),
        ),
        AND(
            EQ(family_id, L(FAMILY_IDS[1])),
            EQ(G(family_expr, "kind"), L("bounded-piecewise-affine")),
            EQ(G(family_expr, "domain"), L("exact-rational-scalar")),
            EQ(G(family_expr, "codomain"), L("exact-rational-scalar")),
            EQ(KEYS(budget), L(["max_candidates", "max_segments"])),
            EQ(G(budget, "max_segments"), L(2)),
            EQ(G(family_expr, "candidate_order"), L("literal-registry-order")),
        ),
        AND(
            EQ(family_id, L(FAMILY_IDS[2])),
            EQ(G(family_expr, "kind"), L("finite-transition-table")),
            EQ(G(family_expr, "domain"), L("symbol:A|B|C")),
            EQ(G(family_expr, "codomain"), L("symbol:red|green|blue")),
            EQ(KEYS(budget), L(["complete_inputs", "max_candidates"])),
            EQ(G(budget, "complete_inputs"), L(3)),
            EQ(G(family_expr, "candidate_order"), L("literal-registry-order")),
        ),
        AND(
            EQ(family_id, L(FAMILY_IDS[3])),
            EQ(G(family_expr, "kind"), L("bounded-expression-tree")),
            EQ(G(family_expr, "domain"), L("exact-rational-scalar")),
            EQ(G(family_expr, "codomain"), L("exact-rational-scalar")),
            EQ(KEYS(budget), L(["max_candidates", "max_complexity", "max_depth"])),
            EQ(G(budget, "max_complexity"), L(5)),
            EQ(G(budget, "max_depth"), L(2)),
            EQ(G(family_expr, "operation_registry"), L(["x", "const", "neg", "abs", "square", "add", "sub", "mul"])),
            EQ(G(family_expr, "candidate_order"), L("literal-registry-order")),
        ),
    )
    return AND(
        contains(L(FAMILY_IDS), family_id, "family_id"),
        EQ(G(family_expr, "schema"), L("TOM-LEARNER-0.2-HYPOTHESIS-FAMILY-1.0")),
        EQ(G(family_expr, "semantic_version"), L("0.2.0")),
        EQ(KEYS(family_expr), expected_keys),
        profile_valid,
        GT(G(budget, "max_candidates"), L(0)),
        EQ(LEN(candidates), G(budget, "max_candidates")),
        GT(LEN(candidates), L(0)),
        unique_values(MAP(candidates, candidate_id, G(R(candidate_id), "id"))),
        unique_values(MAP(candidates, candidate_hash, G(R(candidate_hash), "content_hash"))),
        all_true(candidates, candidate_item, candidate_valid(R(candidate_item), family_expr), "family_candidates"),
        EQ(G(family_expr, "content_hash"), HASH(family_body)),
    )


def registry_valid(registry_expr: Any, partition_policy_hash: Any) -> dict[str, Any]:
    families = G(registry_expr, "families")
    family = fresh("registry_family")
    family_id = fresh("registry_family_id")
    fields = [
        "schema", "id", "seed_sha256", "partition_policy_hash", "family_order", "families",
    ]
    family_ids = MAP(families, family_id, G(R(family_id), "id"))
    candidate_family = fresh("registry_candidate_family")
    candidate_accumulator = fresh("registry_candidate_accumulator")
    all_candidates = FOLD(
        families,
        candidate_family,
        candidate_accumulator,
        LIST([]),
        CONCAT(
            R(candidate_accumulator),
            G(R(candidate_family), "candidates"),
        ),
    )
    global_candidate = fresh("registry_global_candidate")
    global_candidate_hash = fresh("registry_global_candidate_hash")
    return AND(
        exact_keys(registry_expr, fields + ["content_hash"]),
        EQ(G(registry_expr, "schema"), L("TOM-LEARNER-0.2-FAMILY-REGISTRY-1.0")),
        EQ(G(registry_expr, "id"), L("registry:learner-family:0.2")),
        EQ(G(registry_expr, "seed_sha256"), L(SEED_HASH)),
        EQ(G(registry_expr, "partition_policy_hash"), partition_policy_hash),
        EQ(G(registry_expr, "family_order"), L(FAMILY_IDS)),
        EQ(G(registry_expr, "family_order"), family_ids),
        unique_values(family_ids),
        all_true(families, family, family_valid(R(family)), "registry_families"),
        unique_values(MAP(all_candidates, global_candidate, G(R(global_candidate), "id"))),
        unique_values(MAP(all_candidates, global_candidate_hash, G(R(global_candidate_hash), "content_hash"))),
        addressed_valid(registry_expr, fields),
    )


def partition_policy_valid(policy_expr: Any) -> dict[str, Any]:
    fields = ["schema", "id", "rule", "required_partitions"]
    return AND(
        exact_keys(policy_expr, fields + ["content_hash"]),
        EQ(G(policy_expr, "schema"), L("TOM-LEARNER-0.2-PARTITION-POLICY-1.0")),
        EQ(G(policy_expr, "id"), L("partition:explicit-id-lists:0.2")),
        EQ(G(policy_expr, "required_partitions"), L(["train", "validation", "holdout"])),
        EQ(G(policy_expr, "content_hash"), L(PARTITION_POLICY_HASH)),
        addressed_valid(policy_expr, fields),
    )


def observation_valid(observation_expr: Any) -> dict[str, Any]:
    fields = ["schema", "id", "input", "target", "source"]
    return AND(
        exact_keys(observation_expr, fields + ["content_hash"]),
        EQ(G(observation_expr, "schema"), L("TOM-LEARNER-0.2-OBSERVATION-1.0")),
        IS_STRING(G(observation_expr, "id")),
        GT(LEN(G(observation_expr, "id")), L(0)),
        EQ(G(observation_expr, "source"), L("literal-benchmark")),
        addressed_valid(observation_expr, fields),
    )


def dataset_valid(
    dataset_expr: Any,
    registry_expr: Any,
    partition_policy_hash: Any,
    prior_expr: Any,
) -> dict[str, Any]:
    observations = G(dataset_expr, "observations")
    partitions = G(dataset_expr, "partitions")
    assignment = G(dataset_expr, "assignment_basis")
    train_ids = G(partitions, "train")
    validation_ids = G(partitions, "validation")
    holdout_ids = G(partitions, "holdout")
    partition_ids = CONCAT(train_ids, CONCAT(validation_ids, holdout_ids))
    observation = fresh("dataset_observation")
    observation_id = fresh("dataset_observation_id")
    partition_id = fresh("dataset_partition_id")
    eligible_id = fresh("dataset_eligible_family")
    family_id = fresh("dataset_registry_family")
    superseded_definition = fresh("dataset_superseded_definition")
    observation_ids = MAP(observations, observation_id, G(R(observation_id), "id"))
    registry_family_ids = MAP(G(registry_expr, "families"), family_id, G(R(family_id), "id"))
    prior_definition_hashes = MAP(
        G(prior_expr, "definitions"),
        superseded_definition,
        G(R(superseded_definition), "content_hash"),
    )
    table_profile = contains(
        G(dataset_expr, "eligible_families"), L(FAMILY_IDS[2]), "dataset_table_profile",
    )
    typed_observation = fresh("dataset_typed_observation")
    numeric_observations = all_true(
        observations,
        typed_observation,
        AND(
            rational_valid(G(R(typed_observation), "input")),
            rational_valid(G(R(typed_observation), "target")),
        ),
        "dataset_numeric_observations",
    )
    symbolic_observations = all_true(
        observations,
        typed_observation,
        AND(
            contains(L(["A", "B", "C"]), G(R(typed_observation), "input"), "dataset_symbol_input"),
            contains(
                L(["red", "green", "blue"]),
                G(R(typed_observation), "target"),
                "dataset_symbol_target",
            ),
        ),
        "dataset_symbolic_observations",
    )
    assignment_fields = ["schema", "dataset_id", "partition_policy_hash", "partitions"]
    dataset_fields = [
        "schema", "id", "eligible_families", "partition_policy_hash",
        "assignment_basis", "partitions", "observations",
    ]
    return AND(
        OR(
            AND(NOT(HAS(dataset_expr, "supersedes")), exact_keys(dataset_expr, dataset_fields + ["content_hash"])),
            AND(HAS(dataset_expr, "supersedes"), exact_keys(dataset_expr, dataset_fields + ["supersedes", "content_hash"])),
        ),
        EQ(G(dataset_expr, "schema"), L("TOM-LEARNER-0.2-DATASET-1.0")),
        IS_STRING(G(dataset_expr, "id")),
        GT(LEN(G(dataset_expr, "id")), L(0)),
        OR(
            NOT(HAS(dataset_expr, "supersedes")),
            contains(
                prior_definition_hashes,
                G(dataset_expr, "supersedes"),
                "dataset_supersedes_resolves",
            ),
        ),
        EQ(G(dataset_expr, "partition_policy_hash"), partition_policy_hash),
        GT(LEN(G(dataset_expr, "eligible_families")), L(0)),
        unique_values(G(dataset_expr, "eligible_families")),
        all_true(
            G(dataset_expr, "eligible_families"), eligible_id,
            contains(registry_family_ids, R(eligible_id), "eligible_family_resolves"),
            "eligible_families",
        ),
        exact_keys(partitions, ["holdout", "train", "validation"]),
        exact_keys(assignment, assignment_fields + ["content_hash"]),
        EQ(G(assignment, "schema"), L("TOM-LEARNER-0.2-PARTITION-ASSIGNMENT-1.0")),
        EQ(G(assignment, "dataset_id"), G(dataset_expr, "id")),
        EQ(G(assignment, "partition_policy_hash"), partition_policy_hash),
        EQ(G(assignment, "partitions"), partitions),
        addressed_valid(assignment, assignment_fields),
        GT(LEN(observations), L(0)),
        unique_values(observation_ids),
        all_true(observations, observation, observation_valid(R(observation)), "observations"),
        IF(
            table_profile,
            AND(
                EQ(G(dataset_expr, "eligible_families"), L([FAMILY_IDS[2]])),
                symbolic_observations,
            ),
            numeric_observations,
        ),
        unique_values(train_ids),
        unique_values(validation_ids),
        unique_values(holdout_ids),
        unique_values(partition_ids),
        all_true(partition_ids, partition_id, IS_STRING(R(partition_id)), "partition_id_types"),
        EQ(LEN(partition_ids), LEN(observation_ids)),
        all_true(partition_ids, partition_id, contains(observation_ids, R(partition_id), "partition_resolves"), "partition_ids"),
        all_true(observation_ids, observation_id, contains(partition_ids, R(observation_id), "observation_covered"), "observation_ids"),
        addressed_valid(dataset_expr, dataset_fields, optional_field="supersedes"),
    )


def prior_authority_valid(prior_expr: Any) -> dict[str, Any]:
    fields = [
        "schema", "prior_release", "seed_sha256", "prior_terminal_head",
        "prior_terminal_snapshot_hash", "prior_publication_plan_hash",
        "base_records", "definitions",
    ]
    return AND(
        exact_keys(prior_expr, fields + ["content_hash"]),
        EQ(G(prior_expr, "schema"), L("TOM-LEARNER-0.2-PRIOR-AUTHORITY-1.0")),
        EQ(G(prior_expr, "content_hash"), L(PRIOR_AUTHORITY_HASH)),
        EQ(G(prior_expr, "seed_sha256"), L(SEED_HASH)),
        EQ(G(prior_expr, "prior_release"), L("0.5.2")),
        addressed_valid(prior_expr, fields),
    )


def repair_proof_valid(repair_expr: Any) -> dict[str, Any]:
    fields = [
        "schema", "status", "artifact", "authority", "compile_sidecar",
        "execution", "literal_source", "program",
    ]
    return AND(
        exact_keys(repair_expr, fields + ["content_hash"]),
        EQ(G(repair_expr, "content_hash"), L(REPAIR_PROOF_HASH)),
        EQ(G(repair_expr, "schema"), L("TOM-WQK-0.5.2-CODEX-REPAIR-HANDOFF-PROOF-1.0")),
        EQ(G(repair_expr, "status"), L("pass")),
        EQ(G(G(repair_expr, "authority"), "canonical_seed_sha256"), L(SEED_HASH)),
        EQ(G(G(repair_expr, "artifact"), "sha256"), L(REPAIR_ARTIFACT_HASH)),
        EQ(G(G(repair_expr, "execution"), "python_c_full_trace_equal"), L(True)),
        EQ(G(G(repair_expr, "execution"), "python_c_emit_sequence_equal"), L(True)),
        addressed_valid(repair_expr, fields),
    )


def eval_tree(node: Any, x: Any, depth: int) -> Any:
    op = G(node, "op")
    if depth == 0:
        return IF(EQ(op, L("x")), x, G(node, "value"))
    arg = G(node, "arg")
    left = G(node, "left")
    right = G(node, "right")
    unary = IF(EQ(op, L("neg")), {"op":"neg","value":eval_tree(arg,x,depth-1)},
               IF(EQ(op,L("abs")), {"op":"abs","value":eval_tree(arg,x,depth-1)},
                  MUL(eval_tree(arg,x,depth-1), eval_tree(arg,x,depth-1))))
    binary = IF(EQ(op,L("add")), ADD(eval_tree(left,x,depth-1), eval_tree(right,x,depth-1)),
                IF(EQ(op,L("sub")), SUB(eval_tree(left,x,depth-1), eval_tree(right,x,depth-1)),
                   MUL(eval_tree(left,x,depth-1), eval_tree(right,x,depth-1))))
    return IF(EQ(op,L("x")), x,
              IF(EQ(op,L("const")), G(node,"value"),
                 IF(OR(EQ(op,L("neg")),EQ(op,L("abs")),EQ(op,L("square"))), unary, binary)))


def predict(candidate_expr: Any, observation_expr: Any) -> Any:
    family = G(candidate_expr, "family_id")
    x = G(observation_expr, "input")
    coeffs = G(candidate_expr, "coefficients")
    poly = ADD(ADD(G(coeffs,0), MUL(G(coeffs,1),x)), MUL(G(coeffs,2),MUL(x,x)))
    side = IF(LE(x,G(candidate_expr,"breakpoint")), G(candidate_expr,"left"), G(candidate_expr,"right"))
    piece = ADD(MUL(G(side,"slope"),x),G(side,"intercept"))
    entry_name = fresh("entry")
    matches = FILTER(G(candidate_expr,"entries"), entry_name, EQ(G(R(entry_name),"input"),x))
    table = LET([(fresh("matches"), matches)], L(None))  # replaced below with stable name
    mname = fresh("table_matches")
    table = LET([(mname,matches)],
                IF(EQ(LEN(R(mname)),L(1)),
                   RECORD({"defined":L(True),"value":G(G(R(mname),0),"output")}),
                   RECORD({"defined":L(False),"value":L(None)})))
    expr_value = eval_tree(G(candidate_expr,"tree"),x,2)
    numeric = IF(EQ(family,L("family:polynomial:0.2")),poly,
                 IF(EQ(family,L("family:piecewise-affine:0.2")),piece,expr_value))
    return IF(EQ(family,L("family:transition-table:0.2")),table,
              RECORD({"defined":L(True),"value":numeric}))


def candidate_matches(candidate_expr: Any, observation_expr: Any) -> Any:
    pname = fresh("prediction")
    return LET([(pname,predict(candidate_expr,observation_expr))],
               AND(G(R(pname),"defined"), EQ(G(R(pname),"value"),G(observation_expr,"target"))))


def partition_expr(dataset_expr: Any, name: str) -> Any:
    ids = G(G(dataset_expr,"partitions"),name)
    partition_id = fresh("partition_id")
    observation = fresh("partition_observation")
    matches = fresh("partition_matches")
    # Resolve each declared ID exactly once and preserve the partition's literal
    # order.  dataset_valid executes before this expression and rejects missing,
    # duplicate, overlapping, or uncovered membership.
    return MAP(
        ids,
        partition_id,
        LET([
            (
                matches,
                FILTER(
                    G(dataset_expr, "observations"),
                    observation,
                    EQ(G(R(observation), "id"), R(partition_id)),
                ),
            ),
        ], ASSERT(
            EQ(LEN(R(matches)), L(1)),
            "partition observation ID must resolve exactly once",
            G(R(matches), 0),
        )),
    )


def contradictions_expr(dataset_expr: Any) -> Any:
    pair_name = fresh("pair")
    pairs = {"op":"pairs","source":G(dataset_expr,"observations")}
    filtered = FILTER(pairs,pair_name,
                      AND(EQ(G(G(R(pair_name),"left"),"input"),G(G(R(pair_name),"right"),"input")),
                          NE(G(G(R(pair_name),"left"),"target"),G(G(R(pair_name),"right"),"target"))))
    p = fresh("cpair")
    return MAP(filtered,p,addressed_expr({
        "schema":L("TOM-LEARNER-0.2-CONTRADICTION-1.0"),
        "left_observation":G(G(R(p),"left"),"content_hash"),
        "right_observation":G(G(R(p),"right"),"content_hash"),
        "input":G(G(R(p),"left"),"input"),
        "left_target":G(G(R(p),"left"),"target"),
        "right_target":G(G(R(p),"right"),"target"),
    },"contradiction"))


def fit_input_expr(dataset_expr: Any, registry_expr: Any, train_expr: Any) -> Any:
    o = fresh("trainobs")
    body = RECORD({
        "schema":L("TOM-LEARNER-0.2-TRAIN-FIT-INPUT-1.0"),
        "dataset_id":G(dataset_expr,"id"),
        "family_registry_hash":G(registry_expr,"content_hash"),
        "eligible_families":G(dataset_expr,"eligible_families"),
        "train_observations":MAP(train_expr,o,G(R(o),"content_hash")),
    })
    return HASH(body)


def regression_expr(selected_expr: Any, dataset_expr: Any, prior_expr: Any) -> Any:
    supersedes = IF({"op":"has","target":dataset_expr,"key":L("supersedes")},G(dataset_expr,"supersedes"),L(None))
    dname = fresh("prior_def")
    cname = fresh("reg_case")
    replacement = IF(AND(NE(supersedes,L(None)),EQ(supersedes,G(R(dname),"content_hash")),NE(selected_expr,L(None))),selected_expr,G(R(dname),"model"))
    cases = MAP(G(R(dname),"regression_cases"),cname,RECORD({
        "case_id":G(R(cname),"id"),
        "passed":candidate_matches(replacement,RECORD({"input":G(R(cname),"input"),"target":G(R(cname),"expected")})),
    }))
    casename=fresh("case_result")
    results = MAP(G(prior_expr,"definitions"),dname,LET([(fresh("case_rows"),cases)], L(None)))
    # Rebuild with stable local variable names.
    dname=fresh("prior_def")
    case_rows=fresh("case_rows")
    cname=fresh("reg_case")
    replacement = IF(AND(NE(supersedes,L(None)),EQ(supersedes,G(R(dname),"content_hash")),NE(selected_expr,L(None))),selected_expr,G(R(dname),"model"))
    cases = MAP(G(R(dname),"regression_cases"),cname,RECORD({
        "case_id":G(R(cname),"id"),
        "passed":candidate_matches(replacement,RECORD({"input":G(R(cname),"input"),"target":G(R(cname),"expected")})),
    }))
    cr=fresh("case_result")
    results=MAP(G(prior_expr,"definitions"),dname,LET([(case_rows,cases)],RECORD({
        "definition_hash":G(R(dname),"content_hash"),
        "replaced":AND(NE(supersedes,L(None)),EQ(supersedes,G(R(dname),"content_hash"))),
        "passed":all_true(R(case_rows),cr,G(R(cr),"passed"),"case_all"),
        "cases":R(case_rows),
    })))
    rname=fresh("reg_results")
    rr=fresh("reg_row")
    found = OR(EQ(supersedes,L(None)),contains(MAP(G(prior_expr,"definitions"),fresh("pdhash"),G(R(f"pdhash_{next(_counter)-1}"),"content_hash")),supersedes,"supersede_found"))
    # Above generated binding name is fragile; define explicitly.
    pd=fresh("prior_hash_def")
    found=OR(EQ(supersedes,L(None)),contains(MAP(G(prior_expr,"definitions"),pd,G(R(pd),"content_hash")),supersedes,"supersede_found"))
    return LET([(rname,results)], addressed_expr({
        "schema":L("TOM-LEARNER-0.2-REGRESSION-IMPACT-1.0"),
        "dataset_id":G(dataset_expr,"id"),
        "supersedes":supersedes,
        "superseded_definition_found":found,
        "tested_definitions":LEN(R(rname)),
        "all_pass":AND(found,all_true(R(rname),rr,G(R(rr),"passed"),"reg_all")),
        "results":R(rname),
    },"regression"))


def dataset_result_expr(dataset_expr: Any, registry_expr: Any, prior_expr: Any) -> Any:
    train, validation, holdout = fresh("train"),fresh("validation"),fresh("holdout")
    candidates=fresh("candidates")
    contradictions=fresh("contradictions")
    survivor=fresh("survivor")
    survivors=fresh("survivors")
    selected=fresh("selected")
    val_fail=fresh("val_fail")
    hold_fail=fresh("hold_fail")
    regression=fresh("regression")
    family=fresh("family")
    acc=fresh("candidate_acc")
    eligible_candidates=FOLD(G(registry_expr,"families"),family,acc,LIST([]),
        IF(contains(G(dataset_expr,"eligible_families"),G(R(family),"id"),"eligible"),
           CONCAT(R(acc),G(R(family),"candidates")),R(acc)))
    obs=fresh("fit_obs")
    survivors_expr=FILTER(R(candidates),survivor,all_true(R(train),obs,candidate_matches(R(survivor),R(obs)),"train_all"))
    vobs=fresh("vobs")
    hobs=fresh("hobs")
    val_fail_expr=IF(EQ(R(selected),L(None)),LIST([]),FILTER(R(validation),vobs,NOT(candidate_matches(R(selected),R(vobs)))))
    hold_fail_expr=IF(EQ(R(selected),L(None)),LIST([]),FILTER(R(holdout),hobs,NOT(candidate_matches(R(selected),R(hobs)))))
    accepted=fresh("accepted")
    reason=fresh("reason")
    termination=fresh("termination")
    derivation=fresh("derivation")
    ambiguity=fresh("ambiguity")
    decision=fresh("decision")
    learned=fresh("learned")
    rejection=fresh("rejection")
    supersession=fresh("supersession")
    counterexamples=fresh("counterexamples")
    sitem=fresh("sitem")
    cexv=fresh("cexv")
    cexh=fresh("cexh")
    val_cex=MAP(R(val_fail),cexv,addressed_expr({
        "schema":L("TOM-LEARNER-0.2-COUNTEREXAMPLE-1.0"),
        "partition":L("validation"),"observation_hash":G(R(cexv),"content_hash"),"dataset_id":G(dataset_expr,"id")
    },"vcex"))
    hold_cex=MAP(R(hold_fail),cexh,addressed_expr({
        "schema":L("TOM-LEARNER-0.2-COUNTEREXAMPLE-1.0"),
        "partition":L("holdout"),"observation_hash":G(R(cexh),"content_hash"),"dataset_id":G(dataset_expr,"id")
    },"hcex"))
    supersedes=IF({"op":"has","target":dataset_expr,"key":L("supersedes")},G(dataset_expr,"supersedes"),L(None))
    reason_expr=IF({"op":"gt","left":LEN(R(survivors)),"right":L(1)},L("ambiguous-train-survivors"),
        IF(EQ(LEN(R(survivors)),L(0)),L("no-exact-train-candidate"),
        IF({"op":"gt","left":LEN(R(contradictions)),"right":L(0)},L("contradiction"),
        IF({"op":"gt","left":LEN(R(val_fail)),"right":L(0)},L("validation-counterexample"),
        IF({"op":"gt","left":LEN(R(hold_fail)),"right":L(0)},L("holdout-counterexample"),
        IF(NOT(G(R(regression),"all_pass")),L("regression-impact"),L("accepted")))))))
    accepted_expr=AND(EQ(LEN(R(survivors)),L(1)),EQ(LEN(R(contradictions)),L(0)),EQ(LEN(R(val_fail)),L(0)),EQ(LEN(R(hold_fail)),L(0)),G(R(regression),"all_pass"))
    selected_family=IF(EQ(R(selected),L(None)),L(None),G(R(selected),"family_id"))
    learned_expr=IF(R(accepted),addressed_expr({
        "schema":L("TOM-LEARNER-0.2-HYPOTHESIS-DEFINITION-1.0"),
        "id":G(dataset_expr,"id"),
        "kind":selected_family,
        "domain":L("typed-input"),"codomain":L("typed-output"),
        "model":R(selected),
        "relation_interface":L("SDF0@Def"),
        "zero_locus":L("prediction equals observed target under the selected typed family"),
        "supersedes":supersedes,
        "provenance":RECORD({"dataset_hash":G(dataset_expr,"content_hash"),"family_registry_hash":G(registry_expr,"content_hash")}),
    },"learned_def"),L(None))
    rejection_expr=IF(R(accepted),L(None),addressed_expr({
        "schema":L("TOM-LEARNER-0.2-REJECTION-LINEAGE-1.0"),"dataset_id":G(dataset_expr,"id"),"reason":R(reason),
        "survivor_hashes":MAP(R(survivors),sitem,G(R(sitem),"content_hash")),
    },"reject"))
    supersession_expr=IF(AND(R(accepted),NE(supersedes,L(None))),addressed_expr({
        "schema":L("TOM-LEARNER-0.2-SUPERSESSION-1.0"),"prior_definition":supersedes,
        "replacement_definition":G(R(learned),"content_hash"),"regression_certificate":G(R(regression),"content_hash")
    },"supersession"),L(None))
    ambiguity_expr=IF({"op":"gt","left":LEN(R(survivors)),"right":L(1)},addressed_expr({
        "schema":L("TOM-LEARNER-0.2-AMBIGUITY-1.0"),"dataset_id":G(dataset_expr,"id"),
        "candidate_hashes":MAP(R(survivors),sitem,G(R(sitem),"content_hash")),
        "resolution":L("reject-without-hidden-tie-break")
    },"ambiguity"),L(None))
    return LET([
        (train,partition_expr(dataset_expr,"train")),(validation,partition_expr(dataset_expr,"validation")),(holdout,partition_expr(dataset_expr,"holdout")),
        (candidates,eligible_candidates),(contradictions,contradictions_expr(dataset_expr)),
        (survivors,survivors_expr),(selected,IF(EQ(LEN(R(survivors)),L(1)),G(R(survivors),0),L(None))),
        (val_fail,val_fail_expr),(hold_fail,hold_fail_expr),(regression,regression_expr(R(selected),dataset_expr,prior_expr)),
        (accepted,accepted_expr),(reason,reason_expr),
        (termination,addressed_expr({"schema":L("TOM-LEARNER-0.2-TERMINATION-CERTIFICATE-1.0"),"dataset_id":G(dataset_expr,"id"),"candidate_count":LEN(R(candidates)),"evaluated_count":LEN(R(candidates)),"completed":L(True)},"termination")),
        (derivation,addressed_expr({
            "schema":L("TOM-LEARNER-0.2-DERIVATION-EVIDENCE-1.0"),
            "dataset_id":G(dataset_expr,"id"),
            "eligible_families":G(dataset_expr,"eligible_families"),
            "family_registry_hash":G(registry_expr,"content_hash"),
            "fit_input_hash":fit_input_expr(dataset_expr,registry_expr,R(train)),
            "train_ids":G(G(dataset_expr,"partitions"),"train"),
            "survivor_hashes":MAP(R(survivors),sitem,G(R(sitem),"content_hash")),
        },"derivation")),
        (counterexamples,CONCAT(val_cex,hold_cex)),
        (ambiguity,ambiguity_expr),
        (learned,learned_expr),(rejection,rejection_expr),(supersession,supersession_expr),
        (decision,addressed_expr({"schema":L("TOM-LEARNER-0.2-DECISION-1.0"),"dataset_id":G(dataset_expr,"id"),"accepted":R(accepted),"reason":R(reason),"selected_candidate_hash":IF(EQ(R(selected),L(None)),L(None),G(R(selected),"content_hash")),"regression_certificate":G(R(regression),"content_hash")},"decision")),
    ], addressed_expr({
        "schema":L("TOM-LEARNER-0.2-RESULT-ROW-1.0"),"dataset_id":G(dataset_expr,"id"),"dataset_hash":G(dataset_expr,"content_hash"),
        "eligible_families":G(dataset_expr,"eligible_families"),"split_ids":G(dataset_expr,"partitions"),
        "candidate_count":LEN(R(candidates)),"survivor_hashes":MAP(R(survivors),sitem,G(R(sitem),"content_hash")),
        "selected_candidate":R(selected),"selected_family":selected_family,"accepted":R(accepted),"reason":R(reason),
        "contradictions":R(contradictions),"counterexamples":R(counterexamples),"ambiguity_record":R(ambiguity),
        "termination_certificate":R(termination),"derivation_evidence":R(derivation),"regression_impact":R(regression),
        "learned_definition":R(learned),"rejection_lineage":R(rejection),"supersession_record":R(supersession),"decision":R(decision),
    },"result_row"))


def build_learner_program(dataset_count: int) -> dict[str, Any]:
    input_ref = R("learner06_inputs")
    registry = G(input_ref, 0)
    partition = G(input_ref, 1)
    datasets = LIST([G(input_ref, i) for i in range(2, 2 + dataset_count)])
    prior = G(input_ref, 2 + dataset_count)
    repair = G(input_ref, 3 + dataset_count)
    d = fresh("dataset")
    rows = fresh("rows")
    row = fresh("row")
    ac, rc, mc = fresh("accepted_count"), fresh("rejected_count"), fresh("ambiguity_count")
    value = LET([(rows, MAP(datasets, d, dataset_result_expr(R(d), registry, prior)))], addressed_expr({
        "schema": L("TOM-LEARNER-0.2-FAMILY-AUTHORITY-RESULT-0.6"),
        "profile": L("TOM-LEARNER-0.2-FINITE-FAMILY-AUTHORITY"),
        "family_registry_hash": G(registry, "content_hash"),
        "prior_authority_hash": G(prior, "content_hash"),
        "repair_handoff_artifact_hash": G(G(repair, "artifact"), "sha256"),
        "dataset_count": LEN(R(rows)),
        "results": R(rows),
        "accepted_count": FOLD(R(rows), row, ac, L(0), ADD(R(ac), IF(G(R(row), "accepted"), L(1), L(0)))),
        "rejected_count": FOLD(R(rows), row, rc, L(0), ADD(R(rc), IF(G(R(row), "accepted"), L(0), L(1)))),
        "ambiguity_count": FOLD(R(rows), row, mc, L(0), ADD(R(mc), IF(EQ(G(R(row), "reason"), L("ambiguous-train-survivors")), L(1), L(0)))),
        "claim_boundary": L("finite exact registry over polynomial, piecewise-affine, transition-table and depth-two expression-tree candidates"),
    }, "authority_value"))

    checked_dataset = fresh("checked_dataset")
    dataset_id = fresh("checked_dataset_id")
    dataset_hash = fresh("checked_dataset_hash")
    expression = assert_chain(value, [
        (EQ(LEN(input_ref), L(4 + dataset_count)), "Learner 0.2 input sequence length mismatch"),
        (partition_policy_valid(partition), "Learner 0.2 partition policy is invalid"),
        (
            registry_valid(registry, G(partition, "content_hash")),
            "Learner 0.2 family registry is invalid",
        ),
        (prior_authority_valid(prior), "Learner 0.2 prior authority is invalid"),
        (repair_proof_valid(repair), "Learner 0.2 repair handoff proof is invalid"),
        (
            unique_values(MAP(datasets, dataset_id, G(R(dataset_id), "id"))),
            "Learner 0.2 dataset IDs must be globally unique",
        ),
        (
            unique_values(MAP(datasets, dataset_hash, G(R(dataset_hash), "content_hash"))),
            "Learner 0.2 dataset hashes must be globally unique",
        ),
        (
            all_true(
                datasets,
                checked_dataset,
                dataset_valid(
                    R(checked_dataset), registry, G(partition, "content_hash"), prior,
                ),
                "learner_datasets",
            ),
            "Learner 0.2 dataset contract is invalid",
        ),
    ])
    return attach_program_hash({"schema":"TOMAGI-FORMAL-PROGRAM-1.0","id":"formal:tom-learner-0.2-family-authority:0.6","expression":expression})


def result_row_valid(row_expr: Any) -> dict[str, Any]:
    fields = [
        "schema", "dataset_id", "dataset_hash", "eligible_families", "split_ids",
        "candidate_count", "survivor_hashes", "selected_candidate", "selected_family",
        "accepted", "reason", "contradictions", "counterexamples", "ambiguity_record",
        "termination_certificate", "derivation_evidence", "regression_impact",
        "learned_definition", "rejection_lineage", "supersession_record", "decision",
    ]
    return AND(
        exact_keys(row_expr, fields + ["content_hash"]),
        EQ(G(row_expr, "schema"), L("TOM-LEARNER-0.2-RESULT-ROW-1.0")),
        addressed_valid(row_expr, fields),
        IF(
            G(row_expr, "accepted"),
            AND(
                NE(G(row_expr, "learned_definition"), L(None)),
                EQ(G(row_expr, "rejection_lineage"), L(None)),
            ),
            AND(
                EQ(G(row_expr, "learned_definition"), L(None)),
                NE(G(row_expr, "rejection_lineage"), L(None)),
            ),
        ),
    )


def learner_value_valid(
    value_expr: Any,
    registry_expr: Any,
    prior_expr: Any,
    repair_expr: Any,
    dataset_count: int,
) -> dict[str, Any]:
    fields = [
        "schema", "profile", "family_registry_hash", "prior_authority_hash",
        "repair_handoff_artifact_hash", "dataset_count", "results",
        "accepted_count", "rejected_count", "ambiguity_count", "claim_boundary",
    ]
    rows = G(value_expr, "results")
    row = fresh("validated_result_row")
    row_id = fresh("validated_result_row_id")
    row_hash = fresh("validated_result_row_hash")
    accepted_row = fresh("validated_accepted_row")
    accepted_acc = fresh("validated_accepted_acc")
    rejected_row = fresh("validated_rejected_row")
    rejected_acc = fresh("validated_rejected_acc")
    ambiguity_row = fresh("validated_ambiguity_row")
    ambiguity_acc = fresh("validated_ambiguity_acc")
    accepted_count = FOLD(
        rows, accepted_row, accepted_acc, L(0),
        ADD(R(accepted_acc), IF(G(R(accepted_row), "accepted"), L(1), L(0))),
    )
    rejected_count = FOLD(
        rows, rejected_row, rejected_acc, L(0),
        ADD(R(rejected_acc), IF(G(R(rejected_row), "accepted"), L(0), L(1))),
    )
    ambiguity_count = FOLD(
        rows, ambiguity_row, ambiguity_acc, L(0),
        ADD(
            R(ambiguity_acc),
            IF(
                EQ(G(R(ambiguity_row), "reason"), L("ambiguous-train-survivors")),
                L(1),
                L(0),
            ),
        ),
    )
    return AND(
        exact_keys(value_expr, fields + ["content_hash"]),
        EQ(G(value_expr, "schema"), L("TOM-LEARNER-0.2-FAMILY-AUTHORITY-RESULT-0.6")),
        EQ(G(value_expr, "profile"), L("TOM-LEARNER-0.2-FINITE-FAMILY-AUTHORITY")),
        EQ(G(value_expr, "family_registry_hash"), G(registry_expr, "content_hash")),
        EQ(G(value_expr, "prior_authority_hash"), G(prior_expr, "content_hash")),
        EQ(
            G(value_expr, "repair_handoff_artifact_hash"),
            G(G(repair_expr, "artifact"), "sha256"),
        ),
        EQ(G(value_expr, "dataset_count"), L(dataset_count)),
        EQ(LEN(rows), L(dataset_count)),
        unique_values(MAP(rows, row_id, G(R(row_id), "dataset_id"))),
        unique_values(MAP(rows, row_hash, G(R(row_hash), "content_hash"))),
        all_true(rows, row, result_row_valid(R(row)), "validated_result_rows"),
        EQ(G(value_expr, "accepted_count"), accepted_count),
        EQ(G(value_expr, "rejected_count"), rejected_count),
        EQ(G(value_expr, "ambiguity_count"), ambiguity_count),
        EQ(ADD(accepted_count, rejected_count), L(dataset_count)),
        addressed_valid(value_expr, fields),
    )


def dataset_bundle_valid(
    bundle_expr: Any,
    registry_expr: Any,
    partition_hash: Any,
    prior_expr: Any,
    dataset_count: int,
) -> dict[str, Any]:
    fields = ["schema", "dataset_order", "datasets"]
    datasets = G(bundle_expr, "datasets")
    dataset = fresh("bundle_dataset")
    dataset_id = fresh("bundle_dataset_id")
    dataset_hash = fresh("bundle_dataset_hash")
    return AND(
        exact_keys(bundle_expr, fields + ["content_hash"]),
        EQ(G(bundle_expr, "schema"), L("TOM-LEARNER-0.2-DATASET-BUNDLE-1.0")),
        EQ(LEN(datasets), L(dataset_count)),
        EQ(
            G(bundle_expr, "dataset_order"),
            MAP(datasets, dataset_id, G(R(dataset_id), "id")),
        ),
        unique_values(G(bundle_expr, "dataset_order")),
        unique_values(MAP(datasets, dataset_hash, G(R(dataset_hash), "content_hash"))),
        all_true(
            datasets,
            dataset,
            dataset_valid(R(dataset), registry_expr, partition_hash, prior_expr),
            "bundle_datasets",
        ),
        addressed_valid(bundle_expr, fields),
    )


def promotion_context_valid(
    context_expr: Any,
    registry_expr: Any,
    prior_expr: Any,
    bundle_expr: Any,
) -> dict[str, Any]:
    fields = [
        "schema", "seed_sha256", "expected_parent", "family_registry_hash",
        "dataset_bundle_hash", "dataset_order",
    ]
    return AND(
        exact_keys(context_expr, fields + ["content_hash"]),
        EQ(G(context_expr, "schema"), L("TOM-LEARNER-0.2-PROMOTION-CONTEXT-0.6")),
        EQ(G(context_expr, "seed_sha256"), L(SEED_HASH)),
        EQ(G(context_expr, "expected_parent"), G(prior_expr, "prior_terminal_head")),
        EQ(G(context_expr, "family_registry_hash"), G(registry_expr, "content_hash")),
        EQ(G(context_expr, "dataset_bundle_hash"), G(bundle_expr, "content_hash")),
        EQ(G(context_expr, "dataset_order"), G(bundle_expr, "dataset_order")),
        addressed_valid(context_expr, fields),
    )


def build_dataset_bundle(datasets: list[dict[str, Any]]) -> dict[str, Any]:
    return addressed({
        "schema": "TOM-LEARNER-0.2-DATASET-BUNDLE-1.0",
        "dataset_order": [dataset["id"] for dataset in datasets],
        "datasets": datasets,
    })


def build_promotion_context(
    registry: dict[str, Any],
    bundle: dict[str, Any],
    prior: dict[str, Any],
) -> dict[str, Any]:
    return addressed({
        "schema": "TOM-LEARNER-0.2-PROMOTION-CONTEXT-0.6",
        "seed_sha256": SEED_HASH,
        "expected_parent": prior["prior_terminal_head"],
        "family_registry_hash": registry["content_hash"],
        "dataset_bundle_hash": bundle["content_hash"],
        "dataset_order": bundle["dataset_order"],
    })


def build_promotion_program(
    dataset_count: int,
    learner_program_hash: str,
    learner_result_hash: str,
) -> dict[str, Any]:
    """Build parent-bound promotion authority for the finite family registry.

    Input order is deliberately literal and fixed:

    0. addressed Learner 0.2 result;
    1. addressed prior 0.5.2 authority pin;
    2. addressed family registry;
    3. addressed partition policy;
    4. addressed repair handoff proof;
    5. addressed promotion context;
    6. addressed bundle containing every source dataset.

    The resulting 1.1 publication plan carries the exact immutable prefix
    needed to reconstruct the prior HEAD and all new source evidence.  The host
    store only validates, persists and compare-and-swaps that formal plan.
    """

    inp = R("promotion06_inputs")
    learner_result = G(inp, 0)
    prior = G(inp, 1)
    registry = G(inp, 2)
    partition = G(inp, 3)
    repair = G(inp, 4)
    context = G(inp, 5)
    dataset_bundle = G(inp, 6)
    datasets = G(dataset_bundle, "datasets")
    rows = G(G(learner_result, "value"), "results")

    descriptor = addressed_expr({
        "schema": L("TOMAGI-IMMUTABLE-STORE-DESCRIPTOR-1.0"),
        "profile": L("TOM-LEARNER-0.2-PROMOTION-AUTHORITY"),
        "seed_sha256": L(SEED_HASH),
        "base_world_hash": G(prior, "prior_terminal_head"),
        "base_handoff_hash": G(prior, "content_hash"),
        "corrective_handoff_hash": L(REPAIR_ARTIFACT_HASH),
        "namespaces": L(["commits", "objects", "snapshots", "transactions"]),
        "head_namespace": L("commits"),
        "record_encoding": L("canonical-json-plus-lf"),
        "publication_rule": L("write-immutable-records-then-cas-head"),
    }, "descriptor")

    # The immutable prefix explicitly carries the prior terminal snapshot and
    # commit plus every new source record required by the promotion suffix.
    base_dataset = fresh("base_dataset")
    base_row = fresh("base_row")
    base_records = CONCAT(
        G(prior, "base_records"),
        CONCAT(
            LIST([
                RECORD({"namespace": L("objects"), "record": prior}),
                RECORD({"namespace": L("objects"), "record": registry}),
                RECORD({"namespace": L("objects"), "record": partition}),
                RECORD({"namespace": L("objects"), "record": repair}),
                RECORD({"namespace": L("objects"), "record": context}),
                RECORD({"namespace": L("objects"), "record": dataset_bundle}),
                RECORD({"namespace": L("objects"), "record": learner_result}),
            ]),
            CONCAT(
                MAP(datasets, base_dataset,
                    RECORD({"namespace": L("objects"), "record": R(base_dataset)})),
                MAP(rows, base_row,
                    RECORD({"namespace": L("objects"), "record": R(base_row)})),
            ),
        ),
    )

    acc = fresh("pub_acc")
    row = fresh("promotion_row")
    row_objects = fresh("row_objects")
    evidence_hashes = fresh("evidence_hashes")
    snapshot = fresh("snapshot")
    transaction = fresh("transaction")
    commit = fresh("commit")
    writes = fresh("writes")
    publication = fresh("publication")
    expected = G(R(acc), "head")
    parent_snapshot = G(R(acc), "snapshot")
    sequence = {"op": "floor", "value": ADD(G(R(acc), "sequence"), L(1))}

    obj = fresh("row_object")
    objects = FILTER(
        LIST([
            G(R(row), "termination_certificate"),
            G(R(row), "derivation_evidence"),
            G(R(row), "regression_impact"),
            G(R(row), "decision"),
            G(R(row), "ambiguity_record"),
            G(R(row), "learned_definition"),
            G(R(row), "rejection_lineage"),
            G(R(row), "supersession_record"),
        ]),
        obj,
        NE(R(obj), L(None)),
    )

    evidence_obj = fresh("evidence_object")
    evidence_sort = fresh("evidence_sort")
    evidence = UNIQUE(SORT(
        CONCAT(
            LIST([
                G(R(row), "dataset_hash"),
                G(R(row), "content_hash"),
                G(registry, "content_hash"),
                G(partition, "content_hash"),
                G(repair, "content_hash"),
                G(learner_result, "content_hash"),
                G(context, "content_hash"),
                G(prior, "content_hash"),
            ]),
            MAP(R(row_objects), evidence_obj, G(R(evidence_obj), "content_hash")),
        ),
        evidence_sort,
        R(evidence_sort),
    ))

    snapshot_expr = addressed_expr({
        "schema": L("TOM-LEARNER-0.2-PROMOTION-SNAPSHOT-0.6"),
        "sequence": sequence,
        "parent_snapshot": parent_snapshot,
        "parent_commit": expected,
        "dataset_id": G(R(row), "dataset_id"),
        "decision_hash": G(G(R(row), "decision"), "content_hash"),
        "published_definition": IF(
            G(R(row), "accepted"),
            G(G(R(row), "learned_definition"), "content_hash"),
            L(None),
        ),
        "rejection_lineage": IF(
            G(R(row), "accepted"),
            L(None),
            G(G(R(row), "rejection_lineage"), "content_hash"),
        ),
        "supersession_record": IF(
            EQ(G(R(row), "supersession_record"), L(None)),
            L(None),
            G(G(R(row), "supersession_record"), "content_hash"),
        ),
    }, "snapshot")

    transaction_expr = addressed_expr({
        "schema": L("TOM-LEARNER-0.2-PROMOTION-TRANSACTION-0.6"),
        "sequence": sequence,
        "expected_parent": expected,
        "dataset_id": G(R(row), "dataset_id"),
        "evidence_hashes": R(evidence_hashes),
        "decision_hash": G(G(R(row), "decision"), "content_hash"),
        "snapshot_hash": G(R(snapshot), "content_hash"),
        "authority_program_hash": G(learner_result, "program_hash"),
        "authority_result_hash": G(learner_result, "content_hash"),
        "family_registry_hash": G(registry, "content_hash"),
        "source_dataset_hash": G(R(row), "dataset_hash"),
    }, "transaction")

    commit_expr = addressed_expr({
        "schema": L("TOM-LEARNER-0.2-PROMOTION-COMMIT-0.6"),
        "sequence": sequence,
        "parent_commit": expected,
        "snapshot_hash": G(R(snapshot), "content_hash"),
        "transaction_hash": G(R(transaction), "content_hash"),
        "dataset_id": G(R(row), "dataset_id"),
        "status": IF(G(R(row), "accepted"), L("accepted"), L("rejected")),
    }, "commit")

    write_obj = fresh("write_object")
    writes_expr = CONCAT(
        MAP(
            R(row_objects), write_obj,
            RECORD({"namespace": L("objects"), "record": R(write_obj)}),
        ),
        LIST([
            RECORD({"namespace": L("snapshots"), "record": R(snapshot)}),
            RECORD({"namespace": L("transactions"), "record": R(transaction)}),
            RECORD({"namespace": L("commits"), "record": R(commit)}),
        ]),
    )

    required_sort = fresh("required_sort")
    publication_expr = addressed_expr({
        "schema": L("TOMAGI-IMMUTABLE-PUBLICATION-1.0"),
        "profile": L("TOM-LEARNER-0.2-PROMOTION-AUTHORITY"),
        "sequence": sequence,
        "expected_head": expected,
        "replacement_head": G(R(commit), "content_hash"),
        "required_hashes": UNIQUE(SORT(
            CONCAT(R(evidence_hashes), LIST([expected])),
            required_sort,
            R(required_sort),
        )),
        "writes": R(writes),
    }, "publication")

    fold_body = LET([
        (row_objects, objects),
        (evidence_hashes, evidence),
        (snapshot, snapshot_expr),
        (transaction, transaction_expr),
        (commit, commit_expr),
        (writes, writes_expr),
        (publication, publication_expr),
    ], RECORD({
        "publications": APPEND(G(R(acc), "publications"), R(publication)),
        "head": G(R(commit), "content_hash"),
        "snapshot": G(R(snapshot), "content_hash"),
        "sequence": sequence,
    }))

    initial = RECORD({
        "publications": LIST([]),
        "head": G(prior, "prior_terminal_head"),
        "snapshot": G(prior, "prior_terminal_snapshot_hash"),
        "sequence": L(19),
    })
    folded = fresh("folded")
    plan = fresh("plan")
    plan_expr = addressed_expr({
        "schema": L("TOMAGI-IMMUTABLE-PUBLICATION-PLAN-1.1"),
        "profile": L("TOM-LEARNER-0.2-PROMOTION-AUTHORITY"),
        "store_descriptor": R("descriptor"),
        "initial_head": G(prior, "prior_terminal_head"),
        "base_records": R("base_records"),
        "publications": G(R(folded), "publications"),
        "terminal_head": G(R(folded), "head"),
    }, "plan")

    value = LET([
        ("descriptor", descriptor),
        ("base_records", base_records),
        (folded, FOLD(rows, row, acc, initial, fold_body)),
        (plan, plan_expr),
    ], addressed_expr({
        "schema": L("TOM-LEARNER-0.2-PROMOTION-AUTHORITY-RESULT-0.6"),
        "profile": L("TOM-LEARNER-0.2-PROMOTION-AUTHORITY"),
        "learner_result_hash": G(learner_result, "content_hash"),
        "family_registry_hash": G(registry, "content_hash"),
        "prior_authority_hash": G(prior, "content_hash"),
        "dataset_bundle_hash": G(dataset_bundle, "content_hash"),
        "publication_count": LEN(G(R(plan), "publications")),
        "publication_plan": R(plan),
        "terminal_head": G(R(plan), "terminal_head"),
        "claim_boundary": L(
            "formal promotion of finite family-registry decisions under the repaired 0.5.2 expected-parent authority"
        ),
    }, "promotion_value"))

    learner_inputs = CONCAT(
        LIST([registry, partition]),
        CONCAT(datasets, LIST([prior, repair])),
    )
    expected_learner_inputs_hash = HASH(RECORD({"learner06_inputs": learner_inputs}))
    dataset_id = fresh("promotion_dataset_id")
    dataset_hash = fresh("promotion_dataset_hash")
    row_id = fresh("promotion_result_row_id")
    row_dataset_hash = fresh("promotion_result_dataset_hash")
    result_fields = ["schema", "program_hash", "inputs_hash", "steps", "value"]
    expression = assert_chain(value, [
        (EQ(LEN(inp), L(7)), "Learner 0.2 promotion input sequence length mismatch"),
        (partition_policy_valid(partition), "promotion partition policy is invalid"),
        (prior_authority_valid(prior), "promotion prior authority is invalid"),
        (repair_proof_valid(repair), "promotion repair handoff proof is invalid"),
        (
            registry_valid(registry, G(partition, "content_hash")),
            "promotion family registry is invalid",
        ),
        (
            dataset_bundle_valid(
                dataset_bundle,
                registry,
                G(partition, "content_hash"),
                prior,
                dataset_count,
            ),
            "promotion dataset bundle is invalid",
        ),
        (
            promotion_context_valid(context, registry, prior, dataset_bundle),
            "promotion context is invalid",
        ),
        (
            exact_keys(learner_result, result_fields + ["content_hash"]),
            "promotion learner result shape is invalid",
        ),
        (
            EQ(G(learner_result, "schema"), L("TOMAGI-FORMAL-RESULT-1.0")),
            "promotion learner result schema is invalid",
        ),
        (
            addressed_valid(learner_result, result_fields),
            "promotion learner result content hash is invalid",
        ),
        (
            EQ(G(learner_result, "content_hash"), L(learner_result_hash)),
            "promotion learner result is not the generated literal result",
        ),
        (
            EQ(G(learner_result, "program_hash"), L(learner_program_hash)),
            "promotion learner program identity mismatch",
        ),
        (
            EQ(G(learner_result, "inputs_hash"), expected_learner_inputs_hash),
            "promotion learner input-set identity mismatch",
        ),
        (
            learner_value_valid(
                G(learner_result, "value"), registry, prior, repair, dataset_count,
            ),
            "promotion learner value is invalid",
        ),
        (
            EQ(
                MAP(datasets, dataset_id, G(R(dataset_id), "id")),
                MAP(rows, row_id, G(R(row_id), "dataset_id")),
            ),
            "promotion learner row order does not match dataset order",
        ),
        (
            EQ(
                MAP(datasets, dataset_hash, G(R(dataset_hash), "content_hash")),
                MAP(rows, row_dataset_hash, G(R(row_dataset_hash), "dataset_hash")),
            ),
            "promotion learner row dataset hashes do not match source datasets",
        ),
    ])
    return attach_program_hash({
        "schema": "TOMAGI-FORMAL-PROGRAM-1.0",
        "id": "formal:tom-learner-0.2-promotion-authority:0.6",
        "expression": expression,
    })


def build_literal_source(formal_path: Path, sources: list[Path], input_name: str, output_prefix: str, *, max_cells: int = 300_000) -> dict[str, Any]:
    from tomagi.canonical import attach_hash
    definitions=[]
    def add(body):
        definitions.append(attach_hash(body))
    add({"id":"tom:seed","kind":"canonical-seed","domain":"none","codomain":"bytes","dependencies":[],"phase":"parse","order":0,"operation":{"op":"seed.bytes"},"parameters":{},"limits":{},"provenance":{"source":"canonical TOM seed"},"seed_tokens":["TOM1"]})
    add({"id":"tom:tokens","kind":"seed-parse","domain":"bytes","codomain":"record","dependencies":["tom:seed"],"phase":"normalize","order":0,"operation":{"op":"seed.tokens"},"parameters":{},"limits":{},"provenance":{"source":"canonical TOM grammar"},"seed_tokens":["TopologicalOpenModular"]})
    source_ids=[]
    all_sources=[formal_path,*sources]
    for index,path in enumerate(all_sources):
        raw=path.read_bytes(); ident=f"source:{index:03d}"; source_ids.append(ident)
        add({"id":ident,"kind":"literal-json-source","domain":"seed-record","codomain":"record","dependencies":["tom:tokens"],"phase":"resolve","order":index,"operation":{"op":"source.json"},"parameters":{"path":Path(__import__("os").path.relpath(path, OUT)).as_posix(),"bytes":len(raw),"sha256":"sha256:"+__import__('hashlib').sha256(raw).hexdigest(),"canonical_newline":True,"verify_content_hash":True},"limits":{},"provenance":{"source":"Learner 0.2 literal authority input"},"seed_tokens":["Pi"]})
    # The formal program is a separate evaluator dependency, not one of its own
    # named inputs.  Only the declared data/proof sources enter inputs_hash.
    add({"id":"authority:inputs","kind":"record-sequence","domain":"record-sequence","codomain":"sequence","dependencies":source_ids[1:],"phase":"construct","order":0,"operation":{"op":"sequence.construct"},"parameters":{},"limits":{},"provenance":{"source":"declared formal input order"},"seed_tokens":["Pi"]})
    add({"id":"authority:evaluate","kind":"formal-evaluation","domain":"formal-program-sequence","codomain":"record","dependencies":[source_ids[0],"authority:inputs"],"phase":"transform","order":0,"operation":{"op":"formal.evaluate"},"parameters":{"input_name":input_name},"limits":{},"provenance":{"source":"static formal Learner 0.2 authority"},"seed_tokens":["guard"]})
    add({"id":"authority:bytes","kind":"canonical-encoding","domain":"record","codomain":"bytes","dependencies":["authority:evaluate"],"phase":"event","order":0,"operation":{"op":"canonical.encode"},"parameters":{"terminal_newline":True},"limits":{},"provenance":{"source":"canonical formal result"},"seed_tokens":["event"]})
    add({"id":"authority:emit","kind":"byte-emission","domain":"bytes","codomain":"cell_graph","dependencies":["authority:bytes"],"phase":"transition","order":0,"operation":{"op":"emit.graph"},"parameters":{"chunk_bytes":4,"byte_order":"little","id_prefix":f"cell:{output_prefix}","key_base":{"rho":10000,"theta":0,"tick":0,"phi":0},"key_field":"rho","aux_base":1000,"halt_last":True},"limits":{},"provenance":{"source":"generic authenticated EMIT"},"seed_tokens":["transition"]})
    add({"id":"authority:state","kind":"initial-state","domain":"seed-record","codomain":"state64","dependencies":["tom:tokens"],"phase":"construct","order":1,"operation":{"op":"state64.construct"},"parameters":{"fields":{}},"limits":{},"provenance":{"source":"zero initial state"},"seed_tokens":["lineage"]})
    add({"id":"authority:actual-seed-hash","kind":"computed-hash","domain":"bytes","codomain":"string","dependencies":["tom:seed"],"phase":"construct","order":2,"operation":{"op":"hash.sha256"},"parameters":{"prefix":True},"limits":{},"provenance":{"source":"computed canonical root hash"},"seed_tokens":["TOM1"]})
    add({"id":"authority:expected-seed-hash","kind":"literal-hash","domain":"none","codomain":"string","dependencies":[],"phase":"construct","order":3,"operation":{"op":"literal"},"parameters":{"result_type":"string","value":SEED_HASH},"limits":{},"provenance":{"source":"declared canonical root hash"},"seed_tokens":["TOM1"]})
    add({"id":"authority:guard","kind":"hash-guard","domain":"hash-pair","codomain":"bool","dependencies":["authority:actual-seed-hash","authority:expected-seed-hash"],"phase":"guard","order":0,"operation":{"op":"assert.equal"},"parameters":{},"limits":{},"provenance":{"source":"canonical root guard"},"seed_tokens":["guard"]})
    add({"id":"program:root","kind":"artifact-program","domain":"state-graph-guard","codomain":"program","dependencies":["authority:state","authority:emit","authority:guard"],"phase":"lineage","order":0,"operation":{"op":"program.construct"},"parameters":{"seed":1414483271,"default_ticks":max_cells,"emit_bytes":True},"limits":{},"provenance":{"source":"Learner 0.2 formal authority program"},"seed_tokens":["lineage"]})
    return {"tomagi_version":"1.0.0","compilation_profile":"TOM-SEEDED-COMPILATION-1.0","title":f"TOM Learner 0.2 {output_prefix}","seed_genome":{"path":"../../TOM_seed_genome_2026-09-01.txt","bytes":244,"sha256":SEED_HASH[7:],"grammar_id":"TOM-SEED-GRAMMAR-1.0","token_registry":"../../spec/tom_seed_token_registry_1_0.json"},"root_definition":"program:root","budgets":{"max_definitions":128,"max_cells":max_cells,"max_output_bytes":16000000,"max_sequence_items":10000,"max_repeat":1,"max_expression_depth":256,"max_expression_nodes":4000000,"max_string_bytes":8000000},"definitions":definitions}


def main() -> int:
    OUT.mkdir(parents=True,exist_ok=True); DATASETS.mkdir(parents=True,exist_ok=True)
    registry,partition_policy=build_registry(); prior=build_prior_authority(); datasets,oracle=build_datasets(partition_policy,prior)
    write_json(OUT/"family_registry.json",registry); write_json(OUT/"partition_policy.json",partition_policy); write_json(OUT/"prior_authority.json",prior); write_json(OUT/"benchmark_oracle.json",oracle)
    for record in datasets: write_json(DATASETS/(record["id"].replace(":","_")+".json"),record)
    repair_source=ROOT/"sources/codex_0_5_2_repair/CODEX_KERNEL_0_5_2_REPAIR_HANDOFF_PROOF.json"
    repair_path=OUT/"repair_handoff_proof.json"
    repair=json.loads(repair_source.read_text(encoding="utf-8"))
    write_json(repair_path,repair)
    learner=build_learner_program(len(datasets)); write_json(OUT/"learner06_family_authority.formal.json",learner)
    learner_sources=[OUT/"family_registry.json",OUT/"partition_policy.json",*[DATASETS/(r["id"].replace(":","_")+".json") for r in datasets],OUT/"prior_authority.json",repair_path]
    literal=build_literal_source(OUT/"learner06_family_authority.formal.json",learner_sources,"learner06_inputs","learner06-family",max_cells=250000)
    # source paths are relative to examples/learner06; repair path is outside and already represented with relative path.
    write_json(OUT/"learner06_family_authority.literal.json",literal)
    dataset_bundle=build_dataset_bundle(datasets)
    write_json(OUT/"dataset_bundle.json",dataset_bundle)
    context=build_promotion_context(registry,dataset_bundle,prior)
    write_json(OUT/"promotion_context.json",context)
    expected_learner_result=run_program(
        learner,
        {"learner06_inputs":[registry,partition_policy,*datasets,prior,repair]},
        limits=Limits(
            max_steps=4_000_000,
            max_depth=256,
            max_collection_items=20_000,
            max_value_nodes=4_000_000,
            max_canonical_bytes=16_000_000,
        ),
    )
    promotion=build_promotion_program(
        len(datasets),learner["content_hash"],expected_learner_result["content_hash"],
    )
    write_json(OUT/"learner06_promotion_authority.formal.json",promotion)
    # Promotion literal source is generated later after learner materialization exists.
    print(json.dumps({"families":len(registry["families"]),"candidates":sum(len(f["candidates"]) for f in registry["families"]),"datasets":len(datasets),"registry_hash":registry["content_hash"],"learner_program_hash":learner["content_hash"],"promotion_program_hash":promotion["content_hash"]},indent=2,sort_keys=True))
    return 0


if __name__=="__main__": raise SystemExit(main())
