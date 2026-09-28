# Qualification Gate Contract (S10-GATE-QUAL-01)

## 1. Status And Purpose

S10-GATE-QUAL-01 implements the deterministic qualification packet acceptance gate in
`src/data_layer/analytical_research/qualification_gate.py`. It is the only qualification
decision authority over an existing S10-QUAL-01 `QualificationCandidate`:

```
existing immutable NON_WALLET QualificationCandidate (S10-QUAL-01)
+ current verified AlphaFactoryRegistrySnapshot (append-only descendant or equal)
+ exact candidate-bound AF1GateReceipt
+ exact candidate-bound ResearchProvenanceManifest set
    -> structural revalidation / exact external rebinding
    -> eight closed qualification-readiness dimensions
    -> immutable content-addressed QualificationGateReceipt
    -> QUAL_PASS / QUAL_FAIL / QUAL_INCONCLUSIVE
```

Predecessor: PR #197 / S10-QUAL-01, head `652a2181926ac6f92f72d0013af99ec5e24ba892`, merged at
`b5cfb9846ff78af2d1a260843d5f2f1a67639305`. S10-QUAL-01 remains the non-qualifying packet
substrate; `qualification.py`, `experiment_os.py` and `experiment_registry.py` are unchanged and
consumed read-only.

A valid QUAL_PASS says exactly: the exact candidate packet and the evidence bound by this policy
are sufficiently ready to enter a separately authorized candidate-specific WP170 implementation.
QUAL_PASS is NOT predictive edge, OOS success, executable edge, profitability, paper authority,
live authority or Gate C authority, and it does not itself authorize WP170.

This implementation WP builds the deterministic gate capability only. No real candidate was built
or evaluated and no real `QualificationGateReceipt` exists or is persisted. Every QUAL_PASS,
QUAL_FAIL and QUAL_INCONCLUSIVE in the implementation evidence is a synthetic, test-only fixture
outcome.

## 2. One Gate Receipt, No Second Truth System

The module adds exactly one immutable `QualificationGateReceipt`, one closed
`QualificationGateControlResult` and deterministic evaluate / validate / mapping-roundtrip
functions. It adds no SQLite registry, file writer, CLI/operator, current-time lookup, random
source, environment lookup, provenance family, Alpha memory or WP170 object. Canonical
authorities stay where they are:

- Alpha Factory registry -> canonical Alpha research memory;
- `AF1GateReceipt` -> research-system gate predecessor evidence;
- `ResearchProvenanceManifest` -> shared PIT / DQ / replay provenance core;
- `QualificationCandidate` -> frozen non-qualifying candidate packet;
- `QualificationGateReceipt` -> qualification decision only;
- WP170 -> later preregistration / OOS authority; WP172 -> executable economics; WP173 -> paper.

## 3. Public API

Package-root exports (`src.data_layer.analytical_research`):
`QUALIFICATION_GATE_SCHEMA_VERSION` (`1.0.0`), `QUALIFICATION_GATE_RECEIPT_SCHEMA_ID`
(`polymarket-qualification-gate-receipt`), `QUALIFICATION_GATE_POLICY_VERSION`
(`qualification-gate-policy/1.0.0`), `QUALIFICATION_GATE_STATUSES`,
`QUALIFICATION_GATE_DIMENSIONS`, `QUALIFICATION_GATE_DIMENSION_STATUSES`,
`QUALIFICATION_GATE_DISPOSITIONS`, `QUALIFICATION_GATE_ERROR_CODES`, `QualificationGateReceipt`,
`QualificationGateControlResult`, `evaluate_qualification_gate`,
`validate_qualification_gate_receipt`, `qualification_gate_receipt_to_mapping` and
`qualification_gate_receipt_from_mapping`.

`evaluate_qualification_gate(candidate, alpha_registry_snapshot, af1_gate_receipt,
provenance_manifests)` returns a `QualificationGateControlResult`. There is no path argument,
store write, clock, random seed, environment or network.

## 4. Structural Control Result Versus Substantive Decision

Structural control rejection — malformed / tampered / semantically invalid candidate, a
structurally invalid or non-descendant Alpha snapshot, a wrong / malformed / unbound AF1
receipt, a wrong / malformed / unbound provenance manifest set, a schema / type / identity /
authority invariant failure or an internal validation failure — returns `is_valid == false`,
`status == QUALIFICATION_GATE_REJECTED`, `receipt == None` and exactly one closed error code. It
never manufactures QUAL_FAIL or QUAL_INCONCLUSIVE.

