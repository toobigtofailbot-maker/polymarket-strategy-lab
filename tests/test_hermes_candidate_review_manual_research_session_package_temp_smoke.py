from __future__ import annotations

from src.data_layer.hermes_candidate_review_advisory_output_validation_receipt import (
    REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS, REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS,
    build_candidate_review_advisory_output_validation_receipt,
)
from src.data_layer.hermes_candidate_review_human_decision_follow_up_record import (
    REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS,
    build_candidate_review_follow_up_research_task_record, build_candidate_review_human_decision_record,
)
from src.data_layer.hermes_candidate_review_manual_research_session_package import (
    REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS,
    build_candidate_review_manual_research_session_package,
)
from src.data_layer.hermes_candidate_review_research_question_record import (
    REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS, REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS,
    build_candidate_review_research_question_record,
)


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_STORAGE_PATH"


def _notice(storage: bool = False) -> str:
    tail = " not storage/writer/export authority; not automated task authority; not report/export authority." if storage else ""
    return ("Advisory only manual local offline; human review required; not fact without source review; "
            "not a trade signal; not strategy promotion; not paper readiness; not live readiness; not execution authority; "
            "not risk authority; not order authority; not PR approval; not merge readiness; not credential permission; "
            "not account access; not private-state access; not Hermes runtime authority; not prompt runner authority;" + tail)


