"""Run the single foreground WP164A public-population smoke attempt.

This is the only authorized WP164A smoke execution surface.  It fails closed
before any product call unless an exact, commit-bound authorization envelope,
explicit network opt-in, and exact acknowledgement are present.  It has no
retry, scheduler, credential, Hermes, trading, or background authority.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_layer.point_in_time_market_research import (  # noqa: E402
    PolymarketPublicPopulationConfig,
    initialize_manifest_store,
    initialize_point_in_time_record_store,
    load_and_verify_manifest_store,
    load_and_verify_point_in_time_record_store,
    populate_initial_polymarket_public_data,
)


BASE_SHA = "46bc862018208b30971228ed719c7e9337142b41"
BRANCH = "codex/wp164a-public-population-repair"
WP_ID = "WP164A"
ACKNOWLEDGEMENT = "I_AUTHORIZE_EXACT_WP164A_PUBLIC_SMOKE_ATTEMPT_02"
OPERATOR_PATH = "tools/polymarket/run_wp164a_public_smoke.py"
PROMPT_PATH = "docs/wp_specs/WP164A/wp_prompt.txt"
SPEC_PATH = "docs/wp_specs/WP164A/wp_spec.json"
CONTRACT_PATH = "docs/polymarket_point_in_time_public_population_contract.md"

ENVELOPE_SCHEMA_ID = "wp164a-public-smoke-authorization-envelope"
ENVELOPE_SCHEMA_VERSION = "1.0.0"
WORKSPACE_ATTEMPT_ID = "wp164a-public-smoke-attempt-02"
MANIFEST_ID = "manifest:wp164a:public-smoke:1.0.0"
PARAMETER_SET_ID = "params:wp164a:public-smoke:1.0.0"
NORMALIZER_VERSION = "normalizer:wp164a:public-smoke:1.0.0"
VALIDATOR_VERSION = "validator:wp164a:public-smoke:1.0.0"
MARKETS_LIMIT = 25
ORDER_BOOKS_LIMIT = 1
MAX_COORDINATOR_INVOCATIONS = 1
RETRY_LIMIT = 0

SENTINEL_NAME = "WP164A_PUBLIC_SMOKE_INVOCATION.json"
RESULT_NAME = "WP164A_PUBLIC_SMOKE_RESULT.json"
RECORD_STORE_NAME = "point_in_time_records.sqlite3"
MANIFEST_STORE_NAME = "point_in_time_manifest.sqlite3"

STATE_DRIFT = "WP164A_PUBLIC_SMOKE_STATE_DRIFT"
LOCAL_EVIDENCE_DEFECT = "WP164A_PUBLIC_SMOKE_LOCAL_EVIDENCE_DEFECT"
COMPLETE_SUCCESS = "WP164A_PUBLIC_SMOKE_COMPLETE_SUCCESS"
BUILD_FAILED = "WP164A_PUBLIC_SMOKE_BUILD_FAILED"
BATCH_INVALID = "WP164A_PUBLIC_SMOKE_BATCH_INVALID"
EXTERNAL_INVALID = "WP164A_PUBLIC_SMOKE_EXTERNAL_FETCH_OR_RESPONSE_INVALID"

ENVELOPE_KEYS = frozenset(
    {
        "schema_id",
        "schema_version",
        "wp_id",
        "base_sha",
        "phase_a_commit_sha",
        "wp_prompt_sha256",
        "wp_spec_sha256",
        "contract_sha256",
        "operator_path",
        "operator_sha256",
        "workspace_attempt_id",
        "workspace_relpath",
        "manifest_id",
        "parameter_set_id",
        "normalizer_version",
        "validator_version",
        "markets_limit",
        "order_books_limit",
        "max_coordinator_invocations",
        "retry_limit",
        "replacement_invocation_authorized",
        "public_network_authorized",
        "hermes_provider_authorized",
        "h1_fifth_invocation_authorized",
        "af1_attempt_03_authorized",
        "merge_authorized",
        "credentials_authorized",
        "scheduler_authorized",
    }
)


class _StateDrift(Exception):
    pass


class _LocalEvidenceDefect(Exception):
    pass


def _canonical_json_value(value: object) -> object:
    if value is None or type(value) in {bool, int, str}:
        return value
    if isinstance(value, (tuple, list)):
        return [_canonical_json_value(item) for item in value]
    if isinstance(value, Mapping):
        if not all(type(key) is str for key in value):
            raise _LocalEvidenceDefect("non-string mapping key")
        return {
            key: _canonical_json_value(value[key])
            for key in sorted(value)
        }
    raise _LocalEvidenceDefect("unsupported canonical value")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        _canonical_json_value(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _exclusive_json_write(path: Path, mapping: Mapping[str, object]) -> str:
    payload = _canonical_json_bytes(mapping)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as exc:
        raise _LocalEvidenceDefect("exclusive artifact creation failed") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        raise _LocalEvidenceDefect("artifact persistence failed") from None
    return _sha256_bytes(payload)


def _bounded_json_object(path: Path) -> dict[str, object]:
    def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        mapping: dict[str, object] = {}
        for key, value in pairs:
            if key in mapping:
                raise ValueError("duplicate key")
            mapping[key] = value
        return mapping

    def _constant(_value: str) -> object:
        raise ValueError("non-finite number")

    try:
        raw = path.read_bytes()
        if not raw or len(raw) > 32_768:
            raise ValueError
        text = raw.decode("utf-8")
        decoded = json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=_constant,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        raise _StateDrift("authorization envelope unreadable") from None
    if type(decoded) is not dict:
        raise _StateDrift("authorization envelope is not an object")
    return decoded


def _git(*args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        raise _StateDrift("git state unavailable") from None
    if completed.returncode != 0:
        raise _StateDrift("git state invalid")
    return completed.stdout.strip()


def _require_sha(value: object) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _StateDrift("commit SHA invalid")
    return value


def _require_digest(value: object) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _StateDrift("digest invalid")
    return value


def _relative_text(value: object) -> str:
    if type(value) is not str or not value or "\\" in value:
        raise _StateDrift("relative path invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise _StateDrift("relative path invalid")
    return value


def _resolve_inside_repo(relative: str) -> Path:
    candidate = (REPO_ROOT / relative).resolve(strict=False)
    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError:
        raise _StateDrift("path escapes repository") from None
    return candidate


def _validate_envelope(
    envelope: dict[str, object],
    *,
    workspace_arg: str,
    envelope_arg: str,
) -> tuple[str, Path, Path]:
    if set(envelope) != ENVELOPE_KEYS:
        raise _StateDrift("authorization envelope key set invalid")

    phase_sha = _require_sha(envelope["phase_a_commit_sha"])
    expected_workspace = (
        f"local_data/wp164a_public_smoke/{phase_sha}/attempt-02"
    )
    expected_envelope = expected_workspace + ".authorization.json"
    exact_values: dict[str, object] = {
        "schema_id": ENVELOPE_SCHEMA_ID,
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "wp_id": WP_ID,
        "base_sha": BASE_SHA,
        "operator_path": OPERATOR_PATH,
        "workspace_attempt_id": WORKSPACE_ATTEMPT_ID,
        "workspace_relpath": expected_workspace,
        "manifest_id": MANIFEST_ID,
        "parameter_set_id": PARAMETER_SET_ID,
        "normalizer_version": NORMALIZER_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "markets_limit": MARKETS_LIMIT,
        "order_books_limit": ORDER_BOOKS_LIMIT,
        "max_coordinator_invocations": MAX_COORDINATOR_INVOCATIONS,
        "retry_limit": RETRY_LIMIT,
        "replacement_invocation_authorized": False,
        "public_network_authorized": True,
        "hermes_provider_authorized": False,
        "h1_fifth_invocation_authorized": False,
        "af1_attempt_03_authorized": False,
        "merge_authorized": False,
        "credentials_authorized": False,
        "scheduler_authorized": False,
    }
    for key, expected in exact_values.items():
        actual = envelope[key]
        if type(actual) is not type(expected) or actual != expected:
            raise _StateDrift("authorization envelope semantic mismatch")
    for key in (
        "wp_prompt_sha256",
        "wp_spec_sha256",
        "contract_sha256",
        "operator_sha256",
    ):
        _require_digest(envelope[key])

    if _relative_text(workspace_arg) != expected_workspace:
        raise _StateDrift("workspace path mismatch")
    if _relative_text(envelope_arg) != expected_envelope:
        raise _StateDrift("envelope path mismatch")
    workspace = _resolve_inside_repo(expected_workspace)
    envelope_path = _resolve_inside_repo(expected_envelope)
    if envelope_path.parent != workspace.parent or envelope_path == workspace:
        raise _StateDrift("envelope/workspace relationship invalid")
    return phase_sha, workspace, envelope_path


def _validate_repo_and_digests(envelope: dict[str, object], phase_sha: str) -> None:
    if Path.cwd().resolve() != REPO_ROOT.resolve():
        raise _StateDrift("operator must run from repository root")
    if not (REPO_ROOT / ".git").exists():
        raise _StateDrift("expected repository unavailable")
    if _git("rev-parse", "HEAD") != phase_sha:
        raise _StateDrift("HEAD mismatch")
    if _git("branch", "--show-current") != BRANCH:
        raise _StateDrift("branch mismatch")
    if _git("rev-parse", "origin/main") != BASE_SHA:
        raise _StateDrift("origin/main mismatch")
    if _git("merge-base", "--is-ancestor", BASE_SHA, phase_sha):
        raise _StateDrift("base is not an ancestor")
    if _git("status", "--porcelain"):
        raise _StateDrift("worktree is not clean")

    expected = {
        "wp_prompt_sha256": _file_sha256(REPO_ROOT / PROMPT_PATH),
        "wp_spec_sha256": _file_sha256(REPO_ROOT / SPEC_PATH),
        "contract_sha256": _file_sha256(REPO_ROOT / CONTRACT_PATH),
        "operator_sha256": _file_sha256(REPO_ROOT / OPERATOR_PATH),
    }
    if any(envelope[key] != digest for key, digest in expected.items()):
        raise _StateDrift("frozen file digest mismatch")


def _result_mapping(result: object) -> dict[str, object]:
    if not dataclasses.is_dataclass(result) or isinstance(result, type):
        raise _LocalEvidenceDefect("coordinator result is not a dataclass")
    mapping = dataclasses.asdict(result)
    if type(mapping) is not dict:
        raise _LocalEvidenceDefect("coordinator result mapping invalid")
    return mapping


def _stores_are_valid_empty(record_result: object, manifest_result: object) -> bool:
    record_snapshot = getattr(record_result, "snapshot", None)
    manifest_snapshot = getattr(manifest_result, "snapshot", None)
    return bool(
        getattr(record_result, "is_valid", False)
        and getattr(manifest_result, "is_valid", False)
        and record_snapshot is not None
        and manifest_snapshot is not None
        and getattr(record_snapshot, "records", None) == ()
        and getattr(manifest_snapshot, "dataset_references", None) == ()
        and getattr(manifest_snapshot, "manifest_entries", None) == ()
    )


def _classify(
    result: object,
    record_result: object,
    manifest_result: object,
) -> str:
    errors = getattr(result, "error_codes", None)
    network_used = getattr(result, "network_used", None)
    if errors == ("POPULATION_BUILD_FAILED",):
        return (
            BUILD_FAILED
            if _stores_are_valid_empty(record_result, manifest_result)
            else LOCAL_EVIDENCE_DEFECT
        )
    if errors == ("POPULATION_BATCH_INVALID",):
        return (
            BATCH_INVALID
            if _stores_are_valid_empty(record_result, manifest_result)
            else LOCAL_EVIDENCE_DEFECT
        )
    if network_used is True and errors in {
        ("POPULATION_FETCH_FAILED",),
        ("POPULATION_RESPONSE_INVALID",),
    }:
        return (
            EXTERNAL_INVALID
            if _stores_are_valid_empty(record_result, manifest_result)
            else LOCAL_EVIDENCE_DEFECT
        )

    successful_statuses = {
        "POPULATION_PERSISTED_AND_REGISTERED",
        "POPULATION_ALREADY_REGISTERED",
    }
    accepted = getattr(result, "batch_accepted_record_version_ids", None)
    built = getattr(result, "built_record_count", None)
    inserted = getattr(result, "inserted_record_count", None)
    fetched_markets = getattr(result, "fetched_market_count", None)
    fetched_books = getattr(result, "fetched_order_book_count", None)
    record_snapshot = getattr(record_result, "snapshot", None)
    manifest_snapshot = getattr(manifest_result, "snapshot", None)
    success = bool(
        getattr(result, "is_valid", False) is True
        and getattr(result, "status", None) in successful_statuses
        and errors == ()
        and network_used is True
        and getattr(result, "requested_markets_limit", None) == 25
        and getattr(result, "bounded_markets_limit", None) == 25
        and getattr(result, "requested_order_books_limit", None) == 1
        and getattr(result, "bounded_order_books_limit", None) == 1
        and type(fetched_markets) is int
        and 1 <= fetched_markets <= 25
        and type(fetched_books) is int
        and 0 <= fetched_books <= 1
        and type(built) is int
        and built == fetched_markets + fetched_books
        and inserted == built
        and getattr(result, "build_failure_observation_kind", None) is None
        and getattr(result, "build_status", None) is None
        and getattr(result, "build_error_codes", None) == ()
        and getattr(result, "build_warning_codes", None) == ()
        and getattr(result, "build_quarantine_id", None) is None
        and getattr(result, "build_input_fingerprint_sha256", None) is None
        and getattr(result, "batch_is_valid", None) is True
        and getattr(result, "batch_error_codes", None) == ()
        and getattr(result, "batch_quarantined_record_version_ids", None) == ()
        and getattr(result, "batch_exact_duplicate_record_version_ids", None) == ()
        and type(accepted) is tuple
        and len(accepted) == built
        and len(set(accepted)) == built
        and type(getattr(result, "canonical_batch_sha256", None)) is str
        and getattr(result, "record_store_status", None)
        == "RECORD_STORE_APPEND_COMMITTED"
        and getattr(result, "registration_status", None) == "ADAPTER_PERSISTED"
        and getattr(result, "recovery_required", None) is False
        and getattr(record_result, "is_valid", False)
        and record_snapshot is not None
        and len(getattr(record_snapshot, "records", ())) == built
        and {
            getattr(getattr(record, "envelope", None), "record_version_id", None)
            for record in getattr(record_snapshot, "records", ())
        }
        == set(accepted)
        and getattr(manifest_result, "is_valid", False)
        and manifest_snapshot is not None
        and any(
            getattr(reference, "dataset_snapshot_reference_id", None)
            == getattr(result, "dataset_snapshot_reference_id", None)
            for reference in getattr(manifest_snapshot, "dataset_references", ())
        )
        and any(
            getattr(entry, "manifest_entry_id", None)
            == getattr(result, "manifest_entry_id", None)
            for entry in getattr(manifest_snapshot, "manifest_entries", ())
        )
    )
    return COMPLETE_SUCCESS if success else LOCAL_EVIDENCE_DEFECT


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--authorization-envelope", required=True)
    parser.add_argument("--allow-public-network", action="store_true")
    parser.add_argument("--acknowledgement", required=True)
    return parser


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    option_names = (
        "--workspace",
        "--authorization-envelope",
        "--allow-public-network",
        "--acknowledgement",
    )
    if len(argv) != 7 or any(argv.count(name) != 1 for name in option_names):
        raise _StateDrift("exact command surface required")
    try:
        return _build_parser().parse_args(list(argv))
    except SystemExit:
        raise _StateDrift("command arguments invalid") from None


def _summary(
    terminal: str,
    *,
    envelope_sha256: str | None = None,
    sentinel_sha256: str | None = None,
    result_sha256: str | None = None,
    result: object | None = None,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "terminal": terminal,
        "coordinator_invocations": 0 if sentinel_sha256 is None else 1,
        "retry_count": 0,
        "hermes_provider_invocations": 0,
        "authorization_envelope_sha256": envelope_sha256,
        "sentinel_sha256": sentinel_sha256,
        "result_sha256": result_sha256,
    }
    if result is not None:
        for name in (
            "is_valid",
            "status",
            "error_codes",
            "network_used",
            "requested_markets_limit",
            "bounded_markets_limit",
            "requested_order_books_limit",
            "bounded_order_books_limit",
            "fetched_market_count",
            "fetched_order_book_count",
            "built_record_count",
            "inserted_record_count",
            "build_failure_observation_kind",
            "build_status",
            "build_error_codes",
            "batch_is_valid",
            "batch_status",
            "batch_error_codes",
        ):
            summary[name] = getattr(result, name, None)
    return summary


def run(
    argv: Sequence[str],
    *,
    coordinator: Callable[..., object] = populate_initial_polymarket_public_data,
) -> tuple[int, dict[str, object]]:
    sentinel_sha256: str | None = None
    envelope_sha256: str | None = None
    result_sha256: str | None = None
    result: object | None = None
    try:
        args = _parse_args(argv)
        if args.allow_public_network is not True:
            raise _StateDrift("public network opt-in missing")
        if args.acknowledgement != ACKNOWLEDGEMENT:
            raise _StateDrift("acknowledgement mismatch")

        envelope_arg = _relative_text(args.authorization_envelope)
        envelope_path = _resolve_inside_repo(envelope_arg)
        envelope = _bounded_json_object(envelope_path)
        phase_sha, workspace, validated_envelope_path = _validate_envelope(
            envelope,
            workspace_arg=args.workspace,
            envelope_arg=envelope_arg,
        )
        if validated_envelope_path != envelope_path:
            raise _StateDrift("authorization envelope path mismatch")
        envelope_sha256 = _sha256_bytes(_canonical_json_bytes(envelope))
        _validate_repo_and_digests(envelope, phase_sha)
        if workspace.exists():
            raise _StateDrift("workspace already exists")

        try:
            workspace.mkdir(parents=False, exist_ok=False)
        except OSError:
            raise _StateDrift("workspace creation failed") from None
        record_path = workspace / RECORD_STORE_NAME
        manifest_path = workspace / MANIFEST_STORE_NAME
        initialized_record = initialize_point_in_time_record_store(record_path)
        initialized_manifest = initialize_manifest_store(manifest_path)
        if not _stores_are_valid_empty(initialized_record, initialized_manifest):
            raise _StateDrift("fresh store initialization failed")

        config = PolymarketPublicPopulationConfig(
            manifest_id=MANIFEST_ID,
            parameter_set_id=PARAMETER_SET_ID,
            normalizer_version=NORMALIZER_VERSION,
            validator_version=VALIDATOR_VERSION,
            markets_limit=MARKETS_LIMIT,
            order_books_limit=ORDER_BOOKS_LIMIT,
            allow_network=True,
        )
        sentinel = {
            "schema_id": "wp164a-public-smoke-invocation",
            "schema_version": "1.0.0",
            "phase_a_commit_sha": phase_sha,
            "authorization_envelope_sha256": envelope_sha256,
            "operator_sha256": envelope["operator_sha256"],
            "workspace_attempt_id": WORKSPACE_ATTEMPT_ID,
            "markets_limit": MARKETS_LIMIT,
            "order_books_limit": ORDER_BOOKS_LIMIT,
            "invocation_state": "STARTED",
        }
        sentinel_sha256 = _exclusive_json_write(workspace / SENTINEL_NAME, sentinel)

        try:
            result = coordinator(record_path, manifest_path, config)
        except Exception:
            raise _LocalEvidenceDefect("coordinator invocation failed") from None
        result_mapping = _result_mapping(result)
        result_sha256 = _exclusive_json_write(workspace / RESULT_NAME, result_mapping)
        try:
            readback = _bounded_json_object(workspace / RESULT_NAME)
        except _StateDrift:
            raise _LocalEvidenceDefect("result readback failed") from None
        in_memory_bytes = _canonical_json_bytes(result_mapping)
        readback_bytes = _canonical_json_bytes(readback)
        if (
            in_memory_bytes != readback_bytes
            or _sha256_bytes(in_memory_bytes) != _sha256_bytes(readback_bytes)
            or result_sha256 != _sha256_bytes(readback_bytes)
        ):
            raise _LocalEvidenceDefect("result readback mismatch")

        verified_record = load_and_verify_point_in_time_record_store(record_path)
        verified_manifest = load_and_verify_manifest_store(manifest_path)
        if not getattr(verified_record, "is_valid", False) or not getattr(
            verified_manifest, "is_valid", False
        ):
            raise _LocalEvidenceDefect("post-result store verification failed")
        terminal = _classify(result, verified_record, verified_manifest)
        summary = _summary(
            terminal,
            envelope_sha256=envelope_sha256,
            sentinel_sha256=sentinel_sha256,
            result_sha256=result_sha256,
            result=result,
        )
        return (0 if terminal == COMPLETE_SUCCESS else 2), summary
    except _StateDrift:
        return 2, _summary(STATE_DRIFT, envelope_sha256=envelope_sha256)
    except _LocalEvidenceDefect:
        return 2, _summary(
            LOCAL_EVIDENCE_DEFECT,
            envelope_sha256=envelope_sha256,
            sentinel_sha256=sentinel_sha256,
            result_sha256=result_sha256,
            result=result,
        )


def main(argv: Sequence[str] | None = None) -> int:
    code, summary = run(sys.argv[1:] if argv is None else argv)
    print(_canonical_json_bytes(summary).decode("utf-8"))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
