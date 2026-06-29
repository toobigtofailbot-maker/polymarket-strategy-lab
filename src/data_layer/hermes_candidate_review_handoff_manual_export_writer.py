"""Local manual file writer for Hermes candidate-review handoff manual export artifacts.

Accepts a valid WP108 CandidateReviewManualExportArtifactResult, validates its
structure, safety flags, and required groups, then writes a deterministic UTF-8
Markdown artifact to an explicit operator-supplied local path. Fails closed with
a neutral result for invalid input. Never echoes unsafe caller-supplied input in
errors, warnings, or artifact output.

Stdlib-only plus approved WP108 internal import. No network. No subprocess.
No CLI. No credentials. No paper/live/execution/risk/scheduler/dashboard/
bot-loop/runtime/Hermes/prompt-runner behavior. Local/offline/manual-only.
Parent directory must exist; this writer does not create parent directories.
Added in WP109.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
from pathlib import Path
from typing import Any

from src.data_layer.hermes_candidate_review_handoff_manual_export_artifact import (
    REQUIRED_ARTIFACT_GROUPS,
    REQUIRED_ARTIFACT_SAFETY_FLAGS,
    CandidateReviewManualExportArtifactResult,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_SUFFIXES: frozenset[str] = frozenset({".md", ".txt"})

_URI_SCHEMES: tuple[str, ...] = (
    "http://",
    "https://",
    "s3://",
    "gs://",
    "ftp://",
    "ftps://",
    "file://",
)

_BOUNDARY_NOTICE: str = """\
---

**BOUNDARY NOTICE — ADVISORY ONLY**

- This document is advisory only.
- Human review is required before any use.
- This is NOT a trade signal.
- This is NOT position sizing guidance.
- This is NOT an expected-return estimate.
- This is NOT a paper or live readiness statement.
- This is NOT a PR merge-readiness statement.
- This is NOT a strategy promotion.
- This is NOT a runtime instruction.
- This is NOT a credential permission.
- This is NOT an execution authority.
- This is NOT an automated instruction.

Any next research step cited is a manual research suggestion only.

