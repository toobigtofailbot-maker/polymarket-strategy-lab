# B3 Shared-PIT A7 Execution Economics Diagnostic Contract (S10-CAP-EXEC-ECONOMICS-01)

Status: engineering contract for one finite, local, offline, SANITIZED_SYNTHETIC diagnostic. It is not an
execution, paper, strategy, qualification, value or provider claim. W06 stays PARTIAL.

## Chain (native producers only, none modified)

1. `run_relation_wallet_spine.verify` cold-verifies the frozen B2 scratch (B1-A, REL-01, Oracle3 parity, WALLET-01/02/03).
2. The B2 core selects exactly one A5 `ADMITTED` model that contains the B2 shared-case target, one A7-pointer basket by
   id, and one target leg by market id + `YES`/`NO` side. Missing or ambiguous selections stop with a closed code.
3. The frozen REL request and the cold-verified SRC-01 grounding markets feed `run_related_market_alpha._venue_snapshots`
   over the retained Gamma/CLOB bytes. The rebuilt snapshot id must equal the B2 leg id and the single REL `BOUND` record.
4. A caller-frozen native `StrategyVersion` and `ExecutionIntent` (cutoff = REL decision clock, BUY, exact venue identity)
   go to `assess_execution_feasibility` at the REL decision clock. Full recomputation and the record round trip are checked.
5. Optional: one local synthetic PMXT-format Parquet -> WP167 `validate_and_describe_pmxt_v2_archive` -> WP168 conversion
   via WP172 `build_market_truth_window` -> `assess_executable_edge` over caller-frozen non-OOS WP170 fixture records ->
   in-memory serialize/deserialize -> WP173 `build_strategy_binding`, which must refuse with `WP172_BINDING_INVALID`.
6. One write-once `b3research:sha256:` receipt; `verify` recomputes everything from the frozen copies only.

## Case (`s10-cap-b3-execution-economics-case-v1`, strict JSON, exact keys)

`schema_id`, `evidence_class` (`SYNTHETIC_TEST_ONLY`), `b2_receipt_id`, `model_id`, `basket_id`, `leg_side`,
`strategy_version` (native mapping), `probe_intent` (native mapping), `replay` (`null` or the object below).

`replay` exact keys: `parquet_sha256`, `known_gap_policy` (`AS_CAPTURED` or `KNOWN_GAPS` only), `context` (native
`BinaryOptionMarketContext` fields), `experiment` (`PreregisteredExperiment`), `evidence` (`RunEvidenceReceipt`),
`cost_model` (`ExecutionCostModel` mapping with id, rebuilt natively and compared canonically; `fee_rate_bps` must be
`null`), `decision_event` (one `ResearchDecisionEvent`). A replay file is supplied if and only if `replay` is non-null.

Binding rules: no caller market id or clock. Evidence must be `FORMATION`/`SELECTION`, OOS ordinal 0, not an
authoritative first look, with every duplicated lineage field equal. The experiment `cost_model_reference` must equal
the cost model id. Record clocks must not be later than the decision clock. The decision event must match the target market,
`token:polymarket:<snapshot token>`, BUY/ENTER, the decision clock, the probe shares and the probe style.

## Operator (`tools/alpha/run_execution_economics_spine.py`)

`run --b2-scratch ABS --case ABS [--replay-file ABS] --scratch-dir ABS` and `verify --scratch-dir ABS`.
Exit 0 `RUN_COMPLETE`/`VERIFIED`; 1 `STOPPED`/`TAMPER_DETECTED`; 2 `USAGE_ERROR`. Inputs must be absolute,
outside the checkout and disjoint from each other. Links, junctions, hardlinks, sidecars and secret directories are
refused. The scratch must also have no secret-named part and no unsafe existing parent. Caps: aggregate 3 GiB / 20,000
files; case 1 MiB; receipt 16 MiB (checked before the receipt is written); Parquet 16 MiB, 4096 rows and 64 MiB of
declared uncompressed bytes. Every refusal carries a closed code and never echoes caller text, paths or tracebacks.
Every socket entry point is blocked.

