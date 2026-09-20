# Alpha Factory Core Contract (WP175N / S10-ALPHA-01)

## 1. Status And Purpose

S10-ALPHA-01 Multi-Lane Alpha Factory Core is the first canonical Alpha Factory
research-memory substrate. WP175N is the CURRENT_REVIEW_TARGET implementing it; it is
NOT merged, and Gate C is NOT AUTHORIZED. The Alpha Factory is deterministic, bounded,
append-only, local/offline research memory for public/research source references,
research-worthy opportunity candidates, hypothesis/mechanism families, and immutable
research episodes.

Alpha Factory RECORDS research history. It does NOT prove alpha, qualify strategies,
construct WP170 experiments, estimate fair value/probability, rank or prioritise
opportunities, choose side/size, schedule campaigns, call any provider, ingest wallets,
compute executable economics, or create paper/live/Gate-C authority.

Core invariant:

ALPHA FACTORY MEMORY RECORDS RESEARCH HISTORY. DETERMINISTIC QUALIFICATION AND ECONOMIC
AUTHORITY REMAIN OUTSIDE THIS PACKAGE.

## 2. Genuine H1 Basis

S10-GATE-H1: GENUINE_H1_PASS. Accepted H1: H1 #4. Historical real H1 research invocations
consumed: 4 (H1 #1, H1 #2, H1 #3, and H1 #4 were each separately authorized and
consumed). H1 #5 is NOT AUTHORIZED. The accepted H1 #4 machine state was
RESEARCH_DRAFT_VALIDATED (provider/model openai-codex / gpt-5.6-sol, receipt
hermes-research-run-receipt/1.3.0, 22/22 required draft fields present, deterministic
safety PASS, Side11 independent content review PASS). A genuine machine PASS plus an
independent useful/source-grounded quality review was the condition that unlocked
S10-ALPHA-01; that condition was satisfied by H1 #4.

## 3. HAP-01 .. HAP-12 (Canonical Current Truth)

- HAP-01: The accepted H1 inference route was OpenAI Codex via ChatGPT OAuth.
- HAP-02: The accepted H1 model was gpt-5.6-sol.
- HAP-03: The H1 runtime/profile contract required a dedicated Firecrawl-only web backend
  with keyless fallback/rescue disabled and no automatic paid top-up. The matched H1 #4
  session persisted web_search and web_extract tool activity. Pinned Hermes v0.21.3 does
  NOT independently expose downstream Firecrawl HTTP telemetry; direct backend HTTP proof
  that does not exist is NOT claimed (configured Firecrawl-only contract is distinct from
  absent independent backend HTTP telemetry; remote Firecrawl HTTP independently proven:
  NO).
- HAP-04: Every REAL H1 invocation required separate explicit human authorization. H1 #1,
  #2, #3 and #4 were separately authorized and consumed. There was NO automatic controller
  rerun, provider/model substitution, web-backend substitution, or automatic paid-credit
  purchase. H1 #5 is NOT AUTHORIZED. Future autonomous research requires separately
  bounded campaign budgets/rates.
- HAP-05: Hermes may eventually receive broad APPROVED READ-ONLY research information. No
  private keys, signing, order/cancel, capital transfer, or deterministic economic
  authority.
- HAP-06: Later research autonomy may operate only inside explicit model/tool/rate/budget
  limits.
- HAP-07: A genuine machine PASS plus independent useful/source-grounded quality review
  was required to unlock S10-ALPHA-01; satisfied by H1 #4.
- HAP-08: Gate C and live capital remain separately human-authorized.
- HAP-09: No silent provider/model/backend fallback. Any later fallback/escalation must be
  explicit, logged, and budgeted.
- HAP-10: Alpha Factory is canonical project research memory. Hermes
  chat/session/persistent memory is not project authority.
- HAP-11: Long-term research target: scan -> change detection -> prioritization ->
  research -> hypothesis -> outcome learning.
- HAP-12: Hermes research-layer self-improvement may later modify research prompts,
  retrieval, source selection, critics/routing, and related research methods only through
  benchmarked, versioned, reversible governance. It never gains qualification, execution,
  risk, signing, credential, capital, or Gate-C authority.

## 4. Optimization Hierarchy

cost per useful research observation -> cost per novel/falsifiable hypothesis -> cost per
qualified candidate -> cost per durable realized edge.

