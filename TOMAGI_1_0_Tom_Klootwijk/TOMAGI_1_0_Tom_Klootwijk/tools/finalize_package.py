from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT.parent
PACKAGE_NAME = ROOT.name
PDF_REL = Path("report/TOMAGI_1_0_Tom_Klootwijk.pdf")
ZIP_PATH = OUT_DIR / f"{PACKAGE_NAME}.zip"
PDF_COPY = OUT_DIR / f"{PACKAGE_NAME}.pdf"
DIGEST_PATH = OUT_DIR / f"{PACKAGE_NAME}_SHA256.txt"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_intermediates() -> None:
    for directory in ROOT.rglob("__pycache__"):
        if directory.is_dir():
            shutil.rmtree(directory)
    for pattern in ("*.pyc", "*.pyo"):
        for path in ROOT.rglob(pattern):
            path.unlink(missing_ok=True)

    report = ROOT / "report"
    for suffix in (
        ".aux",
        ".fdb_latexmk",
        ".fls",
        ".log",
        ".out",
        ".toc",
        ".lof",
        ".lot",
        ".xdv",
        ".synctex.gz",
    ):
        (report / f"TOMAGI_1_0_Tom_Klootwijk{suffix}").unlink(missing_ok=True)

    # Redundant scratch and superseded validation products.  The canonical
    # per-program state files and test log remain under validation/.
    for relative in (
        "build/c_state.json",
        "build/tomagi-c.new",
        "build/tomagi-c-ubsan",
        "validation/c_state.json",
        "validation/c_python_match.json",
        "validation/tests_rerun.txt",
    ):
        (ROOT / relative).unlink(missing_ok=True)

    pdf_scratch = ROOT / "tmp" / "pdfs"
    if pdf_scratch.is_dir():
        shutil.rmtree(pdf_scratch)
    tmp = ROOT / "tmp"
    if tmp.is_dir() and not any(tmp.iterdir()):
        tmp.rmdir()


def iter_payload_files() -> list[Path]:
    excluded = {
        ROOT / "checksums/SHA256SUMS.txt",
        ROOT / "validation/package_manifest.json",
    }
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path in excluded:
            continue
        if any(part in {".git", ".pytest_cache", "dist"} for part in path.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def write_manifest() -> None:
    files = iter_payload_files()
    manifest = {
        "schema": "TOMAGI-PACKAGE-MANIFEST-1.0",
        "package": PACKAGE_NAME,
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "generated": date.today().isoformat(),
        "file_count_excluding_manifest_and_checksum": len(files),
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
    }
    destination = ROOT / "validation/package_manifest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )


def write_checksums() -> None:
    destination = ROOT / "checksums/SHA256SUMS.txt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(
        (p for p in ROOT.rglob("*") if p.is_file() and p != destination),
        key=lambda p: p.relative_to(ROOT).as_posix(),
    )
    lines = [f"{sha256_file(path)}  {path.relative_to(ROOT).as_posix()}" for path in files]
    destination.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def write_zip() -> None:
    ZIP_PATH.unlink(missing_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(ROOT.rglob("*"), key=lambda p: p.relative_to(ROOT).as_posix()):
            if not path.is_file():
                continue
            arcname = Path(PACKAGE_NAME) / path.relative_to(ROOT)
            zf.write(path, arcname.as_posix())


def main() -> None:
    pdf = ROOT / PDF_REL
    if not pdf.is_file() or pdf.stat().st_size == 0:
        raise SystemExit(f"missing final PDF: {pdf}")

    clean_intermediates()
    write_manifest()
    write_checksums()
    shutil.copy2(pdf, PDF_COPY)
    write_zip()

    digests = {
        "pdf": {"path": PDF_COPY.name, "bytes": PDF_COPY.stat().st_size, "sha256": sha256_file(PDF_COPY)},
        "zip": {"path": ZIP_PATH.name, "bytes": ZIP_PATH.stat().st_size, "sha256": sha256_file(ZIP_PATH)},
    }
    DIGEST_PATH.write_bytes(
        (
            "\n".join(f"{item['sha256']}  {item['path']}" for item in digests.values())
            + "\n"
        ).encode("utf-8")
    )
    print(json.dumps(digests, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
