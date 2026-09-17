# WP170 Falsification-Grade Experiment Registry & Research Dataset OS Contract

## Status and authority

WP170 implements `FALSIFICATION_GRADE_EXPERIMENT_REGISTRY_AND_RESEARCH_DATASET_OS` as a
local/offline, deterministic, append-only research-control substrate. It binds existing
point-in-time and analytical dataset identities, records features and labels, constructs
leakage-aware samples and temporal splits, freezes hypotheses and preregistrations, seals
out-of-sample exposure, and retains every trial result in a bounded SQLite registry.

The records are advisory research metadata only. They are not signals, rankings, expected
returns, trading recommendations, orders, portfolio instructions, or evidence of profit.
Capital at risk is USD 0 and orders submitted are 0. Paper-trading execution is NOT AUTHORIZED.
Live-trading execution is FORBIDDEN. Canonical PIT authority unchanged: YES.
No strategy, cost-adjusted result authority, paper OMS, execution gateway, risk engine,
credential, authenticated access, signing, scheduler, daemon, Hermes runtime, dashboard,
hosted service, product network, or live-trading path is introduced.

The centralized protected boundary groups in `docs/ai/codex/PROTECTED_PATHS.md` remain in
force. WP170 touches none of the forbidden runtime, OMS, reconciliation, risk, overlay,
safe-mode, configuration, or live-trading groups. Merge authorized: NO. Independent live
PR review required: YES.

## Canonical implementation surface

The public source surface is limited to:

- `src/data_layer/analytical_research/experiment_os.py`, containing immutable records,
  closed validators, deterministic identity builders, temporal split construction,
  preregistration, lifecycle control, and evidence receipts;
- `src/data_layer/analytical_research/experiment_registry.py`, containing the bounded
  explicit-path SQLite registry and family summary;
- exports in `src/data_layer/analytical_research/__init__.py`.

The exact dataclass field order, public function signatures, input-mapping key sets,
closed vocabularies, requirements, and evidence nodes are frozen by
`docs/wp_specs/WP170/wp_spec.json`. That machine-readable specification is the API
authority when this prose is less detailed; this document cannot broaden it.

The frozen public experiment records are `DatasetBinding`, `FeatureDefinition`,
`LabelDefinition`, `ResearchSample`, `ResearchDatasetManifest`,
`TemporalSplitManifest`, `AlphaHypothesis`, `MetricDefinition`,
`BaselineDefinition`, `ExperimentFamily`, `PreregisteredExperiment`,
`LifecycleReceipt`, `RunEvidenceReceipt`, `FamilySummary`, and
`ExperimentControlResult`. The registry adds `ExperimentRegistryEntry`,
`ExperimentRegistrySnapshot`, and `ExperimentRegistryResult`.

The builders are:

```text
build_dataset_binding(reference, analytical_manifest, code_version)
build_feature_definition(input_mapping)
build_label_definition(input_mapping)
build_research_dataset_manifest(dataset_binding, feature_definitions, label_definition, sample_inputs, group_policy)
build_temporal_split_manifest(dataset_manifest, split_policy)
build_alpha_hypothesis(input_mapping)
build_metric_definition(input_mapping)
build_baseline_definition(input_mapping)
build_experiment_family(input_mapping)
build_preregistered_experiment(hypothesis, dataset_binding, feature_definitions, label_definition, split_manifest, primary_metric, secondary_metrics, baseline, family, plan)
build_lifecycle_receipt(experiment, prior_receipts, action, occurred_at, provenance, evidence_receipts)
validate_lifecycle(experiment, receipts)
build_run_evidence_receipt(experiment, dataset_manifest, split_manifest, baseline_definition, lifecycle_receipts, prior_evidence, input_mapping)
initialize_experiment_registry(path)
append_experiment_records(path, records)
load_and_verify_experiment_registry(path)
record_experiment_evidence(path, experiment_id, input_mapping)
summarize_experiment_family(path, family_id)
```

All records and result envelopes are frozen dataclasses. Every successful experiment record
has `advisory_only=True` and `no_execution_authority=True`. Invalid calls return closed,
non-echoing envelopes: caller values, paths, exception text, and token-like strings are not
copied into results.

## Closed vocabularies

