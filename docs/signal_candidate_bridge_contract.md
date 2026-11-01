# Offline native rain signal candidate bridge

S10-SIGNAL-CANDIDATE-BRIDGE-01 is a RUNTIME/Risk3, exact-nine-file offline research tool. Karl authorized the frozen prompt/spec with SHA256 `582d0336be55c9301ffaeb43a80594a44830e63b486afd1446ef9b989dd6ff4d` / `b557db1aac2bf877a88fd0f757ec2dd16663d20073da7514428e8b61b4d98021` on merged PR263 (`7a37fbd41f1e972407faa6973e2ff027c4a22264`). No certificate is required or issued. Readiness and implementation do not grant merge or operational authority.

## Interface and native reuse

`tools/alpha/run_signal_candidate_bridge.py` exposes `evaluate_request(request)`, `verify_receipt(request, receipt)` and one foreground CLI:

```
python -B tools/alpha/run_signal_candidate_bridge.py run --request-file /absolute/external/request.json --output-file /absolute/external/new-receipt.json
python -B tools/alpha/run_signal_candidate_bridge.py verify --request-file /absolute/external/request.json --receipt-file /absolute/external/receipt.json
```

Run writes one new external receipt exclusively; verify writes nothing. Exit0 means a completed research verdict/verified receipt, exit1 a closed refusal, exit2 sanitized CLI misuse. Paths/arguments/source bodies/exceptions are never echoed. Inputs, native capture and lifecycle store are read-only. Existing sources, Hermes preview, Gate C, execution, configurations and all production allowlists remain unchanged. No network, process, provider, account, order, scheduler, service or paper-engine call is made.

The exact request and venue bundle schemas, size/type limits, result fields and failure precedence are frozen in `docs/wp_specs/S10-SIGNAL-CANDIDATE-BRIDGE-01/wp_prompt.txt`; `REQUEST_FIELDS`, `BUNDLE_FIELDS`, `RESULT_FIELDS` and `OUTPUT_CLASSIFICATION` are the implementation counterparts. Unknown fields, floats, duplicate JSON keys, malformed types, unsafe paths, symlinks/reparse traversal, hardlinked/nonregular inputs and overwritten outputs reject. File opens use native external-path guards plus pinned parent directories/no-follow semantics and handle/path identity checks. Inputs are hashed and checked again before result/output; source inventory additions/removals and changed store/body/source bytes refuse. Output creation is exclusive with restrictive mode, not an overwrite or second store. SQLite sidecars must be absent on the supplied frozen lifecycle input.

## Source and StrategyVersion binding

The unchanged `provenance.verify_capture` must cold-verify exactly one PR263-format rain-only/no-Hermes capture and its five native module hashes. Native rule/forecast parsing supplies the exact market, condition, ordered Yes/No pair, rule, station and climate day. Each selected source token row must be unique, same condition and correct index. Native source book diagnostics do not invent a new price; separately supplied compatible raw Gamma/CLOB evidence provides repricing.

Pilot alias `RAIN_NWS_V1` maps only to actual Hunter method `nws-gridpoint-pop-climate-day-v1`. Source replay proves local retained-byte/code/clock consistency, **not** independently authenticated original-source origin, finality, statistical skill or calibration. The result always has `source_origin=UNVERIFIED`, `method_state=METHOD_NOT_QUALIFIED`, `production_eligible=false`, null permit/signed order, `no_live=no_order=true`, and accepted production methods/corpora0. Independent event groups remain0; unresolved source counts are copied only after verified replay, otherwise null.

An acyclic `binding_payload` commits the native code map, raw manifest digest, method pair, rule/station/day/deadline/source cutoff, market/condition and ordered tokens. Its reference is `signalbinding:sha256:` plus SHA256 of canonical `{"binding_payload": payload}`. The existing immutable StrategyVersion must already carry exactly that one reference; its native id, verified lifecycle head, creation time and non-retired status must match. The tool does not mint or persist versions, activate policies, create allocations or require a live portfolio. Fixtures prepare synthetic native source/store/version evidence before invoking the tool.

## Time and venue mechanics

