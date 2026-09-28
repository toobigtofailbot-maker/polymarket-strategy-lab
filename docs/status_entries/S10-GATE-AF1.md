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
- Phase: FINALIZED after AF1 Attempt-04 runtime, independent Side12 blind review and
  deterministic Phase-C finalization; post-runtime publication under the explicit
  Side13/Karl lifecycle-test recovery amendment
- Runtime execution head: `dead42658e8fc9139d82f772e1f2fff67ba07674` (the only head that made real Attempt-04 calls);
  final publication head: later recovery commit(s) descending from it
- Final AF1 outcome: `AF1_PASS`; all ten dimensions PASS; receipt
  `af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2`
- Attempts: AF1 Attempt-01 and Attempt-02 CONSUMED / historical invalidated
  evidence; AF1 Attempt-03 CONSUMED on Phase-A head
  `777b33d5e3eb3ae6814716f45f3dc6a8a673ed16` (TRUE_STOP / `PHASE_B_LOCAL_EVIDENCE_DEFECT`,
  AF1 gate result NONE); AF1 Attempt-04 CONSUMED (`workspace_attempt_id`
  `s10-gate-af1-attempt-04`, envelope SHA-256 `627fcd4cb6c946cabfb86bb2b38ef18b27b8c7fbb73400314b96adeb1d3530b1`); additional AF1 attempt NOT
  AUTHORIZED
- Attempt-04 runtime evidence: exactly 1 public population call (25 markets / 1 book actual,
  built 26, inserted 26, `VALID_WITH_WARNINGS` / `EVENT_TIME_MISSING_ALLOWED`, result SHA-256
  `9adb1b68420afbd15172a92dca57aec2feffc6b39df82753d97ae15b311534cc`, cutoff `2026-09-28T01:54:02.507161Z`);
  3 controller invocations, all `RESEARCH_DRAFT_VALIDATED` (openai-codex / gpt-5.6-sol); retry,
  replacement, fallback and fourth call 0; receipt-reported accepted cost USD 0.0 per case;
  backend telemetry NOT_DIRECTLY_ATTESTED; Firecrawl call count UNKNOWN (no invoice-level cost
  attestation); credentials untouched; H1 #5 NOT AUTHORIZED
- Blind review: bundle SHA-256 `12058c282bd24d332bb767b7a75c201e4f0b9fcbdebdf0f7cb09c07672a8e74f`; Side12 decision SHA-256
  `eba65849219faf65f27849a6b5be0fe1c1cf27e0cc47bb3ada084afb77d99bc3`; labels USEFUL_RESEARCH_OUTPUT x3
- Gate outcome: `AF1_PASS` (research-system gate success only); committed evidence state
  `FINALIZED`, byte-identical to the deterministic local evidence (SHA-256 `130a82b5ace6eb2cedf49b540ddd30df48be05cfcc57bf3173b45b452cce22ab`);
  verify-run / verify-review / verify-final VALID
- AF1_PASS does not prove profitability, expected return, qualification, OOS validity,
  executable edge, paper/live readiness or Gate C; non-wallet S10-QUAL-01 is now separately
  eligible to be drafted/authorized, wallet/ALPHA-03/HERMES-SI paths stay separately gated, and
  none is authorized
- Historical envelope `0f7a2680...`: invalidated; historical `current` workspace
  quarantined and not reusable
- Authority: research-system evidence only; no qualification, strategy, expected
  return, paper, execution, risk override, Gate C, capital, or live authority
- Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED` for the final publication PR
- Post-runtime recovery: the package hard-stopped because Phase-A tests pinned the transient
  placeholder/pre-runtime status; the explicit Side13/Karl amendment authorized only the three
  AF1 lifecycle/status test paths plus the six evidence/status paths (follow-up class G)
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

Final Attempt-04 outcome: Attempt-04 executed on runtime execution head `dead42658e8fc9139d82f772e1f2fff67ba07674` and is
CONSUMED. After the independent Side12 blind review, the frozen deterministic finalizer produced
`AF1_PASS` with all ten dimensions PASS and receipt `af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2`; an independent re-derivation
was byte-identical. No public, Hermes, provider or Firecrawl call occurred after runtime, and no
source, operator, prompt, spec or gate-contract byte changed. No additional AF1 attempt is
authorized.