Experiment statuses are `EXPERIMENT_RECORD_VALID`, `EXPERIMENT_LIFECYCLE_VALID`, and
`EXPERIMENT_REJECTED`. Registry statuses are `REGISTRY_INITIALIZED`,
`REGISTRY_ALREADY_INITIALIZED`, `REGISTRY_APPEND_COMMITTED`,
`REGISTRY_APPEND_IDEMPOTENT`, `REGISTRY_LOADED_VERIFIED`, and `REGISTRY_REJECTED`.

Experiment error precedence is the exact order:

```text
SCHEMA_UNSUPPORTED
FIELD_MISSING
FIELD_TYPE_INVALID
FIELD_VALUE_INVALID
IDENTITY_DERIVATION_MISMATCH
DATASET_REFERENCE_INVALID
FEATURE_TIMING_LEAKAGE
LABEL_TIMING_INVALID
SPLIT_INVALID
PURGE_EMBARGO_VIOLATION
GROUP_LEAKAGE_VIOLATION
PREREGISTRATION_STATE_INVALID
OOS_SEALED_EXPOSURE_VIOLATION
TRIAL_FAMILY_CONFLICT
REGISTRY_SCHEMA_CONFLICT
REGISTRY_INTEGRITY_TAMPER
LIMIT_EXCEEDED
INTERNAL_VALIDATION_FAILED
```

Research roles are `FORMATION`, `SELECTION`, and `OUT_OF_SAMPLE`. Group policies are
`EXCLUSIVE` and `DECLARED_NO_ISOLATION`; correction policies are `SINGLETON` and
`FAMILY_TRIAL_COUNT`; metric directions are `HIGHER_IS_BETTER` and
`LOWER_IS_BETTER`. Uncertainty is `NONE`, `INCONCLUSIVE`, or
`INVALIDATED_AFTER_RUN`.

## Identity and canonicalization

Every persistent WP170 record identity is SHA-256 over a type-namespaced
`identity_preimage` object encoded as UTF-8 canonical JSON: keys sorted, compact `,` and
`:` separators, Unicode retained, explicit nulls retained, and array order retained.
Binary floats, NaN, callables, paths, environment state, and write time are excluded.
Bounded JSON accepts strings, integers, booleans, null, and nested arrays/mappings only.

Prefixes are:

| Record | Prefix |
|---|---|
| Dataset binding | `datasetbinding:sha256:` |
| Feature definition | `featuredef:sha256:` |
| Label definition | `labeldef:sha256:` |
| Sample | `sample:sha256:` |
| Research dataset manifest | `researchdataset:sha256:` |
| Split plan | `splitplan:sha256:` |
| Temporal split assignment | `split:sha256:` |
| Hypothesis | `hypothesis:sha256:` |
| Metric | `metric:sha256:` |
| Baseline | `baseline:sha256:` |
| Experiment family | `experimentfamily:sha256:` |
| Preregistered experiment | `experiment:sha256:` |
| Lifecycle receipt | `lifecyclereceipt:sha256:` |
| Run evidence receipt | `runevidence:sha256:` |
| Registry entry | `registryentry:sha256:` |

`DatasetBinding` embeds and rebuilds the complete canonical `DatasetSnapshotReference`.
When an analytical manifest is supplied it also embeds the exact analytical logical-identity
preimage, independently recomputes the WP167 logical dataset ID from canonical rows, and
binds the reference and analytical lineage. Review-conflict inputs cannot be bound as
ordinary research data. Physical Parquet
hashes and local paths do not enter the logical binding identity. Neither predecessor
identity is modified or promoted.

Feature identity commits its dependencies, canonical parameters, lookback, availability,
missing-data, transformation, and no-future-information rules. Dependencies that declare
future outcomes fail closed. Version 1 accepts only the frozen `market_observation.*`
source-field allowlist, `POINT_IN_TIME` or positive `TRAILING_*` lookbacks, exact source
availability/no-future rules, nonnegative integer parameters, and no recursively nested
future/outcome aliases. Label identity separately commits prediction target, horizon,
target time, outcome source, availability time, censoring, parameters, and code version.

## Samples and temporal partitions

A research sample binds a nonempty canonical tuple of ordinary source record-version IDs,
derived source-membership and lineage digests, market and optional group
identities, decision/feature/target/label-availability times, feature set, and label.
Feature availability later than decision time is `FEATURE_TIMING_LEAKAGE`; decision must be
no later than target, and target no later than label availability. Duplicate equivalent
samples collapse deterministically; conflicting reuse of source membership fails closed.
Manifests sort samples by `sample_id` and declare `assignment_order=SAMPLE_ID_ASC`.

