# Alpha Factory Research-System Gate Contract

## Status and authority

`S10-GATE-AF1` evaluates whether the merged Alpha research substrate is sufficiently
integrated, reproducible, bounded, and honest for separately gated downstream
research. It has no strategy, qualification, paper, execution, risk, capital, or
live-trading authority. The protected boundary groups in
`docs/ai/codex/PROTECTED_PATHS.md` remain closed.

The gate invariant is:

`research-system quality != hypothesis qualification != predictive edge != executable edge != profitability != trading authority`.

Phase A is deterministic and makes zero real market or provider calls. A later,
explicit human authorization must bind the exact Phase-A commit, contract digests,
provider/model labels, default controlled-runtime policy, public-population limits,
three-call ceiling, and USD 5 / USD 15 cost ceilings before Phase B can start.

## Canonical authorities

AF1 reads and verifies existing authorities; it does not replace them:

- PIT record/manifests retain market-evidence and knowability authority.
- ALPHA-01 retains canonical research-memory authority.
- ALPHA-02 retains universe, material-change, triage, skip, and queue authority.
- HERMES-CTX retains blind-artifact and sanitized session-evidence authority.

AF1 creates no registry or database. Its five immutable records are
`AF1BenchmarkManifest`, `AF1SeededCaseResult`, `AF1RealCaseEvidence`,
`AF1BlindReviewRecord`, and `AF1GateReceipt`. Each ID is the documented prefix plus
the SHA-256 of canonical JSON for the complete logical record excluding only its own
ID. Closed schemas, binary-float rejection, shared semantic validation, and required
no-authority booleans apply to every record.

## Deterministic Phase-A corpus

Exactly eight adversarial oracles cover duplicate identity, exact-scope negative
evidence, reopen semantics, PIT knowability, claim/evidence support, provider/backend
failure visibility, cost, and authority containment. All eight must pass before a
runtime authorization request. These oracles test system behavior only; they do not
measure market forecasts or profitability.

## Runtime envelope and benchmark chronology

The activation envelope is noncanonical local evidence under `local_data/` and is
never committed. It binds the Phase-A commit and three frozen contract digests,
authorized provider/model/default policy, the exact four WP164 provenance labels,
25 markets, one order book, no retry or fallback, at most three controlled blind
calls, USD 5 per case, and USD 15 aggregate.

Only after a valid bounded public population and frozen ALPHA-02 historical-replay
queue may AF1 create a canonical benchmark manifest. The Alpha-memory posture is
`HISTORICAL_AVAILABILITY_UNPROVEN`; no Alpha registry is manufactured and its head is
null. External all-Polymarket completeness remains unproven. A genuine missing lane
may be recorded only after real universe and queue IDs exist. External acquisition
unavailability creates no fabricated manifest.

## Selection, blind research, and review

The frozen queue deterministically selects the first `CORE_PRIORITY`, first
`EXPLORATION`, and selected `AUDIT` case. Each case uses the exact identity-only market
scope `{market_id, event_id, token_ids}` with scope key `af1-market-scope:` plus the
SHA-256 of the UTF-8 market id, canonical market/event/token subject references, one
fixed research question, and the merged default controlled-runtime policy. There is no
AF1 retry, replacement, fallback, fourth call, or H1 invocation.

Only a validated typed context draft may create a review body. The body contains the
exact scope, summary, confidence, verified URL/digest/source-class triples,
falsification checks, and the closed context-claim fields. Three distinct body hashes
sort into opaque `REVIEW-01` through `REVIEW-03` slots. Provider/model, lane, rank,
cost, runtime identity, and gate labels are absent. Side12 review binds the opaque
slot and immutable body hash with a closed label and reason vocabulary.

## Dimensions and disposition

The ten dimensions are `MEMORY_INTEGRITY`, `PIT_PROVENANCE`,
`DUPLICATE_NEGATIVE_SCOPE`, `MATERIAL_CHANGE_REOPEN`, `CLAIM_EVIDENCE_SUPPORT`,
`RUNTIME_FAILURE_VISIBILITY`, `BUDGET`, `AUTHORITY_CONTAINMENT`,
`COVERAGE_SELECTION_ACCOUNTING`, and `RESEARCH_USEFULNESS_REPRODUCIBILITY`.
Each is exactly `PASS`, `FAIL`, or `INCONCLUSIVE`.

- `AF1_PASS` requires every dimension to pass.
- `AF1_FAIL` results from any failed dimension.
- `AF1_INCONCLUSIVE` results when none fail and at least one is inconclusive.

No score, weighting, vote, profitability proxy, or prose override exists. A valid
fail or inconclusive result can be implementation-review-ready while still blocking
successor eligibility. An `AF1_PASS` says only that separately gated downstream
research may be considered.

## Phase-A checkpoint

The committed evidence placeholder is
`PHASE_A_IMPLEMENTED_RUNTIME_NOT_AUTHORIZED` with null manifest and receipt. After
the exact committed-head guards, focused and upstream regressions, scope/readiness,
security/artifact checks, package check, diff check, and one authoritative full suite
are green, the exact Phase-A commit and three contract hashes freeze. Execution then
stops at `AF1_RUNTIME_AUTHORIZATION_REQUIRED`.

## Local-evidence closure correction

The historical Phase-A commit `af07264a6dc85b9a7bfe6016042011685c957554`
remains an ancestor, but its attempted Phase-B runtime evidence and activation
envelope digest `0f7a26803538cb42c75c46513189008cc91f09d9fedbdcaa94c47b04e6af5326`
are invalidated historical audit facts only. They are not an AF1 disposition or an
A1/A2 result, and the historical `current` workspace is quarantined from reuse.

