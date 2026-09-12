# Machine-Readable Work-Package Specification Standard

## Status and authority

- Status: `WORKFLOW_GOVERNANCE_MANDATORY`
- Schema: `polymarket-work-package-spec@1.0.0`
- Introduced: WP159
- Runtime impact: `NO_RUNTIME_CHANGE`
- Product authority: `NONE`

This standard makes the human-readable WP execution package mechanically
checkable. It does not authorize implementation, review readiness, merge,
runtime behavior, network access, credentials, strategy, paper trading,
execution, or live trading. The human-readable prompt remains normative; the
specification is its exact machine-readable companion.

## Governance-track package topology (WP171G)

Every governed WP has:

1. `docs/wp_specs/<WP>/wp_prompt.txt`
2. `docs/wp_specs/<WP>/wp_spec.json`

`PROTECTED` also requires
`docs/wp_specs/<WP>/draftability_certificate.json`. FAST and RUNTIME do not
require an independent pre-implementation certificate. The readiness gate
derives the minimum track from `identity.risk_level` and `authority`; a prompt
may select a stricter track and may never select a weaker one.

When a certificate is required or supplied, it is never embedded in the
specification. It hashes the exact raw bytes of the prompt and specification.
There is no certificate hash in either hashed artifact, so the topology is not
self-referential. Any protected semantic prompt/spec change invalidates the
certificate and requires a new independent review. Historical valid certified
packages remain accepted as legacy PROTECTED packages.

An execution agent must not create, alter, or claim its own independent PASS
certificate. Human-controlled reviewer separation is an operator assertion;
the guard verifies the attestation, hashes, schema, and semantics but cannot
technically prove reviewer independence.

WP159 itself has one exact, one-time bootstrap exception:
`polymarket-wp-draftability-waiver@1.0.0`. The guard accepts that mode only for
WP159 in `toobigtofailbot-maker/polymarket-strategy-lab`, primary package class
`GOVERNANCE`, base branch `main`, predecessor PR 158 at the locked predecessor
head and merge SHA, Risk Level 0 or 1, zero capital, and no source-runtime,
workflow-file, dependency, network, credential, scheduler, Hermes-runtime,
strategy, paper, execution, or live authority. The waiver must state that
implementation is authorized, review readiness and merge are not authorized,
independent live-PR review remains required, and unresolved decisions are
empty. Its two digests must equal both the exact input bytes and the final
code-bound WP159 digest constants. Rehashing an altered but otherwise valid
prompt or specification cannot reuse the waiver. This exception is not a PASS
certificate and creates no generic waiver route for any other WP.

## Input and JSON policy

- Prompt maximum: 1,048,576 bytes.
- Specification maximum: 1,048,576 bytes.
- Certificate maximum: 262,144 bytes.
- JSON is strict UTF-8 without BOM.
- Duplicate keys, `NaN`, `Infinity`, `-Infinity`, and exponent overflow reject.
- Maximum parsed depth is 32 with the root at depth 1.
- Maximum string length is 16,384 Unicode code points unless narrowed below.
- Maximum array length is 1,024 unless narrowed below.
- A JSON boolean never satisfies an integer or number field.
- Unknown object keys reject.
- Declared array order is retained.

## Exact top-level schema

The specification has exactly, in order:

`schema_id`, `schema_version`, `identity`, `scope`, `authority`, `api_matrix`,
`semantic_fields`, `identity_derivations`, `state_transitions`,
`failure_precedence`, `examples`, `evidence_plan`, `successor_boundary`.

The constants are `polymarket-work-package-spec` and `1.0.0`.

### Identity

`identity` has exactly:

- `wp_id`: `^WP[1-9][0-9]*(?:[A-Z])?$`
- `title`: string[1,200]
- `repository`: exactly one `owner/name` pair matching
  `^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,99})/[A-Za-z0-9](?:[A-Za-z0-9._-]{0,99})$`
- `package_class`: `^[A-Z][A-Z0-9_]{0,127}$`
- `package_size_class`: `S`, `M`, `L`, or `XL`
- `risk_level`: integer 0..4
- `base_branch` and `suggested_branch`: string[1,200] refs without whitespace,
  controls, `..`, `~`, `^`, `:`, `?`, `*`, `[`, or backslash
- `required_predecessor`: exactly positive `pr_number`, lowercase-hex
  `head_sha` (40), and `merge_sha` (40)
- `objective`: string[1,2000]
- `capital_at_risk_usd`: finite number >= 0
- `xl_explicit_authorization`: boolean
- `xl_authorization_basis`: null for S/M/L; string[1,1000] with explicit true
  authorization for XL

### Scope and path rules

`scope` has exactly `required_changed_files`, `allowed_changed_files`,
`forbidden_prefixes`, `max_changed_files`, `exact_scope_required`,
`historical_compatibility_edits`, `rollback_surface`, and `mode_boundaries`.