## 5. Authority Separation

S10-ALPHA-01 is PRE-QUALIFICATION CANONICAL RESEARCH MEMORY. WP170 is the
PREREGISTRATION / EXPERIMENT / OOS EVIDENCE OS. S10-QUAL-01 is the future deterministic
crossing between those systems. The Alpha Factory holds no strategy, qualification,
economic, paper, live, credential, scheduler, or Gate-C authority.

## 6. Canonical Alpha-Memory Rule

Only a validated ResearchEpisode committed to the Alpha Factory registry becomes canonical
Alpha research memory. HERMES producer status grants no authority advantage. Producer,
provider, and model identity never change any mechanism fingerprint.

## 7. Record Model

Four frozen, closed-field, content-addressed record types (schema version
`1.0.0`): `ResearchSourceReference` (`alphasource:sha256:`), `OpportunityCandidate`
(`alphacandidate:sha256:`), `HypothesisFamily` (`alphafamily:sha256:`), and
`ResearchEpisode` (`alphaepisode:sha256:`). Every record is advisory_only,
no_execution_authority, and (where the field exists) no_strategy_authority and
no_qualification_authority, all exactly true. No local path, no registry write time, no
environment metadata, and no binary float enters any logical identity.

## 8. Primitive Evidence Lanes / Derived Multi-Lane

Stored evidence-lane vocabulary is primitive only: `HISTORICAL_REPEATABILITY`,
`FUNDAMENTAL`, `WEATHER`, `CROSS_MARKET`, `RESOLUTION_RULES`, `MICROSTRUCTURE`. COMPOSITE
is NOT stored. "Composite / multi-lane" is DERIVED only: `is_multi_lane =
len(evidence_lanes) >= 2`. Lane input order never changes identity; unknown/duplicate
lanes are rejected. This prevents `{WEATHER, FUNDAMENTAL}` and `{COMPOSITE, WEATHER,
FUNDAMENTAL}` from becoming two identities for the same evidence.

## 9. Result-State Matrix

Closed result states: `RESEARCH_SUPPORTIVE` (evidence_for non-empty; means further
deterministic qualification may be worthwhile, NOT qualified/profitable/tradeable),
`NO_EDGE_CURRENTLY` (evidence_against non-empty; exact scope/regime only, no permanent
ban), `HYPOTHESIS_FALSIFIED` (evidence_against + falsification checks), `DATA_INSUFFICIENT`
(known_missing_data non-empty), `EXECUTION_UNECONOMIC` (deterministic_evidence_refs +
evidence_against; ALPHA-01 does not compute economics), `WATCH_FOR_CHANGE`
(what_would_change_the_conclusion non-empty), `RESEARCH_STALE` (material_change_basis
non-empty; ALPHA-01 does not calculate staleness), `REOPEN_TRIGGERED` (reopened_episode_id
+ material_change_basis; append-only), and `MECHANISM_FAMILY_EXHAUSTED` (evidence_against +
falsification checks; never globalises to a category/market ban). Every episode requires
non-empty falsification_checks_performed, a closed confidence label, and at least one
source_reference_id or deterministic_evidence_ref.

## 10. Exact-Scope Negative Evidence

Negative states bind to the exact `exact_scope_json` and `evidence_regime_json`; a
one-field scope/regime difference produces a distinct episode identity. Negative research
never becomes a market/category permanent blacklist and there is no blacklist API.

## 11. Reopen Immutability

Reopening appends a new `REOPEN_TRIGGERED` episode that references a prior episode of the
SAME candidate and family whose state is not `RESEARCH_SUPPORTIVE` or `REOPEN_TRIGGERED`.
No old record is ever mutated. Reopen is caller-supplied explicit evidence only; automatic
freshness/reopen decisioning is ALPHA-02, not this package.

## 12. Novelty / Mechanism Identities

`novelty_fingerprint` (`alphanovelty:sha256:`) hashes the closed structured novelty
dimensions (`subject_keys`, `scope_key`, `mechanism_key`) plus the canonical primitive
evidence-lane tuple; title/thesis prose is excluded. `mechanism_fingerprint`
(`alphamechanism:sha256:`) hashes only `mechanism_key` and `mechanism_dimensions_json`,
excluding producer/provider/model/prose/path/registry-sequence/environment. These
fingerprints are separate from record ids: record ids preserve immutable full research
history, while fingerprints enforce semantic duplicate resistance. A semantically identical
structured novelty fingerprint conflicts with a non-identical candidate (NOVELTY_DUPLICATE);
one mechanism fingerprint cannot be silently claimed by two non-identical families
(MECHANISM_CONFLICT).

