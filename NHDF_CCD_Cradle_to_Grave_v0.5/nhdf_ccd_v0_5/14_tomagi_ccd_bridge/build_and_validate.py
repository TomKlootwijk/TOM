from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


BRIDGE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = BRIDGE_DIR.parents[2]
SOURCE_PATH = BRIDGE_DIR / "ccd_vf_q4.source.json"
REGISTRY_PATH = BRIDGE_DIR / "token_registry_1_0.json"
FORMAL_PROFILE_PATH = BRIDGE_DIR / "FORMAL_PROFILE.md"
SEED_PATH = REPOSITORY_ROOT / "TOM_seed_genome_2026-09-01.txt"
GENESIS_ZIP = REPOSITORY_ROOT / "TOM_Genesis_1_0_Tom_Klootwijk.zip"
GENESIS_RUNTIME_SHA256 = "ca5214eb9691f4f1e8b9a8e025fa3eb0b7d6003fcb55c0364d9e874be3483152"
SEED_SHA256 = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
REGISTRY_HASH = "sha256:b14140cf9800e186701557ed982d692931966ea957e5790c1e6b4989e854c609"

ARTIFACT_NAMES = (
    "ccd_vf_q4.tmg",
    "ccd_vf_q4.compile_manifest.json",
    "ccd_vf_q4.certificate.json",
    "ccd_vf_q4.replay.json",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _definition_hash(definition: dict[str, Any]) -> str:
    body = {key: value for key, value in definition.items() if key != "content_hash"}
    return "sha256:" + _sha256_bytes(_canonical_bytes(body))


def rehash_source() -> None:
    document = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    for definition in document["definitions"]:
        definition["content_hash"] = _definition_hash(definition)
    SOURCE_PATH.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _verify_input_boundaries() -> None:
    required = (SOURCE_PATH, REGISTRY_PATH, SEED_PATH, GENESIS_ZIP)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("missing bridge inputs: " + ", ".join(missing))
    if len(SEED_PATH.read_bytes()) != 244 or _sha256_file(SEED_PATH) != SEED_SHA256:
        raise RuntimeError("authoritative TOM seed boundary mismatch")
    if _sha256_file(GENESIS_ZIP) != GENESIS_RUNTIME_SHA256:
        raise RuntimeError("Genesis runtime archive boundary mismatch")

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if registry.get("content_hash") != REGISTRY_HASH:
        raise RuntimeError("token registry declared content hash mismatch")
    registry_body = {key: value for key, value in registry.items() if key != "content_hash"}
    if "sha256:" + _sha256_bytes(_canonical_bytes(registry_body)) != REGISTRY_HASH:
        raise RuntimeError("token registry canonical content hash mismatch")

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    bad = [
        definition["id"]
        for definition in source["definitions"]
        if definition.get("content_hash") != _definition_hash(definition)
    ]
    if bad:
        raise RuntimeError("definition hash mismatch: " + ", ".join(bad))


def _tomagi_environment() -> dict[str, str]:
    runtime = GENESIS_ZIP / "TOM_Genesis_1_0_Tom_Klootwijk" / "src" / "python"
    environment = os.environ.copy()
    old_path = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = str(runtime) + (os.pathsep + old_path if old_path else "")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def _run_tomagi(arguments: list[str], cwd: Path) -> str:
    command = [sys.executable, "-B", "-m", "tomagi", *arguments]
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=_tomagi_environment(),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "TOMAGI command failed\n"
            + " ".join(command)
            + "\nstdout:\n"
            + completed.stdout
            + "\nstderr:\n"
            + completed.stderr
        )
    return completed.stdout


def _build_once(directory: Path) -> dict[str, bytes]:
    _run_tomagi(
        [
            "compile",
            str(SOURCE_PATH),
            "ccd_vf_q4.tmg",
            "--manifest",
            "ccd_vf_q4.compile_manifest.json",
        ],
        directory,
    )
    _run_tomagi(
        [
            "materialize",
            "ccd_vf_q4.tmg",
            "ccd_vf_q4.certificate.json",
            "--trace-output",
            "ccd_vf_q4.replay.json",
        ],
        directory,
    )
    return {name: (directory / name).read_bytes() for name in ARTIFACT_NAMES}


def _definition(document: dict[str, Any], identifier: str) -> dict[str, Any]:
    try:
        return next(item for item in document["definitions"] if item["id"] == identifier)
    except StopIteration as exc:
        raise RuntimeError(f"missing required definition {identifier}") from exc


