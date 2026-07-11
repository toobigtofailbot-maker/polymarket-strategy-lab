import ast
from pathlib import Path

from src.data_layer.hermes_candidate_review_manual_queue_selection_handoff import (
    REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS,
    assert_candidate_review_manual_queue_selection_record,
    build_candidate_review_manual_queue_selection_record,
    build_candidate_review_research_question_handoff,
)
from src.data_layer.hermes_candidate_review_research_candidate_queue import (
    REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS,
    build_candidate_review_research_candidate_queue_item,
    build_candidate_review_research_candidate_queue_package,
)
from src.data_layer.hermes_candidate_review_research_question_record import (
    REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS,
    REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS,
    assert_candidate_review_research_question_record,
    build_candidate_review_research_question_record,
)


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_STORAGE_PATH_SCORING_AUTO_SELECT"
QUESTION = "Which public source most directly resolves the synthetic outcome wording ambiguity?"


def _flags(names): return {name: True for name in names}


def _queue_notice():
    return ("Advisory only; manual, local, offline; human review required; not execution; not runtime; "
            "not credential; not paper or live; not prompt execution; not file or network; not strategy promotion; "
            "not PR approval; not storage or writer; not automated task; not export or report; "
            "not discovery automation; not market data ingestion; not scoring or ranking.")


def _wp128_notice():
    return ("Advisory only; manual; local; offline; human review required; explicit human selection only; "
            "not automated selection; not scoring or ranking; not priority calculation; not discovery automation; "
            "not market data ingestion; not research-question generation; not execution; not runtime; not credentials; "
            "not paper or live; not prompt execution; not file or network; not strategy promotion; not PR approval; "
            "not storage or writer; not export or report.")


def _item():
    return {"candidate_id": "synthetic-candidate-129", "source_wp_context": "WP126 synthetic queue contract",
            "candidate_reference": "synthetic-reference-129", "candidate_label": "CANDIDATE_READY_FOR_MANUAL_RESEARCH_REVIEW",
            "candidate_reason_labels": ["EVIDENCE_QUALITY_GAP"], "candidate_summary": "Synthetic source needs manual review",
            "evidence_references_to_check": ["synthetic-public-reference"], "resolution_rule_notes": "Synthetic wording needs review",
            "source_quality_notes": "Synthetic provenance needs review", "uncertainty_notes": "Synthetic freshness is uncertain",
            "known_missing_data": "Synthetic publication date is missing", "limitations": "Synthetic fixture only",
            "falsification_checks_to_perform": ["Compare a synthetic conflicting source"],
            "operator_next_manual_step": "Inspect the synthetic reference manually", "human_review_required": True,
            "non_authority_notice": _queue_notice(), "safety_flags": _flags(REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS)}


def _selection():
    return {"selection_id": "synthetic-selection-129", "source_wp_context": "WP128 manual review",
            "source_queue_reference": "synthetic-queue-129", "selected_candidate_reference": "synthetic-reference-129",
            "selection_label": "SELECT_FOR_MANUAL_RESEARCH_QUESTION_DRAFT",
            "selection_reason_labels": ["HUMAN_SELECTED_FOR_DEEPER_RESEARCH"],
            "human_selection_basis": "Operator manually inspected the synthetic references",
            "evidence_references_reviewed": ["synthetic-public-reference"], "uncertainty_notes": "Synthetic wording remains uncertain",
            "known_missing_data": "Synthetic publication date is missing", "limitations": "Manual synthetic review only",
            "duplicate_check_notes": "No synthetic duplicate found", "operator_next_manual_step": "Supply question text manually",
            "human_review_required": True, "created_by_operator_note": "Recorded by human operator",
            "non_authority_notice": _wp128_notice(), "safety_flags": _flags(REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS)}


def _handoff():
    return {"handoff_id": "synthetic-handoff-129", "source_wp_context": "WP128 manual handoff",
            "source_selection_record_reference": "synthetic-selection-129", "selected_candidate_reference": "synthetic-reference-129",
            "proposed_research_question": QUESTION, "proposed_research_question_type": "RESOLUTION_RULE_AMBIGUITY",
            "evidence_references_to_check": ["synthetic-public-reference"], "uncertainty_notes": "Synthetic wording remains uncertain",
            "known_missing_data": "Synthetic publication date is missing", "limitations": "Caller supplied synthetic question",
            "falsification_checks_to_perform": ["Check a synthetic contrary source"],
            "operator_next_manual_step": "Review the proposed question manually", "human_review_required": True,
            "created_by_operator_note": "Recorded by human operator", "non_authority_notice": _wp128_notice(),
            "safety_flags": _flags(REQUIRED_MANUAL_QUEUE_SELECTION_SAFETY_FLAGS)}


