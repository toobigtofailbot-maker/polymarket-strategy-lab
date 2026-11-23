# B1-A Source/PIT → Research → W01 and Forecast Consumer Spine Contract (S10-CAP-B1-SOURCE-FORECAST-01)

**Status:** offline engineering demonstration (`OFFLINE_ENGINEERING_DEMONSTRATION`). No provider, model,
product network, credential, order, paper, qualification, strategy or capital authority. LIVE DISABLED.

## 1. Purpose

B1-A connects producers that already exist; it does not replace them. One frozen, cold-verified
S10-R3-SRC-01 grounding scratch is consumed by:

| Role | Native producer / consumer (unchanged) | Spine function |
|---|---|---|
| A1 PIT market scout | `source_grounding.load_corpus` (→ `alpha_discovery.build_alpha_universe_snapshot`), `bind_rule_texts`, `public_market_contract_parity.normalize_native`, `MarketCatalog.from_market_records`, SRC-01 `alpha_join` | `source_forecast_spine.scout` |
| A2 research specialist | SRC-01 accepted sources + raw evidence references, `metaculus_source_archive_bridge.assess_sources` (pinned leaves), `official_sdk_search_bridge.invoke_search` + `project_typed_page` (pinned SDK, MockTransport, `fixture.invalid`), `source_grounding.rank_markets` | `source_forecast_spine.research` |
| A3/A4 (W01) | unmodified `tools/alpha/run_hermes_delegated_specialists.run` / `.verify` (pinned Hermes v0.21.3 `345cd2b`, two witnessed leaf children, scripted provider boundary, advisory Alpha append + cold read) | `source_forecast_spine.w01_case` |
| Forecast diagnostic | unmodified `tools/alpha/run_forecast_evaluation.run` / `.verify` | `source_forecast_spine.bind_forecast` |

Operator: `tools/alpha/run_source_forecast_spine.py run|verify`. One finite, manual, foreground pass.

## 2. Call order (run)

1. `run_source_grounding.verify` on the caller's SRC-01 scratch (must be `VERIFIED`).
2. A1 `scout(target_market_id)`. Refusal codes: `TARGET_NOT_IN_UNIVERSE`, `TARGET_IDENTITY_ABSTAINED`,
   `TARGET_CATALOG_CONFLICT`, `TARGET_RULE_NOT_BOUND`, `TARGET_CANDIDATE_MISSING`, `TARGET_CANDIDATE_AMBIGUOUS`.
   The denominators cover examined / identity valid / abstained (with defect counts) / rule bound / catalog duplicate and
   round-trip conflicts / joined candidates / admitted / refused / ambiguous / `discovered_new_markets = 0`.
3. A2 `research`. The W01 source allowlist is the target's SRC-01 `ACCEPTED` labels, **narrowed** by the
   Metaculus upstream verdict: a source with `upstream_passed != True` is excluded with a recorded reason. Upstream
   never adds a source (`promoted_by_upstream = 0`). Each frozen SDK page goes through one real `PublicClient.search`
   call. A target that the SDK projects as anything other than `IDENTITY_CONSISTENT` refuses with
   `SDK_TARGET_IDENTITY_CONFLICT`, and an empty allowlist refuses with `NO_ADMITTED_PRE_CUTOFF_SOURCE`.
4. Seeded-lineage check: candidate, family and source references must already be in the caller's native Alpha registry.
5. `run_forecast_evaluation.run` + `.verify` on the same grounding, then `bind_forecast`. The target row must be
   `SELECTED`, with the same rule hash, question hash, event group, grounding receipt id and admitted source references.
   This runs **before** W01, so a forecast refusal never dispatches or appends.
6. The W01 case is built only from the verified A1/A2 identities and the caller's scripted children, and checked by W01's own
   `parse_case`. `source_cutoff` equals the grounding `as_of`. Then `run_hermes_delegated_specialists.run` + `.verify`.
7. One write-once spine receipt (`b1spine:sha256:`) binds every receipt id, denominator and the capability ledger.

Any refusal returns `STOPPED` with a closed code. No input text, path or traceback is echoed.

## 3. Replay and recovery

- A non-empty scratch is never re-run. With `receipt.json` and identical case bytes it must cold-verify, and the result is
  `IDEMPOTENT_VERIFIED` with no extra Alpha episode. Otherwise the result is `SCRATCH_NOT_EMPTY` (partial scratch,
  unknown worker result, different case).
- A fresh scratch re-runs the real chain. W01's native append is idempotent (same episode id, no new row).
- `verify` re-runs the native forecast and W01 verifiers and recomputes A1/A2 and the bindings from the frozen
  forecast-scratch grounding copy. A tampered receipt, a changed code identity or a stale source is reported as `TAMPER_DETECTED`.

## 4. Measurement honesty

For each SDK page, the spine records the native ranker position and the SDK position of the target on the same query.
`lift` is `NO_LIFT` unless the SDK ranks the target strictly better. Model usage and cost are `UNKNOWN` (scripted
boundary; no spend incurred). Citation integrity is not semantic truth. The forecast receipt is a separate
`DIAGNOSTIC_ONLY` read and never the A3 child forecast (`is_a3_child_forecast = false`, `method_parity = B1_B_PENDING`).

## 5. Capability ledger (36-row CSV unchanged)

Touched, but only with an actual receipt and a downstream read, and never VALUE_VERIFIED: R3-02, R3-01-SOURCE_ARCHIVE,
R3-23, R3-05, R3-05-CITATIONS. Still open: R3-01, R3-10, R3-10-WANG, R3-12, R3-12-SAMPLER and R3-18 (B1-B method parity);
R3-06, R3-20 and R3-22 (later learning owners); R3-07, R3-07-ROUTER, R3-08, R3-13, R3-21 and R3-28 (provider or
source rights); R3-24, R3-25 and R3-27 (deferred same-case parity); R3-15, R3-16, R3-17 and R3-26 (Lane B). All other
rows are unchanged. Roles: A1/A2 are deterministic research functions and A3/A4 are W01's offline witnessed children.
This WP makes no claim of nine-of-nine operation, prospective forecasting, profitability or live availability.

## 6. Market catalog note

The PIT store holds research-provenance records, not WP10 `MarketMetadataSnapshotRecord` rows. The spine projects
PIT markets into snapshot records **only** to use the native catalog lookups as a market / condition / token round-trip
and duplicate cross-check. It is never a new identity (`source = native_pit_projection_cross_check`).

## 7. Tests

`tests/data_layer/analytical_research/test_source_forecast_spine.py` (R001, R002, R004, R005, R008) and
`tests/tools/alpha/test_run_source_forecast_spine.py` (R003, R006, R007, R009). The pinned parts need
`POLYMARKET_HERMES_PIN_ROOT` and otherwise skip; the unpinned refusals still run.