def test_wp121_through_wp124_safe_in_memory_smoke(tmp_path) -> None:
    question = build_candidate_review_research_question_record({
        "record_id": "rq-125", "source_wp_context": {"intake_wp": "WP118"},
        "selected_candidate_reference": {"candidate_id": "synthetic-125"},
        "intake_basis": {flag: True for flag in REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS},
        "research_question": "Which synthetic source needs manual provenance review?",
        "research_question_type": "SOURCE_PROVENANCE_WEAKNESS", "evidence_references_to_check": ["synthetic-source-a"],
        "uncertainty_notes": ["Synthetic source freshness is unknown."], "known_missing_data": ["Synthetic timestamp."],
        "limitations": ["Synthetic fixture only."], "falsification_checks_to_perform": ["Compare a synthetic conflicting source."],
        "forbidden_interpretation_flags": {"not_a_signal": True}, "human_review_required": True,
        "next_manual_step": "Inspect the synthetic source manually.", "created_by_operator_note": "Synthetic operator fixture.",
        "non_authority_notice": _notice(), "safety_flags": {flag: True for flag in REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS},
    })
    assert question.is_valid

    receipt_flags = {flag: True for flag in (*REQUIRED_ADVISORY_OUTPUT_SAFETY_FLAGS, *REQUIRED_ADVISORY_OUTPUT_REVIEW_FLAGS)}
    receipt = build_candidate_review_advisory_output_validation_receipt({
        "receipt_id": "receipt-125", "source_wp_context": {"question_wp": "WP121"},
        "source_research_question_record_reference": {"record_id": question.record["record_id"]},
        "advisory_output_reference": {"artifact_id": "synthetic-advisory-125"}, "receipt_label": "ADVISORY_OUTPUT_NEEDS_MORE_EVIDENCE",
        "source_references_checked": ["synthetic-source-a"], "unsupported_claims": ["No unsupported claims accepted."],
        "uncertainty_review": ["Reviewed."], "limitations_review": ["Reviewed."], "missing_data_review": ["Reviewed."],
        "falsification_review": ["Reviewed."], "human_review_notes": ["Synthetic manual review."],
        "follow_up_research_tasks": ["Recheck synthetic source."], "forbidden_interpretation_flags": {"not_authority": True},
        "human_review_required": True, "non_authority_notice": _notice(True), "safety_flags": receipt_flags,
    })
    assert receipt.is_valid

    record_flags = {flag: True for flag in REQUIRED_CANDIDATE_REVIEW_RECORD_SAFETY_FLAGS}
    common = {"human_review_required": True, "non_authority_notice": _notice(True), "safety_flags": record_flags}
    decision = build_candidate_review_human_decision_record({
        "decision_id": "decision-125", "source_wp_context": {"receipt_wp": "WP122"},
        "source_research_question_record_reference": {"record_id": question.record["record_id"]},
        "source_advisory_output_validation_receipt_reference": {"receipt_id": receipt.receipt["receipt_id"]},
        "decision_label": "NEEDS_MORE_EVIDENCE", "decision_basis": ["Synthetic source recheck needed."],
        "accepted_findings": ["Synthetic comparison is consistent."], "rejected_findings": ["Unsupported claim excluded."],
        "unresolved_questions": ["Synthetic freshness."], "evidence_references_relied_on": ["synthetic-source-a"],
        "uncertainty_notes": ["Bounded synthetic uncertainty."], "limitations": ["Synthetic fixture only."],
        "falsification_checks_completed": ["Synthetic comparison completed."], "follow_up_research_tasks": ["Recheck source."],
        "created_by_operator_note": "Synthetic operator decision.", **common,
    })
    assert decision.is_valid
    task = build_candidate_review_follow_up_research_task_record({
        "task_id": "task-125", "source_wp_context": {"decision_wp": "WP123"},
        "source_human_decision_reference": {"decision_id": decision.decision_record["decision_id"]},
        "task_label": "SOURCE_RECHECK_TASK", "task_question": "Which synthetic source supports the reviewed claim?",
        "evidence_to_check": ["synthetic-source-a"], "source_references_to_revisit": ["synthetic-source-b"],
        "missing_data_to_resolve": ["Synthetic timestamp."], "uncertainty_to_reduce": ["Synthetic freshness."],
        "falsification_check_to_perform": ["Compare synthetic source text."], "blocking_reason": "Manual review incomplete.",
        "next_manual_step": "Inspect the synthetic source manually.", "created_by_operator_note": "Synthetic follow-up.", **common,
    })
    assert task.is_valid

    package_data = {
        "session_id": "session-125", "source_wp_context": "WP121 through WP124 synthetic in-memory chain",
        "research_question_record": {"record_id": question.record["record_id"], "summary": "Synthetic source review"},
        "advisory_output_validation_receipt": {"receipt_id": receipt.receipt["receipt_id"], "summary": "Synthetic claims need review"},
        "human_decision_record": {"decision_id": decision.decision_record["decision_id"], "summary": "More evidence needed"},
        "follow_up_research_task_records": [{"task_id": task.follow_up_task_record["task_id"], "summary": "Recheck synthetic source manually"}],
        "session_label": "SESSION_READY_FOR_MANUAL_REVIEW_MEMORY", "session_summary": "Synthetic manual session in memory",
        "source_references_summary": "Synthetic references manually reviewed", "evidence_gap_summary": "Synthetic timestamp missing",
        "uncertainty_summary": "Synthetic freshness remains uncertain", "limitations_summary": "Synthetic fixture only",
        "falsification_summary": "A synthetic conflict rejects the claim", "operator_next_manual_step": "Recheck the synthetic source manually",
        "human_review_required": True, "non_authority_notice": _notice(True),
        "safety_flags": {flag: True for flag in REQUIRED_MANUAL_RESEARCH_SESSION_PACKAGE_SAFETY_FLAGS},
    }
    package = build_candidate_review_manual_research_session_package(package_data)
    assert package.is_valid and package.errors == package.warnings == ()
    assert all(package.safety_flags.values())

    package_data["session_summary"] = TRAP
    invalid = build_candidate_review_manual_research_session_package(package_data)
    assert not invalid.is_valid
    assert invalid.session_package == {} and invalid.warnings == () and invalid.safety_flags == {}
    assert invalid.session_label is None and TRAP not in repr(invalid)
    assert list(tmp_path.iterdir()) == []