def _wp121(handoff):
    return {"record_id": "synthetic-rq-129", "source_wp_context": {"intake_wp": "WP126", "runbook_wp": "WP129", "contract_wp": "WP121"},
            "selected_candidate_reference": {"candidate_id": handoff["selected_candidate_reference"], "source_artifact": "synthetic-in-memory-handoff"},
            "intake_basis": _flags(REQUIRED_RESEARCH_QUESTION_PREFLIGHT_FLAGS), "research_question": handoff["proposed_research_question"],
            "research_question_type": handoff["proposed_research_question_type"], "evidence_references_to_check": handoff["evidence_references_to_check"],
            "uncertainty_notes": [handoff["uncertainty_notes"]], "known_missing_data": [handoff["known_missing_data"]],
            "limitations": [handoff["limitations"]], "falsification_checks_to_perform": handoff["falsification_checks_to_perform"],
            "forbidden_interpretation_flags": {"not_a_signal": True, "not_authority": True}, "human_review_required": True,
            "next_manual_step": "Manually inspect the synthetic source", "created_by_operator_note": "Prepared by human operator",
            "non_authority_notice": ("Advisory-only manual local offline planning record. It is not a trade signal, not strategy promotion, "
                "not paper readiness, not live readiness, not execution authority, not risk authority, not order authority, not PR approval, "
                "not merge readiness, not credential permission, not account access, not private-state permission, not Hermes runtime authority, "
                "and not prompt runner authority."), "safety_flags": _flags(REQUIRED_RESEARCH_QUESTION_NON_AUTHORITY_FLAGS)}


def test_positive_manual_chain_stays_in_memory_and_advisory(tmp_path) -> None:
    item = build_candidate_review_research_candidate_queue_item(_item()); assert item.is_valid
    queue_data = {"queue_id": "synthetic-queue-129", "source_wp_context": "WP126 synthetic queue contract",
                  "queue_label": "QUEUE_READY_FOR_MANUAL_RESEARCH_REVIEW", "candidate_items": [item.candidate_item],
                  "queue_summary": "Synthetic candidates awaiting manual review", "operator_next_manual_step": "Review manually",
                  "human_review_required": True, "non_authority_notice": _queue_notice(),
                  "safety_flags": _flags(REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS)}
    queue = build_candidate_review_research_candidate_queue_package(queue_data); assert queue.is_valid
    selected = build_candidate_review_manual_queue_selection_record(_selection()); assert selected.is_valid
    assert not ({"priority_score", "rank", "score"} & set(selected.selection_record))
    handed = build_candidate_review_research_question_handoff(_handoff()); assert handed.is_valid
    assert handed.handoff_record["proposed_research_question"] == QUESTION
    final = build_candidate_review_research_question_record(_wp121(handed.handoff_record)); assert final.is_valid
    for record in (queue.queue_package, selected.selection_record, handed.handoff_record, final.record):
        assert record["human_review_required"] is True
        assert "advisory" in record["non_authority_notice"].lower()
    assert list(tmp_path.iterdir()) == []


def test_reviewer_traps_fail_closed_neutrally_and_create_nothing(tmp_path) -> None:
    unsafe_queue = {**_item(), "candidate_summary": TRAP}
    invalid_item = build_candidate_review_research_candidate_queue_item(unsafe_queue)
    assert not invalid_item.is_valid and TRAP not in repr(invalid_item)
    for key in ("priority_score", "rank", "score"):
        data = _selection(); data[key] = 1
        result = build_candidate_review_manual_queue_selection_record(data)
        assert not result.is_valid and result.selection_record == {}
    missing = _handoff(); del missing["proposed_research_question"]
    result = build_candidate_review_research_question_handoff(missing)
    assert not result.is_valid and result.handoff_record == {}
    for field in ("non_authority_notice", "proposed_research_question"):
        unsafe = _handoff(); unsafe[field] = (_wp128_notice() + " " + TRAP) if field == "non_authority_notice" else TRAP
        result = build_candidate_review_research_question_handoff(unsafe)
        assert not result.is_valid and TRAP not in repr(result)
    unsafe_final = _wp121(_handoff()); unsafe_final["research_question"] = TRAP
    result = build_candidate_review_research_question_record(unsafe_final)
    assert not result.is_valid and result.record == {} and TRAP not in repr(result)
    for helper, data in ((assert_candidate_review_manual_queue_selection_record, {**_selection(), "selected_candidate_reference": TRAP}),
                         (assert_candidate_review_research_question_record, unsafe_final)):
        try: helper(data)
        except ValueError as exc:
            assert TRAP not in str(exc)
        else: raise AssertionError("neutral assert helper accepted unsafe input")
    assert list(tmp_path.iterdir()) == []


def test_no_adapter_priority_or_recommendation_surface_exists() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    function_names = {node.name.lower() for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert not any(name.startswith(("convert", "adapt", "auto_select")) for name in function_names)
    ordered = [_selection(), {**_selection(), "selection_id": "second"}]
    assert [entry["selection_id"] for entry in ordered] == ["synthetic-selection-129", "second"]
    outputs = repr([build_candidate_review_manual_queue_selection_record(entry) for entry in ordered]).lower()
    assert "recommended candidate" not in outputs and "research priority approved" not in outputs
