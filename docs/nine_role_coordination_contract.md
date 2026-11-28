# B4 Nine-Role Native Receipt Coordination Contract (S10-CAP-NINE-ROLE-COORD-01)

Status: engineering contract for one finite, local, offline coordination diagnostic
(`OFFLINE_ENGINEERING_COORDINATION_DIAGNOSTIC`). B4 is a read-side consumer of already sealed native receipts. It is
not a dispatcher, scheduler, agent framework, strategy, paper, execution or live path. It does not claim nine
functional agents, integration completion, autonomous recovery, external attestation or supported economics (all
`claims` are `false` in every receipt).

Terms: B1-A is the merged source/forecast spine (A1 scout, A2 research), W01 the prior pinned Hermes delegated-specialist
witness (A3 forecaster, A4 falsifier child pair), B2 the merged relations + public-wallet spine (A5, A6), B3 the merged
execution-economics diagnostic (A7). A8 (learning) and A9 (improvement) are future roles; W09-W12 are the separately
gated successor packages. "Native" means an existing merged producer or verifier, unmodified by B4; "sealed" means a
write-once scratch whose receipt that native verifier accepts.

## Chain (native producers only, none modified)

1. A caller names at most two sealed native cases: a B2 scratch (`run_relation_wallet_spine`) or a B3 scratch
   (`run_execution_economics_spine`), each with its declared `b2research:` / `b3research:` receipt id and one route.
2. B4 freezes byte-identical copies, writes a write-once plan, then for each case calls the unmodified top-level
   native `verify` once (B3's verify re-verifies its nested B2; B2's verify re-verifies B1-A, REL-01 and Oracle3).
3. The declared receipt id must equal the id the native verifier returns (`RECEIPT_ID_MISMATCH` otherwise). Nested
   spine, W01, grounding, universe, target, decision-time and (for B3) B2-lineage identities must agree
   (`NESTED_*_MISMATCH`, `NESTED_B3_UNEXPECTED`, `CASE_RECEIPT_ID_MISMATCH`).
4. One typed pure consumer per eligible role reads the verified native fields by exact key and emits a closed
   projection, its canonical digest and a consumer id. A8/A9 have no consumer.
5. One write-once `b4receipt:sha256:` receipt; `verify` recomputes everything from the frozen copies only.

B4 never runs W01, B1-A, B2 or B3 producers, never starts a Hermes child, model or provider call, and never opens a
socket. The A3/A4 rows are the prior W01 host witness as recorded by its sealed receipt (`new_dispatches: 0`,
`provider_invocations_recorded` copied verbatim, unknown cost stays `UNKNOWN`, never zero).

## Manifest (`side26-nine-role-campaign-v1`, strict JSON, exact keys)

`{"schema_id", "cases": [{"source_kind": "B2"|"B3", "receipt_id", "route"}]}` with 1-2 cases. Duplicate JSON keys,
NaN/Infinity, non-UTF-8, more than 1 MiB and secret-shaped text refuse. Failure precedence: schema -> unknown field ->
missing field -> type -> value -> receipt-id syntax -> duplicate `(receipt_id, route)` (`MANIFEST_*` codes). The
same receipt id under two distinct routes is two declared cases. Case slots are `case-01`, `case-02`; no caller path,
clock, role name or configuration enters the manifest.

## Routing (fixed nine slots per case; 9 planned slots per case, 18 for two)

| Route | Requested roles |
|---|---|
| `SOURCE_REVIEW` | A1, A2 |
| `FORECAST_REVIEW` | A1-A4 |
| `RELATION_REVIEW` | A1-A5, A7 |
| `WALLET_REVIEW` | A1-A4, A6 |
| `FULL_SHARED_CASE` | A1-A7 |

Prerequisites: A2 <- A1; A3 <- A1, A2; A4 <- A1-A3 (atomic W01 pair); A5 and A6 each <- A1-A4, independently of each
other; A7 <- A1-A5. Decision order for each slot (first match wins): A8 `W09_PENDING` / A9 `W10_PENDING`; not on the
route `NOT_REQUESTED`; case not verified `CASE_NOT_VERIFIED`; A7 over a B2 case `B3_NOT_SUPPLIED`;
`PREREQUISITE_NOT_CONSUMED:<role>`; A7 with A5 native status other than `ADMITTED` `A5_NATIVE_NOT_ADMITTED`.
A native A6 refusal does not block A7. The A3/A4 pair is atomic: any structural pair defect refuses both halves
(`W01_PAIR_*`) and every dependent is skipped; a missing second half is never reported as pair success. If A4 alone is
interrupted or fails, A3 stays delivered as recorded and A5-A7 are skipped `PREREQUISITE_NOT_CONSUMED:A4`.

## Delivery vs native disposition

