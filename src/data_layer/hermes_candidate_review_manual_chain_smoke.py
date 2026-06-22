"""In-memory manual chain smoke for Hermes candidate-review research.

This module composes the existing WP103/WP101/WP102 safe helpers to show
that the local/offline/read-only Hermes research-chain pieces can be assembled
without file I/O, network, CLI, prompt execution, Hermes runtime, credentials,
paper/live behavior, or execution/risk behavior.

Stdlib-only plus approved internal imports from
src.data_layer.hermes_candidate_review_context_packet_integration (WP103),
src.data_layer.hermes_context_packet_dry_run_receipt (WP101), and
src.data_layer.hermes_manual_research_dry_run_review (WP102).
Local/offline/read-only. Added in WP104.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.data_layer.hermes_candidate_review_context_packet_integration import (
    build_candidate_review_hermes_context_packet,
)
from src.data_layer.hermes_context_packet_dry_run_receipt import (
    build_hermes_context_packet_dry_run_receipt,
)
from src.data_layer.hermes_manual_research_dry_run_review import (
    build_hermes_manual_research_dry_run_review,
)

_SMOKE_RESULT_TYPE = "HERMES_CANDIDATE_REVIEW_MANUAL_CHAIN_SMOKE_V1"


@dataclass(frozen=True)
class HermesChainSmokeResult:
    """Deterministic result for the Hermes candidate-review manual chain smoke.

    Safety flags are always True; they describe this helper's advisory-only,
    no-authority posture regardless of whether the chain input was valid.
    """

    is_valid: bool
    packet_valid: bool
    receipt_valid: bool
    review_valid: bool
    packet_type: str | None
    receipt_type: str | None
    review_type: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    advisory_only: bool
    manual_review_required: bool
    no_execution_authority: bool
    no_runtime_authority: bool
    no_credential_authority: bool
    no_paper_or_live_authority: bool
    no_prompt_execution: bool
    no_file_or_network: bool


def _make_result(
    *,
    is_valid: bool,
    packet_valid: bool,
    receipt_valid: bool,
    review_valid: bool,
    packet_type: str | None,
    receipt_type: str | None,
    review_type: str | None,
    errors: tuple[str, ...],
    warnings: tuple[str, ...],
) -> HermesChainSmokeResult:
    return HermesChainSmokeResult(
        is_valid=is_valid,
        packet_valid=packet_valid,
        receipt_valid=receipt_valid,
        review_valid=review_valid,
        packet_type=packet_type,
        receipt_type=receipt_type,
        review_type=review_type,
        errors=errors,
        warnings=warnings,
        advisory_only=True,
        manual_review_required=True,
        no_execution_authority=True,
        no_runtime_authority=True,
        no_credential_authority=True,
        no_paper_or_live_authority=True,
        no_prompt_execution=True,
        no_file_or_network=True,
    )


def run_candidate_review_manual_chain_smoke(
    *,
    packet_id: str,
    report_identity: str,
    source_refs: Sequence[str],
    advisory_notice: str,
    human_review_required: bool,
    review_status: str,
    provenance_status: str,
    staleness_status: str,
    recommended_next_review_step: str,
    receipt_id: str,
    reviewer_id: str,
    dry_run_scope: str,
    readiness_checks: Mapping[str, bool],
    review_id: str,
    operator_id: str,
    selected_research_family: str,
    selected_operator_runbook_ref: str,
    source_review_checks: Mapping[str, bool],
    data_quality_warnings: Sequence[str] | None = None,
    known_missing_data: Sequence[str] | None = None,
    key_findings: Sequence[str] | None = None,
    limitations: Sequence[str] | None = None,
    rejection_reasons: Sequence[str] | None = None,
    report_reference: str | None = None,
    uncertainty_notes: Sequence[str] | None = None,
    assumptions: Sequence[str] | None = None,
    falsification_checks: Sequence[str] | None = None,
    related_repo_truth_refs: Sequence[str] | None = None,
    operator_notes: Sequence[str] | None = None,
) -> HermesChainSmokeResult:
    """Run the candidate-review → receipt → review chain in memory.

    Composes WP103/WP101/WP102 safe helpers. Invalid input fails closed at the
    first failing stage without echoing caller-provided content in diagnostics.
    Safety flags are always True and describe this helper's posture.

    Does not run Hermes, execute prompts, call models or providers, access
    networks, read or write files, use credentials or private state, create a
    CLI, or perform paper/live, order, risk, scheduler, dashboard, or bot-loop
    work. Added in WP104.
    """
    source_refs_list = list(source_refs)

    # Stage 1: Build candidate-review context packet (WP103).
    packet_result = build_candidate_review_hermes_context_packet(
        packet_id=packet_id,
        report_identity=report_identity,
        source_refs=source_refs_list,
        advisory_notice=advisory_notice,
        human_review_required=human_review_required,
        review_status=review_status,
        provenance_status=provenance_status,
        staleness_status=staleness_status,
        recommended_next_review_step=recommended_next_review_step,
        data_quality_warnings=(
            list(data_quality_warnings) if data_quality_warnings is not None else None
        ),
        known_missing_data=(
            list(known_missing_data) if known_missing_data is not None else None
        ),
        key_findings=(
            list(key_findings) if key_findings is not None else None
        ),
        limitations=(
            list(limitations) if limitations is not None else None
        ),
        rejection_reasons=(
            list(rejection_reasons) if rejection_reasons is not None else None
        ),
        report_reference=report_reference,
        uncertainty_notes=(
            list(uncertainty_notes) if uncertainty_notes is not None else None
        ),
        assumptions=(
            list(assumptions) if assumptions is not None else None
        ),
        falsification_checks=(
            list(falsification_checks) if falsification_checks is not None else None
        ),
        related_repo_truth_refs=(
            list(related_repo_truth_refs)
            if related_repo_truth_refs is not None
            else None
        ),
    )

    if not packet_result.is_valid:
        return _make_result(
            is_valid=False,
            packet_valid=False,
            receipt_valid=False,
            review_valid=False,
            packet_type=None,
            receipt_type=None,
            review_type=None,
            errors=tuple(f"packet_stage_{e}" for e in packet_result.errors),
            warnings=(),
        )

    packet = packet_result.packet

    # Stage 2: Build dry-run receipt (WP101).
    # Use the same source_refs as checked_source_refs; they are in the packet.
    receipt_result = build_hermes_context_packet_dry_run_receipt(
        receipt_id=receipt_id,
        packet=packet,
        reviewer_id=reviewer_id,
        dry_run_scope=dry_run_scope,
        checked_source_refs=source_refs_list,
        readiness_checks=readiness_checks,
        related_repo_truth_refs=(
            list(related_repo_truth_refs)
            if related_repo_truth_refs is not None
            else None
        ),
        operator_notes=(
            list(operator_notes) if operator_notes is not None else None
        ),
    )

    if not receipt_result.is_valid:
        packet_type_val = packet.get("packet_type")
        return _make_result(
            is_valid=False,
            packet_valid=True,
            receipt_valid=False,
            review_valid=False,
            packet_type=(
                str(packet_type_val) if isinstance(packet_type_val, str) else None
            ),
            receipt_type=None,
            review_type=None,
            errors=tuple(f"receipt_stage_{e}" for e in receipt_result.errors),
            warnings=(),
        )

    receipt = receipt_result.receipt

    # Stage 3: Build manual research dry-run review (WP102).
    review_result = build_hermes_manual_research_dry_run_review(
        review_id=review_id,
        dry_run_receipt=receipt,
        operator_id=operator_id,
        selected_research_family=selected_research_family,
        selected_operator_runbook_ref=selected_operator_runbook_ref,
        source_review_checks=source_review_checks,
        operator_notes=(
            list(operator_notes) if operator_notes is not None else None
        ),
    )

    if not review_result.is_valid:
        packet_type_val = receipt.get("packet_type")
        receipt_type_val = receipt.get("receipt_type")
        return _make_result(
            is_valid=False,
            packet_valid=True,
            receipt_valid=True,
            review_valid=False,
            packet_type=(
                str(packet_type_val) if isinstance(packet_type_val, str) else None
            ),
            receipt_type=(
                str(receipt_type_val) if isinstance(receipt_type_val, str) else None
            ),
            review_type=None,
            errors=tuple(f"review_stage_{e}" for e in review_result.errors),
            warnings=(),
        )

    # All stages succeeded.
    review = review_result.review
    return _make_result(
        is_valid=True,
        packet_valid=True,
        receipt_valid=True,
        review_valid=True,
        packet_type=(
            str(review.get("packet_type"))
            if isinstance(review.get("packet_type"), str)
            else None
        ),
        receipt_type=(
            str(review.get("receipt_type"))
            if isinstance(review.get("receipt_type"), str)
            else None
        ),
        review_type=(
            str(review.get("review_type"))
            if isinstance(review.get("review_type"), str)
            else None
        ),
        errors=(),
        warnings=(),
    )
