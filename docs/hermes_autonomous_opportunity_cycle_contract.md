# Hermes opportunity cycle — offline vertical slice

`src/research_runtime/autonomous_opportunity_cycle.py:evaluate_once` composes a
caller-injected opportunity choice with verified Alpha memory, StrategyLifecycle,
the latest Hermes strategy assessment, native EXEC-FEAS and exploratory Gate C.
It never ranks candidates, changes strategies or policies, or invokes a producer.

This WP permits local synthetic mechanics only. Every receipt has
`proof_level=SYNTHETIC_ONLY`, `model_origin_proof=UNVERIFIED`, `no_live=true`,
`no_order=true`, and `NON_EXECUTABLE_WITHOUT_SEPARATE_LIVE_AUTHORITY` posture.
No receipt proves a genuine Hermes choice, executable edge or profitability.
All protected boundary groups in `docs/ai/codex/PROTECTED_PATHS.md` retain their
existing gates. There is no provider, credential, account, gateway, scheduler,
paper-engine, deployment or live activation path in this connector.

## Inputs and lineage

Supply explicit read-only `lifecycle_store_path`, `hermes_manager_store_path`,
and `alpha_registry_path`; their existing verified loaders alone interpret stores.
These paths are neither serialized nor used in receipt identity. The ordered
`candidate_menu` contains at most eight exact dictionaries with `candidate_id`,
`strategy_version_id`, `gamma_market_id`, `condition_id`, and `token_id`.
Candidate and strategy IDs must be unique within the menu. Each Alpha candidate
must exist in the verified registry and contain the exact canonical
`market:polymarket:<gamma_market_id>` and `token:polymarket:<token_id>` subject refs.
The native strategy must exist and its Alpha-candidate evidence references must
resolve to exactly that candidate. The condition is bound through the validated
native public venue snapshot. Missing or ambiguous linkage rejects; a candidate
needs no formal OOS, WP172 PASS or DATA-03 prerequisite.

`venue_snapshots` contains at most eight native `PublicExecutionVenueSnapshot`
objects, each revalidated by the existing native validator. Duplicate snapshot
IDs reject. A trade needs exactly one matching market/condition/token snapshot.
Acquisition completion must not exceed `information_cutoff_ns`. An explicit
`venue_proof_level=SYNTHETIC_ONLY` admits injected fixtures; other proof labels
reject until a separately authorized producer-verification adapter exists.

## Strict choice protocol

`choice` is UTF-8 JSON text/bytes, 1–16,384 bytes. Native strict JSON decoding
rejects duplicate keys, floats and nonfinite constants. No arbitrary object or
callable is executed. Exact common fields:

- `action`: `TRADE`, `NO_TRADE`, `PAUSE` or `REASSESS`.
- `proof_level`: exactly `SYNTHETIC_ONLY`.
- `information_cutoff_ns`, `produced_at_ns`, `expires_at_ns`: integer Unix ns.

`TRADE` additionally requires exactly `candidate_id`, `strategy_version_id`,
`hermes_assessment_id`, `context_sha256`, `active_policy_id`, `side`,
`execution_style`, `order_type`, `requested_shares`, `price_limit`, `post_only`
and `gtd_expiration_unix_s`. No other fields are accepted, including model prose,
market substitutions, caller-built intents, eligibility flags or mutation proposals.
Order types in this slice are GTC/GTD, subject to native style compatibility;
native contracts therefore admit passive-maker proposals. BUY and SELL are
preserved exactly. Native decimal, quantity, price, tick, minimum, fee and order
shape validation applies without coercion or clamping.

Abstention actions contain only the common fields and produce `NO_TRADE` with
`NO_NEW_EXPOSURE`. With no selected strategy they do not claim a same-strategy
assessment; valid store heads and menu/evidence digests remain recorded. Trade
choices must name the latest verified same-strategy assessment ID, its current
native lifecycle context fingerprint and current active policy. Superseded,
future, stale or mismatched assessments reject. Non-permit-compatible Hermes
actions and strategy restrictions remain governed by native Gate C.

