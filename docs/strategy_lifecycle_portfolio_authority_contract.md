# Strategy Lifecycle + Global Portfolio Authority Contract

Status: S10-STRAT-LIFE-01 contract (repo truth after S10-STRAT-LIFE-01 merges).
Architecture: V2.1 target architecture: ACCEPTED — see the V2.1 section of
`docs/architecture_decision_record.md`.
Implementation: `src/strategy_lifecycle/` (`models.py`, `policy.py`, `store.py`), stdlib-only.
Authority: local/offline lifecycle and portfolio-policy state only. No network, credential,
scheduler, Hermes-runtime, paper-execution, order, execution or live authority; capital/orders
USD 0 / 0.

## 1. Purpose

This is the first V2.1 foundation: the canonical substrate that future packages
(S10-HERMES-STRAT-01, S10-EXEC-FEAS-01, S10-GATE-C-EXPLORE-01, S10-DEPLOY-EXEC-01,
S10-LIVE-ORCH-01) will consume. It records what a strategy is, how it descends from a parent,
how healthy it is, what strategy-local restrictions apply, what budget it currently holds, and
the single human-authorized global envelope that bounds all budgets. It creates no trading path
and is not wired into Alpha Factory, Hermes, paper, qualification, WP170, WP172, Gate C,
execution, deployment or the cockpit.

## 2. Canonical Records

All records are frozen dataclasses with exact field sets. IDs are content addresses:

```text
id = prefix + sha256(canonical JSON of the public mapping with the ID field excluded)
canonical JSON = UTF-8, sort_keys, separators (",", ":"), ensure_ascii False, allow_nan False
```

| Record | Schema ID | ID prefix |
|---|---|---|
| StrategyFamily | `polymarket-strategy-family` | `strategyfamily:sha256:` |
| StrategyVersion | `polymarket-strategy-version` | `strategyversion:sha256:` |
| PortfolioAuthorityPolicy | `polymarket-portfolio-authority-policy` | `portfolioauthoritypolicy:sha256:` |
| PortfolioPolicyReceipt | `polymarket-portfolio-policy-receipt` | `portfoliopolicyreceipt:sha256:` |
| StrategyHealthReceipt | `polymarket-strategy-health-receipt` | `strategyhealth:sha256:` |
| StrategyRiskAllocation | `polymarket-strategy-risk-allocation` | `strategyriskallocation:sha256:` |
| StrategyRestrictionReceipt | `polymarket-strategy-restriction-receipt` | `strategyrestriction:sha256:` |

The machine spec (`docs/wp_specs/S10-STRAT-LIFE-01/wp_spec.json`) records each ID as a
`SHA256_CANONICAL_JSON` derivation over every other top-level field, with a valid example built
from a real product record, so the spec guard re-derives every product ID independently.

