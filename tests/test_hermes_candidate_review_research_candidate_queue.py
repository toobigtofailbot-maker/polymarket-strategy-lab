from __future__ import annotations

import dataclasses
from copy import deepcopy
import pytest

from src.data_layer.hermes_candidate_review_research_candidate_queue import *

TRAP = "NEVER_ECHO_BUY_PRIVATE_KEY_MERGE_READY_PROMPT_RUNNER_STORAGE_PATH_SCORING"

def notice() -> str:
    return ("Advisory only; manual, local, offline; human review required; not execution; not runtime; "
            "not credential; not paper or live; not prompt execution; not file or network; not strategy promotion; "
            "not PR approval; not storage or writer; not automated task; not export or report; "
            "not discovery automation; not market data ingestion; not scoring or ranking.")

def item() -> dict[str, object]:
    return {"candidate_id":"candidate-1", "source_wp_context":"WP126 synthetic context", "candidate_reference":"candidate reference one",
            "candidate_label":"CANDIDATE_READY_FOR_MANUAL_RESEARCH_REVIEW", "candidate_reason_labels":["EVIDENCE_QUALITY_GAP"],
            "candidate_summary":"Candidate needs manual source research", "evidence_references_to_check":["public source reference"],
            "resolution_rule_notes":"Resolution wording needs manual review", "source_quality_notes":"Source provenance needs review",
            "uncertainty_notes":"Outcome remains uncertain", "known_missing_data":"Publication date is missing",
            "limitations":"Research planning surface only", "falsification_checks_to_perform":["Check a conflicting public source"],
            "operator_next_manual_step":"Review the public source manually", "human_review_required":True,
            "non_authority_notice":notice(), "safety_flags":{f:True for f in REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS}}

def package() -> dict[str, object]:
    return {"queue_id":"queue-1", "source_wp_context":"WP126 synthetic context", "queue_label":"QUEUE_READY_FOR_MANUAL_RESEARCH_REVIEW",
            "candidate_items":[item()], "queue_summary":"Manual research candidate collection", "operator_next_manual_step":"Review each candidate manually",
            "human_review_required":True, "non_authority_notice":notice(), "safety_flags":{f:True for f in REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS}}

def public(result: object) -> str: return repr(result)

def test_stdlib_only_import_posture():
    import ast, pathlib
    tree=ast.parse(pathlib.Path("src/data_layer/hermes_candidate_review_research_candidate_queue.py").read_text())
    assert {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} <= {"__future__","dataclasses","typing"}

def test_valid_item_and_package():
    assert validate_candidate_review_research_candidate_queue_item(item()).is_valid
    assert validate_candidate_review_research_candidate_queue_package(package()).is_valid

@pytest.mark.parametrize("label", ALLOWED_RESEARCH_CANDIDATE_QUEUE_ITEM_LABELS)
def test_all_item_labels(label):
    data=item(); data["candidate_label"]=label; assert validate_candidate_review_research_candidate_queue_item(data).is_valid

@pytest.mark.parametrize("reason", ALLOWED_RESEARCH_CANDIDATE_QUEUE_REASON_LABELS)
def test_all_reason_labels(reason):
    data=item(); data["candidate_reason_labels"]=[reason]; assert validate_candidate_review_research_candidate_queue_item(data).is_valid

@pytest.mark.parametrize("label", ALLOWED_RESEARCH_CANDIDATE_QUEUE_LABELS)
def test_all_queue_labels(label):
    data=package(); data["queue_label"]=label; assert validate_candidate_review_research_candidate_queue_package(data).is_valid

def test_unknown_labels():
    data=item(); data["candidate_label"]="UNKNOWN"; assert not validate_candidate_review_research_candidate_queue_item(data).is_valid
    data=item(); data["candidate_reason_labels"]=["UNKNOWN"]; assert not validate_candidate_review_research_candidate_queue_item(data).is_valid
    data=package(); data["queue_label"]="UNKNOWN"; assert not validate_candidate_review_research_candidate_queue_package(data).is_valid

@pytest.mark.parametrize("field", REQUIRED_RESEARCH_CANDIDATE_QUEUE_ITEM_FIELDS)
def test_missing_fields(field):
    data=item(); del data[field]; assert validate_candidate_review_research_candidate_queue_item(data).errors == ("MISSING_REQUIRED_FIELD",)