Only after every structural and external-binding admission check succeeds does the gate emit a
receipt whose `overall_disposition` is exactly one of QUAL_PASS, QUAL_FAIL or QUAL_INCONCLUSIVE.
Admission order is deterministic: candidate, Alpha snapshot, Alpha ancestry, AF1, provenance.

## 5. Receipt Identity And Serialization

`QualificationGateReceipt` field order is frozen (`schema_id` .. `no_gate_c_authority`). Its id
is `qualificationgate:sha256:<64 lowercase hex>` over every normalized field except
`qualification_gate_receipt_id` (canonical UTF-8 JSON, `sort_keys`, `(",", ":")` separators,
`allow_nan=false`). `dimension_statuses` is the exact ordered eight-pair tuple in the dataclass
and an ordered `{dimension: status}` mapping in serialized form; mapping order never alters
identity. Fixed values: schema version `1.0.0`, policy `qualification-gate-policy/1.0.0`,
`experiment_os_schema_version` equal to the current WP170 schema version, and
`successor_authorization_required`, `no_strategy_authority`, `no_paper_authority`,
`no_execution_authority`, `no_live_authority`, `no_gate_c_authority` exactly true. The five
control-result no-authority flags are always true.

`validate_qualification_gate_receipt` proves only the receipt's own closed schema, per-dimension
allowed statuses, aggregation, eligibility and identity; direct dataclass construction with a
self-consistent rehash cannot forge a disposition, eligibility or an impossible dimension status.
`qualification_gate_receipt_from_mapping` requires the exact keyset, rejects binary floats and
fully re-validates. Only `evaluate_qualification_gate` performs current external rebinding.

## 6. Alpha Append-Only Ancestry And Current Lineage

The gate never opens or mutates the registry. It re-proves the supplied in-memory
`AlphaFactoryRegistrySnapshot` against the registry's own derivations: exact type / schema /
version, all four snapshot no-authority flags, a nonempty entry tuple, `total_rows`, sequence
numbers `0..N-1`, exact `previous_entry_hash` links, every entry payload digest and entry hash
re-derived with the registry's own record serialization and chain hash, `total_payload_bytes`,
the head equal to the final entry hash, and the registry's cross-record invariants.

The candidate-bound `alpha_registry_head_entry_hash` MAY be older than the current head: it must
occur exactly once as an entry hash in the current chain (therefore an ancestor of, or equal to,
the current head), the exact candidate, family and governing episode must be present in the
history up to that bound head, and the governing episode `research_as_of` must be at or before the
candidate cutoff. Otherwise: `ALPHA_ANCESTRY_INVALID`, no receipt.

`CURRENT_RESEARCH_LINEAGE` is evaluated across the complete current snapshot using the existing
predecessor / reopened convention: PASS iff the exact `(alpha_candidate_id,
hypothesis_family_id)` lineage has exactly one leaf, equal to the governing episode, with
`result_state == RESEARCH_SUPPORTIVE`. Unrelated appends keep PASS. A later same-lineage episode
(even another supportive one), ambiguous leaves or a non-supportive current leaf is FAIL: the
packet no longer meets the current-lineage criterion; this is not relabelled as a falsified
hypothesis.

## 7. AF1 And Provenance Rebinding

AF1: exact `AF1GateReceipt` type, all AF1 no-authority flags true, the existing
`validate_af1_record` passes, `FINALIZED`, `AF1_PASS`, exact AF1 dimension keyset with every
dimension PASS, and `gate_receipt_id == candidate.af1_gate_receipt_id`. The currently known AF1
receipt id is predecessor evidence only and is never a product constant. Admitted evaluations
record `PREDECESSOR_EVIDENCE = PASS`.

Provenance binding: a nonempty bounded sequence (at most 256) of exact
`ResearchProvenanceManifest` records whose identities verify, current schema id / version,
canonical cutoffs, canonical DQ flags and replay fidelity; supplied ids unique and, sorted, equal
to the candidate manifest ids exactly (no missing, no extra); every manifest cutoff at or before
the candidate cutoff; every split-plan dataset snapshot ref in the union of manifest
`dataset_refs`. Failures: `PROVENANCE_INVALID` / `PROVENANCE_BINDING_INVALID`, no receipt.

## 8. Readiness Dimensions And Aggregation

Every receipt carries exactly eight dimensions in this order:

