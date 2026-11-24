# B2 Shared-PIT Relation (A5) + Public-Wallet (A6) Advisory Handoff Contract (S10-CAP-B2-RELATIONS-WALLET-01)

**Status:** offline engineering demonstration (`OFFLINE_ENGINEERING_DEMONSTRATION`). No provider, model,
product network, credential, wallet/account read, order, paper, qualification, strategy or capital authority.
LIVE DISABLED. Conditional relation economics are not executable, a delayed public quote is not a fill, a public
address is not a person, and nothing here is a signal, rank, recommendation, order, size or value claim.

## 1. Purpose

B2 bundles roadmap W04 (rules/relations) and W05 (wallet/public intelligence) as one thin, deterministic consumer
over producers that already exist. It mints no market, rule, relation, wallet, profile, fee or Alpha identity and is
not a canonical store.

| Role | Native producer (unchanged) | B2 function |
|---|---|---|
| A1–A4 lineage | `tools/alpha/run_source_forecast_spine.verify` (B1-A spine + registry copy) | `relation_wallet_spine.b1a_lineage` (read-only ids) |
| Shared PIT case | `source_forecast_spine.load_grounding` + `scout` on the spine's frozen SRC-01 grounding | `bind_target` |
| A5 relations | `tools/alpha/run_related_market_alpha.verify` (REL-01) + `tools/alpha/run_oracle3_upstream_parity.run`/`.verify` (vendored Oracle3 `check_constraint`, `PolymarketSchedule.fee`) | `relations` |
| A6 wallet | WALLET-01 `load_and_verify_wallet_evidence_ledger`, WALLET-02 mapping loaders + `build_wallet_profile_snapshot`, WALLET-03 `build_wallet_copyability_research_assessment` + mapping round trip | `wallet` |
| A7 pointer | REL-01 native economics rows (read side only) | `relations()["a7_pointer"]` |

Operator: `tools/alpha/run_relation_wallet_spine.py run|verify`. One finite, manual, foreground pass.

## 2. CLI

```
run    --spine-scratch ABS --alpha-registry ABS --rel-scratch ABS --wallet-ledger ABS --case ABS --scratch-dir ABS
verify --scratch-dir ABS
```

Exit codes: 0 `RUN_COMPLETE` / `VERIFIED`; 1 closed refusal (`STOPPED` + `reason_code`) or `TAMPER_DETECTED`;
2 `USAGE_ERROR` (arguments are never echoed). Caps: 1 GiB and 8000 files over the aggregate of all inputs (both
trees, registry, ledger, case and retained members), case ≤ 1 MiB, `model_ids` ≤ 200, retained quote member ≤ 64 KiB,
B2 receipt ≤ 16 MiB (a bounded core of ids, counts and ≤ 200 model rows; ~34 KiB observed).

Inventory (run on caller inputs and again on the frozen copies in every `compute`, including cold `verify`): tree
roots and every child, singleton files and retained members are checked by `lstat` only (regular single-link files,
no symlink, junction/reparse point, hardlink, alias, SQLite sidecar or secret-shaped dir; member parents contained
in their root), and the aggregate caps hold **before any byte is hashed**. Hashing is streamed. The frozen case,
retained members, parity receipt and B2 receipt are read with bounded reads only. The derived `parity/` scratch keeps
the native parity caps; its REL copy must equal B2's frozen REL input. Distinct input roles must be disjoint
(an equal path for two roles refuses `INPUT_PATHS_OVERLAP`).

## 3. Case (`s10-cap-b2-relation-wallet-case-v1`, closed keys)

`schema_id, spine_receipt_id (b1spine:sha256:), rel_receipt_id (relmarket:sha256:), target_market_id (canonical),
model_ids (unique, predeclared), expected_wallet_ledger_head, target_wallet, wallet_as_of (UTC Z), cohort,
market_contexts, identity_observability, quote_witnesses, delay_seconds, cost_scenarios`.

Nested native mappings are validated by their native loaders. Quote witnesses register retained bytes all-or-nothing
(`raw_evidence_reference_id`, `research_provenance_manifest_id`, `raw_content_member`); a member is a
case-parent-relative regular single-link file (no link, junction, alias, `..` or absolute path). Credential-shaped
keys refuse `FORBIDDEN_FIELD`; secret-shaped values refuse `SECRET_MATERIAL_REJECTED` (native `0x`+64-hex condition
ids are masked only at their closed `condition_value` field and must then equal a condition of the shared universe).

## 4. Call order (run)

1. Scratch must be absolute, outside the repository and empty (write once). Every socket entry point is blocked.
2. Freeze: hash caller inputs, copy them under `inputs/`, re-hash (`INPUT_CHANGED_DURING_FREEZE`).
3. Oracle3 parity `run` on the frozen REL copy into `parity/` (genuine upstream calls).
4. `compute`: B1-A `verify` (`SPINE_NOT_VERIFIED`) → lineage → `bind_target` (`TARGET_NOT_ADMITTED:<native>`,
   `SPINE_GROUNDING_MISMATCH`, `SPINE_TARGET_MISMATCH`) → REL `verify` (`REL_NOT_VERIFIED`) → parity `verify`
   (`PARITY_NOT_VERIFIED`, `PARITY_INPUT_MISMATCH`) → `relations` → `wallet` → core.
