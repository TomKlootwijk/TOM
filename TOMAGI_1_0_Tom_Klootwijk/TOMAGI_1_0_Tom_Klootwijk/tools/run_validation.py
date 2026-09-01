from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "validation"
PYTHON_SRC = ROOT / "src/python"
if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cmd, *, env=None, check=True):
    result = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(f"command failed: {cmd}\n{result.stdout}\n{result.stderr}")
    return result


def braces_balanced(text: str) -> bool:
    pairs = {"{": "}", "(": ")", "[": "]"}
    stack = []
    quote = None
    escaped = False
    for character in text:
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in ('"', "'"):
            quote = character
        elif character in pairs:
            stack.append(pairs[character])
        elif character in pairs.values():
            if not stack or stack.pop() != character:
                return False
    return not stack and quote is None


def executable_format(path: Path) -> str | None:
    """Return the container format without executing an untrusted binary."""
    try:
        magic = path.read_bytes()[:4]
    except OSError:
        return None
    if magic == b"\x7fELF":
        return "ELF"
    if magic[:2] == b"MZ":
        return "PE"
    if magic in {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
    }:
        return "Mach-O"
    return "unknown"


def expected_executable_format(system: str | None = None) -> str | None:
    system = system or platform.system()
    return {"Windows": "PE", "Linux": "ELF", "Darwin": "Mach-O"}.get(system)


def is_native_executable(path: Path, system: str | None = None) -> bool:
    expected = expected_executable_format(system)
    return expected is not None and executable_format(path) == expected


def find_native_c_backend(
    root: Path = ROOT, system: str | None = None
) -> tuple[Path | None, str]:
    system = system or platform.system()
    names = ["tomagi-c.exe", "tomagi-c"] if system == "Windows" else ["tomagi-c", "tomagi-c.exe"]
    observed = []
    for name in names:
        path = root / "build" / name
        if not path.is_file():
            continue
        kind = executable_format(path)
        observed.append(f"{path.name}={kind}")
        if is_native_executable(path, system):
            return path, f"compatible {kind} executable found at {path.relative_to(root).as_posix()}"
    expected = expected_executable_format(system)
    detail = ", ".join(observed) if observed else "no C executable found"
    return None, f"no compatible C executable for {system} (expected {expected}; {detail})"


@contextmanager
def hide_incompatible_legacy_backend(root: Path = ROOT, system: str | None = None):
    """Keep legacy fixed-path tests from launching a foreign prebuilt executable."""
    legacy = root / "build" / "tomagi-c"
    if not legacy.is_file() or is_native_executable(legacy, system):
        yield
        return

    backup = legacy.with_name(f".{legacy.name}.incompatible-{os.getpid()}")
    if backup.exists():
        raise RuntimeError(f"temporary backend path already exists: {backup}")
    legacy.replace(backup)
    try:
        yield
    finally:
        if legacy.exists():
            raise RuntimeError(f"cannot restore incompatible backend because {legacy} was recreated")
        backup.replace(legacy)


def unittest_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PYTHON_SRC)
    return environment


def unittest_command() -> list[str]:
    return [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]


