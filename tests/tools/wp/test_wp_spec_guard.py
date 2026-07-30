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


def _write_package(tmp_path: pathlib.Path, *, spec=None, cert=None):
    wp = tmp_path / "wp.txt"
    spec_file = tmp_path / "spec.json"
    cert_file = tmp_path / "certificate.json"
    wp.write_bytes(WP_PATH.read_bytes())
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
        "ddaeaaa774cf81437ad7bf5e9e54403722190e49acdd92be547e5ebb5b3f9a40"
    )
    assert parsed["wp_spec_sha256"] == (
        "207b84aebd21e0a1bb7dc0675234b9e77aa1f58baa2d0e951d8076189d1ca87b"
    )


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
    assert codes == ["CERTIFICATE_HASH_MISMATCH", "DRAFTABILITY_INCOMPLETE"]


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
