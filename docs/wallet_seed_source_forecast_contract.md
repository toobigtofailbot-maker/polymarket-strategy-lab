# S10-WALLET-SEED-02 source and forecast contract

The SEED-02 sections retain the merged synthetic scientific baseline. The ACT-01
section below is the current non-study readiness extension; it supersedes the
baseline CLI-only statement for that separately gated capability only.

Status: LOCAL_IMPLEMENTATION / SYNTHETIC_ONLY / STUDY_NOT_ACTIVATED.
The nine-path M/Risk3/RUNTIME package implements one foreground tool,
`tools/polymarket/wallet_seed.py`, over unchanged WALLET-01/02/03. It implements
strict original-response decoding, canonical native record append, immutable
retention and input bindings, a source-bound prospective seal interface, native
bid/ask admission and deterministic synthetic paired Brier calculations.
It implements no strategy, qualification, paper, execution, scheduler or trade.

The reviewed prompt/spec are under `docs/wp_specs/S10-WALLET-SEED-02/` and retain
their reviewed raw bytes. They are normative. The merged METHOD remains
`wallet-comparison-method@1.0.0`, digest
`walletmethod:sha256:e08fe248dff75bd1e67503426801a6b6940d42ad4acb2bded89dd1650cba1656`.
No actual enrolled study, forecast, label, matched group or empirical advantage
is produced by this implementation. Real enrolled count is NOT_ESTABLISHED;
`synthetic_counts` always denotes simulation, never a research denominator.

## Public APIs and authority

All domain APIs are keyword-only: validate_source_route(route_evidence),
decode_fill(raw_log, receipt, block, finality, instrument),
build_study_seal(method, readiness, cohort, profile, instrument, clocks, budget,
human_approval), capture_seed_evidence(seal, phase, ledger_path, output_dir,
transport=None), materialize_forecast_pair(seal, decision_bundle, ledger_path),
attach_final_label(pair, label_bundle, as_of), and main(argv=None).
The CLI only prints a closed PRODUCTION_DISABLED status and performs no acquisition.

`SourceFrame` retains request identity, original bytes, completion/start UTC clocks,
code SHA and a non-caller-selectable SYNTHETIC origin. `SyntheticTransport` is an
explicit fixture input accepted by exact type; it cannot certify real source origin.
`SyntheticDecisionClock` is an explicit fixture clock. A scalar claimed commit time
produces UNMATCHED, rather than proving an actual prospective forecast commit.
Private result commitments distinguish tool-produced pairs from a JSON mapping or
a caller-rehashed result; they are integrity checks, not credentials or approvals.

No trusted real operator approval adapter is introduced by this WP. Therefore
production capture rejects before transport even when supplied a plausible detached
approval record. Network=true in the authority mirror describes dormant bounded
capability, not permission to invoke it. The RPC primitive admits fixed-host public
read-only methods, rejects mutation methods, redirects and proxies, caps responses
and never retries. Existing `public_get` supplies capped raw-byte venue GET support.
The successor must independently establish a real approval/origin path before any
production wiring or source acquisition. This is a declared activation boundary,
not a false assertion that a checksum proves Karl approved a request.

Reference every Centralized Boundary Group in `docs/ai/codex/PROTECTED_PATHS.md`:
credentials/secrets, authenticated clients, wallet/account behavior, order placement/cancel,
execution gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment,
dependency/lock changes, external code copying, generated artifacts. No protected
runtime path, dependency, config or copied source changes. Generated synthetic evidence
uses temporary test directories; no production source, real wallet ledger or secret is read.

## Verified route facts and proof limits

Chain is Polygon 137. Standard direct, nonproxy exchange:
`0xe111180000d2663c0091e4f400237545b87b996b`; complete runtime SHA256:
`3e2ba43e59d19191f0d208e39b1ec16f920bdda30ebfa062330ea9fe8d8363f5`.
CTF: `0x4d97dcd97ec945f40cf65f87097ace5ea0476045`; runtime SHA256:
`984de1496ba73cea948f777d72201b9418041dce65551bff0b4d62101d2acd62`.
Collateral immutable: `0x2791bca1f2de4661ed88a30c99a7a9449aa84174`.
Fresh code proof binds BOTH entire raw code hashes to the same finalized-block
number. No metadata stripping/opcode masking is accepted during revalidation.