def _fixture_binding(document: dict[str, Any]) -> dict[str, Any]:
    hit = _definition(document, "artifact:hit-record")["parameters"]["value"]
    miss = _definition(document, "artifact:miss-record")["parameters"]["value"]
    expected_fields = {
        "certificate_schema",
        "feature_pair",
        "fixture",
        "fixed_point_scale",
        "method",
        "scope",
        "status",
        "thickness",
        "toi",
        "triangle_q4",
        "vertex_end_q4",
        "vertex_start_q4",
    }
    if set(hit) != expected_fields or set(miss) != expected_fields:
        raise RuntimeError("certificate route fields differ from the fixed bridge profile")
    fixed_profile = {
        "certificate_schema": "TOM-NHDF-CCD-FIXTURE-1.0",
        "feature_pair": "vertex-face",
        "fixture": "vf-q4-linear-probe",
        "fixed_point_scale": 4,
        "method": "TOMAGI KIN2/CONE/SPHERE/RADIX",
        "scope": "single exact zero-thickness q4 query",
        "thickness": 0,
    }
    if any(hit.get(field) != value or miss.get(field) != value for field, value in fixed_profile.items()):
        raise RuntimeError("certificate routes contradict the fixed zero-thickness VF profile")
    if hit.get("status") != "HIT" or miss.get("status") != "MISS" or miss.get("toi") is not None:
        raise RuntimeError("certificate HIT/MISS labels or negative TOI route are invalid")

    common_fields = sorted(expected_fields - {"status", "toi"})
    if any(hit[field] != miss.get(field) for field in common_fields):
        raise RuntimeError("HIT and MISS routes do not describe the same query")

    scale = int(hit["fixed_point_scale"])
    triangle = hit["triangle_q4"]
    vertex_start = hit["vertex_start_q4"]
    vertex_end = hit["vertex_end_q4"]
    expected_triangle = [[0, 0, 0], [scale, 0, 0], [0, scale, 0]]
    if scale != 4 or triangle != expected_triangle:
        raise RuntimeError("bridge profile requires the canonical q4 right triangle")
    if vertex_start[:2] != vertex_end[:2]:
        raise RuntimeError("bridge profile requires constant in-plane vertex coordinates")

    x_q4, y_q4, start_z_q4 = (int(value) for value in vertex_start)
    end_z_q4 = int(vertex_end[2])
    plane_z_q4 = int(triangle[0][2])
    start_rho = start_z_q4 - plane_z_q4
    end_rho = end_z_q4 - plane_z_q4
    delta_rho = end_rho - start_rho
    if delta_rho % scale:
        raise RuntimeError("q4 endpoint motion does not have an integral per-tick velocity")
    vrho = delta_rho // scale
    if vrho == 0:
        raise RuntimeError("fixture has no signed-distance motion")
    root_tick = Fraction(-start_rho, vrho)
    if root_tick.denominator != 1 or not 0 <= root_tick.numerator <= scale:
        raise RuntimeError("fixture root does not lie exactly on the declared q4 grid")
    toi = {"denominator": scale, "numerator": root_tick.numerator}
    if hit["toi"] != toi:
        raise RuntimeError("literal HIT certificate TOI differs from geometry-derived TOI")

    expected_setters = {
        "cell:set-rho": start_rho,
        "cell:set-theta": x_q4,
        "cell:set-tick": 0,
        "cell:set-phi": y_q4,
        "cell:set-vrho": vrho,
        "cell:set-vtick": 1,
    }
    for identifier, expected in expected_setters.items():
        actual = int(_definition(document, identifier)["parameters"]["args"][0])
        if actual != expected:
            raise RuntimeError(
                f"{identifier} initializes {actual}, but query geometry requires {expected}"
            )

    cone_args = [int(value) for value in _definition(document, "cell:contact-x")["parameters"]["args"]]
    sphere_args = [int(value) for value in _definition(document, "cell:y-inside")["parameters"]["args"]]
    if cone_args[:2] != [0, 0] or sphere_args[:2] != [0, 0]:
        raise RuntimeError("runtime support guards do not require exact coplanarity")
    x_bounds = (cone_args[2] - abs(cone_args[3]), cone_args[2] + abs(cone_args[3]))
    y_bounds = (sphere_args[2] - abs(sphere_args[3]), sphere_args[2] + abs(sphere_args[3]))
    if not (x_bounds[0] <= x_q4 <= x_bounds[1] and y_bounds[0] <= y_q4 <= y_bounds[1]):
        raise RuntimeError("query point lies outside its runtime support guards")
    if x_bounds[0] < 0 or y_bounds[0] < 0 or x_bounds[1] + y_bounds[1] > scale:
        raise RuntimeError("runtime support rectangle is not contained in the declared triangle")

    horizon_arg = int(_definition(document, "cell:horizon")["parameters"]["args"][0])
    if horizon_arg != 12 + int(math.log2(scale)):
        raise RuntimeError("RADIX horizon bit does not match the q4 time denominator")

    geometry = {
        "fixed_point_scale": scale,
        "triangle_q4": triangle,
        "vertex_end_q4": vertex_end,
        "vertex_start_q4": vertex_start,
    }
    return {
        "geometry": geometry,
        "geometry_sha256": _sha256_bytes(_canonical_bytes(geometry)),
        "root_tick": root_tick.numerator,
        "scale": scale,
        "vrho": vrho,
        "x_q4": x_q4,
        "y_q4": y_q4,
    }


