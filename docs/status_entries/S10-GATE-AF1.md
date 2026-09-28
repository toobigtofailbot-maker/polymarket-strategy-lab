# S10-GATE-AF1 Status

- WP: `S10-GATE-AF1` — Alpha Factory Research-System Quality, Coverage,
  Reproducibility & Authority Gate
- Base: `1ccf42df0e95586b98c79a0bf912343f9c34df31` (post-S10-HERMES-CTX-03 reconciliation)
- Predecessor: PR #195 / `S10-HERMES-CTX-03`, head `ddc25d189359b6e365edcf08c762cb0552b7170a`, merged at the base
  SHA; exact canonical public Polymarket ids admitted inside `public_market_context` only
- Prior predecessor: PR #194 / `S10-HERMES-CTX-02`, head `f6b337ce1d4581516c3d10d792034f00043a8a74`, merged at
  `15097f70f5f5358879fde73b2b30d26ecdb80402`; exact pinned stock SOUL.md admitted by the shared research-home check
- Runtime dependency: PR #193 / `WP164A`, runtime-certified head
  `1c7de22f31cd093771d6bc0748c440ad5284b105`, merged at
  `70f867bdcd5e97b0dc05d4008c2c023feb461658`; WP164A Attempt-03 CONSUMED /
  `WP164A_PUBLIC_SMOKE_COMPLETE_SUCCESS`; dependency certification COMPLETE
- Historical: drafting base `46bc862018208b30971228ed719c7e9337142b41` (PR #191 /
  `S10-ALPHA-02`); pre-reconciliation handoffs `a1d96fd55f826f9af063ace2c930353cbe41ed73`
  and `af07264a6dc85b9a7bfe6016042011685c957554`
- Governance: RUNTIME, risk 3, capital at risk USD 0
- Scope: exactly 19 paths; dependencies, locks, and workflows unchanged
- Phase: SIDE13 final one-shot post-S10-HERMES-CTX-03 reconciliation and Attempt-04
  Phase-A refreeze (same-capability continuation; not a new roadmap WP); expected stop
  `AF1_ATTEMPT04_RUNTIME_AUTHORIZATION_REQUIRED`
- Attempts: AF1 Attempt-01 and Attempt-02 CONSUMED / historical invalidated
  evidence; AF1 Attempt-03 CONSUMED on Phase-A head
  `777b33d5e3eb3ae6814716f45f3dc6a8a673ed16` (TRUE_STOP / `PHASE_B_LOCAL_EVIDENCE_DEFECT`,
  AF1 gate result NONE); AF1 Attempt-04 UNCONSUMED / NOT AUTHORIZED (future workspace
  `local_data/s10_gate_af1/<PHASE_A_SHA>/attempt-04`, `workspace_attempt_id`
  `s10-gate-af1-attempt-04`)
- Runtime evidence in this package: none; public/product calls 0; Hermes/provider
  calls 0; Firecrawl calls 0; credentials untouched; H1 #5 NOT AUTHORIZED
- Gate outcome: not yet evaluated; the committed evidence state is
  `PHASE_A_IMPLEMENTED_RUNTIME_NOT_AUTHORIZED`
- Historical envelope `0f7a2680...`: invalidated; historical `current` workspace
  quarantined and not reusable
- Authority: research-system evidence only; no qualification, strategy, expected
  return, paper, execution, risk override, Gate C, capital, or live authority
- Evidence mode: `BLOCKED_NOT_READY` until the later runtime and blind-review
  checkpoints complete
- Ready for review: NO at the Phase-A runtime-authorization checkpoint
- Merge authorized: NO

Phase A freezes five content-addressed record contracts, eight deterministic seeded
oracles, ten closed dimensions with a closed terminal override table, a
default-zero-network foreground operator with complete prepare / run-real / verify-run /
build-review-bundle / verify-review / finalize / verify-final paths, and the exact later
activation boundary.

The post-WP164A reconciliation retains the complete 38-field WP164A result, judges
success on actual returned counts with retained batch warnings, rejects
`POPULATION_ALREADY_REGISTERED` in a fresh workspace, binds one canonical
`captured_at_utc` cutoff through the universe and every campaign, keeps the
HISTORICAL_REPLAY Alpha posture, routes a selected market without `question_text` to A2,
passes an absolute `ContextArtifactStore` root, and distinguishes AF1 `retry_limit=0`
from the truthful managed Hermes `api_max_retries=1`. The exact activation envelope has
38 keys. Offline tests drive the real WP164A coordinator, PIT stores, ALPHA-02 allocator,
and HERMES-CTX `run_blind_phase` with fakes only.

Runtime-environment micro-correction: the first Attempt-03 authorization stopped before any
call (Attempt-03 unconsumed) because the operator could not prove the pinned Hermes executable
and research home before the population sentinel. `run-real` now requires explicit
`--hermes-executable` and `--hermes-home` and runs the merged offline version/startup probes and
safe/clean home checks before the sentinel; any failure is `PHASE_B_LOCAL_EVIDENCE_DEFECT` with
zero calls. The 38-key envelope is unchanged.

Post-S10-HERMES-CTX-03 refreeze: Attempt-03 was executed and permanently CONSUMED. Its one
public population succeeded (25 markets / 1 book, built 26, inserted 26, result SHA-256
`fcf5a085aef0954f91812f53231405b9746e583886ea950ca2cd91bc0cf9dc8e`); the C1 controller was
entered, but request construction failed `REQUEST_SECRET_DETECTED` before any Hermes launch
(provider/model calls 0, Firecrawl calls 0, accepted cost USD 0; C2/C3 not attempted; no blind
artifact; no AF1 PASS/FAIL/INCONCLUSIVE receipt). The shared scanner treated the canonical
public event id `event:polymarket:0x<64 lowercase hex>` as secret-like; merged PR #195 repaired
it. AF1 fixtures had used non-live synthetic ids, so AF1 now adds a live-shaped cross-layer
regression (canonical market / event / ~77-digit token refs through `ContextCampaignScope`,
`build_research_run_request` and `run_blind_phase` to the offline fake backend, which fails if
the pre-CTX-03 strict scan returns). The successor Attempt-04 admits only the `attempt-04`
workspace (no automatic increment), performs its own fresh bounded 25/1 population into new
empty stores, and keeps the 38-key envelope, gate criteria, three calls, USD 5 / USD 15,
`retry_limit=0`, no fallback/replacement/fourth call and all authority limits unchanged.
Attempt-03 local evidence is untouched. Attempt-04 workspace, envelope and sentinel are absent;
Attempt-04 public and Hermes/provider calls are 0.