The climate-day start is derived through unchanged station-timezone/standard-offset helpers; Gamma end time and UTC midnight are not substitutes. Forecast source receipts must predate the source cutoff. Native CLOB capture occurs after that cutoff and is not forecast-source evidence. Source cutoff <= native evaluation <= research decision < min(native evaluation+30seconds, climate-day start). The tool has no current-live mode or host-clock reset. Historical clocks remain `RESEARCH_HISTORICAL`; even `SYNTHETIC_ONLY` cannot authenticate origin. Real event-to-order latency is UNMEASURED.

The supplied native venue snapshot is reconstructed from bounded raw Gamma and CLOB bytes and explicit acquisition clocks, then compared in full. Gamma's fresh venue facts may differ from the original capture, but rule/date/station/condition/ordered tokens must agree. Reconstructed content identity proves local mechanics only. Both acquisition-to-decision and book-timestamp-to-decision ages must be nonnegative and <=30seconds; missing/future/stale books are inconclusive. The unchanged evaluator's acquisition-age check is retained independently. Source deadline equality and source-evaluation+30seconds equality refuse.

Fixed BUY/aggressive/FOK mechanics reuse `hunter_cycle.fee_bound`, `size_order`, `fee_max`, `build_execution_intent` and `assess_execution_feasibility`. USD2floor/USD5fee-inclusive cap, separate Gamma USD-notional/CLOB-share minima, exact ticks, depth and zero-delay requirements remain. Dated `scanner.FEE_POLICY` / weather tariff expire at `2026-11-04T00:00:00Z`; no renewal or caller override exists. Conservative fee uses max(native, documented rain rate); it is reported separately from a lower native assessment fee without rewriting snapshot identity. No fee coefficient-to-bps conversion, rebates, fill probability or payout stress-edge is invented.

Quantity is narrowed onto both 0.01-share and USD0.01-principal grids using exact rational/GCD arithmetic, never an unbounded decrement loop, then every minimum/depth/floor/cap/fee is rechecked. `entry_economics` is deliberately not used: its payout-margin requirement would confer unsupported financial meaning. A compatible **synthetic** small-minimum book can reach the native FEASIBLE result while method/live eligibility stays false. USD5principal plus positive fee under USD5total refuses. No dormant USD10 profile is activated.

## Results and verification

Statuses: REFUSED, INCONCLUSIVE, MECHANICALLY_NOT_FEASIBLE, MECHANICALLY_FEASIBLE_RESEARCH_ONLY. Native nested intent/assessment fields and diagnostic codes remain unchanged. Identity/source/version/clock conflicts precede unknown venue/fee facts, then known negative sizing/native results, then mechanical success. No real/current venue feasibility is claimed from this implementation's synthetic tests.

Every public result field is enumerated and classified; validated strings/nested mappings are recursively scanned, primitive booleans/counts/timestamps/nulls are type-exempt with field-coverage evidence. Invalid output is scanned too. A hand-built dictionary is not a full output-surface scan unless a field-coverage test proves it covers every public field. Receipt identity is SHA256 of canonical `{"receipt": receipt_without_receipt_id}`, with prefix `signalcandidate:sha256:`. Canonical JSON preserves explicit nulls/array order, sorts keys, uses compact UTF8 and rejects nonfinite/floating inputs. Cold verify rederives sources, clocks, version/head, raw venue and economics and requires complete equality; a rehashed forged badge is not verification.

## Validation and boundaries

The focused test module maps R002-R010 to native source/Yes-No/version/currentness/fee/minimum/SDK/depth/delay/expiry, field/no-echo/path/tamper and no-side-effect assertions, including both outcome-index positives and decision+1day denial. R001 synchronization/readiness and R011 full/security/review/CI/posted evidence are real process receipts, not facts asserted by a fixture. The negative matrix and policy applicability are in the frozen prompt. Final actual results live in the stable status fragment/current PR body.

Every group in `docs/ai/codex/PROTECTED_PATHS.md` Centralized Boundary Group Reference remains unpromoted: credentials/secrets, authenticated clients, wallet/account behavior, order placement/cancel, execution gateway, paper engine, scheduler/bot loop, runtime/daemon, dashboard/deployment, dependency/lock changes, external code copying and generated artifacts. LIVE DISABLED; METHOD_NOT_QUALIFIED; Karl-only merge. Real source/model/account/host/financial actions require distinct authorization. Revert only the nine scoped files to remove the tool; preserve external original evidence and all existing native history.