UTC values must be valid RFC3339 strings ending in `Z` with at most six fractional digits.
The only inclusion policy is `DECISION_TIME_HALF_OPEN`. The exact half-open roles are:

```text
FORMATION     [formation_start, selection_start)
SELECTION     [selection_start, oos_start)
OUT_OF_SAMPLE [oos_start, end_time)
```

`PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY` removes a prior-role sample when
`max(target_time, label_availability_time)` reaches or exceeds the next boundary. Embargo
removes a later-role sample whose decision time is in `[boundary,
boundary + embargo_seconds)`; equality at the buffer end is allowed. Each role must retain
at least `min_samples_per_role`, which is at least one. Under either group policy, a
content-addressed source record-version ID may occur in only one retained role, so wrapping
the same source in distinct sample identities cannot cross formation, selection, and OOS.

`EXCLUSIVE` requires every sample to have a non-null leakage group and rejects a leakage
group, market ID, or non-null related-group ID spanning roles. `DECLARED_NO_ISOLATION`
requires all leakage-group IDs to be null. No
undeclared or silently weakened group policy exists.

`TemporalSplitManifest.assignment_hash` is an unprefixed lowercase SHA-256 over canonical
JSON with exactly `formation_sample_ids`, `selection_sample_ids`, `oos_sample_ids`,
`purged_sample_ids`, and `embargoed_sample_ids`. Role membership hashes are unprefixed
lowercase SHA-256 over exactly `split_assignment_id`, `evaluated_role`, and the registered
role's exact `sample_ids` tuple.

## Hypotheses, trials, and preregistration

An `AlphaHypothesis` must be explicitly `REVIEWED` and commits a falsifiable claim,
mechanism, cohort, horizon, target, falsification condition, review assertion, code version,
provenance, and predecessor candidates. It remains non-signal research metadata.

Metrics commit direction and parameters. A baseline must declare
`same_partition_required=True` and one closed rule, `CANDIDATE_GTE_BASELINE` or
`CANDIDATE_LTE_BASELINE`, consistent with the primary metric direction. Candidate and
baseline evidence share the exact registered role membership, and the baseline criterion
is recomputed from their canonical decimal values. An `ExperimentFamily` commits research
program, cohort, target, descriptive metric family, correction policy, and optional
predecessor family. Every family in one registry shares a single conservative accounting
ledger. Successor families must form one explicit predecessor chain with unchanged
correction policy, regardless of any caller-controlled research-program, cohort, target,
or metric-family wording. Registry-wide trial numbers are positive, unique, and contiguous
from 1, and `SINGLETON` permits only trial 1. Consequently no spelling, separator,
singular/plural, synonym, parameter, threshold, or feature-label variant can silently reset
the ledger inside the authoritative registry. Distinct research programs are deliberately
co-accounted; this is conservative rather than a claim that they are statistically related.

A `PreregisteredExperiment` freezes the hypothesis, family and trial number; dataset,
features, feature set, label and split; primary and secondary metrics; baseline; inclusion
and exclusion rules; thresholds; search space and chosen parameters; unique sorted
nonnegative seeds; correction policy; optional opaque cost-model reference; stop/failure
rules; code version; provenance; and preregistration time. A changed committed input creates
a different experiment identity. This field can reference a future cost model but WP170
does not implement one and makes no cost-adjusted claim.

## Lifecycle and evidence

The only lifecycle is the one-way exact chain:

```text
LOCK_PREREGISTRATION -> PREREGISTERED_LOCKED
START_FORMATION      -> FORMATION_ACTIVE
START_SELECTION      -> SELECTION_ACTIVE
CLOSE_SELECTION      -> SELECTION_CLOSED
RELEASE_OOS          -> OOS_RELEASED
CLOSE_EXPERIMENT     -> CLOSED
```