---
"""

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class CandidateReviewManualExportWriteResult:
    """Result of writing a Hermes candidate-review handoff manual export artifact.

    Advisory only. Does not authorize execution, credential access, paper/live,
    strategy promotion, PR approval, runtime, scheduler, bot-loop, file/network
    beyond the explicit local output path, or prompt execution. Human review is
    required. Added in WP109.
    """

    is_valid: bool
    output_path: str | None = None
    bytes_written: int = 0
    sha256: str | None = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fail(errors: tuple[str, ...]) -> CandidateReviewManualExportWriteResult:
    return CandidateReviewManualExportWriteResult(
        is_valid=False,
        output_path=None,
        bytes_written=0,
        sha256=None,
        errors=errors,
        warnings=(),
    )


def _safe_str(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


def _safe_int(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _safe_bool_str(value: object) -> str:
    if value is True:
        return "True"
    if value is False:
        return "False"
    return "Unknown"


def _safe_list(value: object) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _render_artifact_markdown(artifact: dict[str, Any]) -> str:
    identity = artifact.get("artifact_identity", {})
    source_identity = artifact.get("source_handoff_identity", {})
    chain = artifact.get("chain_stage_summary", {})
    review = artifact.get("manual_review_summary", {})
    evidence = artifact.get("evidence_and_provenance_summary", {})
    staleness = artifact.get("staleness_and_missing_data_summary", {})
    uncertainty = artifact.get("uncertainty_and_limitations_summary", {})
    falsification = artifact.get("falsification_summary", {})
    decision = artifact.get("human_decision_record_summary", {})
    next_step = artifact.get("next_manual_research_step", {})
    safety_flags = artifact.get("safety_flags", {})
    forbidden_notice = _safe_str(artifact.get("forbidden_scope_notice", ""))

    artifact_id = _safe_str(identity.get("artifact_id"))
    contract_version = _safe_str(identity.get("contract_version"))
    generated_by = _safe_str(identity.get("generated_by"))
    source_wp = _safe_str(identity.get("source_wp"))
    artifact_type = _safe_str(identity.get("artifact_type"))

    handoff_id = _safe_str(source_identity.get("handoff_id"))
    chain_identifier = _safe_str(source_identity.get("chain_identifier"))
    handoff_contract = _safe_str(source_identity.get("contract_version"))
    handoff_generated_by = _safe_str(source_identity.get("generated_by"))

    stages = _safe_list(chain.get("stages"))
    stage_count = _safe_int(chain.get("stage_count"))

    decision_label = _safe_str(review.get("decision_label"))
    handoff_valid = review.get("handoff_is_valid")

    provenance_status = _safe_str(evidence.get("provenance_status"))
    source_ref_count = _safe_int(evidence.get("source_reference_count"))
    artifact_ref_count = _safe_int(evidence.get("artifact_references_count"))
    evidence_summary_present = evidence.get("evidence_summary_present")

    staleness_status = _safe_str(staleness.get("staleness_status"))
    missing_data_count = _safe_int(staleness.get("known_missing_data_count"))
    quality_warning_count = _safe_int(staleness.get("data_quality_warning_count"))
    coverage_limit_count = _safe_int(staleness.get("coverage_limit_count"))

    uncertainty_notes = _safe_int(uncertainty.get("uncertainty_notes_count"))
    assumptions_count = _safe_int(uncertainty.get("assumptions_count"))
    limitations_count = _safe_int(uncertainty.get("limitations_count"))
    boundary_notes_count = _safe_int(uncertainty.get("boundary_notes_count"))

    checks_count = _safe_int(falsification.get("checks_count"))

    operator_role = _safe_str(decision.get("operator_role"))
    timestamp_note = _safe_str(decision.get("timestamp_note"))
    rationale_length = _safe_int(decision.get("rationale_length_chars"))

    step_type = _safe_str(next_step.get("step_type"))
    has_step_description = next_step.get("has_step_description")

    lines: list[str] = []

    # 1. Title
    lines.append("# Hermes Candidate-Review Handoff Manual Export Artifact\n")

    # 2. Artifact identity
    lines.append("## Artifact Identity\n")
    lines.append(f"- Artifact ID: `{artifact_id}`")
    lines.append(f"- Artifact type: `{artifact_type}`")
    lines.append(f"- Contract version: `{contract_version}`")
    lines.append(f"- Generated by: `{generated_by}`")
    lines.append(f"- Source WP: `{source_wp}`")
    lines.append("")

    # 3. Source handoff identity
    lines.append("## Source Handoff Identity\n")
    lines.append(f"- Handoff ID: `{handoff_id}`")
    lines.append(f"- Chain identifier: `{chain_identifier}`")
    lines.append(f"- Handoff contract version: `{handoff_contract}`")
    lines.append(f"- Handoff generated by: `{handoff_generated_by}`")
    lines.append("")

    # 4. Chain stage summary
    lines.append("## Chain Stage Summary\n")
    lines.append(f"- Stage count: {stage_count}")
    lines.append("- Stages:")
    for stage in stages:
        lines.append(f"  - `{stage}`")
    lines.append("")

    # 5. Manual review summary
    lines.append("## Manual Review Summary\n")
    lines.append(f"- Decision label: `{decision_label}`")
    lines.append(f"- Handoff is valid: {_safe_bool_str(handoff_valid)}")
    lines.append("")

    # 6. Evidence and provenance summary
    lines.append("## Evidence and Provenance Summary\n")
    lines.append(f"- Provenance status: `{provenance_status}`")
    lines.append(f"- Source reference count: {source_ref_count}")
    lines.append(f"- Artifact references count: {artifact_ref_count}")
    lines.append(f"- Evidence summary present: {_safe_bool_str(evidence_summary_present)}")
    lines.append("")

    # 7. Staleness and missing-data summary
    lines.append("## Staleness and Missing-Data Summary\n")
    lines.append(f"- Staleness status: `{staleness_status}`")
    lines.append(f"- Known missing data count: {missing_data_count}")
    lines.append(f"- Data quality warning count: {quality_warning_count}")
    lines.append(f"- Coverage limit count: {coverage_limit_count}")
    lines.append("")

    # 8. Uncertainty and limitations summary
    lines.append("## Uncertainty and Limitations Summary\n")
    lines.append(f"- Uncertainty notes count: {uncertainty_notes}")
    lines.append(f"- Assumptions count: {assumptions_count}")
    lines.append(f"- Limitations count: {limitations_count}")
    lines.append(f"- Boundary notes count: {boundary_notes_count}")
    lines.append("")

    # 9. Falsification summary
    lines.append("## Falsification Summary\n")
    lines.append(f"- Falsification checks count: {checks_count}")
    lines.append("")

    # 10. Human decision record summary
    lines.append("## Human Decision Record Summary\n")
    lines.append(f"- Decision label: `{decision_label}`")
    lines.append(f"- Operator role: `{operator_role}`")
    lines.append(f"- Timestamp note: `{timestamp_note}`")
    lines.append(f"- Rationale length (chars): {rationale_length}")
    lines.append("- Note: Raw rationale text is not included in this artifact.")
    lines.append("")

    # 11. Next manual research step
    lines.append("## Next Manual Research Step\n")
    lines.append(f"- Step type: `{step_type}`")
    lines.append(f"- Has step description: {_safe_bool_str(has_step_description)}")
    lines.append("- Note: This is a manual research suggestion only.")
    lines.append("")

    # 12. Safety flags
    lines.append("## Safety Flags\n")
    for flag in REQUIRED_ARTIFACT_SAFETY_FLAGS:
        flag_val = safety_flags.get(flag)
        lines.append(f"- `{flag}`: {_safe_bool_str(flag_val)}")
    lines.append("")

    # 13. Forbidden scope notice
    lines.append("## Forbidden Scope Notice\n")
    lines.append(forbidden_notice)
    lines.append("")

    # Boundary notice at end
    lines.append(_BOUNDARY_NOTICE)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_candidate_review_manual_export_artifact(
    *,
    artifact_result: object,
    output_path: str | os.PathLike[str],
    overwrite: bool = False,
    expected_suffix: str = ".md",
) -> CandidateReviewManualExportWriteResult:
    """Write a deterministic UTF-8 Markdown artifact from a valid WP108 result.

    Validates that artifact_result is a valid WP108
    CandidateReviewManualExportArtifactResult, confirms all required groups and
    safety flags are present and True, then writes a deterministic Markdown file
    to the explicit output_path. Fails closed with a neutral result for invalid
    input. Never echoes unsafe caller-supplied content in errors or warnings.

    This function is advisory only. It does not run Hermes, execute prompts, call
    models or providers, access networks, use credentials or private state, create
    a CLI, or perform paper/live, order, risk, scheduler, dashboard, or bot-loop
    work. Parent directory must already exist. Added in WP109.
    """
    errors: list[str] = []

    # --- Validate expected_suffix ---
    if expected_suffix not in _ALLOWED_SUFFIXES:
        errors.append("UNSUPPORTED_OUTPUT_SUFFIX")
        return _fail(tuple(errors))

    # --- Validate output_path: no URI scheme ---
    try:
        output_path_str = os.fspath(output_path)
    except TypeError:
        errors.append("INVALID_OUTPUT_PATH")
        return _fail(tuple(errors))

    if not isinstance(output_path_str, str):
        errors.append("INVALID_OUTPUT_PATH")
        return _fail(tuple(errors))

    lower_path = output_path_str.lower()
    for scheme in _URI_SCHEMES:
        if lower_path.startswith(scheme):
            errors.append("URI_SCHEME_NOT_ALLOWED_IN_OUTPUT_PATH")
            return _fail(tuple(errors))

    output_p = Path(output_path_str)

    if output_p.suffix.lower() != expected_suffix.lower():
        errors.append("OUTPUT_PATH_SUFFIX_MISMATCH")
        return _fail(tuple(errors))

    # --- Validate artifact_result type ---
    expected_class = "CandidateReviewManualExportArtifactResult"
    actual_class = type(artifact_result).__name__
    required_attrs = ("is_valid", "artifact", "errors", "warnings")
    if actual_class != expected_class or not all(
        hasattr(artifact_result, attr) for attr in required_attrs
    ):
        errors.append("UNSUPPORTED_INPUT_SHAPE")
        return _fail(tuple(errors))

    # --- Validate artifact_result.is_valid ---
    if artifact_result.is_valid is not True:
        errors.append("SOURCE_ARTIFACT_NOT_VALID")
        return _fail(tuple(errors))

    artifact: dict[str, Any] = artifact_result.artifact
    if not isinstance(artifact, dict) or not artifact:
        errors.append("EMPTY_OR_INVALID_ARTIFACT_DICT")
        return _fail(tuple(errors))

    # --- Validate required artifact groups ---
    for group in REQUIRED_ARTIFACT_GROUPS:
        if group not in artifact:
            errors.append("MISSING_REQUIRED_ARTIFACT_GROUP")
            return _fail(tuple(errors))

    # --- Validate required artifact safety flags ---
    safety_flags = artifact.get("safety_flags", {})
    if not isinstance(safety_flags, dict):
        errors.append("MISSING_REQUIRED_SAFETY_FLAG")
        return _fail(tuple(errors))
    for flag in REQUIRED_ARTIFACT_SAFETY_FLAGS:
        if safety_flags.get(flag) is not True:
            errors.append("MISSING_REQUIRED_SAFETY_FLAG")
            return _fail(tuple(errors))

    # --- Check overwrite policy ---
    if output_p.exists() and not overwrite:
        errors.append("OUTPUT_PATH_EXISTS_NO_OVERWRITE")
        return _fail(tuple(errors))

    # --- Require parent directory to exist ---
    if not output_p.parent.exists():
        errors.append("OUTPUT_PARENT_DIRECTORY_DOES_NOT_EXIST")
        return _fail(tuple(errors))

    # --- Render Markdown ---
    content = _render_artifact_markdown(artifact)
    content_bytes = content.encode("utf-8")

    # --- Compute sha256 before writing ---
    sha256_hex = hashlib.sha256(content_bytes).hexdigest()

    # --- Write file ---
    try:
        output_p.write_bytes(content_bytes)
    except OSError:
        errors.append("FILE_WRITE_ERROR")
        return _fail(tuple(errors))

    return CandidateReviewManualExportWriteResult(
        is_valid=True,
        output_path=str(output_p),
        bytes_written=len(content_bytes),
        sha256=sha256_hex,
        errors=(),
        warnings=(),
    )