Closed scratch layout (`SCRATCH_LAYOUT_INVALID` otherwise). The root is exactly `inputs/` before the seal, and exactly
`inputs/` plus a regular `receipt.json` after it. `inputs/` is exactly `b2/` and a regular `case.json`, plus
`replay.parquet` only when the case names a replay (`REPLAY_FILE_CASE_MISMATCH` otherwise). Extra files or directories,
empty ones included, refuse; so do hidden or misnamed entries, sidecars, links, reparse points, hardlinks, a missing
role, and a file where a directory belongs. Nothing is ignored or deleted. The B2 tree's own interior is guarded by the
aggregate walk and by B2's own cold verify.

Order, identical on `run` (caller side and frozen side) and `verify`:
1. The exact layout, then a bounded strict read of the case and, on verify, of the receipt.
2. lstat path, file-count and byte caps.
3. For a supplied replay, the existing pyarrow footer guard (rows, declared uncompressed bytes). It runs before any
   input hash, nested B2 verifier or native WP167 parse; the row data is not loaded.
4. Only then the streamed input hashes. The parsed case bytes must equal the hashed case digest.
5. B2 cold verify and the native B3 consumers.
6. The same layout check and the same inventory, footer and digests again, which must be equal
   (`FROZEN_INPUT_CHANGED`). On verify the receipt bytes must be unchanged (`RECEIPT_CHANGED`).

This is the contracted bounded before/after witness, not a defence against every concurrent external writer. Any
failure returns no receipt id, and verify writes nothing.

## Receipt (`s10-cap-b3-execution-economics-receipt-v1`)

Outer keys exactly `schema_id`, `receipt_id`, `core`. `receipt_id = "b3research:sha256:" + sha256(SG.canonical_bytes(core))`.
Verify needs exact canonical byte equality of the submitted and recomputed core, and the id must be recomputed from
the recomputed core. Failure codes are closed (`CORE_MISMATCH`, `RECEIPT_ID_MISMATCH`, `RECEIPT_SHAPE_INVALID`,
`RECEIPT_SCHEMA_INVALID`, `RECEIPT_FIELDS_INVALID`, `RECOMPUTE_REFUSED:<code>`).

Core keys (closed): `schema_id`, `wp_id`, `evidence_class`, `code_identity` (module + CLI bytes), `input_sha256`
(role -> digest of the sorted relative-path/hash map, so no raw names are echoed), `b2_lineage`, `point_mechanics`,
`replay_diagnostic`, `a7_role`, `capability_ledger`, `authority`, `trace`.

- `b2_lineage`: B2 receipt and code identity, B1-A spine/grounding/universe/as_of/target, the A5 REL/parity receipts with
  native denominators, A6 status and ids, the selected model/basket/leg, its native fields, and the snapshot id.
- `point_mechanics`: native assessment, intent, snapshot and strategy-version ids; status; all nine dimensions; selected
  mechanics as `{value, unit}` (`SHARES`, `USDC`, `USDC_PER_SHARE`, `RATIO`, `RATE`, `SECONDS`); the frozen unknowns
  (`null`); native diagnostic codes.
- `replay_diagnostic`: `NOT_SUPPLIED` (same closed keys, all `null`) or the native projection: source hash, dataset id,
  row denominator, event counts, window lineage, `continuity_complete=false`, WP170 ids/role, cost model, trace and
  assessment ids, status, diagnostics, and the WP173 refusal. No gross/net value, capacity or recommended size.
- `a7_role`: overall `PARTIAL`, or `REFUSED` for native `NOT_FEASIBLE`. It records the point status and the replay status,
  closed reasons, the explicit one-case denominators, `economics_supported=false` and `conditional_only=true`.
- `capability_ledger`: seven rows (R3-09, R3-09-BOOK_GAPS, R3-03-FEES, R3-15, R3-16, R3-17, R3-26) at their exact pins,
  `value_verified=false`, `owner_disposition=PENDING`; the other 29 IDs are unchanged.

## Limitations

Synthetic fixture only. A delayed public snapshot is not a fill. Fee currentness is unverified. Replay continuity is
never complete, and its markout is a retrospective fixture diagnostic. No Synpath call and no Lane B calibration. Real
provider coverage, source rights, OOS qualification, paper eligibility and owner value disposition stay open.