## 13. Producer Provenance

Producer types: `HUMAN_RESEARCH`, `HERMES_CONTROLLED_RESEARCH`, `DETERMINISTIC_ANALYSIS`,
`OTHER_VALIDATED_ADVISORY`. HERMES_CONTROLLED_RESEARCH requires a non-null
producer_receipt_ref; HUMAN_RESEARCH and OTHER_VALIDATED_ADVISORY require at least one
source_reference_id; DETERMINISTIC_ANALYSIS requires at least one deterministic_evidence_ref.
Producer/model/provider identity never changes a mechanism fingerprint and grants no
authority advantage.

## 14. Nested Mapping / Secret / Authority Safety

Every caller free-form mapping (novelty dimensions, mechanism dimensions, exact scope,
evidence regime) is bounded (max depth 8, max nodes 4096, max keys 512, max sequence items
256, max nested JSON bytes 262144, max string 8192) and canonicalised deterministically
(UTF-8, sorted keys, compact separators, allow_nan=False). Binary float is rejected
recursively at every depth. Secret-like keys (api_key, apikey, secret, secret_key,
private_key, seed_phrase, mnemonic, passphrase, auth_token, access_token, bearer_token,
authorization, cookie, set_cookie, authenticated_headers) and authority-like keys
(place_order, cancel_order, submit_order, sign_transaction, position_size, expected_return,
trade_signal, live_signal, paper_order, risk_override, execute, auto_trade, auto_copy,
scheduler_command, credential_request) are rejected case-insensitively, and rejected
keys/values/payloads are never echoed in public failure objects. PUBLIC_HTTPS locators must
be https with a hostname, no userinfo, no local/file semantics, and no secret-bearing query
key (api_key, apikey, token, access_token, auth, authorization, secret, password,
passphrase, signature, credential, private_key); locators are never fetched.

## 15. Registry Design

The Alpha Factory registry (`src/data_layer/analytical_research/alpha_factory_registry.py`)
is a bounded, append-only SQLite store: format id `s10-alpha-factory-registry`, integer
schema version 1, and application id 1464877425. Record kinds: RESEARCH_SOURCE_REFERENCE,
OPPORTUNITY_CANDIDATE, HYPOTHESIS_FAMILY, RESEARCH_EPISODE. It uses an `alpha_registry_meta`
singleton, an `alpha_registry_records` table with a per-entry SHA-256 hash chain, and
BEFORE UPDATE / BEFORE DELETE triggers that raise `append-only`. PRAGMA contract:
application_id 1464877425, user_version 1, journal_mode DELETE, synchronous FULL,
foreign_keys ON. Paths are explicit caller `.sqlite3` files only (no `:memory:`, no
home/env discovery, no directory creation, symlink/hard-link rejected). `initialize`
exclusively creates a missing file and reports ALREADY_INITIALIZED for an existing valid
store; a foreign/nonconforming file is rejected and never overwritten. `append` never
initializes implicitly; caller batch order never affects committed bytes (canonical kind
rank plus predecessor/reopen topological order, record-id tie-break; dependency cycles fail
LINEAGE_CYCLE); one bad record rolls back the whole batch. `load_and_verify` opens
read-only and never alters the file bytes. The logical snapshot schema version is the string
`1.0.0`; the SQLite registry schema version is the integer `1`.

## 16. WP170 Separation

WP170 (`experiment_os.py` / `experiment_registry.py`, application id 1464877424) is
UNCHANGED. The Alpha Factory adds no kinds to the WP170 registry, reuses no WP170
application id, and does not reuse or reinterpret `AlphaHypothesis`, `ExperimentFamily`, or
`PreregisteredExperiment`. `HypothesisFamily` is NOT `ExperimentFamily`. No experiment,
preregistration, OOS, or qualification construction exists here.

## 17. Zero Direct Hermes Runtime