Delivery states are closed: `COMPLETED_CONSUMED`, `SKIPPED`, `REFUSED`, `FAILED`, `QUARANTINED`. Case verify states:
`VERIFIED`, `REFUSED`, `FAILED`, `QUARANTINED`. A genuinely consumed native admission, refusal, insufficiency or
partial result is `COMPLETED_CONSUMED` with its `native_status` carried separately (for example A6
`REFUSED` with `native_reason` `NATIVE_REFUSED:PROFILE_REFERENCE_INVALID`, A7 `PARTIAL`). A native refusal is never
promoted to positive evidence. A consumer that cannot read the verified shape refuses
(`NATIVE_FIELD_SHAPE_INVALID`, `NATIVE_STATUS_INVALID`, `W01_PAIR_*`).

## Role projections (closed; no raw child summaries or large raw records)

- **A1_SCOUT** (`spine core.a1_scout`): native status/reason, target market/event/candidate/catalog, target digest,
  grounding receipt, universe snapshot, `as_of`, denominators.
- **A2_RESEARCH** (`spine core.a2_research`): source allowlist, upstream exclusions, raw-evidence and admitted-label
  reference ids, denominators, native-vs-upstream, Metaculus counts, SDK mock/real request counts, A1 grounding id.
- **A3_FORECASTER / A4_FALSIFIER** (`w01 core.witness_body.children[0|1]`): task index, child role, session, parent
  session, subagent and partner subagent ids, effective tools, recorded api calls/tokens/cost (+ `cost_status`),
  summary digest only, witness id, episode id, W01 receipt id, recorded provider invocations, `new_dispatches: 0`.
  The B1-A spine summary of the children must equal the witnessed children (`W01_PAIR_SUMMARY_MISMATCH`).
- **A5_RELATIONS** (`b2 core.a5_relations`): REL and parity receipt/code ids, decision time, fee policy, upstream,
  denominators, selected models (relation, role, reason, disposition, Oracle3 verdict), rejected, A7 pointer
  (`conditional_only`, never tradable or executable edge).
- **A6_WALLET** (`b2 core.a6_wallet`): cohort snapshot, wallet as-of, ledger entries, context counts, profile id and
  sample strength, assessment id, event-reason counts, delay statuses, native authority; `economics_claimed: false`.
- **A7_EXECUTION_ECONOMICS** (`b3 core.a7_role`): B3/B2 receipt ids, selected model/basket/atomicity, venue snapshot,
  execution-feasibility assessment, point status, fee exactness, replay status (the B3 R007 split stays
  `NOT_SUPPLIED`; no replay is manufactured), reasons, denominators; `economics_supported: false`,
  `wallet_economics: NOT_CLAIMED`.
- **A8 / A9**: handoff fields only (campaign, case, task, version, evidence and dependency references, `authorizes:
  NOTHING`).

Identities are domain-tagged SHA-256 over native canonical bytes with prefixes `b4campaign`, `b4case`, `b4task`,
`b4attempt`, `b4consumer`, `b4event`, `b4plan`, `b4receipt` (`:sha256:`). No timestamp, randomness or path enters
an identity; `usage.elapsed` is the literal `UNKNOWN_NOT_OBSERVED`. The code identity hashes the raw B4 source bytes, so
an LF and a CRLF checkout give different B4 receipt ids (as for the native B2/B3 code identities); the authoritative
identity is the clean LF checkout.

## Operator (`tools/alpha/run_nine_role_coordination.py`)

`run --manifest ABS --evidence-root ABS --scratch-dir ABS`, `resume --scratch-dir ABS`, `verify --scratch-dir ABS`.
Exit 0 `RUN_COMPLETE` / `RESUMED_COMPLETE` / `SEALED_VERIFIED` / `VERIFIED`; 1 `STOPPED` / `TAMPER_DETECTED`;
2 usage error. Output never echoes caller paths, ids, input text or tracebacks.

Inputs must be absolute, outside the checkout, disjoint from the scratch and from each other; secret-named parts
refuse. The evidence root holds exactly `case-01[/case-02]`; each case holds exactly its native top level (B2:
`inputs/`, `parity/`, `receipt.json`; B3: `inputs/`, `receipt.json`). Order on `run`: paths -> write-once scratch
-> exact layout -> lstat walk and caps (native B3 walk per case: 20,000 files / 3 GiB; aggregate 40,000 files /
6 GiB) -> B3 replay Parquet footer bounds -> only then byte hashes. Links, junctions, hardlinks, sidecars and secret
directories refuse (`INPUT_TREE_UNSAFE`) before any hash or native verifier. Every socket entry point is blocked. A
socket attempt during a case verify is recorded durably as `CASE_VERIFY_QUARANTINED` with its own reason
`NETWORK_ATTEMPT_BLOCKED` (never retried, never an ordinary refusal or a clean-interruption record) and the run stops
unsealed; any attempt before the seal, including the seal's own native re-verify on resume, stops without a receipt.
Caller files are re-inventoried after the run and must be unchanged. The inventory covers regular files: an empty
directory carries no evidence bytes, and each case interior beyond its top level is the native verifier's to judge.

Scratch layout: `inputs/{case-NN/, manifest.json}`, `plan.json`, `journal/NNNNNN.json`, then `receipt.json` after
the seal; `active.lock` only while a writer runs. Nothing else is permitted (`SCRATCH_LAYOUT_INVALID`).