| Dimension | Allowed | Rule |
| --- | --- | --- |
| PACKET_INTEGRITY | PASS | structural candidate failure yields no receipt |
| CURRENT_RESEARCH_LINEAGE | PASS / FAIL | Section 6 |
| PREDECESSOR_EVIDENCE | PASS | structural AF1 failure yields no receipt |
| PIT_PROVENANCE_READINESS | PASS / INCONCLUSIVE | every declared evidence ref bound; DQ exactly `("OK",)`; replay `EXACT` / `FAITHFUL`; empty gap summary |
| SAMPLE_POWER_READINESS | PASS / INCONCLUSIVE | available >= required samples; available >= required independent groups; available samples >= 3 x `min_samples_per_role` |
| WP170_CROSSING_READINESS | PASS | structurally admitted current candidate |
| EXECUTION_EVIDENCE_READINESS | PASS / INCONCLUSIVE | `FEES`, `RESOLUTION_RULES`, `TICK_SIZE_MIN_ORDER` AVAILABLE with provenance-bound refs |
| AUTHORITY_CONTAINMENT | PASS | authority invariant failure yields no receipt |

Declared evidence refs are every feature evidence ref, every label evidence ref, the
power-analysis reference and every nonempty execution-feasibility evidence ref; bound refs are the
union of manifest `input_evidence_reference_ids`. The gate never dereferences opaque evidence ids,
never treats `event_time` as public availability, never upgrades PARTIAL to FAITHFUL and never
treats a nonempty gap as sufficient.

Sample / power readiness consumes the declared facts only: no universal power formula, no change
to target power / significance / minimum detectable effect, no sample or OOS materialization; the
three-role check is a necessary aggregate condition for future formation / selection / OOS roles.
A shortfall is INCONCLUSIVE, never a structural invalidity.

WP170 crossing readiness means only that the already-valid candidate is specified enough to BEGIN
separately authorized candidate-specific WP170 work. Current WP170
`SAFE_FEATURE_SOURCE_DEPENDENCIES` are market-observation fields only; the gate does NOT claim
that PUBLIC_NON_MARKET B1 qualification feature refs are valid WP170 FeatureDefinition ids.

`SPREAD_DEPTH`, `LATENCY` and `PARTIAL_FILL` may be AVAILABLE, PARTIAL, MISSING or
NOT_APPLICABLE; they are carried forward in the candidate for WP172 and do not block the gate.
The gate computes no expected return, fair value, price edge, spread-adjusted edge, slippage,
latency impact, partial-fill economics, capacity, position size, PnL, profitability or side.

Aggregation: any FAIL -> QUAL_FAIL; else any INCONCLUSIVE -> QUAL_INCONCLUSIVE; else QUAL_PASS.
`wp170_entry_eligible` is true iff QUAL_PASS. Callers cannot supply statuses, disposition or
eligibility.

## 9. Failure Discipline

Closed error vocabulary (`QUALIFICATION_GATE_ERROR_CODES`, in order): `SCHEMA_UNSUPPORTED`,
`FIELD_TYPE_INVALID`, `FIELD_VALUE_INVALID`, `IDENTITY_DERIVATION_MISMATCH`, `CANDIDATE_INVALID`,
`ALPHA_REGISTRY_INVALID`, `ALPHA_ANCESTRY_INVALID`, `AF1_RECEIPT_INVALID`, `AF1_BINDING_INVALID`,
`PROVENANCE_INVALID`, `PROVENANCE_BINDING_INVALID`, `AUTHORITY_INVARIANT_INVALID`,
`LIMIT_EXCEEDED`, `INTERNAL_VALIDATION_FAILED`. Public failures expose only the closed status, one
closed code and no receipt; never raw mappings, question text, URLs, secrets, paths, exception
repr or local environment details.

## 10. Successor Boundary And Non-Authority

After independent Side13 exact-head review and Karl merge, the immediate operational dependency
is a SEPARATELY AUTHORIZED real NON_WALLET candidate build and evaluation with the merged gate.
A real QUAL_FAIL or QUAL_INCONCLUSIVE makes WP170 not eligible for that candidate. Only a real
valid QUAL_PASS makes candidate-specific WP170 work eligible to be separately drafted and
authorized; that WP170 work must still solve feature / model / calibrator construction and a
durable qualification-receipt handoff without pretending the current `PreregisteredExperiment`
has a qualification receipt field.

First real candidate / evaluation: NOT AUTHORIZED by this WP. Real receipt persistence: NOT
AUTHORIZED. WP170 experiment/OOS: NOT STARTED / NOT AUTHORIZED by this WP. WP172/WP173: NOT
STARTED. Wallet qualification: NOT AUTHORIZED (blocked on S10-WALLET-03 -> S10-WALLET-04 ->
S10-GATE-WALLET-01 -> a real wallet evidence lane). H1 #5: NOT AUTHORIZED. Gate C: NOT
AUTHORIZED. Capital/orders: 0. Network, Hermes/provider, wallet runtime, scheduler, credential,
strategy, paper, execution and live authority: none. Merge: NOT AUTHORIZED by the executor.
