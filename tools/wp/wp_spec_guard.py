"""Deterministic local guard for machine-readable work-package specifications.

The module is import-safe, standard-library-only, offline, read-only, and does
not inspect environment variables.  Diagnostics contain only closed codes,
trusted schema locations, and fixed neutral messages.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import pathlib
import re
import sys
from collections.abc import Mapping
from typing import Any

RESULT_SCHEMA_ID = "polymarket-wp-spec-guard-result"
RESULT_SCHEMA_VERSION = "1.0.0"
SPEC_SCHEMA_ID = "polymarket-work-package-spec"
SPEC_SCHEMA_VERSION = "1.0.0"
CERTIFICATE_SCHEMA_ID = "polymarket-wp-draftability-certificate"
WAIVER_SCHEMA_ID = "polymarket-wp-draftability-waiver"

# The waiver is a one-time bootstrap exception for these exact WP159 bytes.
# Normal independent certificates remain generic.
WP159_WAIVER_WP_SHA256 = (
    "7dfd1e826b688873c3303dcf89d13522d82620840b17f1a40812c3ceb2c74911"
)
WP159_WAIVER_SPEC_SHA256 = (
    "2300bd295bdd0f679857d2aec0d007d296ef05421095e77e69937b457ad094b3"
)
WP159_WAIVER_REPOSITORY = "toobigtofailbot-maker/polymarket-strategy-lab"
WP159_WAIVER_PACKAGE_CLASS = "GOVERNANCE"
WP159_WAIVER_BASE_BRANCH = "main"
WP159_WAIVER_PREDECESSOR_PR = 158
WP159_WAIVER_PREDECESSOR_HEAD = (
    "c7e59f2287501ea2ecab9b7d13d1a4b751f6c0b0"
)
WP159_WAIVER_PREDECESSOR_MERGE = (
    "056f0074b55c3d12cedbb9dfbdb43f7f668df0c3"
)

MAX_WP_BYTES = 1_048_576
MAX_SPEC_BYTES = 1_048_576
MAX_CERTIFICATE_BYTES = 262_144
MAX_JSON_DEPTH = 32
MAX_STRING_LENGTH = 16_384
MAX_ARRAY_LENGTH = 1_024

ERROR_ORDER = (
    "FILE_READ_ERROR",
    "JSON_PARSE_INVALID",
    "SCHEMA_UNSUPPORTED",
    "UNKNOWN_FIELD",
    "FIELD_MISSING",
    "FIELD_TYPE_INVALID",
    "FIELD_VALUE_INVALID",
    "CERTIFICATE_HASH_MISMATCH",
    "DRAFTABILITY_INCOMPLETE",
    "SCOPE_POLICY_INVALID",
    "AUTHORITY_CONTRADICTION",
    "SEMANTIC_CONTRADICTION",
    "IDENTITY_DERIVATION_INVALID",
    "FAILURE_PRECEDENCE_INVALID",
    "EXAMPLE_TRUTH_INVALID",
)
ERROR_MESSAGES = {
    "FILE_READ_ERROR": "required file is unavailable",
    "JSON_PARSE_INVALID": "JSON document is invalid",
    "SCHEMA_UNSUPPORTED": "schema identifier or version is unsupported",
    "UNKNOWN_FIELD": "object contains an unknown field",
    "FIELD_MISSING": "required field is missing",
    "FIELD_TYPE_INVALID": "field type is invalid",
    "FIELD_VALUE_INVALID": "field value is invalid",
    "CERTIFICATE_HASH_MISMATCH": "certificate hash does not match exact bytes",
    "DRAFTABILITY_INCOMPLETE": "draftability certificate is incomplete",
    "SCOPE_POLICY_INVALID": "scope policy is invalid",
    "AUTHORITY_CONTRADICTION": "path scope contradicts authority",
    "SEMANTIC_CONTRADICTION": "specification semantics contradict",
    "IDENTITY_DERIVATION_INVALID": "identity derivation is invalid",
    "FAILURE_PRECEDENCE_INVALID": "failure precedence is invalid",
    "EXAMPLE_TRUTH_INVALID": "example truth is invalid",
}
ERROR_PRIORITY = {code: index for index, code in enumerate(ERROR_ORDER)}

CHECKED_SECTION_ORDER = (
    "files",
    "spec_json",
    "spec_schema",
    "spec_semantics",
    "certificate_json",
    "certificate_schema",
    "certificate_hashes",
    "certificate_draftability",
)
LENS_ORDER = (
    "objective_and_class",
    "public_api",
    "mutability",
    "identity_and_serialization",
    "state_transitions",
    "batch_set_behavior",
    "error_precedence",
    "invalid_input_no_echo",
    "example_truth",
    "scope_compatibility",
    "evidence_publication",
    "successor_boundary",
)
TOP_KEYS = (
    "schema_id",
    "schema_version",
    "identity",
    "scope",
    "authority",
    "api_matrix",
    "semantic_fields",
    "identity_derivations",
    "state_transitions",
    "failure_precedence",
    "examples",
    "evidence_plan",
    "successor_boundary",
)
IDENTITY_KEYS = (
    "wp_id",
    "title",
    "repository",
    "package_class",
    "package_size_class",
    "risk_level",
    "base_branch",
    "required_predecessor",
    "suggested_branch",
    "objective",
    "capital_at_risk_usd",
    "xl_explicit_authorization",
    "xl_authorization_basis",
)
SCOPE_KEYS = (
    "required_changed_files",
    "allowed_changed_files",
    "forbidden_prefixes",
    "max_changed_files",
    "exact_scope_required",
    "historical_compatibility_edits",
    "rollback_surface",
    "mode_boundaries",
)
AUTHORITY_KEYS = (
    "workflow_governance",
    "local_offline_tooling",
    "canonical_evidence_policy",
    "docs",
    "tests",
    "source_runtime",
    "workflow_files",
    "dependencies",
    "network",
    "credentials",
    "scheduler",
    "hermes_runtime",
    "strategy",
    "paper",
    "execution",
    "live",
)
APPLICABILITY_KEYS = ("applicable", "reason", "items")

ITEM_KEYS = {
    "api_matrix": (
        "surface",
        "before",
        "after",
        "change_authorized",
        "compatibility_requirement",
        "authority",
    ),
    "semantic_fields": (
        "path",
        "source",
        "type",
        "required_rule",
        "mutable",
        "identity_role",
        "exclusion_reason",
        "validation_rule",
        "failure_category",
        "safe_output",
        "derivation_rule_id",
    ),
    "identity_derivations": (
        "rule_id",
        "target_path",
        "algorithm",
        "source_paths",
        "excluded_paths",
        "prefix",
        "canonicalization",
    ),
    "state_transitions": (
        "from_state",
        "to_state",
        "condition",
        "failure_category",
    ),
    "failure_precedence": ("condition_id", "category", "priority"),
    "examples": (
        "example_id",
        "expected_valid",
        "expected_error_codes",
        "intended_fault_count",
        "derivation_rule_ids",
        "input",
    ),
    "evidence_plan": (
        "requirement_id",
        "source",
        "test",
        "command",
        "expected_result",
    ),
}

WP_ID_RE = re.compile(r"^WP[1-9][0-9]*(?:[A-Z])?$")
TOKEN_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
LOWER_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
DOT_PATH_RE = re.compile(
    r"^(?:\$external\.[a-z][a-z0-9_]{0,127}|"
    r"[A-Za-z_][A-Za-z0-9_]{0,127}(?:\.[A-Za-z_][A-Za-z0-9_]{0,127})*)$"
)
REPOSITORY_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,99})/"
    r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,99})$"
)
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIREMENT_RE = re.compile(r"^R[0-9]{2,4}$")

FIXED_FAILURE_ITEMS = tuple(
    {
        "condition_id": condition,
        "category": category,
        "priority": priority,
    }
    for condition, category, priority in (
        ("file_unreadable", "FILE_READ_ERROR", 10),
        ("json_invalid", "JSON_PARSE_INVALID", 20),
        ("schema_unsupported", "SCHEMA_UNSUPPORTED", 30),
        ("unknown_field", "UNKNOWN_FIELD", 40),
        ("field_missing", "FIELD_MISSING", 50),
        ("field_type_invalid", "FIELD_TYPE_INVALID", 60),
        ("field_value_invalid", "FIELD_VALUE_INVALID", 70),
        ("certificate_hash_mismatch", "CERTIFICATE_HASH_MISMATCH", 80),
        ("draftability_incomplete", "DRAFTABILITY_INCOMPLETE", 90),
        ("scope_policy_invalid", "SCOPE_POLICY_INVALID", 100),
        ("authority_contradiction", "AUTHORITY_CONTRADICTION", 110),
        ("semantic_contradiction", "SEMANTIC_CONTRADICTION", 120),
        ("identity_derivation_invalid", "IDENTITY_DERIVATION_INVALID", 130),
        ("failure_precedence_invalid", "FAILURE_PRECEDENCE_INVALID", 140),
        ("example_truth_invalid", "EXAMPLE_TRUTH_INVALID", 150),
    )
)

CANONICALIZATION = {
    "sort_keys": True,
    "separators": [",", ":"],
    "ensure_ascii": False,
    "allow_nan": False,
    "encoding": "utf-8",
    "preserve_explicit_nulls": True,
    "preserve_array_order": True,
}

NORMAL_CERTIFICATE_KEYS = (
    "schema_id",
    "schema_version",
    "wp_id",
    "reviewed_repository",
    "reviewed_base_merge_sha",
    "wp_text_sha256",
    "wp_spec_sha256",
    "reviewer_role",
    "independence_attestation",
    "result",
    "covered_lenses",
    "unresolved_decisions",
    "implementability_simulation",
)
WAIVER_KEYS = (
    "schema_id",
    "schema_version",
    "wp_id",
    "waiver_mode",
    "authorization_source",
    "wp_text_sha256",
    "wp_spec_sha256",
    "implementation_authorized",
    "ready_for_review_authorized",
    "merge_authorized",
    "independent_live_pr_review_required",
    "unresolved_decisions",
)

DEPENDENCY_LOCK_BASENAMES = (
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "uv.lock",
    "package.json",
    "package-lock.json",
    "Cargo.toml",
    "Cargo.lock",
)
DEPENDENCY_LOCK_SUFFIXES = (".lock",)
GENERATED_ARTIFACT_PREFIXES = (
    "local_data/",
    ".venv-security/",
    ".venv-official-client/",
    "tools/.bin/",
    "tools/security/.cache/",
    "security-scan-output/",
    "official-client-sandbox-output/",
    ".pytest_cache/",
    "__pycache__/",
)
GENERATED_ARTIFACT_EXACT = (".coverage",)
GENERATED_ARTIFACT_SUFFIXES = (".sarif",)
PROTECTED_PREFIXES_BUILTIN = (
    "tools/hermes/",
    "agent_runtime/",
    "agent_memory/",
)
PROTECTED_EXACT_BUILTIN = (".env",)
PROTECTED_STARTSWITH_BUILTIN = (".env.",)
CREDENTIAL_LIKE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"private.?key",
        r"wallet.?key",
        r"mnemonic",
        r"passphrase",
        r"api.?key",
        r"secret.?key",
        r"\.pem$",
        r"\.p12$",
        r"\.pfx$",
        r"id_rsa",
        r"id_ed25519",
        r"credentials\.json",
        r"keystore",
        r"\.keystore",
    )
)


def _error(code: str, field_path: str) -> dict[str, str]:
    return {
        "code": code,
        "field_path": field_path,
        "message": ERROR_MESSAGES[code],
    }


def _ordered_errors(errors: list[dict[str, str]]) -> tuple[dict[str, str], ...]:
    unique: list[dict[str, str]] = []
    seen: list[tuple[str, str, str]] = []
    for item in errors:
        key = (item["code"], item["field_path"], item["message"])
        if key not in seen:
            seen.append(key)
            unique.append(item)
    unique.sort(
        key=lambda item: (
            ERROR_PRIORITY[item["code"]],
            item["field_path"],
            item["code"],
        )
    )
    return tuple(unique)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _object_keys(
    value: object,
    expected: tuple[str, ...],
    path: str,
    errors: list[dict[str, str]],
) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping):
        errors.append(_error("FIELD_TYPE_INVALID", path))
        return None
    if any(not isinstance(key, str) for key in value):
        errors.append(_error("FIELD_TYPE_INVALID", path))
        return None
    if any(key not in expected for key in value):
        errors.append(_error("UNKNOWN_FIELD", path))
    for key in expected:
        if key not in value:
            errors.append(_error("FIELD_MISSING", f"{path}.{key}"))
    return value


def _string(
    obj: Mapping[str, object],
    key: str,
    path: str,
    errors: list[dict[str, str]],
    minimum: int = 1,
    maximum: int = MAX_STRING_LENGTH,
    pattern: re.Pattern[str] | None = None,
    choices: tuple[str, ...] | None = None,
) -> str | None:
    if key not in obj:
        return None
    value = obj[key]
    field = f"{path}.{key}"
    if not isinstance(value, str):
        errors.append(_error("FIELD_TYPE_INVALID", field))
        return None
    if not minimum <= len(value) <= maximum:
        errors.append(_error("FIELD_VALUE_INVALID", field))
    elif pattern is not None and pattern.fullmatch(value) is None:
        errors.append(_error("FIELD_VALUE_INVALID", field))
    elif choices is not None and value not in choices:
        errors.append(_error("FIELD_VALUE_INVALID", field))
    return value


def _boolean(
    obj: Mapping[str, object],
    key: str,
    path: str,
    errors: list[dict[str, str]],
) -> bool | None:
    if key not in obj:
        return None
    value = obj[key]
    if not isinstance(value, bool):
        errors.append(_error("FIELD_TYPE_INVALID", f"{path}.{key}"))
        return None
    return value


def _integer(
    obj: Mapping[str, object],
    key: str,
    path: str,
    errors: list[dict[str, str]],
    minimum: int = 1,
    maximum: int | None = None,
) -> int | None:
    if key not in obj:
        return None
    value = obj[key]
    field = f"{path}.{key}"
    if not _is_int(value):
        errors.append(_error("FIELD_TYPE_INVALID", field))
        return None
    if value < minimum or (maximum is not None and value > maximum):
        errors.append(_error("FIELD_VALUE_INVALID", field))
    return value


def _string_array(
    obj: Mapping[str, object],
    key: str,
    path: str,
    errors: list[dict[str, str]],
    maximum: int = MAX_ARRAY_LENGTH,
    allow_empty: bool = True,
    unique: bool = False,
) -> list[str] | None:
    if key not in obj:
        return None
    value = obj[key]
    field = f"{path}.{key}"
    if not isinstance(value, list):
        errors.append(_error("FIELD_TYPE_INVALID", field))
        return None
    if len(value) > maximum or (not allow_empty and not value):
        errors.append(_error("FIELD_VALUE_INVALID", field))
    result: list[str] = []
    for index, item in enumerate(value):
        item_path = f"{field}[{index}]"
        if not isinstance(item, str):
            errors.append(_error("FIELD_TYPE_INVALID", item_path))
            continue
        if len(item) > MAX_STRING_LENGTH:
            errors.append(_error("FIELD_VALUE_INVALID", item_path))
        if unique and item in result:
            errors.append(_error("FIELD_VALUE_INVALID", item_path))
        result.append(item)
    return result


def _valid_ref(value: str) -> bool:
    forbidden = set("~^:?*[\\")
    return (
        bool(value)
        and not any(char.isspace() or ord(char) < 32 for char in value)
        and ".." not in value
        and not any(char in forbidden for char in value)
    )


def _valid_path(value: str, *, directory: bool = False) -> bool:
    if not value or "\x00" in value or "\\" in value or value.startswith("./"):
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return False
    segments = value.rstrip("/").split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        return False
    return value.endswith("/") if directory else not value.endswith("/")


def _walk_json(value: object, depth: int = 1, active: list[int] | None = None) -> bool:
    """Return True when built-in JSON value bounds and acyclicity hold."""
    if depth > MAX_JSON_DEPTH:
        return False
    if active is None:
        active = []
    if isinstance(value, str):
        return len(value) <= MAX_STRING_LENGTH
    if value is None or isinstance(value, bool) or _is_int(value):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, (list, dict)):
        identifier = id(value)
        if identifier in active:
            return False
        if len(value) > MAX_ARRAY_LENGTH:
            return False
        active.append(identifier)
        if isinstance(value, list):
            valid = all(_walk_json(item, depth + 1, active) for item in value)
        else:
            valid = all(
                isinstance(key, str)
                and len(key) <= MAX_STRING_LENGTH
                and _walk_json(item, depth + 1, active)
                for key, item in value.items()
            )
        active.pop()
        return valid
    return False


class _DuplicateKey(ValueError):
    pass


def _object_pairs_no_duplicates(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey()
        result[key] = value
    return result


def _reject_constant(_: str) -> object:
    raise ValueError()


def _strict_json(raw: bytes) -> object:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise UnicodeError()
    text = raw.decode("utf-8", errors="strict")
    value = json.loads(
        text,
        object_pairs_hook=_object_pairs_no_duplicates,
        parse_constant=_reject_constant,
    )
    if not _walk_json(value):
        raise ValueError()
    return value


def _validate_identity(
    root: Mapping[str, object], errors: list[dict[str, str]]
) -> Mapping[str, object] | None:
    identity = _object_keys(root.get("identity"), IDENTITY_KEYS, "spec.identity", errors)
    if identity is None:
        return None
    _string(identity, "wp_id", "spec.identity", errors, pattern=WP_ID_RE)
    _string(identity, "title", "spec.identity", errors, maximum=200)
    _string(identity, "repository", "spec.identity", errors, 3, 200, REPOSITORY_RE)
    _string(identity, "package_class", "spec.identity", errors, pattern=TOKEN_RE)
    size = _string(
        identity,
        "package_size_class",
        "spec.identity",
        errors,
        choices=("S", "M", "L", "XL"),
    )
    _integer(identity, "risk_level", "spec.identity", errors, 0, 4)
    for key in ("base_branch", "suggested_branch"):
        ref = _string(identity, key, "spec.identity", errors, maximum=200)
        if ref is not None and not _valid_ref(ref):
            errors.append(_error("FIELD_VALUE_INVALID", f"spec.identity.{key}"))
    predecessor = _object_keys(
        identity.get("required_predecessor"),
        ("pr_number", "head_sha", "merge_sha"),
        "spec.identity.required_predecessor",
        errors,
    )
    if predecessor is not None:
        _integer(
            predecessor,
            "pr_number",
            "spec.identity.required_predecessor",
            errors,
        )
        _string(
            predecessor,
            "head_sha",
            "spec.identity.required_predecessor",
            errors,
            pattern=SHA40_RE,
        )
        _string(
            predecessor,
            "merge_sha",
            "spec.identity.required_predecessor",
            errors,
            pattern=SHA40_RE,
        )
    _string(identity, "objective", "spec.identity", errors, maximum=2000)
    if "capital_at_risk_usd" in identity:
        amount = identity["capital_at_risk_usd"]
        if not _is_number(amount):
            errors.append(
                _error("FIELD_TYPE_INVALID", "spec.identity.capital_at_risk_usd")
            )
        elif amount < 0:
            errors.append(
                _error("FIELD_VALUE_INVALID", "spec.identity.capital_at_risk_usd")
            )
    explicit = _boolean(
        identity, "xl_explicit_authorization", "spec.identity", errors
    )
    basis = identity.get("xl_authorization_basis")
    if size == "XL":
        if explicit is not True:
            errors.append(
                _error(
                    "FIELD_VALUE_INVALID",
                    "spec.identity.xl_explicit_authorization",
                )
            )
        if not isinstance(basis, str):
            errors.append(
                _error("FIELD_TYPE_INVALID", "spec.identity.xl_authorization_basis")
            )
        elif not 1 <= len(basis) <= 1000:
            errors.append(
                _error("FIELD_VALUE_INVALID", "spec.identity.xl_authorization_basis")
            )
    elif basis is not None:
        errors.append(
            _error("FIELD_VALUE_INVALID", "spec.identity.xl_authorization_basis")
        )
    return identity


def _validate_scope(
    root: Mapping[str, object], errors: list[dict[str, str]]
) -> Mapping[str, object] | None:
    scope = _object_keys(root.get("scope"), SCOPE_KEYS, "spec.scope", errors)
    if scope is None:
        return None
    for key, maximum in (
        ("required_changed_files", 35),
        ("allowed_changed_files", 35),
        ("historical_compatibility_edits", 35),
        ("forbidden_prefixes", 64),
    ):
        paths = _string_array(
            scope, key, "spec.scope", errors, maximum=maximum, unique=True
        )
        if paths is not None:
            directory = key == "forbidden_prefixes"
            for index, value in enumerate(paths):
                if not _valid_path(value, directory=directory):
                    errors.append(
                        _error(
                            "FIELD_VALUE_INVALID",
                            f"spec.scope.{key}[{index}]",
                        )
                    )
    _integer(scope, "max_changed_files", "spec.scope", errors)
    _boolean(scope, "exact_scope_required", "spec.scope", errors)
    _string(scope, "rollback_surface", "spec.scope", errors, maximum=2000)
    boundaries = scope.get("mode_boundaries")
    if not isinstance(boundaries, list):
        if "mode_boundaries" in scope:
            errors.append(
                _error("FIELD_TYPE_INVALID", "spec.scope.mode_boundaries")
            )
    else:
        names: list[str] = []
        for index, raw in enumerate(boundaries):
            path = f"spec.scope.mode_boundaries[{index}]"
            item = _object_keys(raw, ("boundary", "crossed"), path, errors)
            if item is None:
                continue
            name = _string(item, "boundary", path, errors, pattern=LOWER_TOKEN_RE)
            _boolean(item, "crossed", path, errors)
            if name is not None:
                if name in names:
                    errors.append(_error("FIELD_VALUE_INVALID", f"{path}.boundary"))
                names.append(name)
    return scope


def _validate_authority(
    root: Mapping[str, object], errors: list[dict[str, str]]
) -> Mapping[str, object] | None:
    authority = _object_keys(
        root.get("authority"), AUTHORITY_KEYS, "spec.authority", errors
    )
    if authority is not None:
        for key in AUTHORITY_KEYS:
            _boolean(authority, key, "spec.authority", errors)
    return authority


def _validate_applicability_schema(
    section_name: str,
    root: Mapping[str, object],
    errors: list[dict[str, str]],
) -> Mapping[str, object] | None:
    path = f"spec.{section_name}"
    section = _object_keys(
        root.get(section_name), APPLICABILITY_KEYS, path, errors
    )
    if section is None:
        return None
    _boolean(section, "applicable", path, errors)
    _string(section, "reason", path, errors, maximum=1000)
    items = section.get("items")
    if not isinstance(items, list):
        if "items" in section:
            errors.append(_error("FIELD_TYPE_INVALID", f"{path}.items"))
        return section
    if len(items) > MAX_ARRAY_LENGTH:
        errors.append(_error("FIELD_VALUE_INVALID", f"{path}.items"))
    for index, raw in enumerate(items):
        item_path = f"{path}.items[{index}]"
        item = _object_keys(raw, ITEM_KEYS[section_name], item_path, errors)
        if item is None:
            continue
        if section_name == "api_matrix":
            for key, maximum in (
                ("surface", 300),
                ("before", 1000),
                ("after", 1000),
                ("compatibility_requirement", 1000),
            ):
                _string(item, key, item_path, errors, maximum=maximum)
            _boolean(item, "change_authorized", item_path, errors)
            _string(item, "authority", item_path, errors, pattern=TOKEN_RE)
        elif section_name == "semantic_fields":
            _string(item, "path", item_path, errors, pattern=DOT_PATH_RE)
            _string(
                item,
                "source",
                item_path,
                errors,
                choices=("CALLER", "CONSTANT", "DERIVED"),
            )
            _string(item, "type", item_path, errors, maximum=128)
            for key in ("required_rule", "validation_rule", "safe_output"):
                _string(item, key, item_path, errors, maximum=1000)
            _boolean(item, "mutable", item_path, errors)
            _string(
                item,
                "identity_role",
                item_path,
                errors,
                choices=("COMMITTED", "EXCLUDED", "NONE"),
            )
            _string(item, "failure_category", item_path, errors, pattern=TOKEN_RE)
            for nullable in ("exclusion_reason", "derivation_rule_id"):
                if nullable in item and item[nullable] is not None:
                    if not isinstance(item[nullable], str):
                        errors.append(
                            _error("FIELD_TYPE_INVALID", f"{item_path}.{nullable}")
                        )
                    elif not 1 <= len(item[nullable]) <= 1000:
                        errors.append(
                            _error("FIELD_VALUE_INVALID", f"{item_path}.{nullable}")
                        )
        elif section_name == "identity_derivations":
            _string(item, "rule_id", item_path, errors, pattern=LOWER_TOKEN_RE)
            _string(item, "target_path", item_path, errors, pattern=DOT_PATH_RE)
            _string(
                item,
                "algorithm",
                item_path,
                errors,
                choices=("SHA256_RAW_BYTES", "SHA256_CANONICAL_JSON"),
            )
            for key in ("source_paths", "excluded_paths"):
                values = _string_array(
                    item, key, item_path, errors, unique=True
                )
                if values is not None:
                    for item_index, value in enumerate(values):
                        if DOT_PATH_RE.fullmatch(value) is None:
                            errors.append(
                                _error(
                                    "FIELD_VALUE_INVALID",
                                    f"{item_path}.{key}[{item_index}]",
                                )
                            )
            _string(item, "prefix", item_path, errors, 0, 128)
            canonicalization = item.get("canonicalization")
            if canonicalization is not None and not isinstance(
                canonicalization, Mapping
            ):
                errors.append(
                    _error(
                        "FIELD_TYPE_INVALID", f"{item_path}.canonicalization"
                    )
                )
        elif section_name == "state_transitions":
            for key in ("from_state", "to_state", "failure_category"):
                _string(item, key, item_path, errors, pattern=TOKEN_RE)
            _string(item, "condition", item_path, errors, maximum=2000)
        elif section_name == "failure_precedence":
            _string(item, "condition_id", item_path, errors, pattern=LOWER_TOKEN_RE)
            _string(item, "category", item_path, errors, pattern=TOKEN_RE)
            _integer(item, "priority", item_path, errors)
        elif section_name == "examples":
            _string(item, "example_id", item_path, errors, maximum=200)
            _boolean(item, "expected_valid", item_path, errors)
            _string_array(
                item, "expected_error_codes", item_path, errors, unique=True
            )
            _integer(item, "intended_fault_count", item_path, errors, minimum=0)
            _string_array(
                item, "derivation_rule_ids", item_path, errors, unique=True
            )
            if "input" in item and not isinstance(item["input"], dict):
                errors.append(_error("FIELD_TYPE_INVALID", f"{item_path}.input"))
        elif section_name == "evidence_plan":
            _string(item, "requirement_id", item_path, errors, pattern=REQUIREMENT_RE)
            for key in ("source", "test", "command", "expected_result"):
                value = _string(item, key, item_path, errors, maximum=4000)
                if key == "command" and value is not None and (
                    "\n" in value or "\x00" in value
                ):
                    errors.append(_error("FIELD_VALUE_INVALID", f"{item_path}.command"))
    return section


def _validate_successor_schema(
    root: Mapping[str, object], errors: list[dict[str, str]]
) -> Mapping[str, object] | None:
    path = "spec.successor_boundary"
    successor = _object_keys(
        root.get("successor_boundary"),
        (
            "next_wp",
            "next_title",
            "separately_gated",
            "feature_validator_moved_to",
            "forbidden_in_this_wp",
        ),
        path,
        errors,
    )
    if successor is None:
        return None
    for key in ("next_wp", "feature_validator_moved_to"):
        _string(successor, key, path, errors, pattern=WP_ID_RE)
    _string(successor, "next_title", path, errors, maximum=300)
    _boolean(successor, "separately_gated", path, errors)
    values = _string_array(
        successor,
        "forbidden_in_this_wp",
        path,
        errors,
        maximum=128,
        allow_empty=False,
        unique=True,
    )
    if values is not None:
        for index, value in enumerate(values):
            if not 1 <= len(value) <= 500:
                errors.append(
                    _error(
                        "FIELD_VALUE_INVALID",
                        f"{path}.forbidden_in_this_wp[{index}]",
                    )
                )
    return successor


def _schema_errors(document: object) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    errors: list[dict[str, str]] = []
    if not isinstance(document, Mapping):
        return [_error("FIELD_TYPE_INVALID", "spec")], None
    root = _object_keys(document, TOP_KEYS, "spec", errors)
    if root is None:
        return errors, None
    schema_id = root.get("schema_id")
    schema_version = root.get("schema_version")
    for key in ("schema_id", "schema_version"):
        if key in root and not isinstance(root[key], str):
            errors.append(_error("FIELD_TYPE_INVALID", f"spec.{key}"))
    if (
        isinstance(schema_id, str)
        and isinstance(schema_version, str)
        and (
            schema_id != SPEC_SCHEMA_ID
            or schema_version != SPEC_SCHEMA_VERSION
        )
    ):
        errors.append(_error("SCHEMA_UNSUPPORTED", "spec"))
    _validate_identity(root, errors)
    _validate_scope(root, errors)
    _validate_authority(root, errors)
    for section in ITEM_KEYS:
        _validate_applicability_schema(section, root, errors)
    _validate_successor_schema(root, errors)
    return errors, dict(root)


def _unique_error(
    values: list[object], field_paths: list[str], errors: list[dict[str, str]], code: str
) -> None:
    seen: list[object] = []
    for value, field_path in zip(values, field_paths):
        if value in seen:
            errors.append(_error(code, field_path))
        seen.append(value)


def _is_dependency_or_lock(path: str) -> bool:
    basename = path.rsplit("/", 1)[-1]
    return basename in DEPENDENCY_LOCK_BASENAMES or any(
        basename.endswith(suffix) for suffix in DEPENDENCY_LOCK_SUFFIXES
    )


def _is_generated_artifact(path: str) -> bool:
    if any(
        path.startswith(prefix) or path == prefix.rstrip("/")
        for prefix in GENERATED_ARTIFACT_PREFIXES
    ):
        return True
    basename = path.rsplit("/", 1)[-1]
    return basename in GENERATED_ARTIFACT_EXACT or any(
        basename.endswith(suffix) for suffix in GENERATED_ARTIFACT_SUFFIXES
    )


def _is_protected_builtin(path: str) -> bool:
    basename = path.rsplit("/", 1)[-1]
    if any(path.startswith(prefix) for prefix in PROTECTED_PREFIXES_BUILTIN):
        return True
    if basename in PROTECTED_EXACT_BUILTIN:
        return True
    if any(
        path.startswith(prefix)
        or basename.startswith(prefix.lstrip("."))
        for prefix in PROTECTED_STARTSWITH_BUILTIN
    ):
        return True
    return any(pattern.search(path) for pattern in CREDENTIAL_LIKE_PATTERNS)


# Exact governance path. The pull-request template is the canonical post-WP91
# current-review evidence surface. It is not under ``.github/workflows/`` so it has no
# authority mapping from the prefix cascade; authorizing it therefore needs an explicit
# narrow exact-path rule requiring BOTH workflow_governance and canonical_evidence_policy.
# No other ``.github/`` path is affected and ``.github/workflows/`` semantics are unchanged.
PR_TEMPLATE_GOVERNANCE_PATH = ".github/pull_request_template.md"
PR_TEMPLATE_GOVERNANCE_AUTHORITY = ("workflow_governance", "canonical_evidence_policy")


def _wp_artifact_paths(wp_id: str) -> frozenset[str]:
    prefix = f"docs/wp_specs/{wp_id}/"
    return frozenset(
        {
            f"{prefix}wp_prompt.txt",
            f"{prefix}wp_spec.json",
            f"{prefix}draftability_certificate.json",
        }
    )


def _authority_requirements(path: str, wp_id: str) -> tuple[str, ...] | None:
    requirements: list[str] = []
    if path == PR_TEMPLATE_GOVERNANCE_PATH:
        return PR_TEMPLATE_GOVERNANCE_AUTHORITY
    if path.startswith("docs/"):
        requirements.append("docs")
    elif path.startswith("tests/"):
        requirements.append("tests")
    elif path.startswith("src/"):
        requirements.append("source_runtime")
    elif path.startswith(".github/workflows/"):
        requirements.append("workflow_files")
    elif path.startswith("tools/"):
        requirements.append("local_offline_tooling")
    else:
        if _is_dependency_or_lock(path):
            requirements.append("dependencies")
        else:
            return None
    if _is_dependency_or_lock(path) and "dependencies" not in requirements:
        requirements.append("dependencies")
    if path.startswith(("tools/hermes/", "agent_runtime/", "agent_memory/")):
        requirements.append("hermes_runtime")
    if _is_protected_builtin(path) and not path.startswith(
        ("tools/hermes/", "agent_runtime/", "agent_memory/")
    ):
        requirements.append("credentials")
    if path.startswith("docs/wp_specs/"):
        if path not in _wp_artifact_paths(wp_id):
            return None
        requirements.append("canonical_evidence_policy")
    return tuple(requirements)


def _resolve_dot(root: object, path: str) -> object:
    current = root
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            raise KeyError()
        current = current[segment]
    return current


def _remove_descendant(root: object, source: str, excluded: str) -> None:
    relative = excluded[len(source) + 1 :].split(".")
    current = root
    for segment in relative[:-1]:
        if not isinstance(current, dict) or segment not in current:
            raise KeyError()
        current = current[segment]
    if not isinstance(current, dict) or relative[-1] not in current:
        raise KeyError()
    del current[relative[-1]]


def _canonical_derived_value(rule: Mapping[str, object], input_value: dict) -> str:
    source_paths = rule["source_paths"]
    excluded_paths = rule["excluded_paths"]
    projected: dict[str, object] = {}
    for source in source_paths:
        value = copy.deepcopy(_resolve_dot(input_value, source))
        for excluded in excluded_paths:
            if excluded.startswith(source + "."):
                _remove_descendant(value, source, excluded)
        projected[source] = value
    raw = json.dumps(
        projected,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return str(rule["prefix"]) + hashlib.sha256(raw).hexdigest()


def _semantic_errors(spec: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    identity = spec["identity"]
    scope = spec["scope"]
    authority = spec["authority"]
    size = identity["package_size_class"]
    maximum = scope["max_changed_files"]
    budget = {"S": 5, "M": 10, "L": 20}.get(size)
    if budget is not None and maximum > budget:
        errors.append(_error("SCOPE_POLICY_INVALID", "spec.scope.max_changed_files"))
    required = scope["required_changed_files"]
    allowed = scope["allowed_changed_files"]
    historical = scope["historical_compatibility_edits"]
    if len(required) > maximum:
        errors.append(_error("SCOPE_POLICY_INVALID", "spec.scope.required_changed_files"))
    if any(path not in allowed for path in required):
        errors.append(_error("SCOPE_POLICY_INVALID", "spec.scope.required_changed_files"))
    if any(path not in allowed for path in historical):
        errors.append(
            _error(
                "SCOPE_POLICY_INVALID",
                "spec.scope.historical_compatibility_edits",
            )
        )
    for field in ("required_changed_files", "allowed_changed_files"):
        for index, path in enumerate(scope[field]):
            field_path = f"spec.scope.{field}[{index}]"
            if (
                path.startswith("docs/wp_specs/")
                and path not in _wp_artifact_paths(identity["wp_id"])
            ):
                errors.append(_error("SCOPE_POLICY_INVALID", field_path))
                continue
            if any(path.startswith(prefix) for prefix in scope["forbidden_prefixes"]):
                errors.append(_error("SCOPE_POLICY_INVALID", field_path))
                continue
            if scope["exact_scope_required"] and (
                _is_protected_builtin(path) or _is_generated_artifact(path)
            ):
                errors.append(_error("SCOPE_POLICY_INVALID", field_path))
                continue
            needs = _authority_requirements(path, identity["wp_id"])
            if needs is None or any(authority[need] is not True for need in needs):
                errors.append(_error("AUTHORITY_CONTRADICTION", field_path))

    categories = [
        item["category"] for item in spec["failure_precedence"]["items"]
    ]
    for section_name in ITEM_KEYS:
        section = spec[section_name]
        if section["applicable"] is True and not section["items"]:
            errors.append(
                _error("SEMANTIC_CONTRADICTION", f"spec.{section_name}.items")
            )
        if section["applicable"] is False and section["items"]:
            errors.append(
                _error("SEMANTIC_CONTRADICTION", f"spec.{section_name}.items")
            )

    api_items = spec["api_matrix"]["items"]
    _unique_error(
        [item["surface"] for item in api_items],
        [f"spec.api_matrix.items[{i}].surface" for i in range(len(api_items))],
        errors,
        "SEMANTIC_CONTRADICTION",
    )
    derivations = spec["identity_derivations"]["items"]
    derivation_ids = [item["rule_id"] for item in derivations]
    _unique_error(
        derivation_ids,
        [
            f"spec.identity_derivations.items[{i}].rule_id"
            for i in range(len(derivations))
        ],
        errors,
        "IDENTITY_DERIVATION_INVALID",
    )
    _unique_error(
        [item["target_path"] for item in derivations],
        [
            f"spec.identity_derivations.items[{i}].target_path"
            for i in range(len(derivations))
        ],
        errors,
        "IDENTITY_DERIVATION_INVALID",
    )
    for index, rule in enumerate(derivations):
        path = f"spec.identity_derivations.items[{index}]"
        sources = rule["source_paths"]
        excluded = rule["excluded_paths"]
        if set(sources).intersection(excluded):
            errors.append(_error("IDENTITY_DERIVATION_INVALID", path))
        if rule["algorithm"] == "SHA256_RAW_BYTES":
            if (
                len(sources) != 1
                or sources[0]
                not in ("$external.wp_file_bytes", "$external.wp_spec_file_bytes")
                or excluded
                or rule["prefix"] != ""
                or rule["canonicalization"] is not None
            ):
                errors.append(_error("IDENTITY_DERIVATION_INVALID", path))
        else:
            if not sources:
                errors.append(
                    _error(
                        "IDENTITY_DERIVATION_INVALID",
                        f"{path}.source_paths",
                    )
                )
            for field_name, values in (
                ("source_paths", sources),
                ("excluded_paths", excluded),
            ):
                for item_index, value in enumerate(values):
                    if value.startswith("$external."):
                        errors.append(
                            _error(
                                "IDENTITY_DERIVATION_INVALID",
                                f"{path}.{field_name}[{item_index}]",
                            )
                        )
            if rule["target_path"].startswith("$external."):
                errors.append(
                    _error(
                        "IDENTITY_DERIVATION_INVALID",
                        f"{path}.target_path",
                    )
                )
            if rule["canonicalization"] != CANONICALIZATION:
                errors.append(
                    _error(
                        "IDENTITY_DERIVATION_INVALID",
                        f"{path}.canonicalization",
                    )
                )
            if any(
                left == right
                or left.startswith(right + ".")
                or right.startswith(left + ".")
                for pos, left in enumerate(sources)
                for right in sources[pos + 1 :]
            ):
                errors.append(_error("IDENTITY_DERIVATION_INVALID", path))
            for exclusion in excluded:
                parents = [s for s in sources if exclusion.startswith(s + ".")]
                if len(parents) != 1:
                    errors.append(_error("IDENTITY_DERIVATION_INVALID", path))
            target = rule["target_path"]
            if any(
                target == source or target.startswith(source + ".")
                for source in sources
            ) and target not in excluded:
                errors.append(_error("IDENTITY_DERIVATION_INVALID", path))

    semantic_items = spec["semantic_fields"]["items"]
    _unique_error(
        [item["path"] for item in semantic_items],
        [
            f"spec.semantic_fields.items[{i}].path"
            for i in range(len(semantic_items))
        ],
        errors,
        "SEMANTIC_CONTRADICTION",
    )
    for index, item in enumerate(semantic_items):
        path = f"spec.semantic_fields.items[{index}]"
        if item["failure_category"] not in categories:
            errors.append(_error("SEMANTIC_CONTRADICTION", f"{path}.failure_category"))
        if item["identity_role"] == "EXCLUDED":
            if item["mutable"] is True or not isinstance(
                item["exclusion_reason"], str
            ):
                errors.append(_error("SEMANTIC_CONTRADICTION", path))
        elif item["exclusion_reason"] is not None:
            errors.append(_error("SEMANTIC_CONTRADICTION", f"{path}.exclusion_reason"))
        derivation_rule_id = item["derivation_rule_id"]
        if (
            item["source"] == "DERIVED"
            and item["identity_role"] == "COMMITTED"
            and (
                derivation_rule_id is None
                or derivation_rule_id not in derivation_ids
            )
        ):
            errors.append(_error("SEMANTIC_CONTRADICTION", f"{path}.derivation_rule_id"))
        elif (
            item["source"] == "DERIVED"
            and derivation_rule_id is not None
            and derivation_rule_id not in derivation_ids
        ):
            errors.append(_error("SEMANTIC_CONTRADICTION", f"{path}.derivation_rule_id"))
        elif item["source"] != "DERIVED" and derivation_rule_id is not None:
            errors.append(_error("SEMANTIC_CONTRADICTION", f"{path}.derivation_rule_id"))

    transitions = spec["state_transitions"]["items"]
    pairs: list[tuple[str, str]] = []
    for index, item in enumerate(transitions):
        path = f"spec.state_transitions.items[{index}]"
        pair = (item["from_state"], item["to_state"])
        if pair in pairs or pair[0] == pair[1]:
            errors.append(_error("SEMANTIC_CONTRADICTION", path))
        pairs.append(pair)
        if item["failure_category"] not in categories:
            errors.append(_error("SEMANTIC_CONTRADICTION", f"{path}.failure_category"))

    if tuple(spec["failure_precedence"]["items"]) != FIXED_FAILURE_ITEMS:
        errors.append(
            _error("FAILURE_PRECEDENCE_INVALID", "spec.failure_precedence.items")
        )

    examples = spec["examples"]["items"]
    example_ids: list[str] = []
    covered_canonical_rules: set[str] = set()
    for index, item in enumerate(examples):
        path = f"spec.examples.items[{index}]"
        if item["example_id"] in example_ids:
            errors.append(_error("EXAMPLE_TRUTH_INVALID", f"{path}.example_id"))
        example_ids.append(item["example_id"])
        expected = item["expected_error_codes"]
        if any(code not in categories for code in expected):
            errors.append(_error("EXAMPLE_TRUTH_INVALID", f"{path}.expected_error_codes"))
        if expected != sorted(expected, key=categories.index):
            errors.append(_error("EXAMPLE_TRUTH_INVALID", f"{path}.expected_error_codes"))
        if any(rule_id not in derivation_ids for rule_id in item["derivation_rule_ids"]):
            errors.append(_error("EXAMPLE_TRUTH_INVALID", f"{path}.derivation_rule_ids"))
        if item["expected_valid"]:
            if expected or item["intended_fault_count"] != 0:
                errors.append(_error("EXAMPLE_TRUTH_INVALID", path))
        elif item["intended_fault_count"] != 1 or not expected:
            errors.append(_error("EXAMPLE_TRUTH_INVALID", path))
        for rule_id in item["derivation_rule_ids"]:
            rule = derivations[derivation_ids.index(rule_id)]
            if rule["algorithm"] != "SHA256_CANONICAL_JSON":
                continue
            try:
                actual = _resolve_dot(item["input"], rule["target_path"])
                derived = _canonical_derived_value(rule, item["input"])
                if not isinstance(actual, str) or actual != derived:
                    raise ValueError()
                if item["expected_valid"] is True:
                    covered_canonical_rules.add(rule_id)
            except (KeyError, TypeError, ValueError, UnicodeError):
                errors.append(_error("EXAMPLE_TRUTH_INVALID", path))
    for index, rule in enumerate(derivations):
        if (
            rule["algorithm"] == "SHA256_CANONICAL_JSON"
            and rule["rule_id"] not in covered_canonical_rules
        ):
            errors.append(
                _error(
                    "EXAMPLE_TRUTH_INVALID",
                    f"spec.identity_derivations.items[{index}].rule_id",
                )
            )

    evidence = spec["evidence_plan"]["items"]
    _unique_error(
        [item["requirement_id"] for item in evidence],
        [
            f"spec.evidence_plan.items[{i}].requirement_id"
            for i in range(len(evidence))
        ],
        errors,
        "SEMANTIC_CONTRADICTION",
    )
    successor = spec["successor_boundary"]
    if successor["separately_gated"] is not True:
        errors.append(
            _error(
                "SEMANTIC_CONTRADICTION",
                "spec.successor_boundary.separately_gated",
            )
        )
    return errors


def validate_spec_document(
    document: object,
) -> tuple[dict[str, object] | None, tuple[dict[str, str], ...]]:
    """Validate a JSON-compatible specification without side effects or raises."""
    try:
        if not _walk_json(document):
            return None, (_error("FIELD_VALUE_INVALID", "spec"),)
        schema_errors, spec = _schema_errors(document)
        ordered_schema_errors = _ordered_errors(schema_errors)
        if ordered_schema_errors:
            return None, ordered_schema_errors
        assert spec is not None
        semantic_errors = _ordered_errors(_semantic_errors(spec))
        if semantic_errors:
            return None, semantic_errors
        return copy.deepcopy(spec), ()
    except (TypeError, ValueError, UnicodeError, OSError, RecursionError):
        return None, (_error("FIELD_VALUE_INVALID", "spec"),)


def _read_regular(path: pathlib.Path, maximum: int) -> bytes | None:
    try:
        if not path.is_file():
            return None
        size = path.stat().st_size
        if size > maximum:
            return None
        data = path.read_bytes()
        if len(data) > maximum:
            return None
        return data
    except (OSError, ValueError):
        return None


def read_and_validate_spec_scope(
    path: str | pathlib.Path,
) -> tuple[dict[str, object] | None, tuple[dict[str, str], ...]]:
    """Read one bounded spec and return its exact validated scope contract."""
    try:
        raw = _read_regular(pathlib.Path(path), MAX_SPEC_BYTES)
        if raw is None:
            return None, (_error("FILE_READ_ERROR", "files.spec"),)
        document = _strict_json(raw)
    except (TypeError, ValueError, UnicodeError, OSError, RecursionError):
        return None, (_error("JSON_PARSE_INVALID", "spec"),)
    spec, errors = validate_spec_document(document)
    if spec is None:
        return None, errors
    identity = spec["identity"]
    scope = spec["scope"]
    result: dict[str, object] = {
        "schema_version": spec["schema_version"],
        "package_class": identity["package_class"],
        "required_changed_files": tuple(scope["required_changed_files"]),
        "allowed_changed_files": tuple(scope["allowed_changed_files"]),
        "forbidden_prefixes": tuple(scope["forbidden_prefixes"]),
        "max_changed_files": scope["max_changed_files"],
        "exact_scope_required": scope["exact_scope_required"],
        "authority": copy.deepcopy(spec["authority"]),
    }
    return result, ()


def _certificate_schema_errors(
    document: object,
) -> tuple[list[dict[str, str]], str | None]:
    errors: list[dict[str, str]] = []
    if not isinstance(document, Mapping):
        return [_error("FIELD_TYPE_INVALID", "certificate")], None
    schema_id = document.get("schema_id")
    mode = "waiver" if schema_id == WAIVER_SCHEMA_ID else "certificate"
    expected = WAIVER_KEYS if mode == "waiver" else NORMAL_CERTIFICATE_KEYS
    cert = _object_keys(document, expected, "certificate", errors)
    if cert is None:
        return errors, mode
    if not isinstance(schema_id, str) or not isinstance(
        cert.get("schema_version"), str
    ):
        errors.append(_error("FIELD_TYPE_INVALID", "certificate"))
    elif schema_id not in (CERTIFICATE_SCHEMA_ID, WAIVER_SCHEMA_ID) or cert[
        "schema_version"
    ] != "1.0.0":
        errors.append(_error("SCHEMA_UNSUPPORTED", "certificate"))
    _string(cert, "wp_id", "certificate", errors, pattern=WP_ID_RE)
    for key in ("wp_text_sha256", "wp_spec_sha256"):
        _string(cert, key, "certificate", errors, pattern=SHA256_RE)
    decisions = cert.get("unresolved_decisions")
    if not isinstance(decisions, list):
        if "unresolved_decisions" in cert:
            errors.append(
                _error(
                    "FIELD_TYPE_INVALID", "certificate.unresolved_decisions"
                )
            )
    elif len(decisions) > MAX_ARRAY_LENGTH:
        errors.append(
            _error("FIELD_VALUE_INVALID", "certificate.unresolved_decisions")
        )
    if mode == "waiver":
        for key in (
            "waiver_mode",
            "authorization_source",
        ):
            _string(cert, key, "certificate", errors, pattern=TOKEN_RE)
        for key in (
            "implementation_authorized",
            "ready_for_review_authorized",
            "merge_authorized",
            "independent_live_pr_review_required",
        ):
            _boolean(cert, key, "certificate", errors)
    else:
        _string(
            cert,
            "reviewed_repository",
            "certificate",
            errors,
            3,
            200,
            REPOSITORY_RE,
        )
        _string(
            cert,
            "reviewed_base_merge_sha",
            "certificate",
            errors,
            pattern=SHA40_RE,
        )
        for key in (
            "reviewer_role",
            "independence_attestation",
            "result",
            "implementability_simulation",
        ):
            _string(cert, key, "certificate", errors, pattern=TOKEN_RE)
        lenses = cert.get("covered_lenses")
        if not isinstance(lenses, list):
            if "covered_lenses" in cert:
                errors.append(
                    _error("FIELD_TYPE_INVALID", "certificate.covered_lenses")
                )
        else:
            for index, raw in enumerate(lenses):
                path = f"certificate.covered_lenses[{index}]"
                item = _object_keys(raw, ("lens", "result"), path, errors)
                if item is not None:
                    _string(item, "lens", path, errors, pattern=LOWER_TOKEN_RE)
                    _string(item, "result", path, errors, pattern=TOKEN_RE)
    return errors, mode


def _certificate_draftability_errors(
    cert: Mapping[str, object], spec: Mapping[str, object], mode: str
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    identity = spec["identity"]
    if cert["wp_id"] != identity["wp_id"]:
        errors.append(_error("DRAFTABILITY_INCOMPLETE", "certificate.wp_id"))
    if cert["unresolved_decisions"] != []:
        errors.append(
            _error("DRAFTABILITY_INCOMPLETE", "certificate.unresolved_decisions")
        )
    if mode == "waiver":
        required_values = {
            "waiver_mode": "WAIVED_FOR_LOW_RISK_DRAFT_PR_IMPLEMENTATION",
            "authorization_source": "EXPLICIT_USER_AUTHORIZATION",
            "implementation_authorized": True,
            "ready_for_review_authorized": False,
            "merge_authorized": False,
            "independent_live_pr_review_required": True,
        }
        for key, expected in required_values.items():
            if cert[key] != expected:
                errors.append(
                    _error("DRAFTABILITY_INCOMPLETE", f"certificate.{key}")
                )
        dangerous = (
            "source_runtime",
            "workflow_files",
            "dependencies",
            "network",
            "credentials",
            "scheduler",
            "hermes_runtime",
            "strategy",
            "paper",
            "execution",
            "live",
        )
        predecessor = identity["required_predecessor"]
        fixed_identity_matches = (
            identity["wp_id"] == "WP159"
            and identity["repository"] == WP159_WAIVER_REPOSITORY
            and identity["package_class"] == WP159_WAIVER_PACKAGE_CLASS
            and identity["base_branch"] == WP159_WAIVER_BASE_BRANCH
            and predecessor["pr_number"] == WP159_WAIVER_PREDECESSOR_PR
            and predecessor["head_sha"] == WP159_WAIVER_PREDECESSOR_HEAD
            and predecessor["merge_sha"] == WP159_WAIVER_PREDECESSOR_MERGE
        )
        fixed_hashes_match = (
            cert["wp_text_sha256"] == WP159_WAIVER_WP_SHA256
            and cert["wp_spec_sha256"] == WP159_WAIVER_SPEC_SHA256
        )
        if (
            not fixed_identity_matches
            or identity["risk_level"] not in (0, 1)
            or identity["capital_at_risk_usd"] != 0
            or any(spec["authority"][key] is not False for key in dangerous)
            or not fixed_hashes_match
        ):
            errors.append(
                _error("DRAFTABILITY_INCOMPLETE", "certificate.waiver_mode")
            )
    else:
        comparisons = (
            ("reviewed_repository", identity["repository"]),
            (
                "reviewed_base_merge_sha",
                identity["required_predecessor"]["merge_sha"],
            ),
            ("reviewer_role", "INDEPENDENT_DRAFTABILITY_REVIEWER"),
            (
                "independence_attestation",
                "SEPARATE_REVIEW_CONTEXT_DECLARED",
            ),
            ("result", "PASS"),
            ("implementability_simulation", "PASS"),
        )
        for key, expected in comparisons:
            if cert[key] != expected:
                errors.append(
                    _error("DRAFTABILITY_INCOMPLETE", f"certificate.{key}")
                )
        lenses = cert["covered_lenses"]
        expected_lenses = [
            {"lens": lens, "result": "PASS"} for lens in LENS_ORDER
        ]
        if lenses != expected_lenses:
            errors.append(
                _error("DRAFTABILITY_INCOMPLETE", "certificate.covered_lenses")
            )
    return errors


def _result(
    status: str,
    checked: list[str],
    errors: list[dict[str, str]] | tuple[dict[str, str], ...],
    *,
    wp_id: str | None = None,
    wp_hash: str | None = None,
    spec_hash: str | None = None,
) -> dict[str, object]:
    return {
        "schema_id": RESULT_SCHEMA_ID,
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": status,
        "wp_id": wp_id,
        "wp_text_sha256": wp_hash,
        "wp_spec_sha256": spec_hash,
        "checked_sections": checked,
        "errors": list(_ordered_errors(list(errors))),
    }


def render_text(result: Mapping[str, object]) -> str:
    lines: list[str] = []
    for key in (
        "schema_id",
        "schema_version",
        "status",
        "wp_id",
        "wp_text_sha256",
        "wp_spec_sha256",
        "checked_sections",
        "errors",
    ):
        value = result[key]
        if value is None:
            rendered = "null"
        elif isinstance(value, str):
            rendered = value
        else:
            rendered = json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        lines.append(f"{key}: {rendered}")
    return "\n".join(lines) + "\n"


def render_json(result: Mapping[str, object]) -> str:
    return (
        json.dumps(
            result,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n"
    )


class _QuietParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError()


def _parse_args(argv: list[str] | None) -> argparse.Namespace | None:
    parser = _QuietParser(add_help=True)
    parser.add_argument("--wp")
    parser.add_argument("--spec")
    parser.add_argument("--certificate")
    parser.add_argument("--format", default="text")
    try:
        args = parser.parse_args(argv)
    except (SystemExit, ValueError):
        return None
    if (
        not args.wp
        or not args.spec
        or not args.certificate
        or args.format not in ("text", "json")
    ):
        return None
    return args


def _validate_package(args: argparse.Namespace) -> tuple[dict[str, object], int]:
    checked = ["files"]
    wp_raw = _read_regular(pathlib.Path(args.wp), MAX_WP_BYTES)
    spec_raw = _read_regular(pathlib.Path(args.spec), MAX_SPEC_BYTES)
    cert_raw = _read_regular(pathlib.Path(args.certificate), MAX_CERTIFICATE_BYTES)
    file_errors: list[dict[str, str]] = []
    if wp_raw is None:
        file_errors.append(_error("FILE_READ_ERROR", "files.wp"))
    if spec_raw is None:
        file_errors.append(_error("FILE_READ_ERROR", "files.spec"))
    if cert_raw is None:
        file_errors.append(_error("FILE_READ_ERROR", "files.certificate"))
    if file_errors:
        return _result("USAGE_ERROR", checked, file_errors), 2
    assert wp_raw is not None and spec_raw is not None and cert_raw is not None
    wp_hash = hashlib.sha256(wp_raw).hexdigest()
    spec_hash = hashlib.sha256(spec_raw).hexdigest()

    checked.append("spec_json")
    try:
        spec_document = _strict_json(spec_raw)
    except (TypeError, ValueError, UnicodeError, OSError, RecursionError):
        return (
            _result(
                "FAIL",
                checked,
                [_error("JSON_PARSE_INVALID", "spec")],
                wp_hash=wp_hash,
                spec_hash=spec_hash,
            ),
            1,
        )
    checked.append("spec_schema")
    schema_errors, schema_spec = _schema_errors(spec_document)
    if schema_errors:
        return (
            _result(
                "FAIL",
                checked,
                schema_errors,
                wp_hash=wp_hash,
                spec_hash=spec_hash,
            ),
            1,
        )
    assert schema_spec is not None
    checked.append("spec_semantics")
    semantic_errors = _semantic_errors(schema_spec)
    wp_id = schema_spec["identity"]["wp_id"]
    if semantic_errors:
        return (
            _result(
                "FAIL",
                checked,
                semantic_errors,
                wp_id=wp_id,
                wp_hash=wp_hash,
                spec_hash=spec_hash,
            ),
            1,
        )

    checked.append("certificate_json")
    try:
        cert_document = _strict_json(cert_raw)
    except (TypeError, ValueError, UnicodeError, OSError, RecursionError):
        return (
            _result(
                "FAIL",
                checked,
                [_error("JSON_PARSE_INVALID", "certificate")],
                wp_id=wp_id,
                wp_hash=wp_hash,
                spec_hash=spec_hash,
            ),
            1,
        )
    checked.append("certificate_schema")
    cert_schema_errors, mode = _certificate_schema_errors(cert_document)
    if cert_schema_errors:
        return (
            _result(
                "FAIL",
                checked,
                cert_schema_errors,
                wp_id=wp_id,
                wp_hash=wp_hash,
                spec_hash=spec_hash,
            ),
            1,
        )
    assert isinstance(cert_document, Mapping) and mode is not None
    checked.append("certificate_hashes")
    certificate_errors: list[dict[str, str]] = []
    for key, digest in (
        ("wp_text_sha256", wp_hash),
        ("wp_spec_sha256", spec_hash),
    ):
        if cert_document[key] != digest:
            certificate_errors.append(
                _error("CERTIFICATE_HASH_MISMATCH", f"certificate.{key}")
            )
    checked.append("certificate_draftability")
    certificate_errors.extend(
        _certificate_draftability_errors(cert_document, schema_spec, mode)
    )
    if certificate_errors:
        return (
            _result(
                "FAIL",
                checked,
                certificate_errors,
                wp_id=wp_id,
                wp_hash=wp_hash,
                spec_hash=spec_hash,
            ),
            1,
        )
    return (
        _result(
            "PASS",
            checked,
            [],
            wp_id=wp_id,
            wp_hash=wp_hash,
            spec_hash=spec_hash,
        ),
        0,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args is None:
        result = _result(
            "USAGE_ERROR",
            [],
            [_error("FIELD_VALUE_INVALID", "cli")],
        )
        sys.stdout.write(render_json(result) if "--format" in (argv or []) and "json" in (argv or []) else render_text(result))
        return 2
    result, exit_code = _validate_package(args)
    sys.stdout.write(render_json(result) if args.format == "json" else render_text(result))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
