# Result Object And Output Invariant Standard

## Status

- Standard version: V1
- Introduced in: WP88
- Applies to: all future result/report/loader/validator WPs

## Purpose

Prevent the class of WP87 failures where:

- a manual serializer silently omitted `advisory_label`;
- a "full result scan" did not prove every public field was scanned;
- invalid output was inspected with a different code path than valid output.

## 1. Result Object Field-Coverage Gate

Every WP that introduces or returns a public result object must include a field-coverage gate.

### 1.1 Required standard

For every public result object introduced or returned by a WP:

1. Enumerate every public field by name.
2. Classify each field as `scanned` / `exempt` / `forbidden`.
3. Test that every public field appears in recursive output-safety scanning.
4. Fail the test if a new public field is added without classification.
5. Scan invalid result objects, not only valid result objects.

### 1.2 Required test pattern

For dataclass result objects, the following pattern (or equivalent) is required:

```python
from dataclasses import fields

def test_result_serializer_covers_all_public_fields():
    result = make_result()
    serialized = _result_to_dict(result)
    assert {f.name for f in fields(type(result))} <= set(serialized)
```

If direct recursive scanning of dataclass objects is available, prefer it over a manual serializer. See Section 2.

### 1.3 Exempt fields

A field may be classified `exempt` only if it is a type that cannot contain forbidden output (e.g., a boolean flag, an int count, a frozen tuple of verified-safe strings). The exemption must be documented with a reason.

### 1.4 Scope

This gate applies to every WP that:

- introduces a new dataclass, TypedDict, namedtuple, or dict-returning function;
- returns a result or report object;
- implements a loader, validator, or report generator;
- adds a new field to an existing result object.

## 2. Manual Serializer Losslessness Rule

Manual serializers are **forbidden** unless they prove losslessness.

### 2.1 Allowed forms

| Form | Requirement |
|---|---|
| `dataclasses.asdict(result)` | No extra requirement — stdlib covers all fields |
| Direct recursive scan of dataclass object | No extra requirement |
| Manual serializer with field-coverage test | Required: test proves every public field is represented |
| Manual serializer with explicit exempt-field list | Required: each exempt field documented with reason |

### 2.2 Forbidden forms

| Form | Reason forbidden |
|---|---|
| Manual `{key: result.key}` dict without field-coverage test | Silently omits newly added fields |
| Manual serializer that omits advisory labels | advisory_label must be scanned |
| Manual serializer that omits notices, warnings, metadata, status fields, errors, normalized records, summaries, or deferred items | These are output surfaces that must be scanned |

### 2.3 Required documentation phrase

Any WP that uses a manual serializer must include this phrase in its docs or inline comment:

> A hand-built dictionary is not a full output-surface scan unless a field-coverage test
> proves it covers every public field.

## 3. Invalid-Output No-Echo Rule

Every result/report/loader/validator WP with invalid input must require that the output surface is scanned for invalid input echo.

### 3.1 Required checks for invalid input

1. Invalid input is rejected (validation error, not an empty success).
2. `normalized_record` or equivalent safe output is empty or minimal for invalid/malformed records.
3. Errors do not echo unsafe keys or values from the invalid input.
4. Warnings do not echo unsafe keys or values from the invalid input.
5. Advisory labels and notices do not echo unsafe keys or values.
6. Metadata or free-form mappings from the input do not pass through unmodified.
7. The **full public result object** is scanned recursively for forbidden terms — not only the error message field.
8. Static forbidden fixture content does not appear in expected output assertions.

### 3.2 Required unsafe fixture classes

Every validator/loader WP must include fixtures from these classes:

| Class | Example |
|---|---|
| Forbidden status values | A status value the validator must reject |
| Forbidden metadata keys | A key that must not pass through |
| Nested forbidden metadata values | A value nested inside a mapping |
| Malformed JSON/input (if applicable) | Intentionally broken syntax |
| Unknown enum or status values | A value outside the allowed enum |
| Mismatch/conflict cases | Combinations that violate gate precedence |

### 3.3 Recursive scan requirement

The test must scan the **entire result object**, not only the `errors` field. This means:

```python
def _recursive_text(obj) -> str:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (list, tuple)):
        return " ".join(_recursive_text(x) for x in obj)
    if isinstance(obj, dict):
        return " ".join(_recursive_text(v) for v in obj.values())
    return str(obj)

def test_invalid_input_does_not_echo_forbidden_term():
    result = loader("path/to/fixture_with_forbidden_term.json")
    full_text = _recursive_text(result)  # scan the whole result object
    assert "FORBIDDEN_TERM" not in full_text
```

Scanning only `result.errors` is insufficient because echo can appear in `warnings`, `advisory_label`, `normalized_record`, `metadata`, or any other field.

## 4. Field-Coverage Gate For WP Template

Every future result/report/loader/validator WP must include in its WP definition:

```
## Field-Coverage Gate

For each public result object:
- [ ] All public fields enumerated by name.
- [ ] Each field classified: scanned / exempt (with reason) / forbidden.
- [ ] Test: {f.name for f in fields(ResultType)} <= set(serialized).
- [ ] Invalid result objects scanned, not only valid result objects.
- [ ] Manual serializer (if used) has field-coverage test or is replaced by dataclasses.asdict.
```

## 5. Cross-References

- `docs/ai/codex/EVIDENCE_ARCHITECTURE.md` — evidence surface model
- `docs/ai/codex/FOLLOWUP_PROMPT_STANDARD.md` — root-cause-first follow-up prompt
- `docs/ai/codex/VALIDATION_MATRIX.md` — validation requirements by package class
- `docs/ai/codex/NEGATIVE_TEST_MATRIX_POLICY.md` — negative test matrix policy
- `docs/ai/codex/WP_DRAFTING_STANDARD.md` — WP drafting standard
