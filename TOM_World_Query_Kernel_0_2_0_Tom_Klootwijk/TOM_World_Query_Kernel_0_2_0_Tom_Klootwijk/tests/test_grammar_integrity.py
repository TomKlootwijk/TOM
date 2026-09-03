from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tom_world.grammar import GrammarEngine
from tom_world.records import make_record
from tom_world.store import WorldStore


ROOT = Path(__file__).resolve().parents[1]
SEED = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
TRANSACTION_PATH = ROOT / "examples/world_counter/initial_transaction.json"


def branched_payload() -> dict:
    return {
        "axiom": ["F"],
        "productions": {
            "F": {
                "zero": ["F", "0"],
                "one": ["F", "1"],
            },
        },
        "budgets": {"max_depth": 2, "max_symbols": 16, "max_stack": 0},
        "branch_policy": "cycle",
    }


class GrammarAcceptedInputTests(unittest.TestCase):
    def test_branched_record_requires_nonempty_integer_bits(self):
        missing = branched_payload()
        with self.assertRaisesRegex(ValueError, "requires nonempty branch_bits"):
            make_record("grammar", "grammar:missing-bits", missing)

        empty = branched_payload()
        empty["branch_bits"] = []
        with self.assertRaisesRegex(ValueError, "requires nonempty branch_bits"):
            make_record("grammar", "grammar:empty-bits", empty)

        boolean = branched_payload()
        boolean["branch_bits"] = [True]
        with self.assertRaisesRegex(ValueError, "integer 0/1"):
            make_record("grammar", "grammar:boolean-bit", boolean)

        valid = branched_payload()
        valid["branch_bits"] = [0, 1]
        record = make_record("grammar", "grammar:valid-bits", valid)
        self.assertEqual(record["payload"]["branch_bits"], [0, 1])

    def test_unbranched_record_does_not_require_bits(self):
        record = make_record(
            "grammar",
            "grammar:unbranched",
            {
                "axiom": ["F"],
                "productions": {"F": ["F", "F"]},
                "budgets": {"max_depth": 1, "max_symbols": 4, "max_stack": 0},
            },
        )
        self.assertNotIn("branch_bits", record["payload"])

    def test_expansion_override_rejects_empty_and_boolean_branch_bits(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WorldStore.initialize(Path(directory), SEED)
            store.commit_transaction_file(TRANSACTION_PATH)
            engine = GrammarEngine(store)

            with self.assertRaisesRegex(ValueError, "nonempty branch_bits"):
                engine.expand("grammar:bounded-binary-branch", depth=0, branch_bits=[])
            with self.assertRaisesRegex(ValueError, "integer 0 and 1"):
                engine.expand("grammar:bounded-binary-branch", depth=1, branch_bits=[True])


if __name__ == "__main__":
    unittest.main()
