# External Historical Research Bridge Contract (WP175D / S10-DATA-02)

Status: normative capability contract for the WP175D external historical research
bridge. Local/offline research only. No network, downloader, credential, scheduler,
Hermes, strategy, paper, execution, or live authority. Canonical PIT authority
unchanged: YES. Merge authorized: NO.

## Purpose

WP175D closes the root cause behind
`LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE`: the merged WP170 experiment OS
accepts only canonical point-in-time (PIT) research lineage
(`DatasetSnapshotReference` / `SOURCE_KIND_CANONICAL_PIT`), and canonical PIT
visibility is ingestion-time authoritative and must never be backdated. Validated
third-party PMXT v2 external history therefore cannot be inserted as canonical PIT
knowledge from the past. This contract defines the smallest truthful,
provenance-separated bridge from that already-validated external history into a
standard WP170 `ResearchDatasetManifest`, so a later, separately authorized
evidence run can produce a genuine WP170 -> WP172 -> WP173 chain.

WP175D does NOT choose a strategy, expose OOS, run WP172, run paper trading,
download data, activate Gate C, or trade.

## Capability boundary

The bridge adds exactly one capability: validated PMXT v2 external-history events can
become a content-addressed, provenance-separated WP170 dataset binding
(`ExternalDatasetBinding`) and a standard `ResearchDatasetManifest`, while retaining
real source availability time and without acquiring canonical-PIT authority. The
bridge is PMXT-v2-specific for this WP; generic arbitrary external-provider support
is not claimed.

## Public surface

- `build_pmxt_v2_research_lineage(source, context, member_event_digests)` ->
  `PmxtV2ResearchLineage` with `PmxtV2ResearchLineageMember` entries. A bounded
  (<= 4096), nonempty, unique selection of exact existing WP168 ordered event-digest
  identities (`<canonical-row-sha256>:<duplicate-ordinal>`), each present exactly
  once in the canonical source stream. Missing, duplicate, malformed, or over-limit
  input rejects closed. The lineage builder and `convert_pmxt_v2_events` share ONE
  internal canonical row validation/order/duplicate-ordinal implementation.
- `build_pmxt_v2_dataset_binding(lineage, code_version)` -> `ExperimentControlResult`
  containing an `ExternalDatasetBinding` on PASS.
- `build_pmxt_v2_research_dataset_manifest(lineage, dataset_binding,
  feature_definitions, label_definition, sample_inputs, group_policy)` ->
  `ExperimentControlResult` containing a standard `ResearchDatasetManifest` on PASS.
- `ExternalDatasetBinding` (public record type) in the WP170 experiment OS. Its
  generic construction/validation helper is PRIVATE/internal
  (`experiment_os._build_external_dataset_binding`) and is intentionally NOT exported
  from the `src.data_layer.analytical_research` package root, so arbitrary
  caller-supplied external metadata cannot construct a binding outside the validated
  PMXT lineage bridge. The ONLY public construction path is
  `build_pmxt_v2_dataset_binding` / `build_pmxt_v2_research_dataset_manifest`, which
  build from a validated `PmxtV2ResearchLineage`. The bridge module never makes
  `experiment_os` import `research_runtime`.

## Provenance and time semantics

- Lineage identity prefix `pmxtresearchlineage:sha256:` binds source dataset kind,
  external dataset id, instrument id, conversion policy version, the canonical
  selected-member order, member count, membership digest, and first/last event and
  availability bounds. Physical source file order and caller request order cannot
  change it.
- Member identity prefix `externalmember:sha256:` binds source external dataset id,
  instrument id, conversion policy version, source event digest, event type, event
  time, and availability time. It contains no path and no raw row. Byte-identical
  duplicate source rows stay distinct via the existing `digest:ordinal` semantics and
  therefore have distinct member ids.
- CRITICAL TIME RULE: `event_time_ns` is the PMXT source timestamp (existing
  `ts_event`) and is diagnostic/source semantics only. `availability_time_ns` is the
  PMXT `timestamp_received` (existing `ts_init`). Availability, leakage, and later
  sample admission use `availability_time_ns`, NEVER `event_time_ns`.

## ExternalDatasetBinding (additive, never canonical PIT)

`ExternalDatasetBinding` is additive to the canonical `DatasetBinding`. Its
`schema_id` is `polymarket-external-dataset-binding`; its `source_kind` is the WP167
external descriptor kind `WP167_EXTERNAL_DATASET_DESCRIPTOR` (never
`SOURCE_KIND_CANONICAL_PIT`). The `dataset_binding_id` remains the generic
`datasetbinding:sha256:` content-addressed id whose preimage includes every semantic
field except the id and the two safety booleans. No local path is stored, no
`DatasetSnapshotReference` is created, and no `AnalyticalDatasetManifest` with
`SOURCE_KIND_CANONICAL_PIT` is fabricated. `advisory_only` and
`no_execution_authority` are always true.

## External ResearchSample admission

The bridge produces the STANDARD WP170 `ResearchDatasetManifest` and `ResearchSample`
records. On the external path, `source_record_version_ids` retains its legacy schema
field name for backward compatibility, but carries external source-evidence member
ids (`externalmember:sha256:`) from THIS exact lineage and never claims canonical
record-version authority. Admission additionally enforces:

- every cited external member exists in the exact bound lineage;
- `feature_availability_time` is at or after the maximum actual `availability_time_ns`
  of all cited members;
- `feature_availability_time` is at or before `decision_time`;
- all existing target/label/group/duplicate/source-membership rules are unchanged;
- timestamp comparison is exact and integer/datetime based, never binary float.

The bridge computes no features, labels, strategy returns, metrics, or results. The
canonical `DatasetBinding` path continues to require real canonical ordinary
record-version ids exactly as before.

## Preregistration and registry compatibility

`build_preregistered_experiment` admission accepts either a canonical
`DatasetBinding` or an `ExternalDatasetBinding`; its public signature and all split,
preregistration-before-OOS, first-look sealing, evidence-receipt, and
multiple-testing/family accounting semantics are unchanged.

`ExternalDatasetBinding` persists under the EXISTING registry record kind
`DATASET_BINDING`. `REGISTRY_FORMAT_ID`, `REGISTRY_SCHEMA_VERSION`,
`REGISTRY_APPLICATION_ID`, the SQLite table/trigger/index schema, and the
`DATASET_BINDING` CHECK vocabulary are unchanged. Decoding a `DATASET_BINDING`
record dispatches by exact `schema_id`
(`polymarket-experiment-dataset-binding` -> `DatasetBinding`;
`polymarket-external-dataset-binding` -> `ExternalDatasetBinding`); any other
`schema_id` fails closed as registry integrity tamper with no ambiguous subtype
inference. Old canonical-only registries remain readable with no migration, repair,
or rewrite.

## Authority posture

Network: NONE. Credentials: NONE. Downloader: NONE. Dependencies/lock/workflow
files: UNCHANGED. Scheduler/Hermes/paper/strategy/execution/live: NONE. Capital at
risk: USD 0. Canonical PIT authority unchanged: YES. External provenance preserved:
YES. WP175 Gate-C activation: NOT AUTHORIZED. WP176: NOT STARTED. Merge authorized:
NO.

## Successor

The first successor is the separately gated evidence run S10-EVID-01 (genuine
strategy evidence production through WP170 -> WP172 -> WP173), then canonical WP176
Mature Controlled Live. WP175-D002 / S10-DATA-02 closes only when WP175D is merged.
`LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE` remains true until genuine evidence
is later produced.
