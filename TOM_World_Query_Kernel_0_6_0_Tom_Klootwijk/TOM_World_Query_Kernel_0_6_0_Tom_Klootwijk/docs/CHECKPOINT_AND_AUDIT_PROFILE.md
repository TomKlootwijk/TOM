# Checkpoint, Batch, and Full-Ancestry Audit Profile

## Exact checkpoints

A checkpoint is produced by a root replay with checkpoints disabled. It records the complete 16-word state plus the instance hash, program blob hash, source commit, and state-certificate hash.

Consumption requires:

- checkpoint tick not after the requested tick;
- exact instance content hash match;
- exact program blob hash match; and
- source commit in the query commit's ancestry.

Selection is maximum tick, then ID. Checkpoints accelerate replay but do not change `state_at` semantics.

The 10,000-record benchmark proves:

```text
state_at(instance:benchmark:042,999)
indexed checkpoint: tick 900 -> 99 replayed steps
root replay:                    999 replayed steps
saved deterministic work:      900 TOMAGI transitions
semantic certificate:          byte-equal
```

## Stable batch reduction

Batch requests execute in declared array order. Each canonical semantic result is prefixed by its 64-bit length before reduction hashing. This prevents concatenation ambiguity and makes order explicit. Indexed and exhaustive batches have the same semantic reduction hash.

## Audit

The audit traverses every commit to sequence zero and independently checks transactions, snapshots, indexes, records, dependencies, blobs, and index reconstruction. It clears in-memory caches first. Its certificate intentionally omits time and host data.

The benchmark's two-commit ancestry has zero errors and zero unreachable immutable objects.
