# Control Center Alpha Factory + Discovery Research Contract (S10-CC-RESEARCH-02)

## Purpose

S10-CC-RESEARCH-02 completes the Control Center Research phase. It exposes the two canonical Alpha
research layers as one bounded, read-only `/alpha` workspace:

- **Research Memory**: the verified Alpha Factory registry (source reference -> opportunity
  candidate -> hypothesis family -> research episode).
- **Discovery Queue**: the verified Alpha Discovery registry (policy -> universe -> material change
  -> triage decision -> research queue).

The projection makes recorded research history, evidence and lineage inspectable. It is not a
second research truth system and it carries no authority. The separations are permanent:

```text
Alpha research memory != Alpha discovery priority != qualification != StrategyLifecycle identity
!= Hermes soft judgment != experiment/OOS evidence != EXEC-FEAS != Gate-C != paper/live authority
```

- Alpha memory != qualification.
- Alpha discovery priority != trade priority.
- Strategy/Hermes linkage = NONE unless a future canonical binding exists.

## Sources (verified loaders only)

| Source | Only allowed loader | Requirement | Store identity |
|---|---|---|---|
| Alpha Factory | `load_and_verify_alpha_factory_registry(path)` | `is_valid` and an `AlphaFactoryRegistrySnapshot` | `s10-alpha-factory-registry`, schema 1, application id 1464877425 |
| Alpha Discovery | `load_and_verify_alpha_discovery_registry(path)` | `is_valid` and an `AlphaDiscoveryRegistrySnapshot` | `s10-alpha-discovery-registry`, schema 1, application id 1464877426 |

The projection lives in the existing `src/operator_cockpit_research.py` module. It never imports
`sqlite3`, opens a store, initializes or appends, repairs records, reimplements hash-chain
verification, fabricates a snapshot, discovers a store path, scans `local_data` or worktrees, or
reads environment variables. Each verified snapshot is the sole integrity authority for its layer.
`PreAllocationTriageBasis` is internal to Discovery and is never exposed.

Store paths are explicit configuration only: two optional fields appended after every existing
`CockpitConfig` field (`alpha_factory_registry_path`, `alpha_discovery_registry_path`) and two CLI
flags (`--alpha-factory-registry`, `--alpha-discovery-registry`). There is no default path or
fallback, and no API response contains a filesystem path. Existing positional construction (for
example `CockpitConfig(None, None, None, None, lifecycle_path, hermes_path)`) is unchanged.

## Source Independence

- Alpha Factory configured, Discovery unavailable: `/api/alpha/memory`, `/api/alpha/candidates`,
  `/api/alpha/candidates/{candidate_id}` and `/api/alpha/episodes/{research_episode_id}` work;
  Discovery routes return `SOURCE_UNAVAILABLE`.
- Discovery configured, Alpha Factory unavailable: the queue and triage routes work; canonical
  matched Alpha ids stay visible on the triage record; `alpha_memory_resolution.status` is
  `UNAVAILABLE`; Alpha memory routes return `SOURCE_UNAVAILABLE`.

## Routes (GET only)

| Route | Body |
|---|---|
| `GET /api/alpha/memory` | memory summary object |
| `GET /api/alpha/candidates` | `{items, count, limit}` |
| `GET /api/alpha/candidates/{candidate_id}` | `{candidate, hypothesis_families, research_episodes, source_references, deterministic_evidence_refs, lineage_summary}` |
| `GET /api/alpha/episodes/{research_episode_id}` | `{item}` |
| `GET /api/alpha/discovery/queue` | `{discovery_registry_head_entry_hash, queue_sequence_number, queue, policy, universe, lanes}` |
| `GET /api/alpha/discovery/triage/{market_triage_decision_id}` | `{triage, universe_market, material_change, alpha_memory_resolution}` |

The cockpit `/api` route set is exactly 24 (18 existing + these 6). POST, PUT, PATCH and DELETE
return 405. The candidate list uses the existing bounded `limit` (default 50, 1..100); a duplicate
`limit` or any unknown query key is `INVALID_INPUT`. No filter, search or pagination protocol exists.

## Identifier Validation

```text
candidate          ^alphacandidate:sha256:[0-9a-f]{64}$
research episode   ^alphaepisode:sha256:[0-9a-f]{64}$
triage decision    ^alphatriage:sha256:[0-9a-f]{64}$
```

Malformed ids fail with 400 `INVALID_INPUT` before any source access. A well-formed id absent from
a valid configured source is 404 `NOT_FOUND`. Rejected ids are never echoed.

## Closed Error Mapping

| Condition | Status / code |
|---|---|
| malformed path identifier | 400 `INVALID_INPUT` |
| valid identifier absent from a valid configured source; valid Discovery registry with no queue | 404 `NOT_FOUND` |
| required source unconfigured, missing, wrong suffix, ambiguous, tampered, invalid or wrong schema | 503 `SOURCE_UNAVAILABLE` |
| same-snapshot reference that cannot be resolved; unexpected projection failure | 503 `SOURCE_UNAVAILABLE` |