def _reference_solver_check(fixture: dict[str, Any]) -> dict[str, Any]:
    source_root = BRIDGE_DIR.parent / "12_v0_5_upgrade" / "src"
    sys.path.insert(0, str(source_root))
    import numpy as np
    from nhdf_ccd_v05 import LinearPoint, Status, Vec3, vertex_face_ccd

    def point(start: tuple[float, float, float], end=None) -> LinearPoint:
        finish = start if end is None else end
        return LinearPoint(Vec3(*start), Vec3(*finish))

    scale = fixture["scale"]
    geometry = fixture["geometry"]
    triangle = [tuple(value / scale for value in item) for item in geometry["triangle_q4"]]
    vertex_start = tuple(value / scale for value in geometry["vertex_start_q4"])
    vertex_end = tuple(value / scale for value in geometry["vertex_end_q4"])
    expected_toi = fixture["root_tick"] / scale
    certificate = vertex_face_ccd(
        point(vertex_start, vertex_end),
        point(triangle[0]),
        point(triangle[1]),
        point(triangle[2]),
        thickness=0.0,
        geom_tol=1e-12,
        time_tol=1e-12,
        pair_id="tomagi-vf-q4",
    )
    if certificate.status is not Status.HIT:
        raise RuntimeError(f"reference solver returned {certificate.status.value}, expected HIT")
    if certificate.toi_lower is None or certificate.toi_upper is None:
        raise RuntimeError("reference solver omitted the TOI interval")
    if not certificate.toi_lower <= expected_toi <= certificate.toi_upper:
        raise RuntimeError("reference solver interval does not contain geometry-derived TOI")
    if certificate.witness is None or certificate.witness.distance is None:
        raise RuntimeError("reference solver omitted the contact witness")
    if not math.isclose(certificate.witness.distance, 0.0, abs_tol=1e-12):
        raise RuntimeError("reference solver witness is not coplanar")
    return {
        "method": certificate.method,
        "status": certificate.status.value,
        "toi_lower": certificate.toi_lower,
        "toi_upper": certificate.toi_upper,
        "witness_distance": certificate.witness.distance,
        "environment": {
            "numpy": np.__version__,
            "python": platform.python_version(),
        },
    }


