"""Focused and adversarial tests for the WP specification guard."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
import math
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
GUARD_PATH = ROOT / "tools" / "wp" / "wp_spec_guard.py"
PACKAGE = ROOT / "docs" / "wp_specs" / "WP159"
SPEC_PATH = PACKAGE / "wp_spec.json"
WP_PATH = PACKAGE / "wp_prompt.txt"
CERT_PATH = PACKAGE / "draftability_certificate.json"

MODULE_SPEC = importlib.util.spec_from_file_location("wp_spec_guard", GUARD_PATH)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
guard = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(guard)


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _waiver() -> dict:
    return json.loads(CERT_PATH.read_text(encoding="utf-8"))


def _codes(errors) -> list[str]:
    return [error["code"] for error in errors]


def _write_package(
    tmp_path: pathlib.Path,
    *,
    spec=None,
    cert=None,
    wp_bytes: bytes | None = None,
):
    wp = tmp_path / "wp.txt"
    spec_file = tmp_path / "spec.json"
    cert_file = tmp_path / "certificate.json"
    wp.write_bytes(WP_PATH.read_bytes() if wp_bytes is None else wp_bytes)
    spec_bytes = json.dumps(
        spec if spec is not None else _spec(),
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")
    spec_file.write_bytes(spec_bytes)
    certificate = copy.deepcopy(cert if cert is not None else _waiver())
    certificate["wp_text_sha256"] = hashlib.sha256(wp.read_bytes()).hexdigest()
    certificate["wp_spec_sha256"] = hashlib.sha256(spec_bytes).hexdigest()
    cert_file.write_text(json.dumps(certificate), encoding="utf-8")
    return wp, spec_file, cert_file


def _run_package(wp, spec_file, cert_file):
    result = subprocess.run(
        [
            sys.executable,
            str(GUARD_PATH),
            "--wp",
            str(wp),
            "--spec",
            str(spec_file),
            "--certificate",
            str(cert_file),
            "--format",
            "json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    return result, json.loads(result.stdout)


def _normal_certificate(document: dict) -> dict:
    identity = document["identity"]
    return {
        "schema_id": "polymarket-wp-draftability-certificate",
        "schema_version": "1.0.0",
        "wp_id": identity["wp_id"],
        "reviewed_repository": identity["repository"],
        "reviewed_base_merge_sha": identity["required_predecessor"]["merge_sha"],
        "wp_text_sha256": "0" * 64,
        "wp_spec_sha256": "0" * 64,
        "reviewer_role": "INDEPENDENT_DRAFTABILITY_REVIEWER",
        "independence_attestation": "SEPARATE_REVIEW_CONTEXT_DECLARED",
        "result": "PASS",
        "covered_lenses": [
            {"lens": lens, "result": "PASS"} for lens in guard.LENS_ORDER
        ],
        "unresolved_decisions": [],
        "implementability_simulation": "PASS",
    }


def _generic_normal_spec(wp_id: str = "WP777") -> dict:
    document = _spec()
    document["identity"]["wp_id"] = wp_id
    old_prefix = "docs/wp_specs/WP159/"
    new_prefix = f"docs/wp_specs/{wp_id}/"
    for field in ("required_changed_files", "allowed_changed_files"):
        document["scope"][field] = [
            new_prefix + path.removeprefix(old_prefix)
            if path.startswith(old_prefix)
            else path
            for path in document["scope"][field]
        ]
    return document


def test_exact_v6_package_and_waiver_pass():
    result = subprocess.run(
        [
            sys.executable,
            str(GUARD_PATH),
            "--wp",
            str(WP_PATH),
            "--spec",
            str(SPEC_PATH),
            "--certificate",
            str(CERT_PATH),
            "--format",
            "json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    parsed = json.loads(result.stdout)
    assert result.returncode == 0
    assert parsed["status"] == "PASS"
    assert parsed["errors"] == []
    assert parsed["wp_text_sha256"] == (
        "7dfd1e826b688873c3303dcf89d13522d82620840b17f1a40812c3ceb2c74911"
    )
    assert parsed["wp_spec_sha256"] == (
        "2300bd295bdd0f679857d2aec0d007d296ef05421095e77e69937b457ad094b3"
    )
    assert guard.WP159_WAIVER_WP_SHA256 == parsed["wp_text_sha256"]
    assert guard.WP159_WAIVER_SPEC_SHA256 == parsed["wp_spec_sha256"]


def test_import_api_signatures_are_exact():
    assert str(inspect.signature(guard.validate_spec_document)) == (
        "(document: 'object') -> "
        "'tuple[dict[str, object] | None, tuple[dict[str, str], ...]]'"
    )
    assert str(inspect.signature(guard.read_and_validate_spec_scope)) == (
        "(path: 'str | pathlib.Path') -> "
        "'tuple[dict[str, object] | None, tuple[dict[str, str], ...]]'"
    )


def test_validate_spec_returns_deep_copy():
    source = _spec()
    validated, errors = guard.validate_spec_document(source)
    assert errors == ()
    assert validated == source
    assert validated is not source
    validated["scope"]["required_changed_files"].append("docs/not-source.md")
    assert "docs/not-source.md" not in source["scope"]["required_changed_files"]


@pytest.mark.parametrize(
    "wp_id",
    ["WP159", "WP168G", "WP175N", "S10-HERMES-CTX-01", "S10-WALLET-01", "S10-GATE-H1"],
)
def test_package_id_grammar_accepts_legacy_wp_and_s10_ids_through_real_validation(wp_id):
    validated, errors = guard.validate_spec_document(_generic_normal_spec(wp_id))
    assert errors == ()
    assert validated is not None
    assert validated["identity"]["wp_id"] == wp_id


@pytest.mark.parametrize(
    "wp_id",
    [
        "S10-",
        "S10--CTX",
        "S10-hermes-CTX-01",
        "S10-HERMES_CTX-01",
        "S11-HERMES-CTX-01",
        "S10/HERMES/CTX/01",
        " S10-HERMES-CTX-01",
        "S10-HERMES-CTX-01 ",
    ],
)
def test_package_id_grammar_rejects_malformed_ids_through_real_validation(wp_id):
    validated, errors = guard.validate_spec_document(_generic_normal_spec(wp_id))
    assert validated is None
    assert "FIELD_VALUE_INVALID" in _codes(errors)


def test_scope_return_has_exact_fields_and_tuples():
    scope, errors = guard.read_and_validate_spec_scope(SPEC_PATH)
    assert errors == ()
    assert list(scope) == [
        "schema_version",
        "package_class",
        "required_changed_files",
        "allowed_changed_files",
        "forbidden_prefixes",
        "max_changed_files",
        "exact_scope_required",
        "authority",
    ]
    assert isinstance(scope["required_changed_files"], tuple)
    assert isinstance(scope["allowed_changed_files"], tuple)
    assert isinstance(scope["forbidden_prefixes"], tuple)


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (lambda d: d.update(extra="x"), "UNKNOWN_FIELD"),
        (lambda d: d.pop("identity"), "FIELD_MISSING"),
        (lambda d: d.update(schema_version="2.0.0"), "SCHEMA_UNSUPPORTED"),
        (
            lambda d: d["identity"].update(risk_level=True),
            "FIELD_TYPE_INVALID",
        ),
        (
            lambda d: d["identity"].update(
                package_size_class="L",
                xl_explicit_authorization=False,
                xl_authorization_basis=None,
            ),
            "SCOPE_POLICY_INVALID",
        ),
        (
            lambda d: d["scope"]["allowed_changed_files"].append("README.md"),
            "AUTHORITY_CONTRADICTION",
        ),
        (
            lambda d: d["scope"]["allowed_changed_files"].append("../x"),
            "FIELD_VALUE_INVALID",
        ),
        (
            lambda d: d["scope"]["forbidden_prefixes"].append("docs/"),
            "SCOPE_POLICY_INVALID",
        ),
        (
            lambda d: d["failure_precedence"]["items"].reverse(),
            "FAILURE_PRECEDENCE_INVALID",
        ),
        (
            lambda d: d["state_transitions"]["items"][0].update(
                to_state="LOCAL_DRAFT"
            ),
            "SEMANTIC_CONTRADICTION",
        ),
    ],
)
def test_negative_matrix_returns_closed_category(mutation, expected_code):
    document = _spec()
    mutation(document)
    validated, errors = guard.validate_spec_document(document)
    assert validated is None
    assert expected_code in _codes(errors)
    assert all(set(error) == {"code", "field_path", "message"} for error in errors)


@pytest.mark.parametrize(
    "bad_path",
    [
        "/absolute",
        "C:/drive",
        "./leading",
        "a//b",
        "a/./b",
        "a/../b",
        "a\\b",
        "trailing/",
        "nul\x00value",
    ],
)
def test_path_grammar_rejects_all_ambiguous_forms(bad_path):
    document = _spec()
    document["scope"]["required_changed_files"][0] = bad_path
    document["scope"]["allowed_changed_files"][0] = bad_path
    validated, errors = guard.validate_spec_document(document)
    assert validated is None
    assert "FIELD_VALUE_INVALID" in _codes(errors)


def test_duplicate_path_rejects_at_second_location():
    document = _spec()
    document["scope"]["allowed_changed_files"].append(
        document["scope"]["allowed_changed_files"][0]
    )
    _, errors = guard.validate_spec_document(document)
    assert any(
        error["field_path"].endswith("allowed_changed_files[23]")
        for error in errors
    )


def test_cyclic_caller_document_is_sanitized():
    document = _spec()
    document["cycle"] = document
    validated, errors = guard.validate_spec_document(document)
    assert validated is None
    assert errors == (
        {
            "code": "FIELD_VALUE_INVALID",
            "field_path": "spec",
            "message": "field value is invalid",
        },
    )


@pytest.mark.parametrize("number", [math.nan, math.inf, -math.inf])
def test_non_finite_caller_number_is_sanitized(number):
    document = _spec()
    document["identity"]["capital_at_risk_usd"] = number
    validated, errors = guard.validate_spec_document(document)
    assert validated is None
    assert "FIELD_VALUE_INVALID" in _codes(errors)


def test_strict_json_rejects_duplicate_key_bom_nan_and_overflow(tmp_path):
    bad_documents = [
        b'{"schema_id":"a","schema_id":"b"}',
        b"\xef\xbb\xbf{}",
        b'{"x":NaN}',
        b'{"x":1e9999}',
    ]
    for index, raw in enumerate(bad_documents):
        path = tmp_path / f"bad-{index}.json"
        path.write_bytes(raw)
        scope, errors = guard.read_and_validate_spec_scope(path)
        assert scope is None
        assert _codes(errors) == ["JSON_PARSE_INVALID"]


def test_depth_and_array_bounds_reject_without_raise(tmp_path):
    path = tmp_path / "deep.json"
    value = "leaf"
    for _ in range(33):
        value = [value]
    path.write_text(json.dumps(value), encoding="utf-8")
    scope, errors = guard.read_and_validate_spec_scope(path)
    assert scope is None
    assert _codes(errors) == ["JSON_PARSE_INVALID"]


def test_unknown_key_never_echoed():
    document = _spec()
    secret = "private-value-that-must-not-appear"
    document["identity"][secret] = secret
    _, errors = guard.validate_spec_document(document)
    rendered = json.dumps(errors)
    assert secret not in rendered
    assert _codes(errors).count("UNKNOWN_FIELD") == 1
    assert errors[0]["field_path"] == "spec.identity"


def test_error_order_uses_closed_precedence_then_path():
    document = _spec()
    document["identity"]["risk_level"] = "bad"
    document["scope"]["exact_scope_required"] = "bad"
    document["identity"]["extra"] = "bad"
    _, errors = guard.validate_spec_document(document)
    assert _codes(errors) == [
        "UNKNOWN_FIELD",
        "FIELD_TYPE_INVALID",
        "FIELD_TYPE_INVALID",
    ]
    assert errors[1]["field_path"] < errors[2]["field_path"]


def test_raw_derivation_contract_is_fail_closed():
    document = _spec()
    document["identity_derivations"]["items"][0]["prefix"] = "x"
    _, errors = guard.validate_spec_document(document)
    assert "IDENTITY_DERIVATION_INVALID" in _codes(errors)


def _canonical_rule_and_example():
    document = _spec()
    source = {"a": 1, "arr": [1, 2], "excluded": "first"}
    rule = {
        "rule_id": "generic_example_digest",
        "target_path": "result.digest",
        "algorithm": "SHA256_CANONICAL_JSON",
        "source_paths": ["payload"],
        "excluded_paths": ["payload.excluded"],
        "prefix": "example:sha256:",
        "canonicalization": copy.deepcopy(guard.CANONICALIZATION),
    }
    input_value = {"payload": source, "result": {"digest": ""}}
    input_value["result"]["digest"] = guard._canonical_derived_value(
        rule, input_value
    )
    document["identity_derivations"]["items"].append(rule)
    document["examples"] = {
        "applicable": True,
        "reason": "generic derivation proof",
        "items": [
            {
                "example_id": "generic-valid",
                "expected_valid": True,
                "expected_error_codes": [],
                "intended_fault_count": 0,
                "derivation_rule_ids": ["generic_example_digest"],
                "input": input_value,
            }
        ],
    }
    return document


def test_generic_canonical_example_recomputes_and_mutations_are_truthful():
    document = _canonical_rule_and_example()
    validated, errors = guard.validate_spec_document(document)
    assert validated is not None and errors == ()
    rule = document["identity_derivations"]["items"][-1]
    original = document["examples"]["items"][0]["input"]
    original_digest = guard._canonical_derived_value(rule, original)

    included = copy.deepcopy(original)
    included["payload"]["a"] = 2
    assert guard._canonical_derived_value(rule, included) != original_digest

    excluded = copy.deepcopy(original)
    excluded["payload"]["excluded"] = "second"
    assert guard._canonical_derived_value(rule, excluded) == original_digest

    reordered = copy.deepcopy(original)
    reordered["payload"]["arr"].reverse()
    assert guard._canonical_derived_value(rule, reordered) != original_digest

    insertion_order = {
        "payload": {
            "excluded": original["payload"]["excluded"],
            "arr": original["payload"]["arr"],
            "a": original["payload"]["a"],
        },
        "result": original["result"],
    }
    assert guard._canonical_derived_value(rule, insertion_order) == original_digest

    prefixed = copy.deepcopy(rule)
    prefixed["prefix"] = "other:"
    assert guard._canonical_derived_value(prefixed, original).endswith(
        original_digest.rsplit(":", 1)[-1]
    )


def test_generic_example_mismatch_is_example_truth_invalid():
    document = _canonical_rule_and_example()
    document["examples"]["items"][0]["input"]["payload"]["a"] = 9
    _, errors = guard.validate_spec_document(document)
    assert "EXAMPLE_TRUTH_INVALID" in _codes(errors)


@pytest.mark.parametrize(
    "artifact_path",
    [
        "docs/wp_specs/WP158/wp_prompt.txt",
        "docs/wp_specs/WP158/wp_spec.json",
        "docs/wp_specs/WP158/draftability_certificate.json",
        "docs/wp_specs/WP159/extra.json",
    ],
)
def test_cross_wp_and_extra_package_artifacts_are_reserved(artifact_path):
    document = _spec()
    document["scope"]["required_changed_files"][0] = artifact_path
    document["scope"]["allowed_changed_files"][0] = artifact_path
    validated, errors = guard.validate_spec_document(document)
    assert validated is None
    assert "SCOPE_POLICY_INVALID" in _codes(errors)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["semantic_fields"]["items"][10].update(
            derivation_rule_id="missing_rule"
        ),
        lambda d: d["semantic_fields"]["items"][0].update(
            derivation_rule_id="wp_text_raw_sha256"
        ),
        lambda d: d["semantic_fields"]["items"][6].update(
            derivation_rule_id="wp_text_raw_sha256"
        ),
    ],
)
def test_semantic_derivation_references_are_closed(mutation):
    document = _spec()
    mutation(document)
    _, errors = guard.validate_spec_document(document)
    assert "SEMANTIC_CONTRADICTION" in _codes(errors)


def test_derived_committed_requires_non_null_existing_derivation():
    document = _spec()
    committed = next(
        item
        for item in document["semantic_fields"]["items"]
        if item["source"] == "DERIVED" and item["identity_role"] == "COMMITTED"
    )
    committed["derivation_rule_id"] = None
    _, errors = guard.validate_spec_document(document)
    assert "SEMANTIC_CONTRADICTION" in _codes(errors)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["identity_derivations"]["items"][-1].update(
            source_paths=["$external.wp_file_bytes"]
        ),
        lambda d: d["identity_derivations"]["items"][-1].update(source_paths=[]),
    ],
)
def test_canonical_derivation_paths_are_input_relative_and_nonempty(mutation):
    document = _canonical_rule_and_example()
    mutation(document)
    _, errors = guard.validate_spec_document(document)
    assert "IDENTITY_DERIVATION_INVALID" in _codes(errors)


def test_canonical_rule_requires_valid_example_coverage():
    document = _canonical_rule_and_example()
    document["examples"]["items"][0]["derivation_rule_ids"] = []
    _, errors = guard.validate_spec_document(document)
    assert "EXAMPLE_TRUTH_INVALID" in _codes(errors)


@pytest.mark.parametrize("missing_kind", ["source", "exclusion", "target"])
def test_canonical_example_requires_every_declared_path(missing_kind):
    document = _canonical_rule_and_example()
    rule = document["identity_derivations"]["items"][-1]
    if missing_kind == "source":
        rule["source_paths"] = ["missing"]
        rule["excluded_paths"] = []
    elif missing_kind == "exclusion":
        rule["excluded_paths"] = ["payload.missing"]
    else:
        rule["target_path"] = "result.missing"
    _, errors = guard.validate_spec_document(document)
    assert "EXAMPLE_TRUTH_INVALID" in _codes(errors)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(_replace_with=_generic_normal_spec("WP160")),
        lambda d: d["identity"].update(repository="other/repository"),
        lambda d: d["identity"].update(package_class="OTHER_GOVERNANCE"),
        lambda d: d["identity"].update(base_branch="develop"),
        lambda d: d["identity"]["required_predecessor"].update(pr_number=157),
        lambda d: d["identity"]["required_predecessor"].update(
            head_sha="1" * 40
        ),
        lambda d: d["identity"]["required_predecessor"].update(
            merge_sha="2" * 40
        ),
    ],
)
def test_waiver_is_exactly_wp159_identity_bound(tmp_path, mutation):
    document = _spec()
    mutation(document)
    if "_replace_with" in document:
        document = document.pop("_replace_with")
    certificate = _waiver()
    certificate["wp_id"] = document["identity"]["wp_id"]
    wp, spec_file, cert_file = _write_package(
        tmp_path, spec=document, cert=certificate
    )
    result, parsed = _run_package(wp, spec_file, cert_file)
    assert result.returncode == 1
    assert "DRAFTABILITY_INCOMPLETE" in _codes(parsed["errors"])


def test_waiver_rejects_rehashed_one_byte_prompt_change_without_echo(tmp_path):
    changed = WP_PATH.read_bytes() + b"\n"
    wp, spec_file, cert_file = _write_package(tmp_path, wp_bytes=changed)
    result, parsed = _run_package(wp, spec_file, cert_file)
    assert result.returncode == 1
    assert _codes(parsed["errors"]) == ["DRAFTABILITY_INCOMPLETE"]
    assert "V6 CORRECTED" not in result.stdout


def test_waiver_rejects_rehashed_semantically_valid_spec_change(tmp_path):
    document = _spec()
    document["identity"]["objective"] += " "
    wp, spec_file, cert_file = _write_package(tmp_path, spec=document)
    result, parsed = _run_package(wp, spec_file, cert_file)
    assert result.returncode == 1
    assert _codes(parsed["errors"]) == ["DRAFTABILITY_INCOMPLETE"]


def test_waiver_rejects_risk_level_two(tmp_path):
    document = _spec()
    document["identity"]["risk_level"] = 2
    wp, spec_file, cert_file = _write_package(tmp_path, spec=document)
    result = subprocess.run(
        [
            sys.executable,
            str(GUARD_PATH),
            "--wp",
            str(wp),
            "--spec",
            str(spec_file),
            "--certificate",
            str(cert_file),
            "--format",
            "json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "DRAFTABILITY_INCOMPLETE" in _codes(json.loads(result.stdout)["errors"])


def test_valid_generic_normal_certificate_passes(tmp_path):
    document = _generic_normal_spec()
    certificate = _normal_certificate(document)
    wp, spec_file, cert_file = _write_package(
        tmp_path, spec=document, cert=certificate
    )
    result, parsed = _run_package(wp, spec_file, cert_file)
    assert result.returncode == 0
    assert parsed["status"] == "PASS"
    assert parsed["wp_id"] == "WP777"
    assert parsed["errors"] == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c: c.update(wp_id="WP778"),
        lambda c: c.update(reviewed_repository="other/repository"),
        lambda c: c.update(reviewed_base_merge_sha="3" * 40),
        lambda c: c.update(reviewer_role="EXECUTION_AGENT"),
        lambda c: c.update(independence_attestation="SAME_CONTEXT"),
        lambda c: c.update(result="FAIL"),
        lambda c: c["covered_lenses"].pop(),
        lambda c: c["covered_lenses"].append(copy.deepcopy(c["covered_lenses"][0])),
        lambda c: c["covered_lenses"].append(
            {"lens": "extra_lens", "result": "PASS"}
        ),
        lambda c: c["covered_lenses"].reverse(),
        lambda c: c["covered_lenses"][0].update(result="FAIL"),
        lambda c: c["unresolved_decisions"].append("unresolved"),
        lambda c: c.update(implementability_simulation="FAIL"),
    ],
)
def test_normal_certificate_draftability_negative_matrix(tmp_path, mutation):
    document = _generic_normal_spec()
    certificate = _normal_certificate(document)
    mutation(certificate)
    wp, spec_file, cert_file = _write_package(
        tmp_path, spec=document, cert=certificate
    )
    result, parsed = _run_package(wp, spec_file, cert_file)
    assert result.returncode == 1
    assert "DRAFTABILITY_INCOMPLETE" in _codes(parsed["errors"])


def test_normal_certificate_missing_or_extra_lens_wrapper_rejects(tmp_path):
    document = _generic_normal_spec()
    for mutate in (
        lambda c: c.pop("covered_lenses"),
        lambda c: c.update(extra="forbidden"),
    ):
        certificate = _normal_certificate(document)
        mutate(certificate)
        wp, spec_file, cert_file = _write_package(
            tmp_path, spec=document, cert=certificate
        )
        result, parsed = _run_package(wp, spec_file, cert_file)
        assert result.returncode == 1
        assert set(_codes(parsed["errors"])).intersection(
            {"FIELD_MISSING", "UNKNOWN_FIELD"}
        )


def test_normal_certificate_hash_and_draftability_errors_are_canonical(tmp_path):
    document = _generic_normal_spec()
    certificate = _normal_certificate(document)
    certificate["result"] = "FAIL"
    wp, spec_file, cert_file = _write_package(
        tmp_path, spec=document, cert=certificate
    )
    rewritten = json.loads(cert_file.read_text(encoding="utf-8"))
    rewritten["wp_text_sha256"] = "0" * 64
    cert_file.write_text(json.dumps(rewritten), encoding="utf-8")
    result, parsed = _run_package(wp, spec_file, cert_file)
    assert result.returncode == 1
    assert _codes(parsed["errors"]) == [
        "CERTIFICATE_HASH_MISMATCH",
        "DRAFTABILITY_INCOMPLETE",
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("implementation_authorized", False),
        ("ready_for_review_authorized", True),
        ("merge_authorized", True),
        ("independent_live_pr_review_required", False),
    ],
)
def test_waiver_cannot_expand_authority(tmp_path, field, value):
    certificate = _waiver()
    certificate[field] = value
    wp, spec_file, cert_file = _write_package(tmp_path, cert=certificate)
    result = subprocess.run(
        [
            sys.executable,
            str(GUARD_PATH),
            "--wp",
            str(wp),
            "--spec",
            str(spec_file),
            "--certificate",
            str(cert_file),
            "--format",
            "json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "DRAFTABILITY_INCOMPLETE" in _codes(json.loads(result.stdout)["errors"])


def test_hash_mismatch_and_draftability_defect_both_report(tmp_path):
    certificate = _waiver()
    certificate["wp_text_sha256"] = "0" * 64
    certificate["merge_authorized"] = True
    wp, spec_file, cert_file = _write_package(tmp_path, cert=certificate)
    certificate = json.loads(cert_file.read_text(encoding="utf-8"))
    certificate["wp_text_sha256"] = "0" * 64
    cert_file.write_text(json.dumps(certificate), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(GUARD_PATH),
            "--wp",
            str(wp),
            "--spec",
            str(spec_file),
            "--certificate",
            str(cert_file),
            "--format",
            "json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    codes = _codes(json.loads(result.stdout)["errors"])
    assert codes == [
        "CERTIFICATE_HASH_MISMATCH",
        "DRAFTABILITY_INCOMPLETE",
        "DRAFTABILITY_INCOMPLETE",
    ]


def test_usage_error_is_neutral_and_exit_two():
    secret = "do-not-echo-this-format"
    result = subprocess.run(
        [sys.executable, str(GUARD_PATH), "--format", secret],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert secret not in result.stdout
    assert secret not in result.stderr
    assert "USAGE_ERROR" in result.stdout


def test_file_error_is_neutral_and_checked_sections_are_gated(tmp_path):
    missing = tmp_path / "private-name"
    result = subprocess.run(
        [
            sys.executable,
            str(GUARD_PATH),
            "--wp",
            str(missing),
            "--spec",
            str(missing),
            "--certificate",
            str(missing),
            "--format",
            "json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    parsed = json.loads(result.stdout)
    assert result.returncode == 2
    assert parsed["checked_sections"] == ["files"]
    assert str(missing) not in result.stdout
    assert _codes(parsed["errors"]) == [
        "FILE_READ_ERROR",
        "FILE_READ_ERROR",
        "FILE_READ_ERROR",
    ]


def test_text_and_json_serialization_are_deterministic_single_newline():
    result = guard._result("PASS", ["files"], [])
    text_one = guard.render_text(result)
    text_two = guard.render_text(result)
    json_one = guard.render_json(result)
    assert text_one == text_two
    assert text_one.endswith("\n") and not text_one.endswith("\n\n")
    assert json_one.endswith("\n") and not json_one.endswith("\n\n")
    assert list(json.loads(json_one)) == [
        "schema_id",
        "schema_version",
        "status",
        "wp_id",
        "wp_text_sha256",
        "wp_spec_sha256",
        "checked_sections",
        "errors",
    ]


def test_import_has_no_cli_side_effect(capsys):
    assert capsys.readouterr().out == ""


def test_source_has_no_network_subprocess_environment_or_product_imports():
    source = GUARD_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "import subprocess",
        "import requests",
        "import socket",
        "os.environ",
        "getenv(",
        "from src",
        "import src",
    ):
        assert forbidden not in source


def _authority_errors_at(document: dict, field_path: str) -> list[str]:
    _, errors = guard.validate_spec_document(document)
    return [
        error["code"]
        for error in errors
        if error["field_path"] == field_path and error["code"] == "AUTHORITY_CONTRADICTION"
    ]


@pytest.mark.parametrize("path", [".gitleaks.toml", ".gitleaksignore"])
def test_secret_scan_config_paths_require_local_offline_tooling(path):
    document = _spec()
    document["scope"]["allowed_changed_files"].append(path)
    field_path = f"spec.scope.allowed_changed_files[{len(document['scope']['allowed_changed_files']) - 1}]"
    assert document["authority"]["local_offline_tooling"] is True
    assert _authority_errors_at(document, field_path) == []
    document["authority"]["local_offline_tooling"] = False
    assert _authority_errors_at(document, field_path) == ["AUTHORITY_CONTRADICTION"]


@pytest.mark.parametrize(
    "path",
    ["README.md", ".gitleaks.toml.bak", "docs2/.gitleaks.toml", ".gitleaks", "gitleaks.toml", ".gitignore"],
)
def test_unmapped_root_and_lookalike_paths_remain_authority_contradictions(path):
    document = _spec()
    document["scope"]["allowed_changed_files"].append(path)
    field_path = f"spec.scope.allowed_changed_files[{len(document['scope']['allowed_changed_files']) - 1}]"
    assert _authority_errors_at(document, field_path) == ["AUTHORITY_CONTRADICTION"]
