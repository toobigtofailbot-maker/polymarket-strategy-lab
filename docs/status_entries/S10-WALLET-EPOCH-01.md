# S10-WALLET-EPOCH-01

RUNTIME / Risk3 / M / exact10. Branch: codex/s10-wallet-epoch-01.
Frozen base and merged predecessor PR265: 7b8d2c895122682bcba915325dd3dd9dafdaa770;
PR265 head f7b997e905e80b94a44bed5eee5ddf330b3bbfa7. Karl explicitly authorized
the exact prompt 3cca1a9132dc674826c41282bc13188479f7b465cd65e17a612bffa3112fcafd /
spec 101825da1574aaae79c3143ca0ed452f4918d4407042789e92a4ca98d069ed2a.
Both are committed byte-identical under docs/wp_specs/S10-WALLET-EPOCH-01/.
Native pre-source readiness IMPLEMENTATION_READY, RUNTIME/DETERMINISTIC, no
certificate. Readiness is not economic or merge authority.

## Scope and behavior

Changed files: src/data_layer/polymarket/public_client.py, its client test module,
tests/data_layer/wallet_intelligence/test_public_ingest.py, the WALLET-01 public
evidence contract, exact frozen prompt/spec, this fragment, project_status,
repo_truth_index and deferred_items_log. No eleventh path; no
src/data_layer/wallet_intelligence/, config, dependency, lock or workflow change.

`get_wallet_trades_page` and `get_wallet_activity_page` keep their signatures and
validate the caller's canonical ISO UTC `start`/`end` (explicit `Z`, full
HH:MM:SS, only an all-zero fraction) with one private stdlib helper, then send them
as decimal non-negative Unix epoch seconds on first and cursor pages. Offset, naive,
non-string, invalid-date, leap-second, pre-1970, nonzero-subsecond and reversed
windows raise the existing closed `FIELD_VALUE_INVALID` before any transport and
never echo input. Equal endpoints stay accepted (no native rule rejects them).
Recorded raw `request_parameters` show the epoch wire values; WalletIngestRequest,
run key, feed receipts and PIT clocks stay ISO UTC. Host, GET-only, no-auth,
no-redirect, no-retry, no cursor loop, page/byte/cursor caps and the combo feed
(no window) are unchanged.

## Validation

Focused offline tests (intercepted openers, no product GET):
test_public_client.py, test_public_ingest.py, test_ledger.py,
test_architecture_boundaries.py, test_project_status_docs.py and
test_repo_truth_docs.py. Exact commands, counts, full-suite, guard and hosted CI
receipts for the final head are recorded in the PR body; this fragment does not fix
its own commit SHA or claim unperformed hosted/posted evidence.

## Limits

Deferred D001: sampled live `/v2/activity` TRADE rows omit `is_combo`; they stay
SCHEMA_DRIFT / identity-ambiguous and are never assumed FALSE. Deferred D002: no
live retest of the fix is authorized or performed. The historical 2026-11-02
ISO-400 / epoch-200 retest motivated the change but is not post-fix, prospective,
alpha, copyability or profitability evidence. No wallet signal, ranking, Hermes,
paper, live, order or capital authority. Karl alone merges.
