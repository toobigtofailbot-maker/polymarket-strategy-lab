# S10-WALLET-SEED-02 source and forecast contract

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

The complete-coverage route conservatively enumerates original canonical blocks
and ALL transaction receipts. It checks contiguous numbering/parent hashes,
finalized end hash, exact transaction membership/index and original relevant logs.
getLogs results must equal the relevant receipt logs; an empty/truncated response
cannot hide a fill. If full receipt enumeration is unavailable or exceeds budget,
the result stays UNKNOWN. This minimum implementation does not trust a caller's
provider-completeness boolean. No-signal requires complete original absence proof.

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