5. Caller inputs re-hashed (`INPUT_CHANGED_DURING_RUN`); receipt `s10-cap-b2-relation-wallet-receipt-v1`,
   id `b2research:sha256:<canonical core>`, written with exclusive create.

`verify` only reads: it recomputes the whole core from the frozen copies (re-running every nested native verifier)
and compares; any difference is `TAMPER_DETECTED` with closed failure codes. The receipt must have exactly the
keys `schema_id`, `receipt_id`, `core` (`RECEIPT_SHAPE_INVALID`), and the outer `schema_id`, which the id does not
hash, must equal `s10-cap-b2-relation-wallet-receipt-v1` exactly (`RECEIPT_SCHEMA_INVALID`). Receipt ids are stable
within one code identity; this WP does not claim to preserve pre-merge B2 development receipts across intentional
code-identity changes.

## 5. A5 relations

REL must bind the same grounding receipt, universe and `as_of`, decided at/after `as_of`
(`REL_GROUNDING_MISMATCH`, `REL_UNIVERSE_MISMATCH`, `REL_DECISION_BEFORE_AS_OF`); parity must come from that REL
receipt (`PARITY_REL_MISMATCH`). Each model id must be unique in REL and parity (`MODEL_ID_NOT_UNIQUE_IN_REL`).
Models without the target are rejected `MODEL_NOT_TARGET_RELATED`; non-evaluated rows `NATIVE_NOT_EVALUATED:<status>`.
Every member market must carry the grounding-bound rule SHA (`RULE_IDENTITY_MISMATCH`). A selected model is
ADMITTED only if native `FORMAL_VALID` and Oracle3 `UPSTREAM_CONDITIONAL_EVALUATED`. Native formal, real-world,
disposition, direction and parity labels are copied, never re-derived; tie/cancel/reschedule/partial without
declared semantics stay `INCONCLUSIVE`, rule claims contrary to the PIT rule stay `RULE_CONFLICT`. Full native
denominators are retained. The A7 pointer carries native economic status and legs only, always
`tradable=false`, `executable_edge=false`, `conditional_only=true`.

## 6. A6 wallet

`wallet_as_of` and the grounding `as_of` must be ≤ the REL decision time (`WALLET_AS_OF_AFTER_DECISION`). The ledger
must natively verify (`WALLET_LEDGER_NOT_VERIFIED`) at the exact expected head (`WALLET_LEDGER_HEAD_MISMATCH`).
Native loader refusals become `WALLET_INPUT_REFUSED:<code>`. Every context must bind by exact condition and token to
the same PIT universe with the exact PIT metadata clock, else REFUSED `CONTEXT_NOT_BOUND_TO_SHARED_PIT_UNIVERSE`
with counts of `CONTEXT_NOT_STANDARD_BINARY_NATIVE_IDS`, `CONTEXT_FOREIGN_TO_PIT_UNIVERSE`,
`CONTEXT_CONDITION_AMBIGUOUS`, `CONTEXT_TOKEN_NOT_IN_MARKET`, `CONTEXT_METADATA_CLOCK_MISMATCH`,
`CONTEXT_OBSERVED_AFTER_WALLET_AS_OF`; exactly one target context is required (`TARGET_CONTEXT_MISSING`/`_AMBIGUOUS`).
Native builder refusals become REFUSED `NATIVE_REFUSED:<code>`. ADMITTED only with a target-eligible event and an
`OBSERVABLE_CONDITIONAL` delay result; otherwise INSUFFICIENT. Output is ids and counts only (never the address).

## 7. Capability ledger (six IDs; the 36-row CSV is never edited)

| ID | B2 status |
|---|---|
| R3-03 | `ENG_OFFLINE_SHARED_CASE_CONSUMED_BY_A5_NOT_VALUE_VERIFIED` when a selected model reached the upstream call, else `NOT_EXERCISED_ON_SHARED_CASE` |
| R3-03-FEES | `FIXTURE_FEE_SCHEDULE_INVOKED_CURRENTNESS_UNVERIFIED` (same condition) |
| R3-04, R3-11, R3-19 | `OPEN`, `NATIVE_ONLY`, with the inspected import-closure / provider cause |
| R3-14 | `OPEN_OWNER_RIGHTS`, `BLOCKED_SCHEMA_INSPECTED_ONLY` (external dataset not downloaded) |

All rows: `value_verified=false`, `owner_disposition=PENDING`. The other 30 IDs are unchanged; Lane B
(R3-15/16/17/26) is separately owned; W06 book gap-fill is not attempted.
