"""Exact TOM canonical seed verification."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .canonical import digest_bytes

CANONICAL_SEED_LENGTH = 244
CANONICAL_SEED_SHA256 = "d1417a3136772c0cf3eddcd4962ce07d42cbf87616f7b5bae09fc652d9b807b5"
CANONICAL_SEED_TEXT = (
    "TOM1[TopologicalOpenModular]|TomKlootwijk|1990-07-10|NL200678942|2026-09-01|"
    "LUTlogp^{Klein,SDF0@Def}(rho,theta,t->;phi,dt,d2,J,v,a,j1)>P1>L2_BST^b>"
    "ASweepCone(T,apex)>Pi[pyrSide,circle,sphere]>support>compatibility>guard>event>"
    "transition>lineage"
)


@dataclass(frozen=True, slots=True)
class SeedIdentity:
    bytes: int
    sha256: str
    text: str

    def as_record(self) -> dict[str, object]:
        return {
            "bytes": self.bytes,
            "sha256": self.sha256,
            "encoding": "ASCII/UTF-8",
            "terminal_line_feed": False,
            "grammar": "TOM-SRS-1.0-COMPACT-SEED",
        }


def verify_seed_bytes(raw: bytes) -> SeedIdentity:
    if not isinstance(raw, bytes):
        raise TypeError("seed must be bytes")
    if raw.endswith((b"\n", b"\r")):
        raise ValueError("canonical TOM seed must not have a terminal line ending")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("canonical TOM seed must contain ASCII characters only") from exc
    if len(raw) != CANONICAL_SEED_LENGTH:
        raise ValueError(f"canonical TOM seed length mismatch: {len(raw)}")
    digest = digest_bytes(raw, prefix=False)
    if digest != CANONICAL_SEED_SHA256:
        raise ValueError(f"canonical TOM seed SHA-256 mismatch: {digest}")
    if text != CANONICAL_SEED_TEXT:
        raise ValueError("canonical TOM seed literal mismatch")
    return SeedIdentity(len(raw), digest, text)


def verify_seed_file(path: str | Path) -> SeedIdentity:
    return verify_seed_bytes(Path(path).read_bytes())
