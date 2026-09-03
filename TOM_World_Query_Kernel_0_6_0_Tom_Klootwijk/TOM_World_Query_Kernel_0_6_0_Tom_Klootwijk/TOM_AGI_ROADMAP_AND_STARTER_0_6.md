# TOM AGI Roadmap — status through WQK 0.6

## Current stack

```text
TOMAGI 1.0
  frozen deterministic 128/64/48-byte ABI

TOM Genesis
  executable seeded definitions -> Cell48 -> authenticated EMIT bytes

WQK 0.1-0.4.1
  persistent query world, indexes, exact events, corrected piecewise continuation

TOM Learner 0.1 / WQK 0.5.1
  exact affine proposal moved into a static bounded formal program

WQK 0.5.2
  acceptance, evidence transaction, promotion, snapshot, commit, and parent-bound
  publication moved into a second static bounded formal program

CODEX 0.5.2 kernel repair
  defined C wrap semantics, reserved-header rejection, same-host publication lock,
  recursive formal-value limits, reproducible packaging, corrected CLI documentation

TOM Learner 0.2 / WQK 0.6
  finite typed family registry, exact train-only search, explicit ambiguity,
  supersession/regression impact, and continuation through repaired promotion authority
```

## Corrective roadmap discipline

Capability expansion remains subordinate to authority closure. A domain decision does not count as implemented when it is hidden in host Python while TOMAGI only transports final bytes.

Each milestone must preserve:

```text
formal authority
independent oracle
mechanical host services
```

The formal authority contains the domain law. The oracle may falsify it. Mechanical host services may validate, hash, compile, execute, persist addressed records, authenticate traces, and perform explicit compare-and-swap publication. They may not choose a semantic winner, waive evidence, or rewrite authority.

## Completed: kernel repair prerequisite

The receiving implementation incorporates and regression-tests the CODEX WQK 0.5.2 repairs:

- C signed arithmetic uses defined wider intermediates and explicit `wrap32` lowering;
- Python and C reject all six nonzero reserved header words;
- publication locking covers expected-HEAD read through immutable verification and atomic replacement;
- recursive formal results and fold accumulators are bounded before parent consumption;
- release packaging excludes volatile parent inventory products and requires clean reproducibility; and
- `audit-store` documentation uses the public `SOURCE STORE` argument order.

The scope remains same-host filesystem coordination. Distributed consensus is not claimed.

## Completed: TOM Learner 0.2 / WQK 0.6

### Purpose

Generalize from one exact affine family to a finite typed hypothesis-family registry without weakening proposal or promotion authority.

### Implemented families

1. **Bounded exact polynomials**
   - degree at most two;
   - exact rational coefficients;
   - 34 literal candidates.

2. **Bounded piecewise-affine models**
   - one exact breakpoint;
   - two exact affine branches;
   - fixed left-inclusive boundary convention;
   - 21 literal candidates.

3. **Finite transition tables**
   - complete tables over symbolic inputs `A`, `B`, `C`;
   - outputs in `red`, `green`, `blue`;
   - 27 literal candidates.

4. **Small bounded expression trees**
   - operation registry `x`, `const`, `neg`, `abs`, `square`, `add`, `sub`, `mul`;
   - bounded depth and complexity;
   - 39 literal candidates.

### Mandatory records now present

- family definition and semantic version;
- finite search budget and termination certificate;
- train-only derivation evidence and fit-input hash;
- validation counterexamples and untouched holdout audit;
- deterministic ambiguity record for multiple survivors;
- contradiction records;
- explicit supersession target;
- regression-impact certificate over twelve pinned 0.5.2 definitions;
- accepted typed `SDF0@Def` definition or rejection lineage;
- formal continuation publication under the repaired 0.5.2 expected-parent profile.

### Canonical benchmark

```text
families:          4
candidates:      121
data sets:        16
accepted:          9
rejected:          7
ambiguities:       3
false promotions:  0
```

The positive fixtures recover exact polynomial, piecewise-affine, transition-table, and expression-tree definitions. The negative fixtures cover validation leakage resistance, contradictions, cross-family ambiguity, within-family ambiguity, supersession regression impact, and a relation outside the finite search space.

### Authority chain

```text
canonical seed
-> repaired 0.5.2 kernel boundary
-> content-addressed family registry and data sets
-> static formal family learner
-> independent Fraction oracle comparison
-> static formal promotion continuation
-> deterministic Cell48 lowering
-> equal Python/C TOMAGI traces
-> authenticated EMIT materialization
-> generic same-host locked immutable publication
-> reconstructed terminal head
```

## Next milestone: TOM Learner 0.3 / WQK 0.7

### Purpose

Introduce noisy and interval-valued evidence without converting confidence into an invisible control path.

### Candidate additions

- exact observation intervals and declared measurement models;
- finite noise-family registry;
- calibration and coverage records;
- robust finite candidate scoring with a declared total order or explicit ambiguity;
- interval counterexamples and contradiction classes;
- confidence certificates as content-addressed evidence;
- distribution-shift and out-of-profile records;
- supersession/regression checks under the declared error model;
- unchanged parent-bound promotion transactions.

### Mandatory discipline

Confidence is not a hidden threshold in TOMAGI. It must remain a typed record inspected by explicit support, compatibility, guard, decision, and promotion definitions.

### Exit criteria

- every noise law and scoring rule is static formal authority;
- finite search and calibration terminate under explicit budgets;
- same-ID validation/holdout mutation probes preserve train-only selection;
- independent exact or interval baseline agreement;
- deterministic ambiguity rather than host tie-breaking;
- zero false promotion on adversarial noisy fixtures;
- stale-parent, missing-evidence, calibration, and regression-impact rejection;
- two clean builds and final-ZIP replay.

## Later milestones

### Memory 0.1

Build semantic, episodic, procedural, and working-memory indexes with explicit retrieval certificates, contradiction-aware supersession, temporal consolidation, forgetting policy, and source provenance.

### Planner 0.1

Represent goals, costs, preconditions, effects, candidate plans, simulations, action permissions, and replanning certificates. Plans remain proposals until an explicit authority gate permits action.

### Perception adapters

Convert text, image, audio, and sensor streams into non-authoritative observations with grounding, uncertainty, and source provenance. Perception output must not bypass observation validation and learner promotion.

### Agent integration

Combine learner, memory, planner, perception, tools, and governance under broad unseen-domain evaluation. Tool calls require explicit capabilities and audit records.

## AGI claim gate

No AGI claim follows from deterministic replay, four finite families, or a content-addressed learner. A general-agent claim requires independent empirical evidence for broad transfer, continual learning, memory, planning, perception, action, metacognition, self-correction, and governance.

WQK 0.6 is narrower but foundational: it demonstrates that heterogeneous learned hypotheses can remain finite, explicit, independently falsifiable, ambiguity-aware, regression-checked, and incapable of becoming authoritative through an unexamined host shortcut.
