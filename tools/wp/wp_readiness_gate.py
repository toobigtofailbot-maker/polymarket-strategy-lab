#!/usr/bin/env python3
"""Deterministic, local/offline pre-implementation package-readiness gate.

This tool composes the existing :mod:`wp_spec_guard` specification and certificate
validation with additional bounded checks. It mechanically derives a minimum
governance track from the specification's risk/authority fields. FAST and RUNTIME
packages may establish deterministic readiness without a certificate; PROTECTED
packages retain the independent exact-hash certificate requirement. It never grants
authorization: ``IMPLEMENTATION_READY`` means only that the package is technically
ready to be authorized by the user.

Design constraints (see docs/wp_specs/WP168G/wp_prompt.txt sections 4, 7, 11):
  * stdlib-only, import-safe, deterministic, bounded;
  * local / offline / read-only; no environment inspection; no network;
  * no product-runtime imports; the readiness validator executes no tests;
  * the sanitized result exposes only closed codes and trusted counts -- never raw
    prompt/spec/test/body content, exception text, or git output.

Exit contract:
  0  IMPLEMENTATION_READY
  1  NOT_IMPLEMENTATION_READY
  2  USAGE_OR_FILE_ERROR
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Mapping, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import wp_spec_guard  # noqa: E402  (local tool reuse; see section 4)

# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------

STATUS_READY = "IMPLEMENTATION_READY"
STATUS_NOT_READY = "NOT_IMPLEMENTATION_READY"
STATUS_USAGE = "USAGE_ERROR"

# Canonical (fixed) order for readiness error codes.
READINESS_ERROR_ORDER = (
    "READINESS_PACKAGE_GUARD_INVALID",
    "READINESS_CERTIFICATE_NOT_PASS",
    "READINESS_PROMPT_STRUCTURE_INVALID",
    "READINESS_GOVERNANCE_TRACK_INVALID",
    "READINESS_RULE_MATRIX_INVALID",
    "READINESS_SEMANTIC_CONTRADICTION",
    "READINESS_SCOPE_INVALID",
    "READINESS_EVIDENCE_NODE_MISSING",
    "READINESS_EVIDENCE_ASSERTION_INADEQUATE",
    "READINESS_STATE_INVALID",
    "READINESS_SUCCESSOR_BOUNDARY_INVALID",
    "READINESS_DIFF_SCOPE_MISMATCH",
)
_ERROR_RANK = {code: index for index, code in enumerate(READINESS_ERROR_ORDER)}

# Closed NORMATIVE_RULE_MATRIX_V1 action vocabulary.
ACTION_VOCAB = frozenset(
    {
        "REQUIRE",
        "OPTIONAL",
        "ACCEPT",
        "REJECT",
        "NORMALIZE_LOWERCASE",
        "NORMALIZE_UPPERCASE",
        "PRESERVE_EXPLICIT_NULL",
        "PRESERVE_EXACT",
        "FORBID",
    }
)

# Closed unresolved-placeholder vocabulary (section 5). Bounded: exactly these tokens.
PLACEHOLDER_TOKENS = ("TBD", "TODO", "<HEAD_SHA>", "<FILL_ME>", "<DECIDE>")

MATRIX_BEGIN = "BEGIN_NORMATIVE_RULE_MATRIX_V1"
MATRIX_END = "END_NORMATIVE_RULE_MATRIX_V1"
MATRIX_HEADER = "RULE_ID|DOMAIN|SUBJECT|CONDITION|ACTION|CANONICAL_EFFECT|SPEC_PATH|EVIDENCE_ID"

_RULE_ID_RE = re.compile(r"^NR\d{3}$")
_DOTTED_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_EFFECT_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_EVIDENCE_ID_RE = re.compile(r"^R\d{3}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PY_TARGET_RE = re.compile(r"(?<![\w./-])((?:[\w./-]+/)?[\w.-]+\.py)")
_TRACK_LINE_RE = re.compile(
    r"^[ \t]*Governance track expected: (FAST|RUNTIME|PROTECTED)[ \t]*\r?$",
    re.MULTILINE,
)
_WP_NUMBER_RE = re.compile(r"^WP([1-9][0-9]*)(?:[A-Z])?$")

GOVERNANCE_TRACKS = ("FAST", "RUNTIME", "PROTECTED")
_TRACK_RANK = {track: index for index, track in enumerate(GOVERNANCE_TRACKS)}
_LEGACY_CERTIFIED_MAX_WP = 171

# Canonical authorization chain (section 2 / state_transitions).
CANONICAL_STATE_CHAIN = (
    ("LOCAL_DRAFT", "DRAFTABILITY_PASS"),
    ("DRAFTABILITY_PASS", "AUTHORIZED"),
    ("AUTHORIZED", "IMPLEMENTED_LOCAL"),
)

# Generic / empty expected_result phrases that are not mechanically reviewable.
_GENERIC_EXPECTED = frozenset({"passes", "pass", "green", "ok", "test exists", "exists", "works"})

# Human-prompt required structural signals (section 5). Each entry is a tuple of
# alternative case-insensitive regex fragments; a section is present when any match.
_PROMPT_SIGNALS = (
    ("wp_identity", (r"\bpackage\s+class\b", r"\bwp\s*id\b", r"\bwp1[0-9]{2}")),
    ("repository_base_predecessor", (r"required\s+predecessor", r"base\s+branch")),
    ("objective", (r"\bobjective\b",)),
    ("authority", (r"authority\s*/\s*non-?authority", r"non-?authority")),
    ("changed_file_set", (r"scope", r"changed-?file")),
    ("hard_stops", (r"hard\s*stop",)),
    ("negative_test_matrix", (r"negative(?:\s+|-)test", r"not_applicable")),
    ("evidence_plan", (r"evidence\s+plan", r"requirement\s+mapping")),
    ("successor_boundary", (r"successor\s+boundary",)),
    ("report_back", (r"report-?back", r"report\s+back")),
    ("normative_rule_matrix", (re.escape(MATRIX_BEGIN),)),
)

_SANITARY_MAX_BYTES = 1_048_576
_MAX_HELPER_DEPTH = 4


# ---------------------------------------------------------------------------
# Result contract
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ReadinessResult:
    """Immutable sanitized readiness result (section 11)."""

    is_ready: bool
    status: str
    wp_id: str | None
    error_codes: tuple[str, ...]
    checked_sections: tuple[str, ...]
    scope_file_count: int
    evidence_item_count: int
    normative_rule_count: int
    package_guard_passed: bool
    certificate_hash_bound: bool
    governance_track: str | None
    minimum_governance_track: str | None
    readiness_basis: str | None
    certificate_required: bool

    def to_public_dict(self) -> dict[str, object]:
        return {
            "schema_id": "polymarket-wp-readiness-result",
            "schema_version": "1.1.0",
            "is_ready": self.is_ready,
            "status": self.status,
            "wp_id": self.wp_id,
            "error_codes": list(self.error_codes),
            "checked_sections": list(self.checked_sections),
            "scope_file_count": self.scope_file_count,
            "evidence_item_count": self.evidence_item_count,
            "normative_rule_count": self.normative_rule_count,
            "package_guard_passed": self.package_guard_passed,
            "certificate_hash_bound": self.certificate_hash_bound,
            "governance_track": self.governance_track,
            "minimum_governance_track": self.minimum_governance_track,
            "readiness_basis": self.readiness_basis,
            "certificate_required": self.certificate_required,
        }


def _order_codes(codes: Sequence[str]) -> tuple[str, ...]:
    unique = {c for c in codes if c in _ERROR_RANK}
    return tuple(sorted(unique, key=lambda c: _ERROR_RANK[c]))


# ---------------------------------------------------------------------------
# Package/certificate reuse (checks A + B)
# ---------------------------------------------------------------------------


class _GuardArgs:
    def __init__(self, wp: str, spec: str, certificate: str) -> None:
        self.wp = wp
        self.spec = spec
        self.certificate = certificate


def _run_package_guard(
    wp_path: str, spec_path: str, cert_path: str
) -> tuple[dict[str, object], int]:
    """Reuse the existing wp_spec_guard package/certificate validator verbatim."""
    return wp_spec_guard._validate_package(_GuardArgs(wp_path, spec_path, cert_path))


def _load_spec(spec_path: str) -> tuple[dict[str, object] | None, bool]:
    """Load one bounded strict specification. The boolean marks a file/usage error."""
    raw = wp_spec_guard._read_regular(pathlib.Path(spec_path), wp_spec_guard.MAX_SPEC_BYTES)
    if raw is None:
        return None, True
    try:
        document = wp_spec_guard._strict_json(raw)
    except (TypeError, ValueError, UnicodeError, OSError, RecursionError):
        return None, False
    spec, errors = wp_spec_guard.validate_spec_document(document)
    return (spec if not errors else None), False


def _minimum_governance_track(spec: Mapping[str, object]) -> str:
    identity = spec["identity"]  # type: ignore[index]
    authority = spec["authority"]  # type: ignore[index]
    risk_level = identity["risk_level"]
    if risk_level == 4 or any(
        authority[field] is True for field in ("credentials", "execution", "live")
    ):
        return "PROTECTED"
    if risk_level == 3 or any(
        authority[field] is True
        for field in ("network", "scheduler", "hermes_runtime", "paper")
    ):
        return "RUNTIME"
    return "FAST"


def _is_legacy_certified_wp(wp_id: object) -> bool:
    if not isinstance(wp_id, str):
        return False
    match = _WP_NUMBER_RE.fullmatch(wp_id)
    return bool(match and int(match.group(1)) <= _LEGACY_CERTIFIED_MAX_WP)


def _selected_governance_track(
    prompt_text: str, *, wp_id: object, certificate_supplied: bool
) -> str | None:
    matches = _TRACK_LINE_RE.findall(prompt_text)
    if len(matches) == 1:
        return matches[0]
    # Historical packages predate the mandatory track line. A supplied certificate
    # keeps those packages valid under the strictest track; no waiver is introduced.
    if not matches and certificate_supplied and _is_legacy_certified_wp(wp_id):
        return "PROTECTED"
    return None


def _track_errors(selected: str | None, minimum: str) -> list[str]:
    if selected is None or _TRACK_RANK[selected] < _TRACK_RANK[minimum]:
        return ["READINESS_GOVERNANCE_TRACK_INVALID"]
    return []


# ---------------------------------------------------------------------------
# Prompt structure (check E)
# ---------------------------------------------------------------------------


def _prompt_structure_errors(prompt_text: str) -> list[str]:
    codes: list[str] = []
    lowered = prompt_text.lower()
    for _name, patterns in _PROMPT_SIGNALS:
        if not any(re.search(p, lowered, re.IGNORECASE) for p in patterns):
            codes.append("READINESS_PROMPT_STRUCTURE_INVALID")
            break
    if _has_unresolved_placeholder(prompt_text):
        codes.append("READINESS_PROMPT_STRUCTURE_INVALID")
    return codes


def _has_unresolved_placeholder(prompt_text: str) -> bool:
    """Detect closed-vocabulary placeholder markers, ignoring the prompt's own
    quoted declaration of that vocabulary (a bullet line that is only the token)."""
    for raw_line in prompt_text.splitlines():
        stripped = raw_line.strip()
        # Skip a bullet whose sole content is the token itself: this is the
        # placeholder-vocabulary declaration / historical quoted prose.
        bullet_body = stripped[1:].strip() if stripped.startswith(("-", "*")) else stripped
        for token in PLACEHOLDER_TOKENS:
            if bullet_body == token:
                continue
            if token.startswith("<"):
                if token in raw_line and bullet_body != token:
                    return True
            else:
                if re.search(rf"\b{re.escape(token)}\b", raw_line) and bullet_body != token:
                    return True
    return False


# ---------------------------------------------------------------------------
# Normative rule matrix (checks F)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _Rule:
    rule_id: str
    domain: str
    subject: str
    condition: str
    action: str
    effect: str
    spec_path: str
    evidence_id: str


def _extract_matrix_blocks(prompt_text: str) -> list[list[str]]:
    lines = prompt_text.splitlines()
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        marker = line.strip()
        if marker == MATRIX_BEGIN:
            current = []
            continue
        if marker == MATRIX_END:
            if current is not None:
                blocks.append(current)
            current = None
            continue
        if current is not None:
            current.append(line)
    return blocks


def _parse_block_rows(block_lines: Sequence[str]) -> tuple[list[_Rule] | None, bool]:
    """Return (rows, well_formed). ``well_formed`` is True only when the block has
    the exact header and every data row is structurally valid."""
    data = [ln.strip() for ln in block_lines if ln.strip()]
    if not data or data[0] != MATRIX_HEADER:
        return None, False
    rows: list[_Rule] = []
    for row_line in data[1:]:
        fields = row_line.split("|")
        if len(fields) != 8:
            return None, False
        rule_id, domain, subject, condition, action, effect, spec_path, evidence = fields
        if not _RULE_ID_RE.match(rule_id):
            return None, False
        if not all(_DOTTED_TOKEN_RE.match(t) for t in (domain, subject, condition)):
            return None, False
        if action not in ACTION_VOCAB:
            return None, False
        if not _EFFECT_TOKEN_RE.match(effect):
            return None, False
        rows.append(
            _Rule(rule_id, domain, subject, condition, action, effect, spec_path, evidence)
        )
    if not rows:
        return None, False
    return rows, True


def _rule_matrix_errors(
    prompt_text: str, spec: Mapping[str, object]
) -> tuple[list[str], int]:
    codes: list[str] = []
    well_formed: list[list[_Rule]] = []
    for block in _extract_matrix_blocks(prompt_text):
        rows, ok = _parse_block_rows(block)
        if ok and rows is not None:
            well_formed.append(rows)
    if len(well_formed) != 1:
        return ["READINESS_RULE_MATRIX_INVALID"], 0
    rows = well_formed[0]

    semantic_paths = {
        item["path"] for item in spec["semantic_fields"]["items"]  # type: ignore[index]
    }
    evidence_ids = {
        item["requirement_id"] for item in spec["evidence_plan"]["items"]  # type: ignore[index]
    }

    # Rule 1: unique RULE_ID.
    seen_ids: set[str] = set()
    for rule in rows:
        if rule.rule_id in seen_ids:
            codes.append("READINESS_RULE_MATRIX_INVALID")
        seen_ids.add(rule.rule_id)

    # Rules 3 + 4: SPEC_PATH and EVIDENCE_ID references.
    for rule in rows:
        if rule.spec_path != "NONE" and rule.spec_path not in semantic_paths:
            codes.append("READINESS_RULE_MATRIX_INVALID")
        if rule.evidence_id != "NONE" and (
            not _EVIDENCE_ID_RE.match(rule.evidence_id)
            or rule.evidence_id not in evidence_ids
        ):
            codes.append("READINESS_RULE_MATRIX_INVALID")

    # Rules 5-8: one ACTION/CANONICAL_EFFECT pair per semantic key.
    by_key: dict[tuple[str, str, str], set[tuple[str, str]]] = {}
    for rule in rows:
        key = (rule.domain, rule.subject, rule.condition)
        by_key.setdefault(key, set()).add((rule.action, rule.effect))
    for pairs in by_key.values():
        if len(pairs) > 1:
            codes.append("READINESS_SEMANTIC_CONTRADICTION")

    return codes, len(rows)


# ---------------------------------------------------------------------------
# Scope authority (check D) + successor boundary (check I)
# ---------------------------------------------------------------------------


def _scope_errors(
    spec: Mapping[str, object], governance_track: str = "PROTECTED"
) -> list[str]:
    codes: list[str] = []
    scope = spec["scope"]  # type: ignore[index]
    identity = spec["identity"]  # type: ignore[index]
    required = list(scope["required_changed_files"])
    allowed = list(scope["allowed_changed_files"])
    if scope["exact_scope_required"] is not True:
        codes.append("READINESS_SCOPE_INVALID")
    if sorted(required) != sorted(allowed):
        codes.append("READINESS_SCOPE_INVALID")
    if len(required) != scope["max_changed_files"]:
        codes.append("READINESS_SCOPE_INVALID")
    artifacts = {
        f"docs/wp_specs/{identity['wp_id']}/wp_prompt.txt",
        f"docs/wp_specs/{identity['wp_id']}/wp_spec.json",
    }
    if governance_track == "PROTECTED":
        artifacts.add(
            f"docs/wp_specs/{identity['wp_id']}/draftability_certificate.json"
        )
    if not artifacts.issubset(set(required)):
        codes.append("READINESS_SCOPE_INVALID")
    forbidden = list(scope["forbidden_prefixes"])
    for path in required:
        if any(path.startswith(prefix) for prefix in forbidden):
            codes.append("READINESS_SCOPE_INVALID")
        if wp_spec_guard._is_generated_artifact(path):
            codes.append("READINESS_SCOPE_INVALID")
    return codes


def _successor_errors(spec: Mapping[str, object]) -> list[str]:
    codes: list[str] = []
    successor = spec["successor_boundary"]  # type: ignore[index]
    if successor.get("separately_gated") is not True:
        codes.append("READINESS_SUCCESSOR_BOUNDARY_INVALID")
    if not successor.get("next_wp"):
        codes.append("READINESS_SUCCESSOR_BOUNDARY_INVALID")
    forbidden = successor.get("forbidden_in_this_wp")
    if not isinstance(forbidden, list) or not forbidden:
        codes.append("READINESS_SUCCESSOR_BOUNDARY_INVALID")
    return codes


def _state_errors(spec: Mapping[str, object]) -> list[str]:
    transitions = spec["state_transitions"]["items"]  # type: ignore[index]
    pairs = [(item["from_state"], item["to_state"]) for item in transitions]
    if tuple(pairs) != CANONICAL_STATE_CHAIN:
        return ["READINESS_STATE_INVALID"]
    return []


# ---------------------------------------------------------------------------
# Evidence plan (checks G + H, and K + L for --check-diff)
# ---------------------------------------------------------------------------


def _pytest_targets(command: str) -> list[str]:
    if "pytest" not in command:
        return []
    return _PY_TARGET_RE.findall(command)


def _module_functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    funcs: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.setdefault(node.name, node)  # first definition wins
    return funcs


def _count_named_defs(tree: ast.Module, name: str) -> int:
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )


def _has_reachable_assertion(
    func: ast.FunctionDef,
    functions: Mapping[str, ast.FunctionDef],
    depth: int,
    visiting: frozenset[str],
) -> bool:
    if depth > _MAX_HELPER_DEPTH:
        return False
    for node in ast.walk(func):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.With):
            for item in node.items:
                if _is_raises_call(item.context_expr):
                    return True
        if isinstance(node, ast.Call) and _is_raises_call(node):
            return True
    # Follow same-module helper calls (bounded recursion).
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            callee = _call_name(node.func)
            if (
                callee is not None
                and callee in functions
                and callee not in visiting
                and callee != func.name
            ):
                if _has_reachable_assertion(
                    functions[callee], functions, depth + 1, visiting | {callee}
                ):
                    return True
    return False


def _is_raises_call(expr: ast.AST) -> bool:
    if not isinstance(expr, ast.Call):
        return False
    name = _call_name(expr.func)
    return name in {"raises", "pytest.raises"}


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = _call_name(func.value)
        return f"{base}.{func.attr}" if base else func.attr
    return None


def _load_module(path: pathlib.Path) -> ast.Module | None:
    raw = wp_spec_guard._read_regular(path, _SANITARY_MAX_BYTES)
    if raw is None:
        return None
    try:
        return ast.parse(raw.decode("utf-8"))
    except (SyntaxError, ValueError, UnicodeError):
        return None


def _evidence_errors(
    spec: Mapping[str, object], repo_root: pathlib.Path, post_implementation: bool
) -> list[str]:
    codes: list[str] = []
    required = set(spec["scope"]["required_changed_files"])  # type: ignore[index]
    for item in spec["evidence_plan"]["items"]:  # type: ignore[index]
        if item.get("source") != "pytest":
            continue
        node_name = str(item.get("test", ""))
        expected = str(item.get("expected_result", "")).strip()
        if len(expected) < 12 or expected.lower() in _GENERIC_EXPECTED:
            codes.append("READINESS_EVIDENCE_ASSERTION_INADEQUATE")
        # Only named-node pytest items get node/target coherence checks. An aggregate
        # item (e.g. a full-suite run) names no function and is not node-targetable.
        if not _IDENTIFIER_RE.match(node_name):
            continue
        targets = _pytest_targets(str(item.get("command", "")))
        if not targets:
            codes.append("READINESS_EVIDENCE_NODE_MISSING")
            continue
        codes.extend(
            _evidence_item_errors(node_name, targets, required, repo_root, post_implementation)
        )
    return codes


def _evidence_item_errors(
    node_name: str,
    targets: Sequence[str],
    required: set[str],
    repo_root: pathlib.Path,
    post_implementation: bool,
) -> list[str]:
    codes: list[str] = []
    existing_hits = 0
    ambiguous = False
    adequate = False
    for rel in targets:
        module = _load_module(repo_root / rel)
        if module is None:
            continue
        count = _count_named_defs(module, node_name)
        if count >= 1:
            existing_hits += count
            functions = _module_functions(module)
            if _has_reachable_assertion(functions[node_name], functions, 1, frozenset({node_name})):
                adequate = True
    in_scope = any(rel in required for rel in targets)

    if existing_hits == 0:
        if post_implementation:
            codes.append("READINESS_EVIDENCE_NODE_MISSING")
        elif not in_scope:
            # Pre-implementation: a missing node is a PLANNED_NEW_NODE only when its
            # exact target test file is certified in scope -- regardless of whether
            # that file already exists on base or is newly created by the WP.
            codes.append("READINESS_EVIDENCE_NODE_MISSING")
        return codes
    if existing_hits > 1:
        ambiguous = True
    if ambiguous:
        codes.append("READINESS_EVIDENCE_NODE_MISSING")
    if post_implementation and not adequate:
        codes.append("READINESS_EVIDENCE_ASSERTION_INADEQUATE")
    return codes


# ---------------------------------------------------------------------------
# --check-diff scope equality (check J)
# ---------------------------------------------------------------------------


def _diff_scope_errors(
    spec: Mapping[str, object], repo_root: pathlib.Path, base: str, head: str
) -> list[str]:
    required = set(spec["scope"]["required_changed_files"])  # type: ignore[index]
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--name-only", "--no-color", base, head],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return ["READINESS_DIFF_SCOPE_MISMATCH"]
    if proc.returncode != 0:
        return ["READINESS_DIFF_SCOPE_MISMATCH"]
    changed = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    if changed != required:
        return ["READINESS_DIFF_SCOPE_MISMATCH"]
    return []


# ---------------------------------------------------------------------------
# Top-level evaluation
# ---------------------------------------------------------------------------


def evaluate_readiness(
    wp_path: str,
    spec_path: str,
    cert_path: str | None,
    repo_root: str,
    *,
    check_diff: bool = False,
    base: str | None = None,
    head: str | None = None,
) -> ReadinessResult:
    """Evaluate package readiness without side effects or raises."""
    checked: list[str] = ["package_guard"]
    prompt_raw = wp_spec_guard._read_regular(
        pathlib.Path(wp_path), wp_spec_guard.MAX_WP_BYTES
    )
    spec, spec_file_error = _load_spec(spec_path)
    if prompt_raw is None or spec_file_error:
        return ReadinessResult(
            False, STATUS_USAGE, None, ("READINESS_PACKAGE_GUARD_INVALID",),
            tuple(checked), 0, 0, 0, False, False, None, None, None, False,
        )
    if spec is None:
        return ReadinessResult(
            False, STATUS_NOT_READY, None, ("READINESS_PACKAGE_GUARD_INVALID",),
            tuple(checked), 0, 0, 0, False, False, None, None, None, False,
        )
    try:
        prompt_text = prompt_raw.decode("utf-8")
    except UnicodeError:
        return ReadinessResult(
            False, STATUS_NOT_READY, None, ("READINESS_PROMPT_STRUCTURE_INVALID",),
            tuple(checked), 0, 0, 0, False, False, None, None, None, False,
        )

    wp_id = spec["identity"]["wp_id"]  # type: ignore[index]
    minimum_track = _minimum_governance_track(spec)
    selected_track = _selected_governance_track(
        prompt_text, wp_id=wp_id, certificate_supplied=bool(cert_path)
    )
    checked.append("governance_track")
    track_codes = _track_errors(selected_track, minimum_track)
    certificate_required = selected_track == "PROTECTED"
    if track_codes:
        return ReadinessResult(
            False, STATUS_NOT_READY, wp_id, _order_codes(track_codes), tuple(checked),
            0, 0, 0, True, False, selected_track, minimum_track, None,
            certificate_required,
        )

    assert selected_track is not None
    package_passed = True
    certificate_hash_bound = False
    readiness_basis = "DETERMINISTIC"

    if certificate_required and not cert_path:
        return ReadinessResult(
            False, STATUS_NOT_READY, wp_id, ("READINESS_CERTIFICATE_NOT_PASS",),
            tuple(checked), 0, 0, 0, True, False, selected_track, minimum_track,
            None, True,
        )

    if cert_path:
        try:
            guard_result, guard_exit = _run_package_guard(wp_path, spec_path, cert_path)
        except Exception:  # pragma: no cover - defensive; never echo exception text
            return ReadinessResult(
                False, STATUS_USAGE, wp_id, ("READINESS_PACKAGE_GUARD_INVALID",),
                tuple(checked), 0, 0, 0, False, False, selected_track,
                minimum_track, None, certificate_required,
            )
        if guard_exit == 2:
            return ReadinessResult(
                False, STATUS_USAGE, wp_id, ("READINESS_PACKAGE_GUARD_INVALID",),
                tuple(checked), 0, 0, 0, False, False, selected_track,
                minimum_track, None, certificate_required,
            )

        guard_codes = {e["code"] for e in guard_result.get("errors", [])}  # type: ignore[index]
        package_passed = guard_result.get("status") == "PASS"
        certificate_hash_bound = (
            "CERTIFICATE_HASH_MISMATCH" not in guard_codes and package_passed
        )
        if not package_passed:
            failure_codes: list[str] = []
            if guard_codes & {"CERTIFICATE_HASH_MISMATCH", "DRAFTABILITY_INCOMPLETE"}:
                failure_codes.append("READINESS_CERTIFICATE_NOT_PASS")
            if guard_codes - {"CERTIFICATE_HASH_MISMATCH", "DRAFTABILITY_INCOMPLETE"}:
                failure_codes.append("READINESS_PACKAGE_GUARD_INVALID")
            if not failure_codes:
                failure_codes.append("READINESS_PACKAGE_GUARD_INVALID")
            return ReadinessResult(
                False, STATUS_NOT_READY, wp_id, _order_codes(failure_codes),
                tuple(checked), 0, 0, 0, False, certificate_hash_bound,
                selected_track, minimum_track, None, certificate_required,
            )
        readiness_basis = "INDEPENDENT_CERTIFICATE"

    root = pathlib.Path(repo_root)

    codes = []
    checked.append("prompt_structure")
    codes.extend(_prompt_structure_errors(prompt_text))
    checked.append("rule_matrix")
    matrix_codes, rule_count = _rule_matrix_errors(prompt_text, spec)
    codes.extend(matrix_codes)
    checked.append("state_and_authority")
    codes.extend(_state_errors(spec))
    checked.append("scope")
    codes.extend(_scope_errors(spec, selected_track))
    checked.append("successor_boundary")
    codes.extend(_successor_errors(spec))
    checked.append("evidence_plan")
    codes.extend(_evidence_errors(spec, root, post_implementation=check_diff))

    if check_diff:
        checked.append("diff_scope")
        if not base or not head:
            codes.append("READINESS_DIFF_SCOPE_MISMATCH")
        else:
            codes.extend(_diff_scope_errors(spec, root, base, head))

    scope_file_count = len(spec["scope"]["required_changed_files"])
    evidence_item_count = len(spec["evidence_plan"]["items"])
    ordered = _order_codes(codes)
    ready = not ordered
    return ReadinessResult(
        ready,
        STATUS_READY if ready else STATUS_NOT_READY,
        wp_id,
        ordered,
        tuple(checked),
        scope_file_count,
        evidence_item_count,
        rule_count,
        package_passed,
        certificate_hash_bound,
        selected_track,
        minimum_track,
        readiness_basis,
        certificate_required,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_READINESS_NOT_AUTHORIZATION = (
    "IMPLEMENTATION_READY is technical package readiness only; it is NOT user "
    "authorization. The user remains the sole source of AUTHORIZED."
)


class _QuietParser(argparse.ArgumentParser):
    def error(self, message: str) -> "None":  # type: ignore[override]
        raise _UsageError()


class _UsageError(Exception):
    pass


def _parse_args(argv: list[str] | None) -> argparse.Namespace | None:
    parser = _QuietParser(add_help=False)
    parser.add_argument("--wp")
    parser.add_argument("--spec")
    parser.add_argument("--certificate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--format", default="text", choices=["text", "json"])
    parser.add_argument("--check-diff", action="store_true")
    parser.add_argument("--base")
    parser.add_argument("--head")
    try:
        args = parser.parse_args(argv)
    except (_UsageError, SystemExit):
        return None
    if not args.wp or not args.spec:
        return None
    if args.check_diff and (not args.base or not args.head):
        return None
    return args


def _render(result: ReadinessResult, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(
            result.to_public_dict(), ensure_ascii=False, allow_nan=False,
            separators=(",", ":"),
        ) + "\n"
    public = result.to_public_dict()
    lines = [f"{key}: {_scalar(value)}" for key, value in public.items()]
    lines.append(f"note: {_READINESS_NOT_AUTHORIZATION}")
    return "\n".join(lines) + "\n"


def _scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args is None:
        usage = ReadinessResult(
            False, STATUS_USAGE, None, (), ("usage",), 0, 0, 0, False, False,
            None, None, None, False,
        )
        fmt = "json" if (argv and "json" in argv) else "text"
        sys.stdout.write(_render(usage, fmt))
        return 2
    result = evaluate_readiness(
        args.wp, args.spec, args.certificate, args.repo_root,
        check_diff=args.check_diff, base=args.base, head=args.head,
    )
    sys.stdout.write(_render(result, args.format))
    if result.status == STATUS_USAGE:
        return 2
    return 0 if result.is_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