[Official deployments](https://docs.polymarket.com/resources/contracts) and retained
[exchange Sourcify v2 record](https://sourcify.dev/server/v2/contract/137/0xE111180000d2663C0091e4f400237545B87B996B?fields=all)
supported draft source binding. The latter identifies matchId 27675274, deployment
transaction `0xd313453c195344b3eea2d91343fb840e51130ba5562fb9c9eda83fd0f82c6c97`,
block 84902353/index113, compiler 0.8.34+commit.80d5c536. Its result is match,
not exact_match. Local closure reproduced 21,037 runtime bytes using 26 explicit
immutable substitutions plus one CBOR metadata substitution. CTF reproduced 15,007
bytes with one metadata substitution. This is not fresh current RPC proof.

Fixed official upstream `ccc0596074f4dfd62c944fbca4de252893b82b4b` interface/Events/Structs
match verified source bytes; Trading differs in comments. Cantina audit base
`dafcfc0c47cf7c326c43660931ee91f71bdc71d9` and Quantstamp base
`a9d2397422a66b5c370b25bb666177a92e3dc47a` have the same event layout/Side enum;
their complete settlement trees differ. The March25 Quantstamp fix review and
named fixes are evidence references, not a blanket deployed-security PASS.
No external Solidity source or bytecode fixture is copied into this WP.

OrderFilled topic is
`0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee`.
Four topics bind order hash, maker and taker; seven ABI words bind side/token,
making/taking amounts, fee, builder and metadata. BUY0/SELL1 belongs to maker,
including the taker's aggregate order with exchange as counterparty. There is
no inverse attribution to the taker field; mint BUY/BUY and merge SELL/SELL retain
each owner. OrdersMatched/Transfers are never promoted to another fill.
Original successful receipt inclusion, native tx/log identity, canonical block
hash/number, removed=false and observed finality <=T0 are required.

## Intake, coverage and retention

RPC parsing is strict: matching request/response IDs, no duplicate keys, floats,
nonfinite constants, error/null reply, excessive nesting or node count. Large hex
strings are permitted only within the 2MiB response cap, so actual pinned runtime
lengths can be verified. Ordinary venue JSON uses the existing bounded decoder.
CTF pure-view calldata and fixed-block results prove two slots, collection index
sets1/2 and the two exact positions using the verified collateral. Unsupported
condition/token/version/identity never acquires strong evidence via a caller flag.

Side19's 2026-10-14 bounded source-policy amendment treats the pinned authorized
RPC as conforming to Ethereum's exhaustive eth_getLogs contract. Completeness is
SOURCE_CONTRACT_COMPLETE_CONDITIONAL, with epistemics
RPC_CONTRACT_CONDITIONAL_NOT_PROVIDER_ATTESTED. Receipts and immutable pair
reports explicitly retain provider_attestation=NOT_ESTABLISHED. This assumption
is not cryptographic absence, physical provider verification or real capture origin.
A consistently silent omission of an entire transaction cannot be detected by this
API path; tests do not establish that PublicNode's serving backend is exhaustive.

The range begins at the first canonical block at/after T0-3600s, proved by its
adjacent predecessor timestamp being earlier; both original numeric headers bind
the boundary. Exclusive deterministic inclusive chunks contain at most 128 blocks
and exactly cover through finalized frontier F, observed by T0. F.timestamp<T0
is valid. The unfinalized suffix is not an admissible action set. No source clock
is replaced by block time or repaired after T0. Numeric canonical RPC/header
semantics are part of the disclosed RPC trust boundary; no full ancestry traversal
is claimed. F preceding the lookback boundary remains conservatively UNKNOWN.

Each filter contains the exact exchange/topic and every sealed maker, using the
same scalar/OR-list form throughout, without token narrowing. Strict original
replies must cover the exact ranges once. Every returned matching transaction
requires its original successful receipt and numeric canonical event header;
the returned block's transaction-hash list must place that transaction at its
original receipt index. Unrelated transaction hashes need no receipt traversal;
receipt logs must exactly equal returned matching rows within those transactions.
This detects returned-row/receipt omissions, conflicts and duplicates, not wholly
omitted transactions. Every proof raw/manifest must already be registered at the
frozen decision head, and native profile event IDs must match the decoded set.

Any range/filter drift, missing/overlapping/gapped chunk, failed/partial reply,
reorg/proof conflict, late availability/finality, timeout, oversize, record-ceiling
ambiguity or budget exhaustion prevents a paired wallet forecast. Exactly 256
rows is rejected conservatively as possible cap ambiguity. Conditional complete
empty ranges plus all anchors/provenance may support NO_SIGNAL; an isolated empty
array cannot. Every capture request, including retained search probes, is counted
against the same 128-call/8MiB/120-second/5-second-request ceilings. No hidden
batching, fallback traversal, retry, new dependency or service is introduced.

Synthetic realistic fixtures cover 1,771 finalized blocks at two seconds/block,
F sixty seconds before T0, fourteen range replies and a retained binary anchor
search. Positive empty, target/complement BUY, native profile/window and paired
states plus negative cases are reported with exact counted requests in external
traces. They prove local feasibility under the assumption, not real provider
behavior. Actual host reachability, operational limits/all-or-error behavior,
finalized support, fresh code hashes and trusted approval/origin lineage remain
separate prospective activation gates. The frozen SEED-01 METHOD is unchanged.

### Historical Side19 feasibility stop (2026-10-14; superseded source policy)

At the structural-stop stage, independent acceptance of reviewed head
`9f6df26e8b44ba646a6a69081f1f2c7f6fe003f4` is WITHHELD. Its passing local
tests do not prove realistic one-hour coverage. The source tool is preserved;
no corrected COMPLETE route or feasible pilot is claimed.

The frozen METHOD admits actions within [T0-3600s,T0] only when their effective
finality and original evidence availability are observed by T0. A finalized
frontier F may precede T0; the unfinalized suffix contributes no admissible action.
Eligible coverage must be exhaustive through F, not pretend that suffix is final
or wait past T0. Event time still selects the native lookback; availability remains
independent. Neither rule, budget nor METHOD digest is amended here.

The former unconditional block/receipt enumeration needed at least 1,771 original
block calls for a two-second chain over [T0-3600s,T0-60s], before any receipts or
other inputs. That exceeds both 128 total calls and the 1,024-header guard. The
existing last-header-at-or-after-T0 condition separately rejects lagging finality.
The external synthetic diagnostic reproduces both; it is not a positive proof.

[Ethereum's API contract](https://ethereum.github.io/execution-apis/api/methods/eth_getLogs/)
specifies all matching logs. The inspected
[Bor GetLogs wrapper](https://github.com/0xPolygon/bor/blob/develop/eth/filters/api.go)
returns underlying logs or errors; that mutable upstream example is not evidence
of the gateway's deployed client/configuration. The
[PublicNode Polygon page](https://polygon.publicnode.com/) identifies the approved
Bor RPC endpoint but supplies no inspected endpoint-specific exhaustiveness,
pagination/truncation/error-limit contract or serving-version binding. This is
an unresolved evidence gap, not a finding that PublicNode actually truncates.

At that stage the reviewed WP required provider-attested exhaustive original range
results or original complete receipt enumeration. A caller completeness flag,
successful short/empty array, general Ethereum specification or synthetic
service response cannot close the missing provider binding. Repeated overlapping
queries cannot rule out consistent omission. Without that binding, sparse range
queries cannot establish COMPLETE; the receipt fallback cannot fit this budget.
No alternative host/API, batching to conceal logical calls, new dependency or
after-T0 repair is authorized. Stop: STRUCTURAL_COVERAGE_PROOF_BLOCKED.
Side19 accepted that stop, then explicitly authorized the conditional RPC source
policy above within the same nine paths. Both stop and original code remain
ancestors; final implementation acceptance still awaits independent review.
SEED02-D004 now tracks the local correction and remaining activation evidence.

Canonical chain events, TRADES-category pages, original observations and CHAIN_ONLY
finality links append using unchanged native builders/ledger. POLYGON_RPC raw
provenance is not relabeled Data-API origin. Raw bytes and manifests are registered
before native profile/book admission; all evaluation proof frames must appear in
the same bounded capture input. Native ledger loading/append semantics remain unchanged.

Exclusive files retain original bytes, exact phase/input binding and study/readiness
digest. Conflicting inputs/replacement seals reject before ledger append. Identical
replays are idempotent. Symbolic links and conflicting existing bytes are rejected;
there is no overwrite, truncation or rollback deletion. Capture receipts cover code,
phase, digest, request parameters/clocks, body hashes/lengths, source refs, consumed
budget and final head. No raw provider body is returned in a result or stdout.

Hard ceilings:128 frames/calls,8MiB total bytes,120seconds,5seconds/request,
2MiB RPC response,65536 book bytes,256 book levels and256 logs/range. The detached
synthetic approval must bind the exact smaller-or-equal limits and phase/hosts/code.
RPC host is polygon-bor-rpc.publicnode.com; GET hosts are clob.polymarket.com/book
and the exact sealed numeric Gamma market. No arbitrary hosts, private/account
routes, authenticated headers, signing/orders, retries, timers, daemon or service.

## Prospective seal, original book and labels

One earlier native readiness cohort/profile window must be truthful <=Tfreeze.
A distinct frozen future native cohort uses the same sole membership/discovery,
window [T0-1h,T0+1us). This resolves native profile as_of constraints without future
dating a readiness profile or creating another study. Original readiness head,
cohort/profile and source references remain bound; evaluation profile is rebuilt at
T0 from the exact decision head. Later head growth cannot substitute for that snapshot.

The closed STUDY payload has exactly the frozen METHOD fields. Its internal
human_approval_record is only a pre-digest intent/request reference. A detached
post-digest receipt binds the complete study digest, METHOD, code, phase, hosts
and budget outside the seal preimage. No circular checksum, success flag or
self-rehash authorizes production. READINESS has its own typed non-study envelope;
it cannot be promoted to DECISION/LABEL approval. Real authorization remains absent.

Tfreeze<=T0-24h; discovery<=freeze; event end is1h..7days afterT0; deadline=end+30days.
One unit, cluster and leakage group; no replacement, ranking, fitting or expansion.
Unknown membership/group/source stays unknown. The tool uses canonical fixed-point
Decimal strings at precision80, never float/exponent/nonfinite input.

Latest target GET /book must be original,<=30s old,0<bid<=ask<1,spread<=0.1,
with exact source/raw/manifest/request/body/clock/head binding. Bid and ask are
two separate unchanged WALLET03 one-witness calls on the same original book/profile;
delay0 and all unknown cost assumptions are retained. Both source_status values
must be OBSERVED. Simultaneous conflicting full book levels/depth are UNKNOWN;
byte-identical duplicates do not add units. No WS/complement/last-trade substitute.

p0=(bid+ask)/2; last admissible observed BUY target votes1, complement votes0;
same-clock opposing votes are UNKNOWN. pW=0.9*p0+0.1*vote; proven no-signal equals
p0 and masked control equals p0. No costs, size or economics enter binary Brier.
The final label uses independent same-rule CTF complementary binary payout and
explicit venue resolution agreement, canonical finality and strictly post-target
availability by deadline. Gamma's native id/conditionId/clobTokenIds/outcomePrices,
negRisk, closed and umaResolutionStatus fields must agree with CTF; the finalized
block itself must be post-target. Mapping, book and label frames bind the sealed
code revision. Unresolved verified sources are PENDING before deadline,
CENSORED after; unknown proof is UNKNOWN, never CENSORED. A valid label scores
the identical immutable source-bound pair; a rehashed caller mapping is rejected.

Precedence is EXCLUDED,UNKNOWN,UNMATCHED,MATCHED,PENDING,CENSORED. Numeric summaries
are absent when unpaired/unknown. Synthetic state counts conserve one simulated
unit while actual enrolled remains NOT_ESTABLISHED. Example p0=0.6 gives0.64 or0.54;
Y1 Brier deltas0.0304/-0.0516 are synthetic arithmetic, not empirical findings.

## Validation and successor

R001-R007 named tests assert decode/identity, original native intake, two-sided
book/profile binding, detached approval/freeze/coverage, math/label/conservation,
disabled transport/replay and recursive output/field coverage. Additional negative
cases cover wrong code/block/chain, hidden fill, duplicate/reorg/missing receipt,
late clock, runtime-size RPC, strict JSON, replacement, forged pair and conflict.
Every SeedResult field is scanned using the existing advisory helper plus the
WP's forbidden forms; raw metadata and false authority/origin flags reject.

Exact-diff readiness/scope, focused/adjacent tests, available surface security and
one authoritative offline Linux full suite precede Side19 acceptance. Full-suite
skips/tool availability and exact commands belong to the external exact-head report.
No hosted CI, PR publication or merge in this local-only step. Evidence mode is
BLOCKED_NOT_READY; Ready for review:NO until independent/release evidence closes.
S10-WALLET-SEED-ACT-01 separately owns the trusted operator approval/origin path,
fresh RPC code/finality, genuine readiness/discovery, actual STUDY seal and one-unit
prospective source/label acquisition. DATA03/ALPHA03/04 and numerical WALLET04 remain
separate. No generated artifacts or real study evidence are committed here.

## S10-WALLET-SEED-ACT-01 non-study readiness extension

Karl authorized offline implementation of Side19's exact reconciled V2 prompt/spec
on 2026-10-14 after native draft readiness. The package remains RUNTIME/Risk3/M,
exactly nine paths; no source, dependency, config or scientific-interface changes.
SEED-02 / PR235 is merged at 1cac654773ea6c1db2e29b53037f2f44528ae33a with accepted
head ed9b25a125081558f0d6716c9a88c70a1d38ca70. Historical fragments are retained.

New keyword-only validate_readiness_request(request) previews one closed flat
request including its digest: kind, request_id, code_sha, method_digest,
not_before, expires_at, output_dir, budget, source_policy_id, digest. Its identity
is walletreadinessrequest:sha256: over the entire canonical object excluding digest.
The frozen V2 policy identity is
walletreadinesspolicy:sha256:1131374f86691e8f599b119f97155a2cda70f4d38fb70b468971a94267d48a2e.
Preview permits a future not_before with a still-future expires_at, validates
the at-most120s window and positive narrowed budgets, and performs no filesystem,
transport, output claim, operator authentication or chain observation. Production
launch must occur inside the actual current UTC window.

capture_readiness(request, output_dir, transport=None) is synthetic-only. None,
callbacks and arbitrary transport objects deny before acquisition; the exact
SyntheticTransport supplies eight original fixture frames only. Existing
SourceFrame, SeedResult, scientific capture, seal, forecast and label admission
remain synthetic-only. No readiness evidence is loaded/promoted into these APIs,
a wallet ledger, discovery cohort/profile or a study.

Default CLI/status remains PRODUCTION_DISABLED. A later private foreground CLI
requires --readiness-request FILE and --approval-record FILE, clean tracked code
at the exact approved SHA, and a human-controlled interactive terminal. The
detached record contains exactly kind=MANUAL_EXTERNAL_APPROVAL_REFERENCE,
request_digest, planned_operator=KARL, external_review_ref, approved_at<=not_before.
The operator first compares it to Karl's actual external exact-digest statement
reviewed by Side19, then confirms both digests and a fresh console challenge.
Flags/environment/redirected stdin, absence, disagreement, future/expired scope,
or a digest-only approval cannot enable production. An in-process permit binds
that request/record, is consumed once, and is never loaded from JSON. Import and
offline/status paths do not call a provider. No actual approval/run is created
by implementation or tests.

This is a manual external trust boundary, not cryptographic human authentication
or protection against hostile same-user Python/PTY control. Outputs always retain
MANUAL_ASSERTION_REQUIRES_EXTERNAL_REVIEW and NOT_MACHINE_ATTESTED. Only the
private fixed-source transport can mint DIRECT_HTTPS_NON_STUDY_PENDING_REVIEW;
ordinary constructor/JSON/rehash cannot establish it. Synthetic seams never
receive direct origin. Side19's independent external review remains necessary.

Fixed source plan: only POST https://polygon-bor-rpc.publicnode.com/; chainId137,
finalized header F, entire EXCHANGE/CTF code at F.number, numeric F cross-check,
empty exchange code at84902352, an empty eth_getLogs filter covering exactly
84902225..84902352 with [TOPIC], and a second numeric F cross-check. Exactly eight
calls, no maker/market/token selection, receipts, wallet discovery, venue GET,
retry, fallback, batch, scheduler or active-period fill/book/label collection.
Finalized age is nonnegative and<=300s at observation and successful completion;
stale/future/noncanonical header or changed code/canonical proof is inconclusive.
Pruned history or nonempty/partial/error/capped response is inconclusive with no
substitute probe. Predeployment code/log results are method-shape diagnostics;
they prove neither historical block canonicality nor provider exhaustiveness,
physical absence, current-period capability or study eligibility.

Ceilings remain128 calls,8388608 total received bytes,120s,5s/request,2097152/body.
Reserve before open, count failed attempts/physical chunks, clamp each request
and socket read to remaining time/bytes, reject redirects/proxies/auth headers,
and stop before interpreting breaches. A read sentinel can exceed the physical
byte budget by at most one; the run reports the breach and is inconclusive.
Stdlib resolver/I/O timeouts cannot guarantee hard wall-clock cancellation;
actual overruns are accounted and prevent further calls. Original RPC decoding
is shared without weakening synthetic-source checks or entire-code parsing.

The canonical approved output must be external or under ignored local_data,
fresh/empty and free of symlink components. Exclusively create run.claim before
any attempt, binding request/approval/SHA. Retain request/record and each original
body, clocks, request, status, hash/size and native raw/PIT/manifest records only
for validated responses. Invalid/partial/nonempty responses remain quarantined.
No ledger append or study artifact is created. Terminal receipt is published last;
retention failure returns measured inconclusive accounting without a completed
receipt. Ctrl-C stops/retains neutral accounting; abrupt kill can leave partial
files and an irrevocably consumed claim. Replay, alternate output, conflict or
replacement never overwrites/deletes evidence or resumes automatically.

ReadinessResult's eighteen public fields are all serialized and recursively
scanned on valid/invalid paths: status, errors, request_digest, receipt_id, origin,
operator_approval, human_identity, observations, accounting, coverage_epistemics,
provider_attestation, enrolled_count, numeric_summary, study_activated,
advisory_only, no_execution_authority, no_strategy_authority,
no_qualification_authority. No raw body/header/upstream exception/path or approval
content enters stdout/results; the controlled terminal displays the approved
scope before confirmation. Real enrolled count is NOT_ESTABLISHED, summary null,
study_activated=false. Provider attestation remains NOT_ESTABLISHED and coverage
RPC_CONTRACT_CONDITIONAL_NOT_PROVIDER_ATTESTED regardless of probe success.

R001-R006 assert request/preview, manual boundary, exact source plan/freshness,
transport budgets, retention/replay and field-covered no-promotion output with
the complete negative matrix. R007 preserves adjacent/native scientific behavior;
R008 exact-diff readiness, R009 stable full suite and R010 security are local gates.
R011 independent acceptance/hosted/posted release evidence remains separately
pending; no publication or hosted CI before Side19 local acceptance.
ACT-OPS-01 separately authorizes an exact one-time non-study operator run.
STUDY-ACT-01 separately owns genuine cohort/profile, approved prospective STUDY,
DECISION and LABEL production capture. No operator/study/trading activation here.