Paths are case-sensitive, repository-relative, forward-slash paths. Absolute
paths, drive letters, leading `./`, empty or `.`/`..` segments, backslashes,
NUL/control characters, duplicates, and trailing slashes reject. Directory
prefixes must end `/`. Required/allowed lists contain at most 35 entries;
forbidden prefixes at most 64. Historical compatibility paths are a subset of
allowed paths. Mode boundaries have exactly unique lowercase-token `boundary`
and boolean `crossed`.

Budgets are S<=5, M<=10, L<=20. XL requires its explicit identity
authorization. `max_changed_files` may not exceed the applicable budget.
Required count may not exceed the maximum, and required is a subset of allowed.
Every path beginning `docs/wp_specs/` is reserved. It must be exactly one of the
three artifact paths for `identity.wp_id`; another WP directory and any extra
filename in the current WP directory are scope failures in both required and
allowed arrays.

### Authority

`authority` has exactly sixteen booleans:

`workflow_governance`, `local_offline_tooling`, `canonical_evidence_policy`,
`docs`, `tests`, `source_runtime`, `workflow_files`, `dependencies`, `network`,
`credentials`, `scheduler`, `hermes_runtime`, `strategy`, `paper`, `execution`,
and `live`.

Mechanical mapping:

- `docs/` requires `docs`
- `tests/` requires `tests`
- `src/` requires `source_runtime`
- `.github/workflows/` requires `workflow_files`
- `tools/` requires `local_offline_tooling`
- recognized dependency/lock basenames require `dependencies`
- `tools/hermes/`, `agent_runtime/`, and `agent_memory/` additionally require
  `hermes_runtime`
- credential-like paths additionally require `credentials`
- the exact three `docs/wp_specs/<identity.wp_id>/` artifacts additionally
  require `canonical_evidence_policy`

A path under a forbidden prefix is a scope failure before authority checks.
For schema 1.0.0, dependency/lock, built-in protected, credential-like, and
generated-artifact classification is mechanically identical to
`tools/git/diff_scope_summary.py`. When `exact_scope_required` is true, every
path that the exact-scope helper necessarily classifies as protected or
generated is a `SCOPE_POLICY_INVALID` failure before authority checks.
Unknown top-level path families are authority contradictions.

## Applicability sections and nested item schemas

`api_matrix`, `semantic_fields`, `identity_derivations`, `state_transitions`,
`failure_precedence`, `examples`, and `evidence_plan` each have exactly:

```json
{"applicable":true,"reason":"bounded explanation","items":[]}
```

The reason is string[1,1000]. True requires 1..1024 items; false requires no
items. Item schemas are:

- API: `surface`, `before`, `after`, `change_authorized`,
  `compatibility_requirement`, `authority`; surfaces are unique.
- Semantic field: `path`, `source`, `type`, `required_rule`, `mutable`,
  `identity_role`, `exclusion_reason`, `validation_rule`, `failure_category`,
  `safe_output`, `derivation_rule_id`; paths are unique dot paths.
- Derivation: `rule_id`, `target_path`, `algorithm`, `source_paths`,
  `excluded_paths`, `prefix`, `canonicalization`; IDs and targets are unique.
- Transition: `from_state`, `to_state`, `condition`, `failure_category`;
  self-transitions and duplicate pairs reject.
- Precedence: `condition_id`, `category`, `priority`; all three identities are
  unique and priority is positive.
- Example: `example_id`, `expected_valid`, `expected_error_codes`,
  `intended_fault_count`, `derivation_rule_ids`, `input`.
- Evidence: `requirement_id`, `source`, `test`, `command`, `expected_result`;
  requirement IDs match `^R[0-9]{2,4}$`, are unique, and commands have no NUL
  or newline.

Semantic sources are `CALLER`, `CONSTANT`, or `DERIVED`; identity roles are
`COMMITTED`, `EXCLUDED`, or `NONE`. EXCLUDED requires a reason and cannot be
mutable. DERIVED+COMMITTED requires a non-null existing derivation.
DERIVED+NONE may use null when its deterministic validation rule is present,
but every non-null derivation ID must exist. Non-DERIVED fields cannot carry a
derivation ID. Failure categories reference the fixed precedence table.

## Identity derivation rules

`SHA256_RAW_BYTES` has exactly one source:
`$external.wp_file_bytes` or `$external.wp_spec_file_bytes`. Exclusions are
empty, prefix is empty, canonicalization is null, and the digest covers exact
bytes.

`SHA256_CANONICAL_JSON` has at least one source. Its source, exclusion, and
target paths are dot paths relative to the same example `input`; `$external.*`
is forbidden. Its canonicalization is exactly:

```json
{"sort_keys":true,"separators":[",",":"],"ensure_ascii":false,"allow_nan":false,"encoding":"utf-8","preserve_explicit_nulls":true,"preserve_array_order":true}
```

