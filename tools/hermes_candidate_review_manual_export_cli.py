"""Local/manual CLI wrapper for WP108 candidate-review manual export artifacts.

This tool accepts one strict local JSON envelope containing an already-built
valid WP108 artifact-result snapshot and writes it through the existing WP109
writer to one explicit local .md or .txt output path.

Added in WP115. Local/offline/manual only. No network, subprocess, Hermes
runtime/provider/model/prompt runner, credentials, account state, paper/live,
execution/risk/order, scheduler, daemon, dashboard, dependency, workflow, or
generated-artifact behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.data_layer.hermes_candidate_review_handoff_manual_export_artifact import (
    REQUIRED_ARTIFACT_GROUPS,
    REQUIRED_ARTIFACT_SAFETY_FLAGS,
    CandidateReviewManualExportArtifactResult,
)
from src.data_layer.hermes_candidate_review_handoff_manual_export_writer import (
    write_candidate_review_manual_export_artifact,
)


_ENVELOPE_TYPE = "HERMES_CANDIDATE_REVIEW_MANUAL_EXPORT_ARTIFACT_RESULT_V1"
_EXPECTED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "envelope_type",
        "source_wp",
        "source_contract",
        "produced_by",
        "artifact_result",
        "safety_flags",
        "provenance_notice",
        "human_review_required",
    }
)
_ALLOWED_OUTPUT_SUFFIXES: frozenset[str] = frozenset({".md", ".txt"})
_URI_MARKERS: tuple[str, ...] = (
    "://",
    "file:",
    "http:",
    "https:",
    "s3:",
    "gs:",
    "ftp:",
    "ftps:",
)
_PROTECTED_REPO_PARTS: frozenset[str] = frozenset(
    {
        ".github",
        "docs",
        "src",
        "tests",
        "tools",
        "local_data",
        ".venv-security",
        ".venv-official-client",
        "security-scan-output",
        "official-client-sandbox-output",
    }
)
_GENERATED_PARTS: frozenset[str] = frozenset(
    {
        "local_data",
        ".venv-security",
        ".venv-official-client",
        "security-scan-output",
        "official-client-sandbox-output",
        ".cache",
    }
)
_RAW_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "raw_metadata",
        "free_form_metadata",
        "caller_metadata",
        "arbitrary_metadata",
        "raw_input",
        "untrusted_input",
        "notes_raw",
        "warnings_raw",
        "reason_text_raw",
        "custom",
        "extras",
        "metadata",
        "freeform",
        "extra",
        "context",
        "custom_fields",
        "raw_response",
        "model_response",
        "prompt",
        "completion",
        "raw",
        "free_form",
        "arbitrary",
        "raw_model_output",
        "raw_hermes_output",
        "prompt_runner_output",
        "runtime_logs",
        "strategy_recommendation_text",
        "trade_signal_text",
        "expected_return_text",
        "position_sizing_text",
        "pr_approval_text",
        "merge_readiness_text",
        "credentials",
        "api_keys",
        "private_keys",
        "account_state",
        "order_state",
        "paper_state",
        "live_state",
    }
)
_BOUNDARY_KEY_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "forbidden_scope_notice",
        "safety_flags",
        "advisory_only",
        "human_review_required",
        "no_execution_authority",
        "no_runtime_authority",
        "no_credential_authority",
        "no_paper_or_live_authority",
        "no_prompt_execution",
        "no_file_or_network_beyond_explicit_local_manual_export",
        "no_strategy_promotion_authority",
        "no_pr_approval_authority",
        "no_trade_signal",
        "no_position_sizing",
        "no_expected_return",
    }
)
_FORBIDDEN_TERMS: tuple[str, ...] = (
    "raw model output",
    "raw hermes output",
    "prompt runner output",
    "runtime log",
    "strategy recommendation",
    "trade signal",
    "buy",
    "sell",
    "order",
    "trade",
    "trading",
    "execute",
    "execution",
    "entry",
    "exit",
    "expected return",
    "fair value",
    "alpha",
    "edge",
    "position size",
    "position sizing",
    "allocation",
    "paper ready",
    "live ready",
    "deployment ready",
    "approve pr",
    "approve pull request",
    "merge ready",
    "merge readiness",
    "credential",
    "api key",
    "private key",
    "secret",
    "passphrase",
    "wallet",
    "account state",
    "private state",
    "order state",
    "paper state",
    "live state",
    "hermes runtime",
    "model provider",
    "prompt runner",
    "network api",
    "account endpoint",
    "scheduler",
    "daemon",
    "bot loop",
    "dashboard",
)


class _CliError(Exception):
    def __init__(self, exit_code: int, code: str) -> None:
        super().__init__(code)
        self.exit_code = exit_code
        self.code = code


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _CliError(2, "INVALID_ARGUMENTS")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_uri_like(value: str) -> bool:
    lower = value.strip().lower()
    return any(marker in lower for marker in _URI_MARKERS)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _has_protected_part(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return bool(parts & _PROTECTED_REPO_PARTS) or "tools" in parts and ".bin" in parts


def _has_generated_part(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return bool(parts & _GENERATED_PARTS) or "tools" in parts and ".bin" in parts


def _validate_input_path(value: str) -> Path:
    if not isinstance(value, str) or not value.strip() or _is_uri_like(value):
        raise _CliError(3, "INVALID_ARTIFACT_JSON_PATH")
    path = Path(value).expanduser()
    if str(path).strip() in {"-", ""}:
        raise _CliError(3, "INVALID_ARTIFACT_JSON_PATH")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise _CliError(3, "INVALID_ARTIFACT_JSON_PATH") from exc
    if not resolved.is_file() or resolved.suffix.lower() != ".json":
        raise _CliError(3, "INVALID_ARTIFACT_JSON_PATH")
    root = _repo_root()
    if _is_relative_to(resolved, root) or _has_protected_part(resolved) or _has_generated_part(resolved):
        raise _CliError(4, "PROTECTED_INPUT_PATH")
    return resolved


def _validate_output_path(value: str, *, overwrite: bool) -> Path:
    if not isinstance(value, str) or not value.strip() or _is_uri_like(value):
        raise _CliError(3, "INVALID_OUTPUT_PATH")
    path = Path(value).expanduser()
    if str(path).strip() in {"-", ""}:
        raise _CliError(3, "INVALID_OUTPUT_PATH")
    try:
        resolved = path.resolve(strict=False)
    except OSError as exc:
        raise _CliError(3, "INVALID_OUTPUT_PATH") from exc
    root = _repo_root()
    if _is_relative_to(resolved, root) or _has_protected_part(resolved) or _has_generated_part(resolved):
        raise _CliError(4, "PROTECTED_OUTPUT_PATH")
    if resolved.suffix.lower() not in _ALLOWED_OUTPUT_SUFFIXES:
        raise _CliError(3, "INVALID_OUTPUT_SUFFIX")
    if not resolved.parent.exists() or not resolved.parent.is_dir():
        raise _CliError(3, "OUTPUT_PARENT_MISSING")
    if resolved.exists() and not overwrite:
        raise _CliError(3, "OUTPUT_EXISTS_NO_OVERWRITE")
    return resolved


def _normalize(value: str) -> str:
    return value.lower().replace("_", " ").replace("-", " ")


def _validate_safe_string(value: object) -> None:
    if not isinstance(value, str):
        raise _CliError(2, "INVALID_ENVELOPE")
    text = _normalize(value)
    if _is_uri_like(value):
        raise _CliError(2, "UNSAFE_INPUT_VALUE")
    for term in _FORBIDDEN_TERMS:
        if term in text:
            raise _CliError(2, "UNSAFE_INPUT_VALUE")


def _scan_untrusted(value: object, *, key_name: str | None = None, depth: int = 0) -> None:
    if depth > 20:
        raise _CliError(2, "INVALID_ENVELOPE")
    if key_name in _BOUNDARY_KEY_EXCEPTIONS:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if key_text.lower() in _RAW_METADATA_KEYS:
                raise _CliError(2, "RAW_METADATA_NOT_ALLOWED")
            if key_text not in _BOUNDARY_KEY_EXCEPTIONS:
                _validate_safe_string(key_text)
            _scan_untrusted(child, key_name=key_text, depth=depth + 1)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _scan_untrusted(child, key_name=key_name, depth=depth + 1)
    elif isinstance(value, str):
        _validate_safe_string(value)


def _validate_neutral_warnings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise _CliError(2, "INVALID_WARNINGS")
    warnings: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise _CliError(2, "INVALID_WARNINGS")
        if not all(char.isupper() or char.isdigit() or char == "_" for char in item):
            raise _CliError(2, "INVALID_WARNINGS")
        _validate_safe_string(item)
        warnings.append(item)
    return tuple(warnings)


def _validate_envelope(envelope: object) -> CandidateReviewManualExportArtifactResult:
    if not isinstance(envelope, dict):
        raise _CliError(2, "INVALID_ENVELOPE")
    if set(envelope.keys()) != set(_EXPECTED_TOP_LEVEL_KEYS):
        raise _CliError(2, "INVALID_ENVELOPE_KEYS")
    if envelope.get("envelope_type") != _ENVELOPE_TYPE:
        raise _CliError(2, "INVALID_ENVELOPE_TYPE")
    if envelope.get("source_wp") != "WP108" or envelope.get("source_contract") != "WP107":
        raise _CliError(2, "INVALID_SOURCE_CONTRACT")
    if envelope.get("human_review_required") is not True:
        raise _CliError(2, "HUMAN_REVIEW_REQUIRED")

    produced_by = envelope.get("produced_by")
    if not isinstance(produced_by, str) or not produced_by.strip():
        raise _CliError(2, "INVALID_PRODUCED_BY")
    _validate_safe_string(produced_by)

    provenance_notice = envelope.get("provenance_notice")
    if not isinstance(provenance_notice, str) or not provenance_notice.strip():
        raise _CliError(2, "INVALID_PROVENANCE_NOTICE")
    _validate_safe_string(provenance_notice)

    artifact_result = envelope.get("artifact_result")
    if not isinstance(artifact_result, dict):
        raise _CliError(2, "INVALID_ARTIFACT_RESULT")
    expected_result_keys = {"is_valid", "artifact", "errors", "warnings"}
    if set(artifact_result.keys()) != expected_result_keys:
        raise _CliError(2, "INVALID_ARTIFACT_RESULT_KEYS")
    if artifact_result.get("is_valid") is not True:
        raise _CliError(2, "SOURCE_ARTIFACT_NOT_VALID")
    errors = artifact_result.get("errors")
    if not isinstance(errors, (list, tuple)) or len(errors) != 0:
        raise _CliError(2, "SOURCE_ARTIFACT_ERRORS_PRESENT")
    warnings = _validate_neutral_warnings(artifact_result.get("warnings"))
    artifact = artifact_result.get("artifact")
    if not isinstance(artifact, dict) or not artifact:
        raise _CliError(2, "INVALID_ARTIFACT")
    if set(REQUIRED_ARTIFACT_GROUPS) - set(artifact.keys()):
        raise _CliError(2, "MISSING_REQUIRED_ARTIFACT_GROUP")
    artifact_flags = artifact.get("safety_flags")
    if not isinstance(artifact_flags, dict):
        raise _CliError(2, "MISSING_REQUIRED_SAFETY_FLAG")
    for flag in REQUIRED_ARTIFACT_SAFETY_FLAGS:
        if artifact_flags.get(flag) is not True:
            raise _CliError(2, "MISSING_REQUIRED_SAFETY_FLAG")

    envelope_flags = envelope.get("safety_flags")
    if not isinstance(envelope_flags, dict):
        raise _CliError(2, "MISSING_REQUIRED_SAFETY_FLAG")
    for flag in REQUIRED_ARTIFACT_SAFETY_FLAGS:
        if envelope_flags.get(flag) is not True:
            raise _CliError(2, "MISSING_REQUIRED_SAFETY_FLAG")

    _scan_untrusted(envelope)
    return CandidateReviewManualExportArtifactResult(
        is_valid=True,
        artifact=artifact,
        errors=(),
        warnings=warnings,
    )


def _load_envelope(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _CliError(2, "INVALID_JSON_ENVELOPE") from exc


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="python -m tools.hermes_candidate_review_manual_export_cli",
        description="Local manual WP108 artifact-result export wrapper.",
    )
    parser.add_argument("--artifact-json", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true", default=False)
    return parser


def _write_error(code: str) -> None:
    print(json.dumps({"status": "error", "code": code}, sort_keys=True), file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        artifact_json_path = _validate_input_path(args.artifact_json)
        output_path = _validate_output_path(args.output, overwrite=bool(args.overwrite))
        artifact_result = _validate_envelope(_load_envelope(artifact_json_path))
        result = write_candidate_review_manual_export_artifact(
            artifact_result=artifact_result,
            output_path=output_path,
            overwrite=bool(args.overwrite),
            expected_suffix=output_path.suffix.lower(),
        )
        if result.is_valid is not True:
            code = result.errors[0] if result.errors else "WRITE_FAILED"
            if "PATH" in code or "SUFFIX" in code or "PARENT" in code or "OVERWRITE" in code:
                raise _CliError(3, code)
            raise _CliError(5, "WRITE_FAILED")
        summary = {
            "bytes_written": result.bytes_written,
            "output_path": result.output_path,
            "sha256": result.sha256,
            "status": "success",
            "warnings": list(result.warnings),
        }
        print(json.dumps(summary, sort_keys=True))
        return 0
    except SystemExit:
        raise
    except _CliError as exc:
        _write_error(exc.code)
        return exc.exit_code
    except Exception:
        _write_error("UNEXPECTED_INTERNAL_ERROR")
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
