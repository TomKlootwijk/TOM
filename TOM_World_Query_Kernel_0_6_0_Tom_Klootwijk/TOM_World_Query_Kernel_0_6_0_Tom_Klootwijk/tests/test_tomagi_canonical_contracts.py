from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

from tomagi.canonical import attach_hash, canonical_bytes
from tomagi.compiler import compile_document


def definition(
    ident: str,
    *,
    kind: str,
    domain: str,
    codomain: str,
    dependencies: list[str],
    phase: str,
    order: int,
    op: str,
    parameters: dict,
    limits: dict | None = None,
    provenance: dict | None = None,
) -> dict:
    return attach_hash({
        "id": ident,
        "kind": kind,
        "domain": domain,
        "codomain": codomain,
        "dependencies": dependencies,
        "phase": phase,
        "order": order,
        "operation": {"op": op},
        "parameters": parameters,
        "limits": {} if limits is None else limits,
        "provenance": {"source": "canonical contract regression"}
        if provenance is None else provenance,
    })


def seeded_source() -> dict:
    seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    definitions = [
        definition(
            "seed", kind="canonical-seed", domain="none", codomain="bytes",
            dependencies=[], phase="parse", order=0, op="seed.bytes", parameters={},
        ),
        definition(
            "tokens", kind="seed-parse", domain="bytes", codomain="record",
            dependencies=["seed"], phase="normalize", order=0, op="seed.tokens",
            parameters={},
        ),
        definition(
            "bytes", kind="literal-bytes", domain="seed-record", codomain="bytes",
            dependencies=["tokens"], phase="construct", order=0, op="literal",
            parameters={"result_type": "bytes", "value": "x"},
        ),
        definition(
            "state", kind="initial-state", domain="seed-record", codomain="state64",
            dependencies=["tokens"], phase="construct", order=1,
            op="state64.construct", parameters={"fields": {}},
        ),
        definition(
            "guard", kind="literal-guard", domain="seed-record", codomain="bool",
            dependencies=["tokens"], phase="guard", order=0, op="literal",
            parameters={"result_type": "bool", "value": True},
        ),
        definition(
            "graph", kind="byte-emission", domain="bytes", codomain="cell_graph",
            dependencies=["bytes"], phase="event", order=0, op="emit.graph",
            parameters={},
        ),
        definition(
            "program", kind="artifact-program", domain="state-graph-guard",
            codomain="program", dependencies=["state", "graph", "guard"],
            phase="lineage", order=0, op="program.construct",
            parameters={"default_ticks": 1, "emit_bytes": True},
        ),
    ]
    return {
        "tomagi_version": "1.0.0",
        "compilation_profile": "TOM-SEEDED-COMPILATION-1.0",
        "seed_genome": {
            "path": "TOM_seed_genome_2026-09-01.txt",
            "bytes": len(seed),
            "sha256": __import__("hashlib").sha256(seed).hexdigest(),
            "grammar_id": "TOM-SEED-GRAMMAR-1.0",
            "token_registry": "spec/tom_seed_token_registry_1_0.json",
        },
        "root_definition": "program",
        "budgets": {
            "max_definitions": 32,
            "max_cells": 32,
            "max_output_bytes": 512,
            "max_sequence_items": 32,
            "max_repeat": 1,
            "max_expression_depth": 32,
            "max_expression_nodes": 512,
            "max_string_bytes": 256,
        },
        "definitions": definitions,
    }


def compile_seeded(source: dict):
    seed = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
    registry = json.loads(
        (ROOT / "spec/tom_seed_token_registry_1_0.json").read_text(encoding="utf-8")
    )
    return compile_document(source, seed_bytes=seed, token_registry=registry)


class CanonicalJSONContractTests(unittest.TestCase):
    def test_python_tuple_is_not_a_json_array(self):
        with self.assertRaisesRegex(TypeError, "not JSON-native"):
            canonical_bytes({"items": (1, 2)})
        with self.assertRaisesRegex(TypeError, "not JSON-native"):
            attach_hash({"items": (1, 2)})

    def test_json_object_keys_must_be_strings(self):
        with self.assertRaisesRegex(TypeError, "object keys must be strings"):
            canonical_bytes({1: "coerced by json.dumps"})
        with self.assertRaisesRegex(TypeError, "object keys must be strings"):
            attach_hash({"nested": {1: "coerced by json.dumps"}})


class SeededCompilerStringBudgetTests(unittest.TestCase):
    def test_encoded_byte_literal_uses_output_budget_not_carrier_string_budget(self):
        source = seeded_source()
        bytes_index = next(
            index for index, item in enumerate(source["definitions"])
            if item["id"] == "bytes"
        )
        byte_literal = copy.deepcopy(source["definitions"][bytes_index])
        byte_literal["parameters"] = {
            "result_type": "bytes",
            "value": {
                "encoding": "base64",
                "data": __import__("base64").b64encode(b"x" * 96).decode("ascii"),
            },
        }
        byte_literal["limits"] = {"max_string_bytes": 64}
        source["definitions"][bytes_index] = attach_hash(byte_literal)

        compiled = compile_seeded(source)

        self.assertEqual(len(compiled.cells), 24)

    def test_unselected_definition_parameter_strings_obey_effective_limit(self):
        source = seeded_source()
        source["definitions"].append(definition(
            "unused",
            kind="literal-string",
            domain="none",
            codomain="string",
            dependencies=[],
            phase="transform",
            order=0,
            op="literal",
            parameters={"result_type": "string", "value": "x" * 33},
            limits={"max_string_bytes": 32},
            provenance={"source": "test"},
        ))

        with self.assertRaisesRegex(
            ValueError, "parameters contains a string exceeding max_string_bytes",
        ):
            compile_seeded(source)

    def test_emit_generated_cell_ids_obey_effective_limit(self):
        source = seeded_source()
        graph_index = next(
            index for index, item in enumerate(source["definitions"])
            if item["id"] == "graph"
        )
        graph = copy.deepcopy(source["definitions"][graph_index])
        graph["parameters"] = {"id_prefix": "abcdefghijklm"}
        graph["limits"] = {"max_string_bytes": 13}
        graph["provenance"] = {"source": "test"}
        source["definitions"][graph_index] = attach_hash(graph)

        with self.assertRaisesRegex(
            ValueError, "generated cell ID exceeds max_string_bytes",
        ):
            compile_seeded(source)


if __name__ == "__main__":
    unittest.main()