def _validate_execution(
    artifacts: dict[str, bytes], source: dict[str, Any], fixture: dict[str, Any]
) -> dict[str, Any]:
    replay = json.loads(artifacts["ccd_vf_q4.replay.json"])
    materialized = json.loads(artifacts["ccd_vf_q4.certificate.json"])
    expected = _definition(source, "artifact:hit-record")["parameters"]["value"]
    if materialized != expected:
        raise RuntimeError("materialized certificate differs from literal HIT route")

    state = replay["state"]
    if state["tick"] != fixture["root_tick"] or state["rho"] != 0:
        raise RuntimeError("runtime state did not compute the exact q4 contact tick")
    if materialized["toi"] != {"denominator": fixture["scale"], "numerator": state["tick"]}:
        raise RuntimeError("materialized TOI does not match replayed State64.tick")

    trace = replay["trace"]
    kinematic_steps = [item for item in trace if item["opcode"] == 3]
    cone_hits = [
        item
        for item in trace
        if item["opcode"] == 7 and item["branch"] == 1 and item["rho"] == 0
    ]
    sphere_hits = [item for item in trace if item["opcode"] == 8 and item["branch"] == 1]
    if len(kinematic_steps) != fixture["root_tick"] or not cone_hits or not sphere_hits:
        raise RuntimeError("runtime trace lacks the expected KIN2/CONE/SPHERE contact path")
    if trace[-1]["opcode"] != 14 or not (state["status"] & 1 and state["status"] & 8):
        raise RuntimeError("runtime did not terminate through an EMIT cell")

    emits = replay["emits"]
    if not emits or any(item["mode"] != "bytes" for item in emits):
        raise RuntimeError("generic materialization contains non-byte EMIT records")
    if sum(item["byte_count"] for item in emits) != len(
        artifacts["ccd_vf_q4.certificate.json"]
    ):
        raise RuntimeError("ordered EMIT byte count differs from materialized artifact")

    return {
        "computed_toi": {"denominator": fixture["scale"], "numerator": state["tick"]},
        "emitted_bytes": len(artifacts["ccd_vf_q4.certificate.json"]),
        "emit_records": len(emits),
        "final_lineage": state["lineage"],
        "final_status": state["status"],
        "kinematic_steps": len(kinematic_steps),
        "trace_steps": len(trace),
        "query_binding": {
            "geometry_sha256": fixture["geometry_sha256"],
            "runtime_vrho": fixture["vrho"],
            "runtime_x_q4": fixture["x_q4"],
            "runtime_y_q4": fixture["y_q4"],
        },
    }


def build_and_validate() -> dict[str, Any]:
    _verify_input_boundaries()
    with tempfile.TemporaryDirectory(prefix="tomagi-ccd-a-") as first_name, tempfile.TemporaryDirectory(
        prefix="tomagi-ccd-b-"
    ) as second_name:
        first = _build_once(Path(first_name))
        second = _build_once(Path(second_name))

    equality = {name: first[name] == second[name] for name in ARTIFACT_NAMES}
    if not all(equality.values()):
        failed = [name for name, same in equality.items() if not same]
        raise RuntimeError("non-deterministic replay boundaries: " + ", ".join(failed))

    source_document = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    fixture = _fixture_binding(source_document)
    execution = _validate_execution(first, source_document, fixture)
    reference = _reference_solver_check(fixture)
    for name, data in first.items():
        (BRIDGE_DIR / name).write_bytes(data)

    proof = {
        "schema": "TOM-NHDF-CCD-REPLAY-PROOF-1.0",
        "status": "PASS",
        "claim_boundary": "single exact zero-thickness q4 vertex-face fixture",
        "inputs": {
            "bridge_validator": {
                "bytes": Path(__file__).stat().st_size,
                "sha256": _sha256_file(Path(__file__)),
            },
            "definition_source": {
                "bytes": SOURCE_PATH.stat().st_size,
                "sha256": _sha256_file(SOURCE_PATH),
            },
            "genesis_runtime_archive": {
                "bytes": GENESIS_ZIP.stat().st_size,
                "sha256": _sha256_file(GENESIS_ZIP),
            },
            "normative_profile": {
                "bytes": FORMAL_PROFILE_PATH.stat().st_size,
                "sha256": _sha256_file(FORMAL_PROFILE_PATH),
            },
            "reference_solver_sources": {
                path.name: {"bytes": path.stat().st_size, "sha256": _sha256_file(path)}
                for path in sorted((BRIDGE_DIR.parent / "12_v0_5_upgrade" / "src" / "nhdf_ccd_v05").glob("*.py"))
            },
            "root_seed": {"bytes": 244, "sha256": _sha256_file(SEED_PATH)},
            "token_registry": {
                "bytes": REGISTRY_PATH.stat().st_size,
                "content_hash": REGISTRY_HASH,
                "sha256": _sha256_file(REGISTRY_PATH),
            },
        },
        "boundaries": {
            name: {"bytes": len(data), "sha256": _sha256_bytes(data)}
            for name, data in first.items()
        },
        "determinism": {
            "isolated_rebuilds": 2,
            "byte_identical": equality,
        },
        "execution": execution,
        "reference_solver": reference,
    }
    proof_path = BRIDGE_DIR / "ccd_vf_q4.proof.json"
    proof_path.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return proof


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and validate the TOMAGI q4 CCD bridge")
    parser.add_argument(
        "--rehash-source",
        action="store_true",
        help="mechanically refresh literal definition content_hash fields before building",
    )
    args = parser.parse_args()
    if args.rehash_source:
        rehash_source()
    proof = build_and_validate()
    print(json.dumps(proof, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
