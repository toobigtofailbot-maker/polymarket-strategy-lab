"""Tests for tools/validation/validation_output_summary.py."""

import importlib
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

# ── Load the helper module ───────────────────────────────────────────────────
_HELPER_PATH = (
    pathlib.Path(__file__).resolve().parent.parent.parent.parent
    / "tools" / "validation" / "validation_output_summary.py"
)
_spec = importlib.util.spec_from_file_location("validation_output_summary", _HELPER_PATH)
vos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vos)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent

PYTHON = sys.executable


# ── 1. CLI help ──────────────────────────────────────────────────────────────

def test_cli_help_exits_zero():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH), "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "validation output summary" in result.stdout.lower()


# ── 2. Metadata mode ─────────────────────────────────────────────────────────

def test_metadata_mode_basic_pass():
    summary = vos.build_summary(
        command="python -m pytest",
        check_type="full-pytest",
        exit_code=0,
        combined_text="878 passed, 1 warning",
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    assert summary["status"] == "PASS"
    assert summary["pass_count"] == 878
    assert summary["warning_count"] == 1
    assert summary["fail_count"] == 0


def test_metadata_mode_with_exit_code_nonzero():
    summary = vos.build_summary(
        command="python -m pytest",
        check_type="full-pytest",
        exit_code=1,
        combined_text="5 failed, 878 passed",
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    assert summary["status"] == "FAIL"
    assert summary["fail_count"] == 5
    assert summary["pass_count"] == 878


# ── 3. Parser/stdin mode ─────────────────────────────────────────────────────

def test_stdin_failure_produces_fail_status():
    stdin_text = "FAILED tests/foo.py::test_bar - AssertionError\n1 failed, 10 passed"
    summary = vos.build_summary(
        command="python -m pytest tests/foo.py",
        check_type="focused-pytest",
        exit_code=1,
        combined_text=stdin_text,
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    assert summary["status"] == "FAIL"
    assert summary["failure_snippet"]


def test_stdin_failure_snippet_present():
    stdin_text = "FAILED tests/foo.py::test_bar\nAssertionError: expected 1 got 2\n1 failed"
    summary = vos.build_summary(
        command="pytest",
        check_type="focused-pytest",
        exit_code=1,
        combined_text=stdin_text,
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    snippet_text = "\n".join(summary["failure_snippet"])
    assert "FAILED" in snippet_text or "AssertionError" in snippet_text


# ── 4. JSON output ───────────────────────────────────────────────────────────

def test_json_format_is_parseable():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--command", "python -m pytest",
         "--exit-code", "0",
         "--check-type", "full-pytest",
         "--stdout-text", "878 passed, 1 warning",
         "--format", "json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, dict)


def test_json_contains_required_fields():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--command", "python -m pytest",
         "--exit-code", "0",
         "--check-type", "full-pytest",
         "--stdout-text", "878 passed, 1 warning",
         "--format", "json"],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert "summary_schema_version" in data
    assert "status" in data
    assert "pass_count" in data
    assert "fail_count" in data
    assert "warning_count" in data
    assert "validation_reminder" in data
    assert "raw_log_retention_note" in data
    assert "command" in data
    assert "check_type" in data
    assert "exit_code" in data
    assert "mandatory_evidence_present" in data
    assert "secret_like_output_detected" in data


# ── 5. Text output ───────────────────────────────────────────────────────────

def test_text_output_contains_required_fields():
    summary = vos.build_summary(
        command="python -m pytest",
        check_type="full-pytest",
        exit_code=0,
        combined_text="878 passed, 1 warning",
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    text = vos.render_text(summary)
    assert "python -m pytest" in text
    assert "full-pytest" in text
    assert "PASS" in text
    assert "878" in text
    assert "validation_reminder" in summary
    assert vos.VALIDATION_REMINDER in text
    assert vos.RAW_LOG_RETENTION_NOTE in text


def test_text_output_does_not_dump_huge_logs():
    big_text = "some line\n" * 10000
    summary = vos.build_summary(
        command="python -m pytest",
        check_type="full-pytest",
        exit_code=1,
        combined_text=big_text + "\n1 failed",
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    text = vos.render_text(summary)
    assert len(text.splitlines()) < 200


# ── 6. Pytest parser ─────────────────────────────────────────────────────────

def test_pytest_parser_passed_only():
    r = vos.parse_pytest_output("10 passed")
    assert r["pass_count"] == 10
    assert r["fail_count"] == 0
    assert r["has_result"] is True


def test_pytest_parser_failed_only():
    r = vos.parse_pytest_output("3 failed")
    assert r["fail_count"] == 3
    assert r["has_result"] is True


def test_pytest_parser_error_count():
    r = vos.parse_pytest_output("2 errors")
    assert r["error_count"] == 2
    assert r["has_result"] is True


def test_pytest_parser_warning_count():
    r = vos.parse_pytest_output("5 warnings")
    assert r["warning_count"] == 5
    assert r["has_result"] is True


def test_pytest_parser_combined_line():
    r = vos.parse_pytest_output("878 passed, 1 warning")
    assert r["pass_count"] == 878
    assert r["warning_count"] == 1
    assert r["fail_count"] == 0
    assert r["has_result"] is True


def test_pytest_parser_full_combined():
    r = vos.parse_pytest_output("5 failed, 878 passed, 2 errors, 3 warnings")
    assert r["fail_count"] == 5
    assert r["pass_count"] == 878
    assert r["error_count"] == 2
    assert r["warning_count"] == 3


def test_pytest_parser_empty():
    r = vos.parse_pytest_output("")
    assert r["has_result"] is False
    assert r["pass_count"] == 0


def test_pytest_parser_multiline():
    text = "FAILED tests/foo.py::test_bar\n1 failed, 10 passed, 2 warnings"
    r = vos.parse_pytest_output(text)
    assert r["fail_count"] == 1
    assert r["pass_count"] == 10
    assert r["warning_count"] == 2


# ── 7. Artifact guard parser ─────────────────────────────────────────────────

def test_artifact_guard_pass():
    r = vos.parse_artifact_guard_output("Generated artifact guard passed.")
    assert r == "pass"


def test_artifact_guard_fail_blocked():
    r = vos.parse_artifact_guard_output("blocked: generated artifacts visible")
    assert r == "fail"


def test_artifact_guard_fail_failed():
    r = vos.parse_artifact_guard_output("Guard failed: staged local_data file found")
    assert r == "fail"


def test_artifact_guard_unknown():
    r = vos.parse_artifact_guard_output("no relevant output here")
    assert r is None


# ── 8. Remote Main Sync Gate parser ──────────────────────────────────────────

def test_sync_gate_pass():
    r = vos.parse_sync_gate_output("Remote Main Sync Gate passed")
    assert r == "pass"


def test_sync_gate_fail_stale():
    r = vos.parse_sync_gate_output("stale: local HEAD is behind origin/main")
    assert r == "fail"


def test_sync_gate_fail_dirty():
    r = vos.parse_sync_gate_output("dirty: working tree has uncommitted changes")
    assert r == "fail"


def test_sync_gate_fail_missing():
    r = vos.parse_sync_gate_output("missing required file: AGENTS.md")
    assert r == "fail"


def test_sync_gate_unknown():
    r = vos.parse_sync_gate_output("no relevant output")
    assert r is None


# ── 9. Security tool availability ────────────────────────────────────────────

def test_security_all_unavailable_is_unavailable():
    status = vos.classify_security_status({
        "semgrep": "unavailable",
        "gitleaks": "unavailable",
        "pip-audit": "unavailable",
    })
    assert status == "UNAVAILABLE"


def test_security_mixed_passed_unavailable_is_partial():
    status = vos.classify_security_status({
        "gitleaks": "passed",
        "semgrep": "unavailable",
    })
    assert status == "PARTIAL"


def test_security_any_failed_is_fail():
    status = vos.classify_security_status({
        "gitleaks": "passed",
        "semgrep": "failed",
    })
    assert status == "FAIL"


def test_security_all_passed_is_pass():
    status = vos.classify_security_status({
        "gitleaks": "passed",
        "semgrep": "passed",
        "pip-audit": "passed",
    })
    assert status == "PASS"


def test_security_unavailable_not_pass():
    status = vos.classify_security_status({"semgrep": "unavailable"})
    assert status != "PASS"


def test_security_skipped_not_available_is_unavailable():
    status = vos.classify_security_status({
        "pip-audit": "skipped_not_available",
        "gitleaks": "skipped_not_available",
    })
    assert status == "UNAVAILABLE"


def test_invalid_tool_availability_exits_2():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--check-type", "security",
         "--tool-availability", "semgrep=notavalidstatus"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2


# ── 10. Missing evidence ─────────────────────────────────────────────────────

def test_no_exit_code_no_output_is_error():
    summary = vos.build_summary(
        command=None,
        check_type="full-pytest",
        exit_code=None,
        combined_text="",
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    assert summary["status"] == "ERROR"
    assert summary["mandatory_evidence_present"] is False


def test_fail_on_missing_evidence_exits_nonzero():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--check-type", "full-pytest",
         "--fail-on-missing-required-evidence"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


# ── 11. Failure snippet ───────────────────────────────────────────────────────

def test_failure_snippet_includes_meaningful_lines():
    text = "some output\nFAILED tests/foo.py::test_bar\nAssertionError\n10 failed"
    snippet, _ = vos.extract_failure_snippet(text, max_lines=30)
    combined = "\n".join(snippet)
    assert "FAILED" in combined or "AssertionError" in combined


def test_failure_snippet_respects_max_lines():
    lines = [f"FAILED test_{i}" for i in range(100)]
    text = "\n".join(lines)
    snippet, truncated = vos.extract_failure_snippet(text, max_lines=10)
    assert len(snippet) <= 10
    assert truncated is True


def test_failure_snippet_sets_truncated_flag():
    lines = [f"ERROR: {i}" for i in range(50)]
    text = "\n".join(lines)
    _, truncated = vos.extract_failure_snippet(text, max_lines=5)
    assert truncated is True


def test_failure_snippet_no_truncation_when_short():
    text = "FAILED one_test\n1 failed"
    snippet, truncated = vos.extract_failure_snippet(text, max_lines=30)
    assert truncated is False


# ── 12. Secret-like output handling ──────────────────────────────────────────

def test_detect_api_key():
    text = "API_KEY=sk-abc123secretvalue"
    _, detected = vos.detect_and_redact_secrets(text)
    assert detected is True


def test_redact_api_key():
    text = "API_KEY=sk-abc123secretvalue"
    redacted, _ = vos.detect_and_redact_secrets(text)
    assert "sk-abc123secretvalue" not in redacted
    assert "[REDACTED]" in redacted


def test_detect_private_key():
    text = "PRIVATE_KEY=0xdeadbeef1234567890abcdef"
    _, detected = vos.detect_and_redact_secrets(text)
    assert detected is True


def test_detect_bearer_token():
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc.def"
    _, detected = vos.detect_and_redact_secrets(text)
    assert detected is True


def test_detect_pem_key():
    # EXAMPLE_ONLY: construct the pattern string to avoid literal key header in source
    pem_header = "-----BEGIN PRIVATE KEY-----"  # EXAMPLE_ONLY
    text = pem_header + "\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----"
    _, detected = vos.detect_and_redact_secrets(text)
    assert detected is True


# ── 12b. Full multi-line PEM block redaction (follow-up fix) ─────────────────

def _make_pem_block(key_type: str, body: str) -> str:
    """Helper: build a fake PEM block without literal header in one place."""  # EXAMPLE_ONLY
    begin = f"-----BEGIN {key_type}-----"  # EXAMPLE_ONLY
    end = f"-----END {key_type}-----"      # EXAMPLE_ONLY
    return f"{begin}\n{body}\n{end}"


_FAKE_PEM_BODY = "MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC7EXAMPLE"


def test_full_pem_block_detected():
    block = _make_pem_block("PRIVATE KEY", _FAKE_PEM_BODY)
    _, detected = vos.detect_and_redact_secrets(block)
    assert detected is True


def test_full_pem_block_body_not_in_redacted_text():
    block = _make_pem_block("PRIVATE KEY", _FAKE_PEM_BODY)
    redacted, _ = vos.detect_and_redact_secrets(block)
    assert _FAKE_PEM_BODY not in redacted


def test_rsa_pem_block_body_not_echoed():
    block = _make_pem_block("RSA PRIVATE KEY", _FAKE_PEM_BODY)
    redacted, detected = vos.detect_and_redact_secrets(block)
    assert detected is True
    assert _FAKE_PEM_BODY not in redacted


def test_ec_pem_block_body_not_echoed():
    block = _make_pem_block("EC PRIVATE KEY", _FAKE_PEM_BODY)
    redacted, detected = vos.detect_and_redact_secrets(block)
    assert detected is True
    assert _FAKE_PEM_BODY not in redacted


def test_openssh_pem_block_body_not_echoed():
    block = _make_pem_block("OPENSSH PRIVATE KEY", _FAKE_PEM_BODY)
    redacted, detected = vos.detect_and_redact_secrets(block)
    assert detected is True
    assert _FAKE_PEM_BODY not in redacted


def test_pem_block_body_not_in_text_output():
    """Full summary render must not contain PEM body lines."""
    block = _make_pem_block("PRIVATE KEY", _FAKE_PEM_BODY)
    # Embed the PEM block in a larger output (like a test log that leaked a key)
    combined = f"some output line\n{block}\nanother output line\n1 failed"
    summary = vos.build_summary(
        command="some command",
        check_type="focused-pytest",
        exit_code=1,
        combined_text=combined,
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    text_out = vos.render_text(summary)
    assert _FAKE_PEM_BODY not in text_out


def test_pem_block_body_not_in_json_output():
    """JSON summary must not contain PEM body lines."""
    block = _make_pem_block("PRIVATE KEY", _FAKE_PEM_BODY)
    combined = f"some output line\n{block}\n1 failed"
    summary = vos.build_summary(
        command="some command",
        check_type="focused-pytest",
        exit_code=1,
        combined_text=combined,
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    import json as _json
    json_out = vos.render_json(summary)
    assert _FAKE_PEM_BODY not in json_out


def test_pem_block_sets_secret_detected_flag():
    block = _make_pem_block("PRIVATE KEY", _FAKE_PEM_BODY)
    summary = vos.build_summary(
        command="cmd",
        check_type="other",
        exit_code=0,
        combined_text=block,
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    assert summary["secret_like_output_detected"] is True


def test_pem_block_fail_on_secret_exits_nonzero():
    pem_header = "-----BEGIN PRIVATE KEY-----"  # EXAMPLE_ONLY
    stdin_input = pem_header + "\n" + _FAKE_PEM_BODY + "\n-----END PRIVATE KEY-----"
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--check-type", "other",
         "--exit-code", "0",
         "--from-stdin",
         "--fail-on-secret"],
        input=stdin_input, capture_output=True, text=True,
    )
    assert result.returncode != 0


def test_pem_block_multiline_redact_marker_present():
    """After redaction the output should contain the redact marker, not the body."""
    block = _make_pem_block("PRIVATE KEY", _FAKE_PEM_BODY)
    redacted, _ = vos.detect_and_redact_secrets(block)
    assert "REDACTED" in redacted
    assert _FAKE_PEM_BODY not in redacted


def test_normal_output_not_affected_by_pem_fix():
    """Non-secret output is unchanged by the PEM redaction logic."""
    text = "878 passed, 1 warning"
    redacted, detected = vos.detect_and_redact_secrets(text)
    assert detected is False
    assert redacted == text


def test_secret_not_echoed_in_summary():
    text = "API_KEY=sk-supersecret12345"
    summary = vos.build_summary(
        command="some command",
        check_type="other",
        exit_code=0,
        combined_text=text,
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    rendered = vos.render_text(summary)
    assert "sk-supersecret12345" not in rendered


def test_secret_detected_sets_flag():
    summary = vos.build_summary(
        command="some command",
        check_type="other",
        exit_code=0,
        combined_text="TOKEN=supersecretvalue123",
        tool_availability={},
        max_failure_lines=30,
        fail_on_missing_evidence=False,
        fail_on_secret=False,
        secret_detected_in_input=False,
    )
    assert summary["secret_like_output_detected"] is True


def test_fail_on_secret_exits_nonzero():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--check-type", "other",
         "--exit-code", "0",
         "--stdout-text", "API_KEY=sk-testvalue",
         "--fail-on-secret"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


# ── 13. Generated output path detection ──────────────────────────────────────

def test_detects_local_data_path():
    text = "Summary written to: local_data/validation_summaries/wp32.json"
    paths = vos.extract_generated_output_paths(text)
    assert any("local_data" in p for p in paths)


def test_detects_json_path():
    text = "output file: results.json"
    paths = vos.extract_generated_output_paths(text)
    assert any(".json" in p for p in paths)


def test_detects_sarif_path():
    text = "Scan written to security-scan-output/results.sarif"
    paths = vos.extract_generated_output_paths(text)
    assert any(".sarif" in p for p in paths)


# ── 14. Input path validation ─────────────────────────────────────────────────

def test_valid_input_path_accepted():
    err = vos.validate_input_path(
        "local_data/validation_summaries/inputs/pytest.out",
        "--stdout-file",
    )
    assert err is None


def test_input_absolute_path_rejected():
    err = vos.validate_input_path("/tmp/pytest.out", "--stdout-file")
    assert err is not None
    assert "absolute" in err.lower()


def test_input_traversal_rejected():
    err = vos.validate_input_path(
        "local_data/validation_summaries/inputs/../../etc/passwd",
        "--stdout-file",
    )
    assert err is not None
    assert "traversal" in err.lower()


def test_input_outside_allowed_path_rejected():
    err = vos.validate_input_path("docs/project_status.md", "--stdout-file")
    assert err is not None


def test_input_env_file_rejected():
    err = vos.validate_input_path(
        "local_data/validation_summaries/inputs/.env",
        "--stdout-file",
    )
    assert err is not None


def test_input_private_key_file_rejected():
    err = vos.validate_input_path(
        "local_data/validation_summaries/inputs/private_key.txt",
        "--stdout-file",
    )
    assert err is not None


def test_input_windows_backslash_accepted():
    err = vos.validate_input_path(
        r"local_data\validation_summaries\inputs\pytest.out",
        "--stdout-file",
    )
    assert err is None


# ── 15. Output path validation ────────────────────────────────────────────────

def test_valid_output_path_accepted():
    err = vos.validate_output_path("local_data/validation_summaries/wp32_test.json")
    assert err is None


def test_output_absolute_path_rejected():
    err = vos.validate_output_path("/tmp/output.json")
    assert err is not None
    assert "absolute" in err.lower()


def test_output_traversal_rejected():
    err = vos.validate_output_path("local_data/validation_summaries/../../etc/cron.d/evil")
    assert err is not None
    assert "traversal" in err.lower()


def test_output_outside_allowed_rejected():
    err = vos.validate_output_path("docs/output.json")
    assert err is not None


def test_output_windows_drive_letter_rejected():
    err = vos.validate_output_path("C:/Users/test/output.json")
    assert err is not None
    assert "absolute" in err.lower()


def test_output_path_rejects_diff_scope_dir():
    err = vos.validate_output_path("local_data/diff_scope_summaries/file.json")
    assert err is not None


# ── 16. No forbidden imports/terms ───────────────────────────────────────────

def test_no_forbidden_imports():
    source = _HELPER_PATH.read_text(encoding="utf-8")
    forbidden_imports = [
        "import subprocess",
        "import requests",
        "import httpx",
        "import aiohttp",
        "import websockets",
        "import socket",
        "import openai",
        "import anthropic",
        "import langchain",
        "import hermes",
        "import py_clob_client",
    ]
    for imp in forbidden_imports:
        assert imp not in source, f"Forbidden import found: {imp!r}"


def test_no_command_execution_calls():
    source = _HELPER_PATH.read_text(encoding="utf-8")
    forbidden_calls = [
        "os.system(",
        "subprocess.run(",
        "subprocess.Popen(",
        "check_output(",
        "eval(",
        "exec(",
    ]
    for call in forbidden_calls:
        assert call not in source, f"Forbidden call found: {call!r}"


def test_no_trading_execution_terms():
    source = _HELPER_PATH.read_text(encoding="utf-8")
    forbidden_terms = [
        "post_order",
        "submit_order",
        "sign_order",
        "execute_trade",
        "create_trade_proposal",
        "generate_signal",
    ]
    for term in forbidden_terms:
        assert term not in source, f"Forbidden trading term found: {term!r}"


# ── 17. CLI smoke tests ───────────────────────────────────────────────────────

def test_cli_metadata_smoke_exits_zero():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--command", "python -m pytest",
         "--exit-code", "0",
         "--check-type", "full-pytest",
         "--stdout-text", "878 passed, 1 warning"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_cli_json_smoke_exits_zero_and_parseable():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--command", "python -m pytest",
         "--exit-code", "0",
         "--check-type", "full-pytest",
         "--stdout-text", "878 passed, 1 warning",
         "--format", "json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "PASS"
    assert data["pass_count"] == 878


def test_cli_stdin_failure_exits_zero_but_status_fail(tmp_path):
    stdin_input = "FAILED tests/foo.py::test_bar\n1 failed, 10 passed"
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--from-stdin",
         "--command", "python -m pytest tests/foo.py",
         "--exit-code", "1",
         "--check-type", "focused-pytest",
         "--format", "json"],
        input=stdin_input, capture_output=True, text=True,
    )
    # Default (no strict flag): exits 0 even for FAIL
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "FAIL"


def test_cli_invalid_output_path_exits_two():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--check-type", "other",
         "--exit-code", "0",
         "--output", "/absolute/forbidden/path.json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2


def test_cli_security_all_unavailable_status():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--command", "python tools/security/run_available_security_checks.py",
         "--exit-code", "0",
         "--check-type", "security",
         "--tool-availability", "gitleaks=unavailable",
         "--tool-availability", "semgrep=unavailable",
         "--tool-availability", "pip-audit=unavailable",
         "--format", "json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "UNAVAILABLE"
    assert "gitleaks" in data["unavailable_tools"] or "semgrep" in data["unavailable_tools"]


def test_cli_security_partial_status():
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--command", "python tools/security/run_available_security_checks.py",
         "--exit-code", "0",
         "--check-type", "security",
         "--tool-availability", "gitleaks=passed",
         "--tool-availability", "semgrep=unavailable",
         "--format", "json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "PARTIAL"


def test_cli_no_output_file_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        [PYTHON, str(_HELPER_PATH),
         "--command", "python -m pytest",
         "--exit-code", "0",
         "--check-type", "full-pytest",
         "--stdout-text", "878 passed, 1 warning"],
        capture_output=True, text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0
    # No output file should be created in tmp_path
    assert not list(tmp_path.glob("**/*.json"))
