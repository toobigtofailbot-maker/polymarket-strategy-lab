# Blind-First Hermes Context Broker And Reconciliation Contract

Status: S10-HERMES-CTX-01 implementation complete on branch; merge not authorized.
Runtime activation: NO. Real Hermes/provider/Firecrawl calls authorized by this package: 0.

## State and blind barrier

The immutable sequence is `SCOPE_FROZEN -> BLIND_RESEARCH -> BLIND_FROZEN ->
REVEAL_ELIGIBILITY -> CONTEXT_REVEALED -> RECONCILIATION -> EVIDENCE_VERIFY ->
REVISION_REQUIRED | TERMINAL_FAILED | TERMINAL_ACCEPTED`. The only return edge is an
explicit caller-supplied revision from `REVISION_REQUIRED` to `RECONCILIATION`.
Terminal states do not transition. Model prose never selects a transition.

`BLIND_FROZEN` is reached only after the content-addressed blind artifact is durably
appended to the caller-rooted `ContextArtifactStore`. The blind request accepts no Alpha
registry, reveal set, project summary, prior campaign, Hermes memory, or session-history
input. Store writes are exclusive-create and idempotent only for identical canonical
bytes; there is no update, delete, or `latest` API.

## Context output contract

Ordinary H1 keeps its existing required field set. Context mode separately requires
`context_claims`; its schema and validator derive from the same constants and closed
vocabularies. A validated claim has a repo-derived id, bounded statement/kind/subjects/
direction/source indices/assumptions/uncertainty, and may cite only validated source
references. The context contract digest binds the context request identity, prompt,
blind artifact, reconciliation revision, verification, and terminal provenance.

## Exact reveal and shared PIT semantics

The broker runs only from a persisted matching `BLIND_FROZEN` state. Inputs identify the
exact verified Alpha Factory registry path, explicit root record ids, shared
`ResearchProvenanceManifest` objects, and decisive `ObservabilityEvidence`. It calls the
existing read-only registry verifier and shared `evaluate_replay_admissibility`; only
`ADMISSIBLE` plus `EXACT`/`FAITHFUL` replay fidelity passes. Registry entry/payload hashes,
manifest ids, admissibility basis, retained DQ flags, gap summaries, and exact dependencies
are part of reveal identity. `INDETERMINATE`, post-cutoff, scope mismatch, missing evidence,
or cross-campaign binding fails closed. Alpha text is deterministically framed as untrusted
data and delimiter-neutralized; it cannot change policy, tools, authority, retries, state,
or acceptance.

## Evidence, contradiction, and quality

Precedence is `RAW_DIRECT > DETERMINISTIC_DERIVED > ALPHA_SUMMARY > HERMES_INFERENCE`.
Every material claim must match campaign subjects and exact scope, cite PIT-admissible
evidence in the observed blind-web or exact reveal set, state assumptions for inference/
hypothesis claims, retain uncertainty, and pass contradiction review. Blind-web membership
uses the existing exact `SanitizedSourceReference.url_digest`: SHA-256 over the exact
validated HTTPS URL UTF-8 bytes, with no URL-equivalence normalization. Citation presence
alone is not support. Stronger contrary evidence cannot be overridden by a summary.

Structural validity and substantive research quality are separate gates. Schema-valid but
unsupported claims produce `REVISION_REQUIRED` or `FAIL`, never acceptance. The validated
falsification checks are retained and consumed. A revision is a new immutable artifact
linked to its prior reconciliation; it never mutates blind or prior revision evidence.

## Hermes memory and telemetry non-authority

Hermes `state.db`, persistent memory, USER/SOUL/project context, session history, web text,
Alpha prose, and model summaries are not canonical project memory. The managed profile
disables memory/user profile/provider, compression, auxiliary retries/title/background
review, project skill discovery/external skills, lazy installs, and private URLs. The
research-home preflight rejects `config.yaml`, non-empty `plugins/` or `skills/`, and
instruction-bearing profile files by name without reading secret values.

The session projection opens only `<research_home>/state.db` read-only and selects the
exact usage-file session id. It exposes only a session-id digest, ordered tool names,
argument/result hashes, exact HTTPS URL digests, bounded content hashes, and auxiliary task
names. Unexpected tools fail context verification.

| Fact | Status |
|---|---|
| configured backend | FIRECRAWL (policy) |
| local pre-dispatch URL safety | ENFORCED_PINNED_V0_21_3 |
| post-result final-URL safety | ENFORCED_PINNED_V0_21_3 |
| actual backend attestation | NOT_DIRECTLY_ATTESTED |
| remote Firecrawl HTTP/redirect telemetry | UNAVAILABLE |
| remote private-target proof | UNKNOWN |
| same-provider recovery | UNKNOWN_POSSIBLE unless directly evidenced |
| exact physical provider attempt count | UNKNOWN where recovery cannot be ruled out |

Configured behavior and usage `api_call_count` never upgrade unavailable remote telemetry.
S10-HERMES-CTX-01 authorizes no real run, H1 #5, credentials, paid fallback, merge,
WALLET-02, ALPHA-02, HERMES-SI, qualification, WP170, paper/live, Gate C, signing,
capital, or order action. The separately gated successor is S10-WALLET-02.