Every source/excluded path exists. Sources are neither equal nor
ancestor/descendant. An exclusion is a strict descendant of exactly one source
and traverses objects only. A target equal to or below a source is excluded or
the rule is self-referential. The preimage is an object mapping each full
source path to its deep-copied projected value. Keys sort; array order and
explicit nulls remain. The required target is
`prefix + sha256(canonical_utf8_bytes).hexdigest()`. Tests must prove included
scalar mutation and array reorder sensitivity, excluded scalar insensitivity,
object insertion-order insensitivity, prefix behavior, and input-relative
target resolution.

Valid examples have zero faults and errors. Invalid examples have exactly one
intended fault and non-empty errors in canonical precedence order. Every
canonical-JSON rule is referenced and independently recomputed successfully by
at least one valid example, proving that every required source, exclusion, and
target path exists.

## Fixed failure order and diagnostics

The schema-1.0.0 order is exactly:

1. `FILE_READ_ERROR`
2. `JSON_PARSE_INVALID`
3. `SCHEMA_UNSUPPORTED`
4. `UNKNOWN_FIELD`
5. `FIELD_MISSING`
6. `FIELD_TYPE_INVALID`
7. `FIELD_VALUE_INVALID`
8. `CERTIFICATE_HASH_MISMATCH`
9. `DRAFTABILITY_INCOMPLETE`
10. `SCOPE_POLICY_INVALID`
11. `AUTHORITY_CONTRADICTION`
12. `SEMANTIC_CONTRADICTION`
13. `IDENTITY_DERIVATION_INVALID`
14. `FAILURE_PRECEDENCE_INVALID`
15. `EXAMPLE_TRUTH_INVALID`

Priorities are respectively 10 through 150 by tens, with condition IDs locked
by the WP159 specification. Diagnostics sort by priority, trusted canonical
field path, then code; fully equal diagnostics preserve first occurrence.
Unknown keys produce one error at the known parent and never echo the key.
Duplicate array identities report the second and later trusted identity paths.

The neutral messages and result contract are implemented by
`tools/wp/wp_spec_guard.py`. Outputs never contain raw values, file contents,
exception strings, tracebacks, environment values, or timestamps.

## PROTECTED certificate contract

A normal certificate has exactly thirteen fields:

`schema_id`, `schema_version`, `wp_id`, `reviewed_repository`,
`reviewed_base_merge_sha`, `wp_text_sha256`, `wp_spec_sha256`, `reviewer_role`,
`independence_attestation`, `result`, `covered_lenses`,
`unresolved_decisions`, `implementability_simulation`.

Constants are:

- schema `polymarket-wp-draftability-certificate@1.0.0`
- reviewer role `INDEPENDENT_DRAFTABILITY_REVIEWER`
- attestation `SEPARATE_REVIEW_CONTEXT_DECLARED`
- result and implementability simulation `PASS`

The twelve lenses, each exactly once with PASS, are:
`objective_and_class`, `public_api`, `mutability`,
`identity_and_serialization`, `state_transitions`, `batch_set_behavior`,
`error_precedence`, `invalid_input_no_echo`, `example_truth`,
`scope_compatibility`, `evidence_publication`, `successor_boundary`.
Unresolved decisions is exactly empty. Repository, WP ID, and reviewed base
match the spec. Both lowercase SHA-256 values match exact raw bytes.

The normal certificate path remains generic and is not restricted to WP159. It
is mandatory for PROTECTED and optional for FAST/RUNTIME; if supplied, it must
pass this unchanged contract.
The WP159 waiver is a separate one-time path. In addition to its exact schema
and authorization booleans, it requires the locked WP159 identity, repository,
primary package class, base, predecessor PR/head/merge, safe authority posture,
and code-bound final prompt/spec hashes. Any mismatch is the closed
`DRAFTABILITY_INCOMPLETE` diagnostic without input echo.

## Guard phase gate

For a certificate-bearing package, the canonical started-section prefix is:

`files`, `spec_json`, `spec_schema`, `spec_semantics`, `certificate_json`,
`certificate_schema`, `certificate_hashes`, `certificate_draftability`.

FAST/RUNTIME readiness without a certificate validates the bounded strict prompt
and specification before continuing with track, structure, semantic, evidence,
scope, and successor checks. Certificate-bearing packages retain the phase order
below.

File failures are usage failures (exit 2) and stop before parsing. JSON failures
exit 1 and stop the affected later phases. Spec schema defects stop semantics;
spec semantic defects stop certificate work; certificate schema defects stop
hash/draftability work. Hash and draftability checks both run once their phases
start. Exit 0 means the guard accepts the package for the authority its
certificate or constrained waiver actually grants; it is not merge authority.

## Successor boundary

`successor_boundary` has exactly `next_wp`, `next_title`, `separately_gated`,
`feature_validator_moved_to`, and `forbidden_in_this_wp`. The WP IDs use the WP
grammar; the title is string[1,300]; separately gated is true; the forbidden
list contains 1..128 unique string[1,500] entries.

WP160 owns pre-ready semantic review/publication automation, class-specific
templates, secondary workflow-doc propagation, and active historical-scope
migration. WP161 owns the manifest-entry/dataset-snapshot feature validator.
Neither successor is authorized by WP159.