Bodies are exactly `{"error": {"code": ...}}`. Internal Alpha error codes, SQLite text, paths,
tracebacks, exception text, raw invalid ids and raw invalid records never leak.

## Alpha Memory Summary

`head_entry_hash`, `total_rows`, `total_payload_bytes`, `record_counts`
(`research_source_references`, `opportunity_candidates`, `hypothesis_families`,
`research_episodes`) and the four true no-authority flags (`advisory_only`,
`no_execution_authority`, `no_strategy_authority`, `no_qualification_authority`). A valid empty
registry is 200 with `head_entry_hash: null` and zero counts; it is not unavailable.

## Candidate Ordering

Candidates are ordered by registry `sequence_number` DESC, then `candidate_id` ASC. The sequence is
canonical registry append order, not a timestamp. `limit` applies after sorting and `count` is the
returned item count. `is_multi_lane` is derived only as `len(evidence_lanes) >= 2`; `COMPOSITE` is
never invented or stored.

## Candidate Lineage and Research Leaves

Candidate detail contains only same-candidate episodes (registry sequence ASC) and the hypothesis
families those episodes reference (sequence ASC, then id ASC), all from the same verified snapshot.
Source references are the union of those episodes' references (sequence ASC); deterministic evidence
references are their first-seen union.

Within one exact `(candidate_id, hypothesis_family_id)` lineage an episode is non-leaf when another
episode of that lineage names it as `predecessor_episode_id` or `reopened_episode_id`; otherwise it is
a **research leaf**. Several leaves may coexist (divergent branches are displayed truthfully) and
none is required to be unique. A research leaf is never labelled qualified, qualification-ready,
approved or tradeable.

## Episode Evidence and Source References

Episode detail returns the exact canonical episode fields, including every evidence-for/against,
uncertainty, missing-data, falsification, limitation, change-the-conclusion and next-step text,
`exact_scope_json`, `evidence_regime_json`, producer provenance and the no-authority flags. Each
`source_reference_id` is resolved only from the same verified snapshot to `source_reference_id`,
`source_kind`, `source_class`, `source_locator`, `title`, `observed_at`, `content_sha256`,
`provenance`, `public_research_only`, `advisory_only` and `no_execution_authority`; an unresolvable
reference is `SOURCE_UNAVAILABLE`. `source_locator` is validated public/research metadata rendered as
text only: never linked, fetched or previewed. `deterministic_evidence_refs` are opaque canonical
references: no type, URL, file, experiment, gate or route is guessed for them.

## Research Result States

`RESEARCH_SUPPORTIVE`, `NO_EDGE_CURRENTLY`, `HYPOTHESIS_FALSIFIED`, `DATA_INSUFFICIENT`,
`EXECUTION_UNECONOMIC`, `WATCH_FOR_CHANGE`, `RESEARCH_STALE`, `REOPEN_TRIGGERED`,
`MECHANISM_FAMILY_EXHAUSTED` are shown exactly as recorded.

`RESEARCH_SUPPORTIVE` means research evidence suggests further deterministic qualification may be
worthwhile. It is not `QUAL_PASS`, qualified, proven predictive edge, OOS positive, executable edge,
profitable, paper ready, live ready or Gate-C eligible. Negative states are exact-scope /
evidence-regime records only, never a permanent market or category blacklist. A reopen is
append-only lineage; the earlier episode is never mutated or visually replaced.

## Discovery Queue

The latest recorded discovery queue is the `AlphaResearchQueueSnapshot` with the greatest Discovery
registry `sequence_number`; no wall clock is used. A valid registry with no queue is `NOT_FOUND`.
Policy, universe and every triage id are resolved from the same verified snapshot.

- Queue: canonical identity, temporal mode/posture, Alpha binding head, historical flags, capacity,
  configured/selected/unused slots, unused-capacity reasons, `max_per_category`,
  `prior_only_market_ids`, no-authority flags.
- Policy: id, version, eligible statuses, the three recorded freshness thresholds, capacity/slot
  settings, taxonomy version. `audit_seed` is omitted.
- Universe: id, `as_of`, cutoff mode, query engine/parameter ids, `coverage_scope`,
  `external_universe_completeness`, market count. The universe is always shown as
  `BOUNDED_OBSERVED_UNIVERSE` with completeness `UNPROVEN`; it is never presented as all of
  Polymarket.
- Lanes: `core`, `exploration`, `audit`, `deferred`, `skipped_ineligible`, `skipped_capacity`, each
  in the queue's exact canonical array order, as triage summaries.

The queue is never labelled a live queue, current market queue or current Polymarket universe.

## Triage Detail

