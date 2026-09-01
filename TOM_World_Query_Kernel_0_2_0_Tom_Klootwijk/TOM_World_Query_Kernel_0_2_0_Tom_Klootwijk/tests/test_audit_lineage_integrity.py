from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tom_world.audit import audit_store
from tom_world.canonical import attach_hash
from tom_world.indexes import build_index_record
from tom_world.seed import CANONICAL_SEED_SHA256
from tom_world.store import SNAPSHOT_SCHEMA, WorldStore


ROOT = Path(__file__).resolve().parents[1]
SEED = (ROOT / "TOM_seed_genome_2026-09-01.txt").read_bytes()
COUNTER_TRANSACTION = ROOT / "examples/world_counter/initial_transaction.json"


class AuditLineageIntegrityTests(unittest.TestCase):
    def test_audit_replays_transaction_into_referenced_snapshot(self):
        """Individually valid hashes must not mask false commit lineage."""

        with tempfile.TemporaryDirectory() as directory:
            store = WorldStore.initialize(Path(directory), SEED)
            store.commit_transaction_file(COUNTER_TRANSACTION)
            original_commit = store.read_commit()

            empty_index = build_index_record(
                {},
                lambda record_id, object_id: (_ for _ in ()).throw(
                    AssertionError(f"unexpected record load: {record_id} {object_id}")
                ),
                seed_sha256="sha256:" + CANONICAL_SEED_SHA256,
            )
            empty_index_id = store._put_hashed_json(store.indexes_dir, empty_index)
            false_snapshot = attach_hash({
                "schema": SNAPSHOT_SCHEMA,
                "version": "0.2.0",
                "seed_sha256": "sha256:" + CANONICAL_SEED_SHA256,
                "records": {},
                "blobs": {},
                "indexes_hash": empty_index_id,
            })
            false_snapshot_id = store._put_hashed_json(store.snapshots_dir, false_snapshot)

            false_commit_body = {
                key: value for key, value in original_commit.items() if key != "content_hash"
            }
            false_commit_body["snapshot_hash"] = false_snapshot_id
            false_commit_body["indexes_hash"] = empty_index_id
            false_commit = attach_hash(false_commit_body)
            false_commit_id = store._put_hashed_json(store.commits_dir, false_commit)
            store.head_path.write_text(false_commit_id + "\n", encoding="ascii")
            store.clear_caches()

            certificate = audit_store(store)
            self.assertFalse(certificate["valid"])
            self.assertTrue(any(
                item["kind"] == "transaction"
                and "does not reproduce snapshot maps" in item["message"]
                for item in certificate["errors"]
            ))


if __name__ == "__main__":
    unittest.main()