@pytest.mark.parametrize("bad", [None,"","   "])
def test_null_blank_scalar(bad):
    data=item(); data["candidate_summary"]=bad; assert not validate_candidate_review_research_candidate_queue_item(data).is_valid

@pytest.mark.parametrize("bad", [None,"text",[],1])
def test_unsupported_shapes(bad):
    assert validate_candidate_review_research_candidate_queue_item(bad).errors == ("UNSUPPORTED_INPUT_SHAPE",)
    assert validate_candidate_review_research_candidate_queue_package(bad).errors == ("UNSUPPORTED_INPUT_SHAPE",)

def test_empty_and_invalid_package_items():
    data=package(); data["candidate_items"]=[]; assert not validate_candidate_review_research_candidate_queue_package(data).is_valid
    data=package(); data["candidate_items"]=["bad"]; assert not validate_candidate_review_research_candidate_queue_package(data).is_valid

@pytest.mark.parametrize("mutation", ["missing","false","truthy"])
def test_safety_flags(mutation):
    data=item(); flags=dict(data["safety_flags"]); flag=REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS[0]
    if mutation=="missing": del flags[flag]
    elif mutation=="false": flags[flag]=False
    else: flags[flag]=1
    data["safety_flags"]=flags; assert not validate_candidate_review_research_candidate_queue_item(data).is_valid

def test_flags_sanitized_and_human_review_exact_true():
    data=item(); data["safety_flags"]["benign_extra"]=True; result=validate_candidate_review_research_candidate_queue_item(data)
    assert result.is_valid and set(result.safety_flags)==set(REQUIRED_RESEARCH_CANDIDATE_QUEUE_SAFETY_FLAGS)
    data=item(); data["human_review_required"]=1; assert not validate_candidate_review_research_candidate_queue_item(data).is_valid

@pytest.mark.parametrize("bad", ["", notice()+" This grants permission to continue."])
def test_notice_required_and_no_permission(bad):
    data=item(); data["non_authority_notice"]=bad; assert not validate_candidate_review_research_candidate_queue_item(data).is_valid

@pytest.mark.parametrize("unsafe", ["buy now","expected return and edge","paper ready","private key","account state","runtime logs","prompt runner","model call","provider","Hermes runtime","scheduler","dashboard","bot loop","automated task","parser","loader","file writer","storage path","exporter","CLI command","market data ingestion","discovery automation","scoring","ranking"])
def test_forbidden_families_recursively(unsafe):
    data=item(); data["evidence_references_to_check"]=[{"safe":unsafe}]
    assert validate_candidate_review_research_candidate_queue_item(data).errors == ("FORBIDDEN_CONTENT",)

@pytest.mark.parametrize("key", ["raw_metadata","metadata","custom_fields","raw_response","prompt","free_form"])
def test_raw_metadata_keys(key):
    data=item(); data["evidence_references_to_check"]=[{"safe":{key:"benign"}}]
    assert validate_candidate_review_research_candidate_queue_item(data).errors == ("RAW_METADATA_NOT_ALLOWED",)

@pytest.mark.parametrize("field", ["safety_flags","candidate_reference"])
def test_hidden_unsafe_content_fails_closed(field):
    data=item(); data[field]={"safe":TRAP}; result=validate_candidate_review_research_candidate_queue_item(data)
    assert not result.is_valid and result.candidate_item=={} and TRAP not in public(result)

def test_assert_neutral_no_echo():
    data=item(); data["candidate_reference"]=TRAP
    with pytest.raises(ValueError) as exc: assert_candidate_review_research_candidate_queue_item(data)
    assert TRAP not in str(exc.value)
    q=package(); q["queue_summary"]=TRAP
    with pytest.raises(ValueError) as exc: assert_candidate_review_research_candidate_queue_package(q)
    assert TRAP not in str(exc.value)

def test_build_no_mutation_and_dataclass_fields():
    data=item(); original=deepcopy(data); assert build_candidate_review_research_candidate_queue_item(data).is_valid; assert data==original
    q=package(); original=deepcopy(q); assert build_candidate_review_research_candidate_queue_package(q).is_valid; assert q==original
    assert [f.name for f in dataclasses.fields(HermesCandidateReviewResearchCandidateQueueItemResult)] == ["is_valid","candidate_item","errors","warnings","candidate_label","candidate_reason_labels","safety_flags"]
    assert [f.name for f in dataclasses.fields(HermesCandidateReviewResearchCandidateQueuePackageResult)] == ["is_valid","queue_package","errors","warnings","queue_label","safety_flags"]