The Alpha Factory package works with zero Hermes installation and never imports
`src/research_runtime/hermes_controlled_runtime/` or any Hermes/provider module. It has no
network surface.

## 18. Wallet Intelligence First-Class Capability

Wallet intelligence is a required first-class capability. The immediate software successor
after WP175N MERGE is S10-WALLET-01, then S10-HERMES-CTX-01. WP175N does not authorize or
start WALLET-01. Wallet intelligence never creates direct strategy, paper/live, or Gate-C
authority, automatic copy trading/sizing, deanonymization, "insider probability", a parallel
Alpha memory, a parallel economics engine, or a parallel paper engine.

## 19. Decomposed Current Roadmap

GENUINE H1 PASS -> S10-ALPHA-01 -> S10-WALLET-01 -> S10-HERMES-CTX-01 -> S10-WALLET-02 ->
S10-ALPHA-02 -> S10-GATE-AF1. After GATE-AF1, non-wallet hypotheses flow GATE-AF1 ->
S10-QUAL-01 -> S10-GATE-QUAL-01 -> WP170 -> WP172 -> WP173 -> the existing restricted-live
path; wallet-dependent hypotheses flow GATE-AF1 -> S10-WALLET-03 -> S10-WALLET-04 ->
S10-GATE-WALLET-01 -> a wallet-specific evidence lane inside S10-QUAL-01 -> S10-GATE-QUAL-01
-> the SAME WP170/WP172/WP173 path. S10-GATE-WALLET-01 IS CONDITIONAL: it is not a global
qualification blocker. Later roadmap owners: S10-HERMES-CTX-01 (read-only project-aware
context broker consuming verified Alpha memory; no repository shell/admin or trading
authority), S10-ALPHA-02 (market-universe triage, freshness, material-change detection,
automatic reopen decisions, prioritization, exploration/exploitation, skipped-market
allocation), S10-ALPHA-03 (recurring research campaigns, scheduler, budgets/rates, explicit
provider/backend fallback/escalation), S10-ALPHA-04 (downstream outcome learning), and
S10-HERMES-SI-01 / S10-GATE-HSI-01 (research-layer self-improvement). S10-HERMES-SI-01's
unlock condition is sufficient accepted AF1 benchmark material and it may run in parallel
with wallet proof, qualification, WP170, WP172, WP173, and later live progression; it gains
no deterministic/economic authority. The old monolithic WP180/WP181 Hermes/Alpha sequencing
is SUPERSEDED. WP176 remains decomposed into WP176A-E for mature deterministic live
capability.

## 20. Qualification Boundary

The Alpha Factory does not qualify strategies. Evidence sufficiency and deterministic
qualification are later owned by S10-QUAL-01 and the WP170 experiment OS.

## 21. Gate-C Boundary

Gate C is NOT AUTHORIZED. It and live capital remain separately human-authorized. WP175N
creates no Gate-C authority, capital, or orders.

## 22. Immediate Successor After Merge

The immediate software successor after WP175N MERGE is S10-WALLET-01. WP175N does not start
it.

## 23. Next Successor

After S10-WALLET-01, the next successor is S10-HERMES-CTX-01, the read-only project-aware
context broker that consumes verified Alpha memory.

## 24. ALPHA-02 / ALPHA-03 / ALPHA-04 Ownership

Universe triage, freshness, material-change detection, automatic reopen, and prioritization
are S10-ALPHA-02. Scheduler, budgets/rates, and campaign autonomy are S10-ALPHA-03.
Downstream outcome learning is S10-ALPHA-04. None of these are in WP175N.

## 25. HERMES-SI Benchmark-Parallel Rule

S10-HERMES-SI-01 unlocks on sufficient accepted AF1 benchmark material, not on full live
completion, and may run in parallel with wallet proof, qualification, and later live
progression while gaining no deterministic/economic authority.

## 26. Explicit Non-Authority Statement

WP175N / S10-ALPHA-01 grants no provider/model/Hermes runtime, Firecrawl, OAuth, wallet
network, market network, scheduler/background, prioritization, qualification, strategy,
paper, execution, live, credential, signing, order, or Gate-C authority. Provider/model
calls 0, Firecrawl 0, OAuth 0, Hermes runtime calls 0, H1 invocations 0, wallet network 0,
market network 0, capital at risk USD 0, orders 0. Merge authorized: NO.