## Clocks, deterministic evaluation and output

All times are caller-supplied integer Unix nanoseconds (0 through 2^63−1).
No wall clock or background timer is sampled. Require cutoff ≤ produced ≤ evaluated
< choice expiry ≤ caller deadline; cutoff must equal the choice cutoff. Deadline
is at most 300 seconds after evaluation. Public age is 1 ns–300 seconds (default
5 seconds); Hermes age is 1 ns–24 hours (default 300 seconds). Assessment decision
and its UTC information cutoff cannot exceed cycle cutoff. Evidence freshness
uses these explicit clocks; this is not runtime host-time attestation.

The connector builds the native intent, assesses native mechanics and calls
native exploratory Gate C using exact stores and native objects. It rechecks
the two store heads returned by Gate C to reject a concurrent state change.
Only `PERMIT_ELIGIBLE` reaches the native permit builder. The unmodified native
permit is returned only as a tagged preview mapping. `preview_valid_until_ns`
is bounded by the native permit, choice expiry and Hermes freshness deadline;
the wrapper never rewrites a native permit or conveys live authority. A later
runtime must revalidate its own current stores, clocks, account and authority.

One dictionary receipt always returns: `NO_TRADE`, `REJECTED`, `INCONCLUSIVE`,
or `ELIGIBLE_PREVIEW`. It contains input digests and available verified IDs,
store heads, timestamps, exact intent mapping, native feasibility/decision IDs,
all native diagnostic/capacity/rejection codes, and the preview if eligible.
Invalid fields unavailable for safe binding remain null. Errors are closed
codes; raw exception text, paths and untrusted choice text are excluded.
`receipt_id` is `decisioncycle:sha256:` plus SHA-256 of native canonical JSON
of all other receipt fields. Identical inputs and verified state replay byte
identically; choice/cutoff/public-evidence changes propagate into receipt identity.
No journal or second persistence system is added. Retain all returned outcomes
as the future no-trade denominator; no paper feedback loop is activated here.

The module imports without performing network, process, store or environment
mutation. Existing Hermes/Alpha analytical initialization is deferred until an
explicit cycle. Existing verified loaders are read-only; no store is created,
repaired, migrated or changed. Read-only composition is not an atomic transaction
across three stores, and receipts are observations at the explicit evidence time.

## Requirement-to-evidence and negative matrix

| Requirement | New focused test | Positive and negative evidence |
|---|---|---|
| R001 | `test_hermes_choice_controls_candidate_and_exact_intent` | Two real Alpha/strategy references; second candidate, SELL, exact size/price preserved; NO_TRADE/PAUSE/REASSESS |
| R002 | `test_native_exec_feas_and_gate_c_only_preview` | Actual native call chain, GTC/GTD preview, exact IDs, minimum-size rejection cannot call permit builder |
| R003 | `test_missing_or_stale_policy_hermes_venue_rejects` | Missing allocation/policy/assessment/venue, superseded/stale assessment, expired policy, paused/quarantined strategy, soft risk reduction, fee/tick/minimum/budget failures |
| R004 | `test_untrusted_choice_and_forged_lineage_fail_closed` | Duplicate/unknown fields, NaN/float/numeric syntax/bounds, unsupported order, forged producer/assessment/context/strategy/candidate/snapshot, ambiguous/oversized menu, wrong condition/cutoff/deadline, store race |
| R005 | `test_content_address_replay_no_side_effects` | Byte replay, changed choice/cutoff/evidence IDs, unchanged store hashes, blocked sockets/processes, fresh-interpreter import audit |
| R006 | `test_architecture_exact_approval_preserves_all_original_guards` plus native families and final suite | Original seven guards accept exact module, all reject sibling; final-three invariant and every other guard byte preserved; exact seven-path readiness |

The sole historical edit inserts one exact literal and factual comment in
`APPROVED_SRC_SCOPES`, before its existing final three entries. Full validation
and final evidence are local only; independent SIDE20 acceptance remains separate.
