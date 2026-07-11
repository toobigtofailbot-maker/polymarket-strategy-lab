from copy import deepcopy

from src.data_layer.hermes_candidate_review_research_candidate_queue import (
    REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS,
    build_candidate_review_research_candidate_queue_item,
    build_candidate_review_research_candidate_queue_package,
)


TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_STORAGE_PATH_SCORING"


def _notice() -> str:
    return (
        "Advisory only; manual, local, offline; human review required; not execution; not runtime; "
        "not credential; not paper or live; not prompt execution; not file or network; not strategy promotion; "
        "not PR approval; not storage or writer; not automated task; not export or report; "
        "not discovery automation; not market data ingestion; not scoring or ranking."
    )


def _flags() -> dict[str, bool]:
    return {flag: True for flag in REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS}


def _item() -> dict[str, object]:
    return {
        "candidate_id": "synthetic-candidate-127", "source_wp_context": "WP126 synthetic queue contract",
        "candidate_reference": "synthetic-reference-127", "candidate_label": "CANDIDATE_READY_FOR_MANUAL_RESEARCH_REVIEW",
        "candidate_reason_labels": ["EVIDENCE_QUALITY_GAP"], "candidate_summary": "Synthetic source needs manual review",
        "evidence_references_to_check": ["synthetic-public-reference"],
        "resolution_rule_notes": "Synthetic resolution wording needs manual review",
        "source_quality_notes": "Synthetic provenance needs manual review",
        "uncertainty_notes": "Synthetic source freshness remains uncertain",
        "known_missing_data": "Synthetic publication date is missing", "limitations": "Synthetic fixture only",
        "falsification_checks_to_perform": ["Compare a synthetic conflicting source"],
        "operator_next_manual_step": "Inspect the synthetic reference manually", "human_review_required": True,
        "non_authority_notice": _notice(), "safety_flags": _flags(),
    }


def test_wp126_candidate_queue_safe_in_memory_smoke_and_fail_closed_trap(tmp_path) -> None:
    item_data = _item()
    item = build_candidate_review_research_candidate_queue_item(item_data)
    assert item.is_valid and item.errors == item.warnings == ()
    assert item.candidate_item and all(item.safety_flags.values())

    queue_data = {
        "queue_id": "synthetic-queue-127", "source_wp_context": "WP126 synthetic queue contract",
        "queue_label": "QUEUE_READY_FOR_MANUAL_RESEARCH_REVIEW", "candidate_items": [item.candidate_item],
        "queue_summary": "Synthetic candidates awaiting manual review",
        "operator_next_manual_step": "Review each synthetic candidate manually", "human_review_required": True,
        "non_authority_notice": _notice(), "safety_flags": _flags(),
    }
    queue = build_candidate_review_research_candidate_queue_package(queue_data)
    assert queue.is_valid and queue.errors == queue.warnings == ()
    assert len(queue.queue_package["candidate_items"]) == 1 and all(queue.safety_flags.values())
    for flag in REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS:
        assert queue.safety_flags[flag] is True

    unsafe = deepcopy(queue_data)
    unsafe["queue_summary"] = TRAP
    invalid = build_candidate_review_research_candidate_queue_package(unsafe)
    assert not invalid.is_valid
    assert invalid.queue_package == {} and invalid.safety_flags == {}
    assert invalid.queue_label is None and invalid.warnings == () and TRAP not in repr(invalid)
    assert list(tmp_path.iterdir()) == []
