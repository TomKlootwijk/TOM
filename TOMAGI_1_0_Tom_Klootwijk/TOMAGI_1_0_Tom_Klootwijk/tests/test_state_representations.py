from __future__ import annotations

import copy
import csv
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from hashlib import sha256
from pathlib import Path

from tomagi.canonical import attach_hash, verify_hash
from tomagi.compiler import compile_document
from tomagi.core import FLAG_EMIT_HALT, Opcode, STATUS_HALT, run
from tomagi.format import dumps
from tomagi.genome import (
    evaluate_definition_genome,
    evaluate_definition_records,
)
from tomagi.project import MATERIALIZATION_PROFILE, emit_byte_count, materialize_program


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SEED_FILE = ROOT / "sources" / "TOM_seed_genome_2026-09-01.txt"
ORBIT_SOURCE = EXAMPLES / "tomagi_state_orbit.json"
ORBIT_BINARY = EXAMPLES / "tomagi_state_orbit.tmg"
ORBIT_TRACE = EXAMPLES / "tomagi_state_orbit.trace.json"
SEED_TEXT = (
    "TOM1[TopologicalOpenModular]|TomKlootwijk|1990-07-10|NL200678942|"
    "2026-09-01|LUTlogp^{Klein,SDF0@Def}(rho,theta,t->;phi,dt,d2,J,v,a,j1)"
    ">P1>L2_BST^b>ASweepCone(T,apex)>Pi[pyrSide,circle,sphere]>support>"
    "compatibility>guard>event>transition>lineage"
)
SEED_FILE_SHA256 = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
SEED_DEFINITION_HASH = (
    "sha256:092f1cd576a0ee5faf7cd425aae162acad5bbda1c15aae191a6ff6913940c73d"
)
CHAIN = [
    Opcode.SDF0,
    Opcode.JIT1,
    Opcode.KIN2,
    Opcode.PHI,
    Opcode.KLEIN,
    Opcode.HINGE,
    Opcode.LSYS,
    Opcode.CONE,
    Opcode.PROJECT,
    Opcode.EMIT,
]
REPRESENTATIONS = {
    "2d": {
        "source": EXAMPLES / "tomagi_state_2d.json",
        "binary": EXAMPLES / "tomagi_state_2d.tmg",
        "artifact": EXAMPLES / "tomagi_state_2d.svg",
        "manifest": EXAMPLES / "tomagi_state_2d.manifest.json",
        "project": "orbit2d:theta-rho-canvas",
    },
    "3d": {
        "source": EXAMPLES / "tomagi_state_3d.json",
        "binary": EXAMPLES / "tomagi_state_3d.tmg",
        "artifact": EXAMPLES / "tomagi_state_3d.obj",
        "manifest": EXAMPLES / "tomagi_state_3d.manifest.json",
        "project": "orbit3d:rho-theta-phi-coordinates",
    },
    "4d": {
        "source": EXAMPLES / "tomagi_state_4d.json",
        "binary": EXAMPLES / "tomagi_state_4d.tmg",
        "artifact": EXAMPLES / "tomagi_state_4d.csv",
        "manifest": EXAMPLES / "tomagi_state_4d.manifest.json",
        "project": "orbit4d:raw-state-fields",
    },
}


def _literal(ident: str, kind: str, parameters: dict) -> dict:
    return attach_hash({
        "id": ident,
        "kind": kind,
        "domain": "literal_definition",
        "codomain": "byte_string",
        "dependencies": [],
        "parameters": parameters,
    })


def _derived(ident: str, kind: str, dependencies: list[dict], parameters: dict) -> dict:
    parameters = dict(parameters)
    parameters["dependency_hashes"] = [item["content_hash"] for item in dependencies]
    return attach_hash({
        "id": ident,
        "kind": kind,
        "domain": "ordered_byte_strings",
        "codomain": "byte_string",
        "dependencies": [item["id"] for item in dependencies],
        "parameters": parameters,
    })