`triage` carries the bounded public `MarketTriageDecision` fields (market/event/category,
eligibility, priority class, reopen disposition, readiness, reason codes, capture requests, material
change id, newly-observed flag, final disposition, selected lane, audit fields, temporal mode and
posture, Alpha binding head, historical replay flags, matched Alpha ids, coverage, no-authority
flags). `universe_market` is a bounded summary of the exact market in the triage's universe (rule and
book counts only, never their payloads). `material_change` is the exact referenced
`MaterialChangeEvent` or `null`. An unresolvable reference is `SOURCE_UNAVAILABLE`.

## Exact Alpha-Memory Resolution (display only)

The only Discovery -> Alpha relationship is the triage record's stored `matched_candidate_ids`,
`matched_hypothesis_family_ids` and `matched_research_episode_ids`. No textual or fuzzy join exists.

| Status | Rule |
|---|---|
| `NOT_BOUND` | `triage.alpha_registry_head_entry_hash` is null; nothing resolved |
| `UNAVAILABLE` | a head is bound but the Alpha Factory store is unconfigured or cannot be verified; matched ids stay visible; the Discovery route still succeeds |
| `HEAD_MISMATCH` | both sources verify but the Alpha snapshot head differs from the bound head; nothing is resolved against the wrong snapshot |
| `RESOLVED` | the bound head is non-null and equals the verified Alpha snapshot head exactly; only the matched ids are resolved |

Under a matching head, a matched id that is missing or of the wrong type is an impossible
cross-source inconsistency and the route fails `SOURCE_UNAVAILABLE`. `HEAD_MISMATCH` is research
lineage/currentness truth only: it is not market freshness and not authority.

## Discovery Vocabulary Semantics

- `CORE_PRIORITY` is a research allocation lane, not trade priority.
- `READY` is research-control readiness, not trading readiness.
- `REOPEN_ELIGIBLE` is a research reopen condition, not strategy or live authorization.

Priority, readiness, final-disposition, reopen and coverage vocabularies are shown exactly as
recorded.

## No Strategy / Hermes / Qualification / AF1 Inference

Alpha candidates, families and episodes are never joined to `StrategyVersion`, `StrategyFamily`,
`HermesStrategyAssessment`, `QualificationCandidate`, `QualificationGateReceipt` or
`PreregisteredExperiment` by title, label, question, thesis, subject or evidence refs, source refs,
producer receipt, provenance or hash text. No field such as qualified, qualification_ready,
approved, tradeable, profitable, expected_return, strategy_selected, execution_ready, paper_ready,
live_ready or gate_c_passed exists. There is no qualification route, list, packet construction, gate
evaluation or PASS inference, and the package-specific AF1 gate evidence is not parsed.

## Frontend

- One new primary route `/alpha`; navigation `/overview /markets /experiments /strategies /hermes
  /alpha /paper /audit`.
- Component-local tabs: **Research Memory** and **Discovery Queue** (no state library).
- `QueryFamily` gains `alpha`; keys `["cc","alpha","memory"]`, `["cc","alpha","candidates","list"]`,
  `["cc","alpha","candidates","detail",candidate_id]`,
  `["cc","alpha","episodes","detail",research_episode_id]`, `["cc","alpha","discovery","queue"]`,
  `["cc","alpha","discovery","triage",market_triage_decision_id]`.
- Conservative Query defaults are unchanged (no retry, no focus/reconnect refetch, `staleTime`
  Infinity, no polling, EventSource or WebSocket). Refresh on `/alpha` invalidates only the `alpha`
  family. There is no mutation, run, qualify, promote, reopen or trade control.
- Required notices: "Alpha Factory records research history. RESEARCH_SUPPORTIVE is not
  qualification, executable edge, profitability or trading authority." and "Discovery priority is
  research allocation only. It is not strategy selection or trade priority."
- Long ids, locators and canonical JSON wrap without page-level horizontal overflow.
- Storybook/MSW reference states intercept every `/api/alpha/**` surface.

## Currentness Wording

This phase is read-only and manually refreshed. The UI uses "recorded research memory",
"registry head", "latest recorded discovery queue", "universe as_of", "recorded freshness" and
"Alpha-memory binding head". It never claims live, up-to-date-now, current-market or streaming
state unless a canonical record owns the field. Query-cache staleness is unrelated to domain
freshness. Realtime delivery is S10-CC-STREAM-01.

## Non-Authority

No Alpha Factory or Discovery mutation, Hermes invocation, provider/model call, external
product/source request, credential, account read, strategy or paper mutation, qualification action,
EXEC-FEAS, Gate-C, LIVE-ORCH, signing, order, capital, deployment, dependency, workflow or live
authority. This contract supersedes the S10-CC-RESEARCH-01 "Alpha Exclusion" section only by adding
the verified read-only Alpha projections above; the Strategy/Hermes contract is otherwise unchanged.
