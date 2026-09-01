from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_validation


ROOT = Path(__file__).resolve().parents[1]


class NativeBackendTests(unittest.TestCase):
    def test_foreign_elf_is_not_selected_on_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / "build"
            build.mkdir()
            legacy = build / "tomagi-c"
            legacy.write_bytes(b"\x7fELF" + b"\0" * 12)

            selected, detail = run_validation.find_native_c_backend(root, "Windows")
            self.assertIsNone(selected)
            self.assertIn("expected PE", detail)
            self.assertIn("tomagi-c=ELF", detail)

            native = build / "tomagi-c.exe"
            native.write_bytes(b"MZ" + b"\0" * 14)
            selected, _ = run_validation.find_native_c_backend(root, "Windows")
            self.assertEqual(selected, native)

    def test_foreign_legacy_backend_is_hidden_and_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / "build"
            build.mkdir()
            legacy = build / "tomagi-c"
            payload = b"\x7fELF" + b"foreign"
            legacy.write_bytes(payload)

            with run_validation.hide_incompatible_legacy_backend(root, "Windows"):
                self.assertFalse(legacy.exists())
            self.assertEqual(legacy.read_bytes(), payload)


class ValidationToolTests(unittest.TestCase):
    def test_portable_tee_returns_child_failure_status(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "tests.txt"
            command = [
                sys.executable,
                "-c",
                "import sys; print('tee-check'); raise SystemExit(7)",
            ]
            with patch.object(run_validation, "unittest_command", return_value=command):
                status = run_validation.run_unittests_with_tee(output)
            self.assertEqual(status, 7)
            self.assertEqual(output.read_text(encoding="utf-8"), "tee-check\n")

    def test_scope_note_describes_actual_tool_modes(self):
        note = run_validation.build_scope_note(
            c_mode="not-run",
            opencl_mode="not-run",
            glsl_mode="compiled",
            wgsl_mode="source-checked",
        )
        self.assertIn("C execution was not run", note)
        self.assertIn("OpenCL was not syntax-checked", note)
        self.assertIn("GLSL was compiled with glslang", note)
        self.assertIn("WGSL received structural source checks", note)
        self.assertIn("No physical GPU dispatch", note)

    def test_validation_dependencies_are_declared(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[project.optional-dependencies]", pyproject)
        for dependency in ("jsonschema>=4.18", "numpy>=1.26", "matplotlib>=3.8"):
            self.assertIn(f'"{dependency}"', pyproject)


class SpecAssetBuildTests(unittest.TestCase):
    def test_package_local_generation_is_deterministic_without_external_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "package"
            (root / "tools").mkdir(parents=True)
            (root / "sources").mkdir()
            (root / "spec").mkdir()
            shutil.copy2(ROOT / "tools/build_spec_assets.py", root / "tools/build_spec_assets.py")
            shutil.copy2(ROOT / "sources/source_register.json", root / "sources/source_register.json")
            shutil.copy2(
                ROOT / "sources/ugts_knowledge_catalog_211.json",
                root / "sources/ugts_knowledge_catalog_211.json",
            )
            original_register = (root / "sources/source_register.json").read_bytes()
            original_catalog = (root / "sources/ugts_knowledge_catalog_211.json").read_bytes()

            environment = os.environ.copy()
            environment.pop("TOMAGI_SOURCE_ROOT", None)
            environment.pop("TOMAGI_CATALOG_PATH", None)
            first = subprocess.run(
                [sys.executable, str(root / "tools/build_spec_assets.py")],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertIn("external source hash regeneration skipped", first.stderr)
            first_assets = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in sorted((root / "spec").iterdir())
                if path.is_file()
            }

            incomplete_root = root / "optional-inputs"
            incomplete_root.mkdir()
            environment["TOMAGI_SOURCE_ROOT"] = str(incomplete_root)
            environment["TOMAGI_CATALOG_PATH"] = str(incomplete_root / "missing-catalog.json")
            second = subprocess.run(
                [sys.executable, str(root / "tools/build_spec_assets.py")],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("preserving the shipped source register", second.stderr)
            self.assertIn("using shipped condensed catalog", second.stderr)
            second_assets = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in sorted((root / "spec").iterdir())
                if path.is_file()
            }
            self.assertEqual(first_assets, second_assets)
            self.assertEqual((root / "sources/source_register.json").read_bytes(), original_register)
            self.assertEqual((root / "sources/ugts_knowledge_catalog_211.json").read_bytes(), original_catalog)

            precedence = json.loads((root / "spec/precedence.json").read_text(encoding="utf-8"))
            self.assertEqual(
                precedence,
                json.loads((ROOT / "spec/precedence.json").read_text(encoding="utf-8")),
            )
            schema = json.loads((root / "spec/tomagi.schema.json").read_text(encoding="utf-8"))
            self.assertIn("content_hash", schema["$defs"]["definition"]["required"])
            self.assertEqual(json.loads(second.stdout)["crosswalk"], 322)


if __name__ == "__main__":
    unittest.main()