Every schema version is `1.0.0`. Binary floats, NaN/Infinity, booleans-as-integers, unknown or
missing fields, duplicate JSON keys, non-canonical text and unsorted/duplicate evidence refs
reject. Opaque references (provenance, code identity, decision, human authorization, account
scope, evidence refs) are bounded tokens that reject path-like text (`/`, `\`, `..`, drive
prefixes, leading `.`/`~`) and secret-like text (secret/password/passphrase/mnemonic/private
key/API key/bearer/credential markers in any case or separator spelling, or `0x` followed by 64 or
more hex digits). The single exception is a reference that is entirely the canonical public
Polymarket event identity `event:polymarket:0x` + exactly 64 lowercase hex; uppercase,
wrong-namespace, wrong-length and padded forms still reject and no caller allowlist exists.
Errors are closed codes that never echo payload. No time, environment or randomness is
generated; all times are caller-supplied non-negative integer nanoseconds.

A family is a lineage grouping only. A version carries `evidence_posture`
(REPEATABLE_STATISTICAL, EVENT_INFORMATION, RELATIVE_VALUE_STRUCTURAL, MICROSTRUCTURE_MAKER,
WALLET_DEPENDENT, NOVEL_EXPLORATORY) as advisory metadata only: it is not a PASS/FAIL gate and
grants no paper/live eligibility.

`strategy_spec_json` is canonical JSON with exactly `thesis`, `universe`, `entry_rule`,
`exit_rule`, `execution_rule` (objects) and `parameters` (object of lower-case names). Bounds:
65,536 canonical bytes, depth 8, 4,096 nodes, 256 parameters, 256 evidence refs.
`adaptive_bounds_json` maps parameter names to exactly one of `INTEGER_RANGE`, `DECIMAL_RANGE`
(canonical decimal strings) or `ENUM` (unique ordered strings). A bound frozen on a version
limits how far a bounded child may move that parameter.

## 3. Adaptation Classification

`ROOT` iff there is no parent. A child must reference an existing exact parent in the same
family, must not be created before it, and must not be semantically identical to it (same
posture, code identity, spec and bounds); no-op children reject. A child is
`BOUNDED_ADAPTATION` only if posture, code identity, the five rule objects, the adaptive-bound
declaration and the parameter key set are all unchanged, at least one parameter changes, and
every changed parameter is adaptive and inside its frozen parent bound. Anything else is
`MATERIAL_ADAPTATION`. The validator derives the class; a declared class must equal it. Only
mechanical boundedness is classified — never whether an adaptation is good.

`derive_inherited_risk_band_ceiling(parent_band, adaptation_class)` over
PAPER < EXPLORATORY_LIVE < VALIDATED_LIVE < MATURE_LIVE: bounded children may inherit at most
the exact parent band; material children are capped at min(parent band, EXPLORATORY_LIVE);
ROOT has no inherited band. This is an inheritance ceiling only and grants no live authority. A
material child may later earn a stronger band through another valid future decision/evidence
path. No per-child or per-strategy human approval field exists.

## 4. Global Portfolio Authority Policy

One global `PortfolioAuthorityPolicy` is the human-defined outer envelope: venue scope
`("POLYMARKET",)`, a sanitized non-secret `account_scope_ref`, an effective/expiry window,
canonical non-negative decimal USD limits (global capital at risk, gross exposure, daily loss,
drawdown, cumulative loss, three band pools, three per-strategy band maxima, per-market, order
notional), integer counts (active strategies, active markets, open orders, mutations per
minute) and `allowed_order_styles` drawn from AGGRESSIVE_TAKER, PASSIVE_MAKER in canonical
order. Construction enforces pool sum <= global capital, each per-strategy maximum <= its
pool, per-market <= gross exposure, order notional <= per-market, created <= effective, and
expiry > effective. No leverage or correlation assumption is made. A policy is only a proposal
until an ACTIVATE receipt exists; no policy is activated as production data by this package.

`PortfolioPolicyReceipt` (ACTIVATE/REVOKE) requires a bounded non-secret
`human_authorization_ref`. ACTIVATE needs the policy to exist, `previous_active_policy_id` to
equal the current active policy (or null), the policy not to be already active, and the receipt
time to fall inside the policy's creation/expiry window. REVOKE needs the policy and the
previous reference to equal the current active policy. Exactly zero or one policy is active.
This package does not cryptographically prove who supplied the authorization reference; later
operator/live packages own the actual human activation procedure.

## 5. Health, Restrictions, Allocations

Health: NEW (derived on registration), HEALTHY, WATCH, DEGRADED, QUARANTINED, RETIRED. The
previous state must equal the derived current state; no self-transition; NEW is never
re-entered; RETIRED is terminal; otherwise any non-NEW move is allowed. Health is independent of
risk band and of authority.

Restrictions are strategy-local only: APPLY needs the key inactive; CLEAR needs the exact active
key with the same kind and cap. Kinds: PAUSE_NEW_EXPOSURE, PAPER_ONLY, ACTIVE_BUDGET_CAP (cap
required; other kinds forbid a cap). A strategy-local event never creates a global restriction.

Allocations reserve budget for one strategy version under the current active policy, inside the
policy validity window, with `valid_until_ns` null or greater than `valid_from_ns`. PAPER
requires budget exactly `"0"`. PARENT_INHERITANCE needs a parent with a current allocation and a
band within the derived inheritance ceiling. DIRECT_DECISION performs no evidence-quality gate;
the caller owns whatever evidence/authority supports the decision, and capacity still applies.
A new allocation supersedes only that version's current allocation; history stays append-only.

## 6. Snapshot And Portfolio Capacity

`StrategyLifecycleSnapshot` is derived only by verified replay (it cannot be constructed
directly) and carries the store head hash, row/byte totals, active policy, families, versions,
policies, current health, current allocations and active restrictions, plus fixed
`no_credential_authority`, `no_paper_execution_authority`, `no_order_authority`,
`no_execution_authority` and `no_live_authority` truths.

`evaluate_portfolio_capacity(snapshot, at_time_ns)` returns PORTFOLIO_CAPACITY_VALID or
PORTFOLIO_CAPACITY_REJECTED with closed reasons and per-strategy results. Only allocations
active at `at_time_ns` count; expired/future allocations contribute zero. A positive active
budget is blocked for QUARANTINED/RETIRED health (HEALTH_BLOCKS_ACTIVE_RISK), for
PAUSE_NEW_EXPOSURE/PAPER_ONLY (RESTRICTION_BLOCKS_ACTIVE_RISK), above the smallest active cap
(ACTIVE_BUDGET_CAP_EXCEEDED), above the band per-strategy maximum, and when it references a
non-active policy (ALLOCATION_POLICY_MISMATCH, excluded from totals). Band totals must fit their
pools, the live total must fit global capital, and the count of positive-budget strategies must
fit `max_active_strategies`. Strategy-local failure stays strategy-local: an unrelated healthy
strategy keeps a VALID per-strategy result. The evaluator reserves budget only; it does not
model orders, market exposure, fills, PnL or reconciliation. Per-market, gross exposure, order
notional, active markets, open orders and mutation rate are persisted for later hard-kernel
enforcement and are not measured here.

On append, an allocation is rejected (CAPACITY_INVALID) if its own strategy result is rejected
or it creates a pool, global-capital or active-strategy overflow at its start or at any other
allocation start inside its validity window. Quarantine, retirement and restrictions are never
refused for capacity reasons.

## 7. Append-Only Store

One explicit caller-selected `.sqlite3` file: format `s10-strategy-lifecycle-store`, schema 1,
application id `0x53544C31` (1398033457), user_version 1, journal DELETE, synchronous FULL,
foreign_keys ON, established and verified on every initialize, append and verified-load
connection (a file whose persistent journal mode is not DELETE, such as WAL drift, fails closed
and is never converted). Tables `lifecycle_meta` (singleton) and `lifecycle_records` with exact
no-UPDATE/no-DELETE triggers; no materialized current-state table. Entry hash =
SHA-256(canonical JSON of sequence_number, record_kind, record_id, payload_sha256,
previous_entry_hash), sequence from 0, first previous hash null. Bounds: 100,000 records,
262,144 payload bytes per record, 536,870,912 aggregate.

Paths must already have an existing non-symlink parent, a `.sqlite3` suffix, no symlink and a
single hard link; no directory is created and no default path exists. Every load verifies
application/user version, exact DDL and triggers, `PRAGMA integrity_check`, the meta row, each
payload hash, strict canonical JSON, each content ID, the entry chain, and every cross-record
transition by replay; any drift fails closed and nothing is migrated. Appends are single-record
and transactional; an identical retry is idempotent, a conflicting payload for an existing ID
rejects, and a rejected append leaves the database unchanged. Statuses: STORE_INITIALIZED,
STORE_ALREADY_INITIALIZED, STORE_APPEND_COMMITTED, STORE_APPEND_IDEMPOTENT,
STORE_LOADED_VERIFIED, STORE_REJECTED.

## 8. Non-Integration And Successors

Not wired into: Alpha Factory, Hermes controlled runtime, ResearchPaperStrategyBinding,
PaperEngine, qualification, WP170, WP172, Gate C, execution gateway, deployment service or
operator cockpit. No existing store schema is migrated; no daemon or CLI is added. Successful
merge establishes only STRATEGY_LIFECYCLE_CORE_MERGED and V2_1_REPO_TRUTH_RECONCILED and makes
S10-HERMES-STRAT-01 and S10-EXEC-FEAS-01 separately draftable; S10-ALPHA-03, S10-DEPLOY-01 host
activation and DATA-03 stay parallel. First exploratory live remains impossible from this
package alone.
