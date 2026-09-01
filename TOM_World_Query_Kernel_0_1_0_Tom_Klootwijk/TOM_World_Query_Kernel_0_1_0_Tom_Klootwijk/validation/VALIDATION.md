# TOM World & Query Kernel 0.1 validation

Status: **pass**

Checks: 16 passed; 0 failed.

| Check | Status | Detail |
|---|---|---|
| canonical seed identity | pass | Exact 244-byte TOM-SRS root with no terminal line feed. |
| TOMAGI ABI unchanged | pass | World/query code does not alter the TOMAGI 1.0 record sizes. |
| original TOMAGI regression | pass | The original polar loop remains byte-format compatible and reaches its recorded terminal values. |
| counter world build | pass | Literal program/world sources reproduced a committed content-addressed world and all starter certificates. |
| state_at | pass | Exact replay index 3 returns rho=3 and stored tick=3. |
| next_event | pass | The exact discrete solver found the first gated zero event at replay index 5. |
| events_in_support | pass | The declared support selects one event in (0,8]. |
| compatible(q1,q2) | pass | The same-topology predicate has both a positive and a negative exact-state test. |
| bounded binary grammar | pass | Branch-selected grammar expansion terminated inside depth, symbol, stack, and strict-bit budgets. |
| lineage reconstruction | pass | The committed lineage replays its source commit and reproduces the event certificate bytes. |
| persistent world transaction | pass | The store contains immutable initial and event commits with one event and one lineage record. |
| Python/C trajectory trace | pass | The complete eight-step TOMAGI trace and final State64 are equal. |
| roadmap literal EMIT artifact | pass | The primary documentation is byte-equal to its source after definition compilation and Python/C EMIT execution. |
| conformance tests | pass | 47 tests passed, including the original TOMAGI suite. |
| static specifications and schemas | pass | Roadmap, normative profile, source PDFs, schemas, definitions, and artifact sources passed static verification. |
| clean rebuild | pass | A generated-output-free copy rebuilt the selected world, query, and documentation boundaries byte-for-byte. |

## Evidence boundary

This release executes Python and C99. It retains the original GPU mappings but does not claim a new physical device dispatch. The event solver is exact over whole discrete TOMAGI transitions and does not claim continuous root isolation. Observation, hypothesis, and goal records are present, but no autonomous learner or planner is claimed.

Validation report content hash: `sha256:11b9b2881f13732e456bedd2b3e68a5bab279d93929c6f222043b4007e5ea864`
