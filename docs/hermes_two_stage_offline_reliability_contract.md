# Hermes TS02 offline reliability contract

This module proves offline synthetic software mechanics only. It has no provider,
model, credential, tool-launch, strategy-manager, paper, execution or live authority.
The protected boundary groups in `docs/ai/codex/PROTECTED_PATHS.md` remain unchanged.
The injected callback is a trusted offline test/integration component, not a sandbox:
an empty capability tuple describes the protocol and does not constrain arbitrary
Python code or prove a real provider's effective tools.

## Input and handoff

The trusted caller cold-opens the local TS01 archive using unchanged
`export_trusted_research_pair(path)` and supplies that producer-owned result to
`build_handoff` or `run_offline_two_stage`. Neither Stage A nor Stage B may supply
or edit this input. TS01 verifies actual archive membership; TS02 verifies consistency
of the supplied export, not independent archive authentication. Both rely on the
operator's local evidence custody; no upstream signature is claimed.

Inputs are explicit keyword arguments: `stage_a_text`, `trusted_pair`, `cutoff`,
`expected_request_id`, `strategy_parameter_names`, and optional `max_sources=8`.
`build_handoff` rejects invalid input with sanitized `ValueError` or a parsing/type
exception; the run API converts any admission failure to `SOURCE_UNTRUSTED`, before
calling Stage B. Callers should use the run API for sanitized boundary reporting.

Stage A is nonempty UNTRUSTED UTF-8 text, at most 20,000 bytes. Its URLs are never
sources. The separate export must be ADMITTED / LOCAL_PRODUCER_WITNESS. TS02 checks
two distinct selected occurrences, every raw hash/byte length, reconstructed canonical
receipt digest, ordered receive clocks, first Gamma token, market and CLOB condition
linkage. The supported offline subset bounds each raw body and canonical receipt
to 65,536 bytes, attempts to 12, parameters to 64, and max_sources to 1–8.
This can reject a larger otherwise-valid TS01 export; no truncation or source promotion.

Clocks require RFC3339 shape with T, optional 1–6 fractional digits, and Z or ±HH:MM.
Comparisons use parsed UTC values. Excess precision and fractional offsets reject;
no silent datetime rounding is used to admit evidence after cutoff.

The deterministic handoff contains source IDs, hashes, receipt digest, receive clocks,
cutoff, request/parameter/schema bindings, content-derived run and A/B stage IDs, and
`UNTRUSTED_STAGE_A_TEXT`. Its canonical digest binds the complete text. The callback
receives a detached JSON copy, native machine-generated strategy output contract,
exact request ID, immutable parameter-name tuple and `tool_capabilities=()`.

## Output and durable replay

`run_offline_two_stage(output_dir, stage_b=callback, **inputs)` uses one caller-selected
ignored/local output directory. Never point it at tracked or shared provider state.
The module neither chooses source paths from model text nor creates a provider/process.
It bounds returned bytes at 65,536, calls unchanged `validate_research_draft` with
strategy mode and the expected request/parameter names, and calls unchanged
`check_strategy_assessment_consistency`. There is no reprompt or automatic retry.

Before callback dispatch, an exclusive `<run_id>.reserved` marker and A/handoff records
are flushed with file fsync; POSIX parent directory entries are also fsynced. Windows
uses exclusive creation and file fsync without a POSIX directory-fsync guarantee.
Four canonical immutable stage files (A, handoff, B outcome, terminal) form a SHA256
predecessor chain rooted in the reservation. They store bounded source metadata and
hashes, never Stage A prose, raw TS01 bodies, raw model output, or fabricated usage.
The callback receives a synthetic protocol only; its returned draft is never exported
as a native receipt, accepted strategy decision or risk instruction.

`verify_offline_run(output_dir, run_id)` cold-verifies canonical records, reservation
identity, exact file set, chain and terminal consistency. It never writes or dispatches.
Once reserved, repeated/concurrent calls never dispatch again. A surviving marker or
run directory blocks redispatch after partial writes, crashes or individual deletion.
Incomplete/corrupt state returns `INCOMPLETE_BLOCKED`, without cleanup or auto-resume.
An interrupted callback exception becomes `INTERRUPTED_BLOCKED`; process interruption
can leave an incomplete journal. Retain both tombstones; deleting the whole journal
destroys local replay memory. Hashes detect inconsistency, not a malicious operator
rewriting all local evidence. Journal custody is the same local trust assumption as TS01.

Closed terminals: `OFFLINE_SYNTHETIC_VALIDATED`, `INVALID_OUTPUT`, `SOURCE_UNTRUSTED`,
`INTERRUPTED_BLOCKED`, `INCOMPLETE_BLOCKED`. Every terminal remains SYNTHETIC_ONLY /
provider_toolfree=UNPROVEN. No cost, usage, actual provider success, capital, or
canonical StrategyAssessment is asserted. Actual Stage B transport and empirical
tool-free proof require a separately authorized future package.

## Validation matrix

R001: valid cold synthetic TS01 result; receipt/hash/occurrence/clock corruption,
missing archive, malformed receipt, naive/late/unsupported-precision cutoff and oversized
Stage A rejection. R002: native valid full draft; malformed/wrong-encoding/oversized/null
output, missing/false/wrong-type authority flags, wrong request, missing sources,
unknown adaptation parameter, unsafe case-insensitive wording and inconsistent action.
R003: pre-dispatch marker, cold replay, record mutation/deletion/partial bytes, missing
marker with surviving directory, interrupted callback and concurrent second call.
R004: synthetic-only terminal, no usage/cost/native promotion, no text in journal,
and callback mutation cannot change expected request identity. R005: unchanged Hermes,
strategy/context and public TS01 regression families; exact historical guard additions
accept while a third similarly named module rejects. R006: native exact-scope readiness,
artifact/whitespace/compatibility checks and one stable-head full local suite, recorded
in the external evidence ZIP. None of these validations authorizes publication or CI.