## Journal, interruption and recovery

- Each event is `{event_id, event: {schema_id, seq, prev, type, payload}}`, hash-chained from the plan id, written as
  a new exclusive (`O_EXCL`), fsynced file in canonical bytes. An event is written only if strict replay of the
  journal plus that event is legal (`JOURNAL_ORDER_INVALID` otherwise); the event family must match the next step.
- Intent before call: `CASE_VERIFY_STARTED` is durable before the native verifier is entered and `ROLE_STARTED`
  before the consumer runs. At most one logical attempt exists per subject (attempt ids come from the plan).
- One writer: `active.lock` is created exclusively and never stolen; a competing `run`/`resume` refuses
  `WRITER_LOCK_PRESENT`, and `verify` refuses `ACTIVE_WRITER_PRESENT`. A clean interruption unwinds the lock.
- `resume` on an unsealed scratch re-validates the exact plan and journal bytes, records an in-flight subject as
  `QUARANTINED` (`INTERRUPTED_IN_FLIGHT`, never retried), continues with the next subject and case, and seals. A
  completed earlier case is cold re-read only to recompute its projections for the seal (validation, not a new
  logical attempt). A terminal journal with an interrupted seal is sealed without any new event.
- `resume` on a sealed scratch only verifies (`SEALED_VERIFIED`) and writes nothing.
- A torn, empty, gapped, reordered or alien journal file, or a changed plan, refuses without writing
  (`JOURNAL_EVENT_INVALID`, `JOURNAL_SEQUENCE_INVALID`, `JOURNAL_CHAIN_BROKEN`, `JOURNAL_ORDER_INVALID`,
  `SCRATCH_LAYOUT_INVALID`, `PLAN_MISMATCH`).
- Hard-kill recovery (a stale lock after process death, a torn final write, a torn receipt) is detected and refused,
  never repaired automatically; operator recovery is deferred (W11/W12, deferred log). A lock left by a failed lock
  write is likewise refused, never removed.

## Receipt and cold verify

`{schema_id: b4-nine-role-receipt-v1, receipt_id, core}`. The core carries the campaign, plan and head-event ids,
the code identity, per-case verify state, lineage, tasks (status, reason, native status, source member, projection,
digest, dependencies, consumer id), totals (planned slots, completed consumed, skipped, refused, failed, quarantined,
attempted, per-reason and per-native-status counts), the inventory digests, the prior W01 host witness, `usage`,
`new_activity` (all zero), `authority`, `claims` (all false), the A8/A9 handoffs, the two capability concept rows and
the deferrals.

The plan binds the exact frozen manifest bytes (their SHA-256) as well as their parse, and the receipt file must be its
exact serialization (`sort_keys`, indent 1, UTF-8).

`verify` is read-only: exact layout, bounded strict reads, exact plan and journal, then a whole-scratch digest; full
recompute through the same native verifiers and consumers; exact canonical core bytes (no bool/int/float or
null/absent conflation); the id from the recomputed core; the whole-scratch digest again. Any difference is
`TAMPER_DETECTED` with closed failures (`CORE_MISMATCH`, `RECEIPT_ID_MISMATCH`, `RECEIPT_SHAPE_INVALID`,
`RECEIPT_SCHEMA_INVALID`, `RECEIPT_BYTES_NONCANONICAL`, `RECOMPUTE_REFUSED:<code>`, `SCRATCH_CHANGED_DURING_VERIFY`).
A missing, unreadable or non-JSON receipt, a wrong layout or a present lock is `STOPPED` instead (`RECEIPT_UNREADABLE`,
`SCRATCH_LAYOUT_INVALID`, `ACTIVE_WRITER_PRESENT`). A rehashed forgery of a
native receipt is refused by the native verifier itself, never accepted on a matching hash.

## Capability rows (static historical concept references, not adoption)

- **R3-21** `pmxt-dev/pmxt-mcp` @ `b47230894e7d0b2a97fc571ce6fea32cf566a9a8` (createServer; generated tool catalog
  including write routes) -> native concept `CLOSED_ROUTE_TABLE_AND_DENIED_MUTATION_NO_TOOL_CATALOG`.
- **R3-29** `valory-xyz/trader` @ `b5b0281adecfeca56e0fb5bb7aec7c35c96d24b6` (`RequestType` enum in
  `polymarket_client/request_types.py`) -> native concept `CLOSED_TASK_TERMINAL_STATES_FAIL_ABORT_QUARANTINE`.

Both stay `CONCEPT_ONLY` / `PARTIAL_CONCEPT_UNACCEPTED`: not invoked, not value-verified, owner disposition
`PENDING`; no upstream code is copied or imported. The other 34 capability IDs are unchanged.

## Successor boundary

A8 (W09) and A9 (W10) real work, any new Hermes/W01 dispatch, hard-kill recovery (W11/W12), the B3 R007
single-environment witness and every paper, execution or live path need their own separately gated packages.