def run_unittests_with_tee(output_path: Path) -> int:
    """Stream unittest output to console and disk while returning its real status."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with hide_incompatible_legacy_backend():
        process = subprocess.Popen(
            unittest_command(),
            cwd=ROOT,
            env=unittest_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert process.stdout is not None
        with output_path.open("w", encoding="utf-8", newline="") as stream, process.stdout:
            for line in process.stdout:
                stream.write(line)
                stream.flush()
                sys.stdout.write(line)
                sys.stdout.flush()
        return process.wait()


def run_unittests_capture():
    with hide_incompatible_legacy_backend():
        return run(unittest_command(), env=unittest_environment(), check=False)


def structural_shader_check(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    opcode_dispatch = all(
        f"op=={index}u" in text or (index == 0 and "op==0u" not in text)
        for index in range(16)
    )
    return (
        braces_balanced(text)
        and "State64" in text
        and "Cell48" in text
        and "mix32" in text
        and opcode_dispatch
    )


def find_glslang() -> str | None:
    return shutil.which("glslangValidator") or shutil.which("glslang-validator")


def first_version_line(executable: str | None, flag: str = "--version") -> str | None:
    if not executable:
        return None
    result = run([executable, flag], check=False)
    lines = (result.stdout + result.stderr).splitlines()
    return lines[0] if lines else None


def build_scope_note(
    *, c_mode: str, opencl_mode: str, glsl_mode: str, wgsl_mode: str
) -> str:
    parts = ["Python was executed."]
    if c_mode == "executed":
        parts.append("A platform-compatible C backend was executed.")
    else:
        parts.append("C execution was not run because no platform-compatible backend was available.")

    if opencl_mode == "checked":
        parts.append("OpenCL was syntax-checked with Clang.")
    elif opencl_mode == "failed":
        parts.append("OpenCL syntax checking was attempted with Clang and failed.")
    else:
        parts.append("OpenCL was not syntax-checked because Clang was unavailable.")

    if glsl_mode == "compiled":
        parts.append("GLSL was compiled with glslang.")
    elif glsl_mode == "failed":
        parts.append("GLSL compilation was attempted with glslang and failed.")
    else:
        parts.append("GLSL received structural source checks because glslang was unavailable.")

    if wgsl_mode == "source-checked":
        parts.append("WGSL received structural source checks; no WGSL compiler was configured.")
    else:
        parts.append("WGSL structural source checks failed.")
    parts.append("No physical GPU dispatch was performed.")
    return " ".join(parts)


def validation_main() -> int:
    VAL.mkdir(exist_ok=True)
    checks = []

    def add(name, status, detail, **extra):
        checks.append({"name": name, "status": status, "detail": detail, **extra})

    # Schema validation is an explicit validation dependency, not a silent skip.
    try:
        import jsonschema
    except ModuleNotFoundError:
        add(
            "JSON Schema examples",
            "fail",
            "jsonschema is required for validation; install the 'validation' extra "
            "(for example: python -m pip install -e '.[validation]').",
        )
    else:
        try:
            schema = json.loads((ROOT / "spec/tomagi.schema.json").read_text(encoding="utf-8"))
            validated = []
            for name in (
                "polar_loop.json",
                "exact19_rule.json",
                "tomagi_state_orbit.json",
                "tomagi_state_2d.json",
                "tomagi_state_3d.json",
                "tomagi_state_4d.json",
            ):
                document = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
                jsonschema.Draft202012Validator(schema).validate(document)
                validated.append(name)
            add(
                "JSON Schema examples",
                "pass",
                f"Draft 2020-12 validation: {', '.join(validated)}",
            )
        except Exception as exc:
            add("JSON Schema examples", "fail", str(exc))

    # Python results and equality with a platform-compatible C executable.
    c_executable, c_backend_detail = find_native_c_backend()
    c_executed = False
    parity_programs = (
        ("polar_loop", "polar_loop.expected.json"),
        ("exact19_rule", "exact19_rule.expected.json"),
        ("tomagi_state_orbit", "tomagi_state_orbit.trace.json"),
    )
    for stem, expected_name in parity_programs:
        expected_path = ROOT / "examples" / expected_name
        program_path = ROOT / f"examples/{stem}.tmg"
        if c_executable is None:
            add(f"Python/C equality: {stem}", "not-run", c_backend_detail)
            continue
        if not expected_path.is_file() or not program_path.is_file():
            add(f"Python/C equality: {stem}", "fail", "expected JSON or compiled .tmg example missing")
            continue
        expected = json.loads(expected_path.read_text(encoding="utf-8"))["state"]
        try:
            completed = run([str(c_executable), str(program_path)], check=False)
            c_executed = True
        except OSError as exc:
            add(f"Python/C equality: {stem}", "fail", f"C backend could not execute: {exc}")
            continue
        if completed.returncode:
            detail = (completed.stderr or completed.stdout).strip()
            add(
                f"Python/C equality: {stem}",
                "fail",
                detail or f"C backend exited with status {completed.returncode}",
            )
            continue
        try:
            actual = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            add(f"Python/C equality: {stem}", "fail", f"C backend returned invalid JSON: {exc}")
            continue
        state_path = VAL / f"{stem}_c_state.json"
        state_path.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        add(
            f"Python/C equality: {stem}",
            "pass" if actual == expected else "fail",
            "All 16 State64 fields match exactly." if actual == expected else "State mismatch.",
            python_state=expected,
            c_state=actual,
        )

    # The state representations must be a byte-for-byte replay of the literal
    # seed -> source -> .tmg -> authenticated State64 trace -> definition DAG
    # -> byte-EMIT .tmg -> generic materialization chain.
    try:
        import xml.etree.ElementTree as ET

        from tomagi.compiler import compile_document
        from tomagi.core import Opcode, STATUS_HALT, run as run_tomagi
        from tomagi.format import dumps, load
        from tomagi.genome import evaluate_definition_genome
        from tomagi.project import materialize_program

        examples_dir = ROOT / "examples"
        orbit_source = examples_dir / "tomagi_state_orbit.json"
        orbit_binary = examples_dir / "tomagi_state_orbit.tmg"
        orbit_trace_path = examples_dir / "tomagi_state_orbit.trace.json"
        orbit_document = json.loads(orbit_source.read_text(encoding="utf-8"))
        orbit_program = compile_document(orbit_document, base_dir=examples_dir)
        stored_orbit_trace = json.loads(orbit_trace_path.read_text(encoding="utf-8"))
        orbit_final, orbit_trace = run_tomagi(orbit_program, ticks=640, trace=True)
        orbit_state = {
            name: getattr(orbit_final, name) for name in orbit_final.__dataclass_fields__
        }
        emissions = [row for row in orbit_trace if row["opcode"] == int(Opcode.EMIT)]
        expected_cycle = [
            int(Opcode.SDF0), int(Opcode.JIT1), int(Opcode.KIN2), int(Opcode.PHI),
            int(Opcode.KLEIN), int(Opcode.HINGE), int(Opcode.LSYS), int(Opcode.CONE),
            int(Opcode.PROJECT), int(Opcode.EMIT),
        ]
        seed_file = ROOT / "sources/TOM_seed_genome_2026-09-01.txt"
        seed_definition = next(
            definition
            for definition in orbit_document["definitions"]
            if definition["id"] == "literal:tom1-seed-genome"
        )

        representation_rows: dict[str, list[tuple[int, ...]]] = {}
        representation_ok = True
        representation_details = []
        for dimension, suffix in (("2d", "svg"), ("3d", "obj"), ("4d", "csv")):
            source = examples_dir / f"tomagi_state_{dimension}.json"
            binary = examples_dir / f"tomagi_state_{dimension}.tmg"
            artifact = examples_dir / f"tomagi_state_{dimension}.{suffix}"
            manifest_path = examples_dir / f"tomagi_state_{dimension}.manifest.json"
            document = json.loads(source.read_text(encoding="utf-8"))
            program = compile_document(document, base_dir=examples_dir)
            evaluated = evaluate_definition_genome(
                document["definitions"], document["entry"], base_dir=examples_dir
            )
            replay = materialize_program(load(binary))
            stored_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            trace_definition = next(
                definition
                for definition in document["definitions"]
                if definition["kind"] == "authenticated_trace"
            )
            parameters = trace_definition["parameters"]
            item_ok = (
                dumps(program) == binary.read_bytes()
                and evaluated.data == artifact.read_bytes()
                and replay.data == artifact.read_bytes()
                and replay.manifest == stored_manifest
                and parameters["source_sha256"] == sha(orbit_source)
                and parameters["program_sha256"] == sha(orbit_binary)
                and parameters["trace_sha256"] == sha(orbit_trace_path)
                and seed_definition["content_hash"]
                in parameters["source_definition_hashes"]
            )
            representation_ok &= item_ok
            representation_details.append(
                f"{dimension}={len(replay.data)} bytes/{replay.manifest['artifact_sha256']}"
            )

            if dimension == "2d":
                svg_root = ET.fromstring(replay.data)
                polyline = svg_root.find("{http://www.w3.org/2000/svg}polyline")
                points = [] if polyline is None else [
                    tuple(int(value) for value in pair.split(","))
                    for pair in polyline.attrib.get("points", "").split()
                ]
                representation_rows[dimension] = points
                representation_ok &= (
                    svg_root.tag == "{http://www.w3.org/2000/svg}svg"
                    and len(points) == len(emissions)
                    and len({row[0] for row in points}) >= 16
                    and len({row[1] for row in points}) >= 16
                )
            elif dimension == "3d":
                text = replay.data.decode("utf-8")
                vertices = [
                    tuple(int(value) for value in line.split()[1:])
                    for line in text.splitlines() if line.startswith("v ")
                ]
                topology = [line for line in text.splitlines() if line.startswith("l ")]
                representation_rows[dimension] = vertices
                representation_ok &= (
                    len(vertices) == len(emissions)
                    and len(topology) == 1
                    and topology[0].split()[1:] == [
                        str(index) for index in range(1, len(emissions) + 1)
                    ]
                    and all(len({row[axis] for row in vertices}) >= 16 for axis in range(3))
                )
            else:
                rows = list(csv.reader(replay.data.decode("utf-8").splitlines()))
                coordinates = [tuple(int(value) for value in row) for row in rows[1:]]
                expected = [
                    (row["rho"], row["theta"], row["tick"], row["phi"])
                    for row in emissions
                ]
                representation_rows[dimension] = coordinates
                representation_ok &= (
                    rows[0] == ["rho", "theta", "tick", "phi"]
                    and coordinates == expected
                    and all(len({row[axis] for row in coordinates}) >= 16 for axis in range(4))
                )

        orbit_ok = (
            dumps(orbit_program) == orbit_binary.read_bytes()
            and orbit_trace == stored_orbit_trace["trace"]
            and orbit_state == stored_orbit_trace["state"]
            and len(orbit_trace) == 640
            and len(emissions) == 64
            and all(
                [row["opcode"] for row in orbit_trace[offset:offset + 10]] == expected_cycle
                for offset in range(0, 640, 10)
            )
            and not any(row["status"] & STATUS_HALT for row in orbit_trace)
            and sha(seed_file)
            == "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
            and seed_definition["parameters"]["text"].encode("utf-8")
            == seed_file.read_bytes()
        )
        literal_representation_ok = orbit_ok and representation_ok
        add(
            "Literal State64 2D/3D/4D representation replay",
            "pass" if literal_representation_ok else "fail",
            (
                "The 640-step/64-EMIT source orbit and all authenticated definition DAGs "
                "compile and replay byte-identically; " + "; ".join(representation_details)
            ) if literal_representation_ok else
            "A stored state orbit or representation differs from fresh authenticated replay.",
        )
    except Exception as exc:
        add("Literal State64 2D/3D/4D representation replay", "fail", str(exc))

    # Key vectors.
    from tomagi.core import key_as_u64, pack_key_contiguous, pack_key_morton

    coordinates = (949111, 0, 1920, 227)
    contiguous = key_as_u64(*pack_key_contiguous(*coordinates))
    morton = key_as_u64(*pack_key_morton(*coordinates))
    keys_ok = contiguous == 0xE7B77000007800E3 and morton == 0x88823BB88099128B
    add(
        "64-bit key reference vectors",
        "pass" if keys_ok else "fail",
        f"contiguous=0x{contiguous:016x}; Morton=0x{morton:016x}",
    )

    # OpenCL parser check.
    clang = shutil.which(os.environ.get("CLANG", "clang"))
    if clang:
        completed = run(
            [
                clang,
                "-x",
                "cl",
                "-cl-std=CL1.2",
                "-fsyntax-only",
                str(ROOT / "src/gpu/tomagi_step.cl"),
            ],
            check=False,
        )
        opencl_mode = "checked" if completed.returncode == 0 else "failed"
        detail = (completed.stderr or completed.stdout).strip()
        add(
            "OpenCL C syntax",
            "pass" if completed.returncode == 0 else "fail",
            detail or "clang -cl-std=CL1.2 accepted the kernel",
        )
    else:
        opencl_mode = "not-run"
        add("OpenCL C syntax", "not-run", "clang was not found on PATH")

    # GLSL uses glslang when available, falling back to an explicit source check.
    glsl_path = ROOT / "src/gpu/tomagi_step.comp"
    glsl_source_ok = structural_shader_check(glsl_path)
    glslang = find_glslang()
    if not glsl_source_ok:
        glsl_mode = "failed"
        add("GLSL 4.50 source", "fail", "Structural source check failed.")
    elif glslang:
        completed = run([glslang, "-S", "comp", str(glsl_path)], check=False)
        glsl_mode = "compiled" if completed.returncode == 0 else "failed"
        detail = (completed.stderr or completed.stdout).strip()
        add(
            "GLSL 4.50 source",
            "pass" if completed.returncode == 0 else "fail",
            detail or "glslang accepted the GLSL 4.50 compute shader",
        )
    else:
        glsl_mode = "source-checked"
        add(
            "GLSL 4.50 source",
            "source-checked",
            "Balanced delimiters, shared ABI symbols and opcode dispatch present; "
            "glslang was not found on PATH.",
        )

    # No bundled WGSL compiler is required; keep its fallback status explicit.
    wgsl_path = ROOT / "src/gpu/tomagi_step.wgsl"
    wgsl_ok = structural_shader_check(wgsl_path)
    wgsl_mode = "source-checked" if wgsl_ok else "failed"
    add(
        "WGSL source",
        "source-checked" if wgsl_ok else "fail",
        "Balanced delimiters, shared ABI symbols and opcode dispatch present; "
        "no WGSL compiler was configured."
        if wgsl_ok
        else "Structural source check failed.",
    )

    # Catalog/source coverage.
    operators = json.loads((ROOT / "spec/operator_catalog.json").read_text(encoding="utf-8"))
    crosswalk = json.loads((ROOT / "spec/source_crosswalk.json").read_text(encoding="utf-8"))
    register = json.loads((ROOT / "sources/source_register.json").read_text(encoding="utf-8"))
    source_ids = {row["source"].split(":", 1)[0] for row in crosswalk["rows"]}
    coverage = (
        operators["count"] == 43
        and crosswalk["count"] == 322
        and len(register["sources"]) == 8
        and len(source_ids) >= 8
    )
    add(
        "Operator/source condensation",
        "pass" if coverage else "fail",
        f"{operators['count']} operators; {crosswalk['count']} crosswalk rows; "
        f"{len(register['sources'])} source artifacts; source labels {sorted(source_ids)}",
    )

    # Binary record sizes.
    from tomagi.format import CELL_SIZE, HEADER_SIZE, STATE_SIZE, load

    program_path = ROOT / "examples/polar_loop.tmg"
    program = load(program_path)
    length = program_path.stat().st_size
    sizes_ok = (HEADER_SIZE, STATE_SIZE, CELL_SIZE) == (128, 64, 48) and length == 128 + 48 * len(program.cells)
    add(
        "Binary ABI sizes",
        "pass" if sizes_ok else "fail",
        f"header={HEADER_SIZE}; state={STATE_SIZE}; cell={CELL_SIZE}; polar_loop bytes={length}",
    )

    # Re-run tests for a machine-readable validation result.
    completed = run_unittests_capture()
    combined_output = completed.stdout + completed.stderr
    (VAL / "tests_rerun.txt").write_text(combined_output, encoding="utf-8")
    ran = next((line for line in combined_output.splitlines() if line.startswith("Ran ")), "")
    add(
        "Python conformance suite",
        "pass" if completed.returncode == 0 else "fail",
        f"{ran}; return code {completed.returncode}",
    )

    # Artifact hashes that exist before final packaging. Foreign binaries are
    # deliberately excluded from the current platform's executable evidence.
    artifacts = []
    artifact_paths = [
        ROOT / "examples/polar_loop.tmg",
        ROOT / "examples/exact19_rule.tmg",
        ROOT / "examples/tomagi_state_orbit.json",
        ROOT / "examples/tomagi_state_orbit.tmg",
        ROOT / "examples/tomagi_state_orbit.trace.json",
        ROOT / "examples/tomagi_state_2d.json",
        ROOT / "examples/tomagi_state_2d.tmg",
        ROOT / "examples/tomagi_state_2d.svg",
        ROOT / "examples/tomagi_state_2d.manifest.json",
        ROOT / "examples/tomagi_state_3d.json",
        ROOT / "examples/tomagi_state_3d.tmg",
        ROOT / "examples/tomagi_state_3d.obj",
        ROOT / "examples/tomagi_state_3d.manifest.json",
        ROOT / "examples/tomagi_state_4d.json",
        ROOT / "examples/tomagi_state_4d.tmg",
        ROOT / "examples/tomagi_state_4d.csv",
        ROOT / "examples/tomagi_state_4d.manifest.json",
        ROOT / "src/gpu/tomagi_step.comp",
        ROOT / "src/gpu/tomagi_step.wgsl",
        ROOT / "src/gpu/tomagi_step.cl",
    ]
    if c_executable is not None:
        artifact_paths.append(c_executable)
    for path in artifact_paths:
        if path.exists():
            artifacts.append(
                {
                    "file": path.relative_to(ROOT).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha(path),
                }
            )

    cc = shutil.which(os.environ.get("CC", "cc"))
    report = {
        "schema": "TOMAGI-VALIDATION-1.0",
        "tomagi_version": "1.0.0",
        "generated": "2026-09-01",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cc": first_version_line(cc),
            "clang": first_version_line(clang),
            "glslang": first_version_line(glslang),
        },
        "summary": {
            "pass": sum(check["status"] == "pass" for check in checks),
            "source_checked": sum(check["status"] == "source-checked" for check in checks),
            "fail": sum(check["status"] == "fail" for check in checks),
            "not_run": sum(check["status"] == "not-run" for check in checks),
        },
        "checks": checks,
        "artifacts": artifacts,
        "scope_note": build_scope_note(
            c_mode="executed" if c_executed else "not-run",
            opencl_mode=opencl_mode,
            glsl_mode=glsl_mode,
            wgsl_mode=wgsl_mode,
        ),
    }
    (VAL / "validation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown = [
        "# TOMAGI 1.0 validation report",
        "",
        f"Generated: {report['generated']}",
        "",
        f"Pass: {report['summary']['pass']}; source-checked: {report['summary']['source_checked']}; "
        f"failures: {report['summary']['fail']}; not run: {report['summary']['not_run']}",
        "",
    ]
    for check in checks:
        markdown += [f"## {check['name']}", f"**{check['status']}** - {check['detail']}", ""]
    markdown += ["## Scope", report["scope_note"], ""]
    (VAL / "VALIDATION.md").write_text("\n".join(markdown), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 1 if report["summary"]["fail"] else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run TOMAGI validation or portable unittest teeing.")
    parser.add_argument(
        "--run-tests",
        metavar="OUTPUT",
        help="stream unittest output to OUTPUT and return the unittest process status",
    )
    arguments = parser.parse_args(argv)
    if arguments.run_tests:
        output = Path(arguments.run_tests)
        if not output.is_absolute():
            output = ROOT / output
        return run_unittests_with_tee(output)
    return validation_main()


if __name__ == "__main__":
    raise SystemExit(main())
