"""Finite, budgeted deterministic grammar expansion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .canonical import attach_hash
from .store import WorldStore


@dataclass(slots=True)
class _BitCursor:
    bits: list[int]
    policy: str
    index: int = 0

    def take(self) -> tuple[int, int]:
        if not self.bits:
            raise ValueError("branched grammar production has no branch bits")
        source_index = self.index
        if self.policy == "strict" and self.index >= len(self.bits):
            raise ValueError("branched grammar exhausted strict branch_bits")
        bit = self.bits[self.index % len(self.bits)]
        self.index += 1
        return bit, source_index


def _stack_depth(symbols: list[str]) -> int:
    depth = 0
    maximum = 0
    for symbol in symbols:
        if symbol == "[":
            depth += 1
            maximum = max(maximum, depth)
        elif symbol == "]":
            depth -= 1
            if depth < 0:
                raise ValueError("grammar emitted an unmatched closing bracket")
    if depth != 0:
        raise ValueError("grammar emitted unbalanced brackets")
    return maximum


class GrammarEngine:
    def __init__(self, store: WorldStore, *, commit: str | None = None) -> None:
        self.store = store
        self.commit = commit or store.head
        if self.commit is None:
            raise ValueError("grammar engine requires a committed world")

    def expand(
        self,
        grammar_id: str,
        *,
        depth: int | None = None,
        branch_bits: list[int] | None = None,
    ) -> dict[str, Any]:
        record = self.store.read_record(grammar_id, commit=self.commit)
        if record["record_type"] != "grammar":
            raise TypeError(f"{grammar_id} is not a grammar record")
        payload = record["payload"]
        budgets = payload["budgets"]
        maximum_depth = int(budgets["max_depth"])
        requested_depth = maximum_depth if depth is None else depth
        if isinstance(requested_depth, bool) or not isinstance(requested_depth, int) or requested_depth < 0:
            raise ValueError("grammar depth must be a nonnegative integer")
        if requested_depth > maximum_depth:
            raise ValueError(f"grammar depth budget exceeded: {requested_depth} > {maximum_depth}")

        bits = list(payload.get("branch_bits", [])) if branch_bits is None else list(branch_bits)
        if any(bit not in (0, 1) for bit in bits):
            raise ValueError("branch_bits must contain only 0 and 1")
        cursor = _BitCursor(bits, str(payload.get("branch_policy", "cycle")))
        productions: Mapping[str, Any] = payload["productions"]
        current = list(payload["axiom"])
        max_symbols = int(budgets["max_symbols"])
        max_stack = int(budgets["max_stack"])
        if len(current) > max_symbols:
            raise ValueError("grammar axiom exceeds max_symbols")
        if _stack_depth(current) > max_stack:
            raise ValueError("grammar axiom exceeds max_stack")

        generations: list[dict[str, Any]] = [{
            "depth": 0,
            "symbols": current,
            "symbol_count": len(current),
            "stack_depth": _stack_depth(current),
            "branch_decisions": [],
        }]

        for generation in range(1, requested_depth + 1):
            next_symbols: list[str] = []
            decisions: list[dict[str, Any]] = []
            for input_index, symbol in enumerate(current):
                production = productions.get(symbol)
                if production is None:
                    replacement = [symbol]
                elif isinstance(production, list):
                    replacement = list(production)
                elif isinstance(production, Mapping):
                    bit, bit_index = cursor.take()
                    replacement = list(production["one" if bit else "zero"])
                    decisions.append({
                        "input_index": input_index,
                        "symbol": symbol,
                        "branch_bit": bit,
                        "branch_bit_index": bit_index,
                    })
                else:  # Record validation normally makes this unreachable.
                    raise ValueError(f"invalid production for {symbol}")
                next_symbols.extend(replacement)
                if len(next_symbols) > max_symbols:
                    raise ValueError(
                        f"grammar symbol budget exceeded at depth {generation}: "
                        f"{len(next_symbols)} > {max_symbols}"
                    )
            stack = _stack_depth(next_symbols)
            if stack > max_stack:
                raise ValueError(
                    f"grammar stack budget exceeded at depth {generation}: {stack} > {max_stack}"
                )
            current = next_symbols
            generations.append({
                "depth": generation,
                "symbols": current,
                "symbol_count": len(current),
                "stack_depth": stack,
                "branch_decisions": decisions,
            })

        return attach_hash({
            "schema": "TOM-GRAMMAR-EXPANSION-CERTIFICATE-0.1",
            "commit": self.commit,
            "grammar_id": grammar_id,
            "grammar_hash": record["content_hash"],
            "requested_depth": requested_depth,
            "branch_bits": bits,
            "branch_policy": cursor.policy,
            "bits_consumed": cursor.index,
            "generations": generations,
            "terminal_symbols": current,
            "terminal_symbol_count": len(current),
            "status": "complete",
        })