Receipts have contiguous sequence numbers, exact previous links, nondecreasing strict-UTC
times beginning no earlier than preregistration, and no reset. Evidence is recordable only
in its exact active role state and cannot be backdated. Its `created_at` must be at or after
the maximum registered `label_availability_time` across every sample in the exact evaluated
role membership; the split is deterministically rebuilt from the revalidated dataset
manifest and frozen split policy rather than trusting caller timing or membership.
OOS evidence is unavailable before
the irreversible selection close and explicit OOS release. Release itself contaminates the
registered OOS source-record membership even if no evidence is recorded. Exposure
accounting is independent of feature, label, and split identity: any overlap in
content-addressed source record-version IDs contaminates the later OOS role. An OOS evidence
ordinal is `1 + max(count of earlier overlapping-source releases excluding the current
experiment's release, earlier overlapping-source OOS evidence ordinals, 1 when any earlier
overlapping formation or selection evidence exists, 0)`. Data used in controlled formation
or tuning therefore cannot later become pristine OOS. Only ordinal 1 is pristine; every
later OOS evaluation is retained as `OOS_REUSED_DIAGNOSTIC`.

These controls govern repo-owned lifecycle and evidence APIs. They cannot cryptographically
prove that a human never viewed equivalent information outside the controlled workflow, and
they do not restore pristine status when such external exposure is known.

Run-evidence input has exactly `metric_results`, `baseline_results`,
`baseline_membership_hash`, `candidate_criterion_met`, `baseline_criterion_met`,
`uncertainty_state`, `created_at`, and `creation_provenance`. Role is derived from the unique
matching registered membership hash, not selected by the caller. Result status is derived:

- invalidated uncertainty -> `EVIDENCE_INVALIDATED_AFTER_RUN`;
- inconclusive uncertainty -> `EVIDENCE_INCONCLUSIVE`;
- either criterion false -> `EVIDENCE_NEGATIVE`;
- otherwise formation/selection -> `FORMATION_CRITERIA_MET` or
  `SELECTION_CRITERIA_MET`;
- otherwise first OOS -> `OOS_CRITERIA_MET_UNCOSTED`;
- later OOS -> `OOS_REUSED_DIAGNOSTIC`.

Metric results contain exactly one canonical primary decimal and the exact registered
secondary-metric mapping. Baseline results contain one canonical baseline decimal and the
identical registered role-membership hash. The candidate boolean is recomputed from the
registered GTE/LTE threshold; the baseline boolean is recomputed by comparing the candidate
decimal with the baseline decimal under the registered closed baseline rule. Both persisted
booleans must match those independently derived comparisons.

All negative, inconclusive, invalidated, successful, and diagnostic receipts remain in the
registry and family summary. `evidence_receipt_ids` and `evidence_statuses` are aligned in
registry sequence and preserve every evidence event. `trial_statuses` remains one current
or terminal status per ascending trial, while negative and inconclusive counts cover each
distinct trial that ever recorded the applicable evidence, even if a later phase succeeds.
`CLOSE_EXPERIMENT` requires prior authoritative OOS evidence
and records the earliest same-experiment OOS result; invalidated or diagnostic first
evidence closes inconclusive. Metric values are stored as evidence only;
they do not imply statistical significance, expected return, profitability, or deployment
readiness.

## Registry contract

The registry path is caller supplied and must have the exact lowercase `.sqlite3` suffix.
Its parent must already be a real directory. Parent and target symlinks are rejected, and
an existing target must be a regular file with link count exactly one. There is no default
path, discovery, directory creation, network, or background writer.

SQLite identity is exact: format `wp170-experiment-registry`, schema version 1,
`application_id=1464877424`, `user_version=1`, `journal_mode=DELETE`,
`synchronous=FULL`, and `foreign_keys=ON`. The only user-defined objects are
`registry_meta`, `experiment_records`, and `BEFORE UPDATE` / `BEFORE DELETE` triggers
`experiment_records_no_update` and `experiment_records_no_delete`, both aborting mutation.
There are no explicit indexes, views, or extra schema objects.

The persisted kinds are exactly the twelve records from `DATASET_BINDING` through
`RUN_EVIDENCE_RECEIPT` in the order frozen by the machine spec. No caller-declared or other
class is persistable. A registry entry hash commits exact keys `sequence_number`,
`record_kind`, `record_id`, `payload_sha256`, and `previous_entry_hash`; payload SHA-256 is
computed over the canonical complete dataclass mapping.

Bounds are `MAX_REGISTRY_RECORDS=4096`, `MAX_RECORD_PAYLOAD_BYTES=262144`,
`MAX_STORE_PAYLOAD_BYTES=16777216`, and `MAX_APPEND_BATCH=256`. A batch is a list or tuple
of 1..256 records. Records are independently revalidated and new entries sort by fixed
kind rank, with predecessor-topological family order, registry-wide accounting key then
trial-number preregistration order, lifecycle sequence order, and deterministic
ID/hash tie-breaks. Exact duplicates
collapse idempotently. Conflicting identity or payload fails the whole `BEGIN IMMEDIATE`
transaction. All projected bounds are checked before inserts; an exact idempotent retry at
the full bound remains valid.