def _rehash_document(document: dict) -> dict:
    document = copy.deepcopy(document)
    by_id = {definition["id"]: definition for definition in document["definitions"]}
    complete: set[str] = set()

    def refresh(ident: str) -> None:
        if ident in complete:
            return
        definition = by_id[ident]
        dependencies = definition.get("dependencies", [])
        for dependency in dependencies:
            refresh(dependency)
        parameters = definition.get("parameters")
        if isinstance(parameters, dict) and "dependency_hashes" in parameters:
            parameters["dependency_hashes"] = [
                by_id[dependency]["content_hash"] for dependency in dependencies
            ]
        definition.update(attach_hash(definition))
        complete.add(ident)

    for definition in document["definitions"]:
        refresh(definition["id"])
    return document


def _affine(field: dict, value: int) -> int:
    product = value * field.get("numerator", 1)
    denominator = field.get("denominator", 1)
    if field.get("rounding", "floor") == "floor":
        quotient = product // denominator
    else:
        quotient = abs(product) // denominator
        if product < 0:
            quotient = -quotient
    return quotient + field.get("offset", 0)


class DefinitionGenomeAlgebraTests(unittest.TestCase):
    def test_utf8_hex_concat_and_repeat_have_exact_total_semantics(self):
        text = _literal("text", "literal_utf8", {"text": "TOM"})
        binary = _literal("binary", "literal_hex", {"hex": "00ff"})
        joined = _derived("joined", "concat", [text, binary], {})
        repeated = _derived("repeated", "repeat", [joined], {"count": 2})

        result = evaluate_definition_genome(
            [text, binary, joined, repeated], "repeated"
        )
        self.assertEqual(result.data, b"TOM\x00\xffTOM\x00\xff")

        changed_text = attach_hash({**text, "parameters": {"text": "tampered"}})
        with self.assertRaisesRegex(ValueError, "dependency hash mismatch"):
            evaluate_definition_genome(
                [changed_text, binary, joined, repeated], "repeated"
            )

    def test_raw_cell_documents_remain_backward_compatible(self):
        document = json.loads((EXAMPLES / "polar_loop.json").read_text())
        program = compile_document(document)
        self.assertEqual(len(program.cells), 14)
        self.assertEqual(Opcode(program.cells[program.entry].opcode), Opcode.SDF0)


class StateOrbitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(ORBIT_SOURCE.read_text(encoding="utf-8"))
        cls.stored = json.loads(ORBIT_TRACE.read_text(encoding="utf-8"))
        cls.program = compile_document(cls.document, base_dir=EXAMPLES)
        cls.final_state, cls.trace = run(cls.program, ticks=640, trace=True)
        cls.emissions = [row for row in cls.trace if row["opcode"] == int(Opcode.EMIT)]

    def test_seed_is_exact_and_transitively_authenticates_the_orbit(self):
        seed_bytes = SEED_FILE.read_bytes()
        self.assertEqual(len(seed_bytes), 244)
        self.assertEqual(seed_bytes, SEED_TEXT.encode("utf-8"))
        self.assertEqual(sha256(seed_bytes).hexdigest(), SEED_FILE_SHA256)

        seed = self.document["definitions"][0]
        self.assertTrue(verify_hash(seed))
        self.assertEqual(seed["content_hash"], SEED_DEFINITION_HASH)
        self.assertEqual(seed["parameters"]["text"].encode("utf-8"), seed_bytes)
        self.assertEqual(seed["parameters"]["source_sha256"], SEED_FILE_SHA256)
        self.assertEqual(seed["provenance"]["source_sha256"], SEED_FILE_SHA256)
        for definition in self.document["definitions"]:
            self.assertTrue(verify_hash(definition))

        by_id = {definition["id"]: definition for definition in self.document["definitions"]}
        for cell in self.document["cells"]:
            ancestors: set[str] = set()

            def visit(ident: str) -> None:
                if ident in ancestors:
                    return
                ancestors.add(ident)
                for dependency in by_id[ident].get("dependencies", []):
                    visit(dependency)

            visit(cell["definition_ref"])
            self.assertIn("literal:tom1-seed-genome", ancestors, cell["id"])

    def test_definition_driven_cells_compile_byte_identically(self):
        self.assertEqual(dumps(self.program), ORBIT_BINARY.read_bytes())
        self.assertEqual(
            [cell.key_u64 for cell in self.program.cells],
            list(range(len(CHAIN))),
        )
        self.assertEqual(
            [Opcode(cell.opcode) for cell in self.program.cells],
            CHAIN,
        )
        for cell in self.document["cells"]:
            self.assertEqual(set(cell), {"id", "key", "definition_ref"})

    def test_definition_fields_are_causal_and_duplicate_fields_must_match(self):
        changed = copy.deepcopy(self.document)
        kin2 = next(
            definition for definition in changed["definitions"]
            if definition["id"] == "definition:orbit-kin2"
        )
        kin2["parameters"]["args"][0] += 1
        changed = _rehash_document(changed)
        self.assertNotEqual(dumps(compile_document(changed)), dumps(self.program))

        conflict = copy.deepcopy(self.document)
        conflict["cells"][0]["op"] = "HALT"
        with self.assertRaisesRegex(ValueError, "opcode does not match definition"):
            compile_document(conflict)

    def test_declared_dependency_hashes_are_enforced(self):
        changed = copy.deepcopy(self.document)
        phi = next(
            definition for definition in changed["definitions"]
            if definition["id"] == "definition:orbit-phi"
        )
        phi["parameters"]["dependency_hashes"][0] = "sha256:" + "0" * 64
        phi.update(attach_hash(phi))
        with self.assertRaisesRegex(ValueError, "dependency hash mismatch"):
            compile_document(changed)

    def test_every_cycle_executes_the_complete_non_halting_literal_chain(self):
        self.assertEqual(self.trace, self.stored["trace"])
        self.assertEqual(
            {name: getattr(self.final_state, name)
             for name in self.final_state.__dataclass_fields__},
            self.stored["state"],
        )
        self.assertEqual(len(self.trace), 640)
        self.assertEqual(len(self.emissions), 64)
        expected = [int(opcode) for opcode in CHAIN]
        for offset in range(0, 640, len(CHAIN)):
            self.assertEqual(
                [row["opcode"] for row in self.trace[offset:offset + len(CHAIN)]],
                expected,
            )
        self.assertFalse(any(cell.opcode == int(Opcode.HALT) for cell in self.program.cells))
        self.assertFalse(self.final_state.status & STATUS_HALT)
        self.assertEqual(self.final_state.cell, self.program.entry)

    def test_emit_samples_span_each_state_dimension(self):
        for field, minimum in {"rho": 60, "theta": 60, "tick": 60, "phi": 55}.items():
            self.assertGreaterEqual(
                len({row[field] for row in self.emissions}),
                minimum,
                field,
            )
        self.assertEqual((self.emissions[0]["rho"], self.emissions[-1]["rho"]),
                         (201197, 680006))
        self.assertEqual((self.emissions[0]["theta"], self.emissions[-1]["theta"]),
                         (20580, 218400))


class StateRepresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = {}
        cls.programs = {}
        cls.materialized = {}
        cls.projected = {}
        for name, paths in REPRESENTATIONS.items():
            document = json.loads(paths["source"].read_text(encoding="utf-8"))
            program = compile_document(document, base_dir=EXAMPLES)
            cls.documents[name] = document
            cls.programs[name] = program
            cls.materialized[name] = materialize_program(program)
            cls.projected[name] = evaluate_definition_records(
                document["definitions"], paths["project"], base_dir=EXAMPLES
            ).records
        cls.orbit_trace = json.loads(ORBIT_TRACE.read_text(encoding="utf-8"))["trace"]
        cls.emissions = [
            row for row in cls.orbit_trace if row["opcode"] == int(Opcode.EMIT)
        ]

    def test_all_documents_match_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        schema = json.loads((ROOT / "spec" / "tomagi.schema.json").read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(
            json.loads(ORBIT_SOURCE.read_text(encoding="utf-8"))
        )
        for document in self.documents.values():
            jsonschema.Draft202012Validator(schema).validate(document)

    def test_each_root_is_transitively_anchored_to_the_exact_seed(self):
        for name, document in self.documents.items():
            by_id = {definition["id"]: definition for definition in document["definitions"]}
            visited: set[str] = set()

            def visit(ident: str) -> None:
                if ident in visited:
                    return
                visited.add(ident)
                for dependency in by_id[ident].get("dependencies", []):
                    visit(dependency)

            visit(document["entry"])
            self.assertIn("literal:tom1-seed-genome", visited, name)
            seed = by_id["literal:tom1-seed-genome"]
            self.assertEqual(seed["content_hash"], SEED_DEFINITION_HASH)
            self.assertEqual(seed["parameters"]["text"], SEED_TEXT)
            trace_definition = next(
                definition for definition in document["definitions"]
                if definition["kind"] == "authenticated_trace"
            )
            parameters = trace_definition["parameters"]
            self.assertEqual(parameters["source_definition_hashes"], [SEED_DEFINITION_HASH])
            self.assertEqual(parameters["dependency_hashes"], [SEED_DEFINITION_HASH])

    def test_authenticated_paths_and_hashes_name_the_exact_orbit_chain(self):
        expected = {
            "source_sha256": sha256(ORBIT_SOURCE.read_bytes()).hexdigest(),
            "program_sha256": sha256(ORBIT_BINARY.read_bytes()).hexdigest(),
            "trace_sha256": sha256(ORBIT_TRACE.read_bytes()).hexdigest(),
        }
        for name, document in self.documents.items():
            trace_definition = next(
                definition for definition in document["definitions"]
                if definition["kind"] == "authenticated_trace"
            )
            parameters = trace_definition["parameters"]
            self.assertEqual(parameters["source_path"], ORBIT_SOURCE.name, name)
            self.assertEqual(parameters["program_path"], ORBIT_BINARY.name, name)
            self.assertEqual(parameters["trace_path"], ORBIT_TRACE.name, name)
            self.assertEqual(parameters["path_semantics"],
                             "relative_to_definition_document")
            for field, digest in expected.items():
                self.assertEqual(parameters[field], digest, name)

    def test_json_to_tmg_and_emit_bytes_are_byte_deterministic(self):
        for name, paths in REPRESENTATIONS.items():
            document = self.documents[name]
            program = self.programs[name]
            result = self.materialized[name]
            self.assertEqual(dumps(program), paths["binary"].read_bytes(), name)
            self.assertEqual(
                dumps(compile_document(document, base_dir=EXAMPLES)),
                dumps(program),
                name,
            )
            evaluated = evaluate_definition_genome(
                document["definitions"], document["entry"], base_dir=EXAMPLES
            )
            self.assertEqual(evaluated.data, result.data, name)
            self.assertEqual(result.data, paths["artifact"].read_bytes(), name)
            self.assertEqual(
                result.manifest,
                json.loads(paths["manifest"].read_text(encoding="utf-8")),
                name,
            )
            self.assertEqual(result.manifest["materialization_profile"],
                             MATERIALIZATION_PROFILE)
            self.assertEqual(result.manifest["emit_count"], len(program.cells))
            self.assertEqual(result.manifest["executed_ticks"], len(program.cells))
            self.assertTrue(all(cell.opcode == int(Opcode.EMIT) for cell in program.cells))
            self.assertEqual([cell.key_u64 for cell in program.cells],
                             list(range(len(program.cells))))
            self.assertFalse(any(cell.flags & FLAG_EMIT_HALT for cell in program.cells[:-1]))
            self.assertTrue(program.cells[-1].flags & FLAG_EMIT_HALT)
            self.assertTrue(result.state.status & STATUS_HALT)
            self.assertTrue(all(1 <= emit_byte_count(cell.flags) <= 4
                                for cell in program.cells))

    def test_every_projected_number_is_declared_affine_state64_data(self):
        self.assertEqual(len(self.emissions), 64)
        for name, paths in REPRESENTATIONS.items():
            document = self.documents[name]
            definition = next(
                item for item in document["definitions"]
                if item["id"] == paths["project"]
            )
            expected = []
            for source_record in self.emissions:
                expected.append({
                    field["name"]: _affine(field, source_record[field["source"]])
                    for field in definition["parameters"]["fields"]
                })
            self.assertEqual(list(self.projected[name]), expected, name)

    def test_svg_points_are_the_declared_theta_rho_projection(self):
        root = ET.fromstring(REPRESENTATIONS["2d"]["artifact"].read_bytes())
        polyline = root.find("{http://www.w3.org/2000/svg}polyline")
        self.assertIsNotNone(polyline)
        points = [tuple(map(int, point.split(",")))
                  for point in polyline.attrib["points"].split()]
        expected = [(row["x"], row["y"]) for row in self.projected["2d"]]
        self.assertEqual(points, expected)
        self.assertGreaterEqual(len({x for x, _ in points}), 60)
        self.assertGreaterEqual(len({y for _, y in points}), 60)

    def test_obj_vertices_and_topology_are_the_declared_rho_theta_phi_projection(self):
        lines = REPRESENTATIONS["3d"]["artifact"].read_text(encoding="utf-8").splitlines()
        vertices = [tuple(map(int, line.split()[1:])) for line in lines if line.startswith("v ")]
        expected = [(row["x"], row["y"], row["z"])
                    for row in self.projected["3d"]]
        self.assertEqual(vertices, expected)
        for axis in range(3):
            self.assertGreaterEqual(len({vertex[axis] for vertex in vertices}), 55)
        topology = next(line for line in lines if line.startswith("l "))
        self.assertEqual(list(map(int, topology.split()[1:])), list(range(1, 65)))

    def test_csv_rows_are_the_four_unmodified_state64_fields(self):
        with REPRESENTATIONS["4d"]["artifact"].open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[0], ["rho", "theta", "tick", "phi"])
        values = [tuple(map(int, row)) for row in rows[1:]]
        expected = [tuple(row[field] for field in rows[0])
                    for row in self.projected["4d"]]
        self.assertEqual(values, expected)
        self.assertEqual(
            values,
            [tuple(row[field] for field in rows[0]) for row in self.emissions],
        )

    def test_no_pre_authored_numeric_artifact_is_stored_in_the_genomes(self):
        samples = {
            "2d": f'{self.projected["2d"][0]["x"]},{self.projected["2d"][0]["y"]}',
            "3d": "v " + " ".join(str(self.projected["3d"][0][field])
                                    for field in ("x", "y", "z")),
            "4d": ",".join(str(self.projected["4d"][0][field])
                            for field in ("rho", "theta", "tick", "phi")),
        }
        for name, paths in REPRESENTATIONS.items():
            source_text = paths["source"].read_text(encoding="utf-8")
            self.assertNotIn(samples[name], source_text, name)
            literals = [definition for definition in self.documents[name]["definitions"]
                        if definition["kind"].startswith("literal_")]
            self.assertEqual([definition["id"] for definition in literals],
                             ["literal:tom1-seed-genome"])

    def test_authenticated_source_must_compile_to_the_authenticated_program(self):
        document = copy.deepcopy(self.documents["4d"])
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            altered_source = json.loads(ORBIT_SOURCE.read_text(encoding="utf-8"))
            altered_source["initial_state"]["rho"] += 1
            altered_bytes = (
                json.dumps(altered_source, indent=2, ensure_ascii=False) + "\n"
            ).encode("utf-8")
            (base / ORBIT_SOURCE.name).write_bytes(altered_bytes)
            (base / ORBIT_BINARY.name).write_bytes(ORBIT_BINARY.read_bytes())
            (base / ORBIT_TRACE.name).write_bytes(ORBIT_TRACE.read_bytes())
            trace_definition = next(
                definition for definition in document["definitions"]
                if definition["kind"] == "authenticated_trace"
            )
            trace_definition["parameters"]["source_sha256"] = sha256(
                altered_bytes
            ).hexdigest()
            document = _rehash_document(document)
            with self.assertRaisesRegex(
                ValueError, "authenticated program is not the compiled source document"
            ):
                compile_document(document, base_dir=base)

    def test_host_evaluator_has_no_representation_specific_vocabulary(self):
        implementation = (ROOT / "src" / "python" / "tomagi" / "genome.py").read_text(
            encoding="utf-8"
        ).lower()
        for token in (
            "<svg", "polyline", "<rect", "v {x}", "rho,theta,tick,phi",
            "image/svg+xml", "model/obj", "text/csv",
        ):
            self.assertNotIn(token, implementation)


if __name__ == "__main__":
    unittest.main()