The corrected activation envelope is an exact closed schema. `retry_limit` is its
only retry field and must be integer zero; aliases, missing/nonzero values, and
unknown fields fail closed. The envelope also binds a fresh caller-selected
`workspace_attempt_id`, and its digest is computed only after complete validation.

Immediately before the one public-population coordinator call, the operator
exclusively and durably creates `AF1_PUBLIC_POPULATION_INVOCATION.json` with exactly
the Phase-A SHA, authorized envelope digest, attempt identity, 25/1 limits, and
`STARTED` state. An existing sentinel permanently prevents another call in that
workspace. The sentinel proves invocation start only.

Immediately after the coordinator returns, before classification or downstream
work, the operator exclusively persists every typed
`PolymarketPublicPopulationResult` field to
`AF1_PUBLIC_POPULATION_RESULT.json`, reads it back, and hashes its complete canonical
mapping. Missing, corrupt, mismatched, or unpersisted result evidence is a true
`PHASE_B_LOCAL_EVIDENCE_DEFECT`. Store length and logs never replace typed counts or
status evidence.

A1 external unavailability requires exactly a rejected, network-used result whose
sole error is `POPULATION_FETCH_FAILED` or `POPULATION_RESPONSE_INVALID`. Every
mixed/additional/different error and every local input, store, policy, guard, build,
batch, append, registration, recovery, or unexpected error remains a true local
defect.

`public_population_result_sha256` is required identity material in
`AF1BenchmarkManifest`. It is nullable identity material in `AF1GateReceipt`, but is
non-null on every path that reached the coordinator, equals the manifest value on
manifest-backed paths, binds A1 directly when the manifest is null, and is null only
when population was never invoked. Committed evidence carries the digest, never the
raw local result. Any later real attempt requires a new authorized Phase-A checkpoint,
fresh workspace, attempt identity, stores, sentinel, and envelope.

## Post-WP164A reconciliation and Phase-A recertification

The current certified base is `70f867bdcd5e97b0dc05d4008c2c023feb461658`, the PR #193
merge of WP164A whose exact runtime-certified head is
`1c7de22f31cd093771d6bc0748c440ad5284b105`. WP164A Attempt-03 is consumed as
`WP164A_PUBLIC_SMOKE_COMPLETE_SUCCESS`; its observed 25/1/26/26 counts are historical
evidence, not contract guarantees, and AF1 is no longer blocked by WP164A. AF1 Attempts 01
and 02 remain consumed historical evidence; AF1 Attempt-03 and H1 #5 remain unauthorized.

- **Complete result.** The operator retains the exact current 38-field
  `PolymarketPublicPopulationResult` before any other work; the key set must equal that
  contract and the retained bytes define `public_population_result_sha256`.
- **Actual counts.** Fresh success is `POPULATION_PERSISTED_AND_REGISTERED` with
  `1 <= markets <= 25`, `0 <= books <= 1`, `built = markets + books`, `inserted = built`,
  unique accepted ids equal to `built`, a valid batch (warnings such as
  `EVENT_TIME_MISSING_ALLOWED` are retained, not failures), no build diagnostics, committed
  store/adapter statuses, and verified stores whose record ids, manifest entry, dataset
  reference, AF1 labels, and batch digest match. `POPULATION_ALREADY_REGISTERED` in a fresh
  workspace is a local defect.
- **A1 exactness.** A1 additionally requires empty verified stores and no build, batch,
  store, or registration evidence; build and batch diagnostics are retained verbatim.
- **One cutoff.** The retained `captured_at_utc` equals the universe `as_of` and every
  campaign `information_cutoff` (HERMES-CTX canonical spelling of the same instant); no
  later wall-clock value is sampled.
- **Alpha posture.** `HISTORICAL_REPLAY`, `HISTORICAL_AVAILABILITY_UNPROVEN`, no Alpha
  registry, no prior, no material changes. Core capacity is one and audit is not
  category-capped. A missing lane (`REQUIRED_LANE_ABSENT`) or a selected market without
  usable `question_text` (`REQUIRED_LANE_NOT_RESEARCH_EXECUTABLE`) finalizes A2 with zero
  Hermes calls.
- **Context store.** `ContextArtifactStore` receives an absolute
  `<workspace>/context_artifacts/case-N` root; relative, `..`, symlinked, or outside roots
  are rejected, and every workspace resolves beneath `local_data/s10_gate_af1/`.
- **Retry truth.** AF1 `retry_limit=0` and at most three controller calls are distinct from
  the managed Hermes profile's truthful `api_max_retries=1` same-provider recovery.
  Provider/model fallback is none; unknown physical attempt counts and unattested backend
  telemetry are not treated as fallback.
- **Terminal and review paths.** The receipt graph is closed per terminal path, the ten
  dimensions derive from one closed override table replayed by `verify-final`, and only the
  three-valid-case path produces the opaque review bundle.
- **Envelope.** `AF1_RUNTIME_AUTHORIZATION_ENVELOPE.json` inside
  `local_data/s10_gate_af1/<PHASE_A_SHA>/attempt-03` is an exact closed 38-key schema whose
  three contract digests must equal the raw bytes on disk.
- **Runtime-environment preflight.** `run-real` requires explicit `--hermes-executable`
  and `--hermes-home` machine-local launch parameters (never envelope keys or committed
  evidence). Before the population sentinel exists, both must be absolute, alias-free real
  paths outside the repository and `local_data`, the home must pass the existing safe and
  clean control-plane checks, and the pinned executable must pass the merged offline
  version (exactly 0.21.3) and `--help` startup probes. Any failure is
  `PHASE_B_LOCAL_EVIDENCE_DEFECT` with zero calls, and the attempt is not consumed. The
  validated values reach every `run_blind_phase` call; no PATH or default-home fallback.