Generic append rejects `RunEvidenceReceipt`. `record_experiment_evidence` loads the complete
authoritative history inside one immediate transaction, derives role, all-labels-ready
eligibility, criteria, status, and OOS ordinal, and appends the resulting receipt atomically.
Exact evidence-request
retries remain idempotent after lifecycle advancement or closure: the already-verified
immutable receipt is returned without creating another exposure. Family summary accepts a
registry path, verifies complete history,
and returns every trial across the registry-wide accounting lineage, one current or terminal
status for every ascending trial, and every evidence status in sequence. It never accepts a
caller-fabricated snapshot or exposes a winner-only view.

The caller selects the explicit registry path. WP170 can enforce one ledger inside each
verified registry but cannot cryptographically link independently created registry files;
operational research authority therefore requires reuse and retention of the designated
repo-controlled registry rather than treating a new file as continuation evidence.

Every load verifies the exact schema, integrity checks, canonical payloads, record
identities, sequence continuity, and full history hash chain. Before commit, the complete
existing-plus-new history is revalidated: every dependency must be registered earlier;
manifests, splits, preregistrations, families, lifecycle chains, membership hashes, evidence
eligibility, OOS ordinals, and terminal close evidence must agree. Missing, mismatched, or
out-of-order dependencies reject and roll back.

## Compatibility, validation, and successor boundary

Existing priority, calibration, relationship, resolution, label, and wallet research
objects remain advisory non-signal inputs. WP167 analytical materialization, WP168 offline
replay, and WP169 acquisition/PIT promotion semantics are unchanged. No new dependency or
lock-file change is authorized; hosted CI provides Linux/Windows Python 3.12/3.14 evidence
using the already pinned environment.

The package prompt, machine spec, and independent draftability certificate are immutable
under `docs/wp_specs/WP170/`. The exact changed-file scope is 26, and the committed status
fragment is `docs/status_entries/WP170.md`.

WP171 — Interactive Operator Cockpit is the next separately gated work package. It is not
implemented here. WP172 Hermes, WP173 executable/cost modeling, WP174 portfolio and risk,
WP175 paper trading, WP176 authenticated execution, WP177 restricted live, and WP178 mature
live remain separately gated. WP170 does not start any successor.

## WP175D external dataset binding path (additive; canonical path preserved)

WP175D adds a second, additive dataset-binding path so validated external history can enter
the experiment OS without canonical-PIT masquerading. The original canonical path is fully
preserved: `build_dataset_binding` still requires a canonical `DatasetSnapshotReference`,
`build_research_dataset_manifest` still proves membership against the exact ordinary
record-version ids, and `SOURCE_KIND_CANONICAL_PIT` and every canonical `datasetbinding:sha256:`
identity byte are unchanged. Canonical PIT authority unchanged: YES.

The additive `ExternalDatasetBinding` (schema id `polymarket-external-dataset-binding`,
`source_kind` = WP167 external descriptor kind, generic `datasetbinding:sha256:` identity)
carries the real receive-time availability bounds from a validated PMXT v2
`PmxtV2ResearchLineage` and never creates a `DatasetSnapshotReference`. It persists under the
EXISTING `DATASET_BINDING` registry record kind with exact `schema_id` subtype dispatch, so
`wp170-experiment-registry`, `application_id=1464877424`, `MAX_REGISTRY_RECORDS=4096`,
`MAX_APPEND_BATCH=256`, and the `DATASET_BINDING` CHECK vocabulary are unchanged and old
canonical registries remain readable with no migration. `build_preregistered_experiment`
accepts either binding subtype with an unchanged public signature and unchanged
`OOS_REUSED_DIAGNOSTIC`, first-look sealing, `splitplan:sha256:`, `runevidence:sha256:`,
`PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY`, and `DECISION_TIME_HALF_OPEN` semantics.
External `ResearchSample` availability is bound to `timestamp_received` / `ts_init`, never the
source event time. The normative WP175D capability contract is
`docs/external_historical_research_bridge_contract.md`. Paper-trading execution is NOT
AUTHORIZED; Live-trading execution is FORBIDDEN; Merge authorized: NO.
