"""Focused docs tests for docs/resolution_ambiguity_taxonomy_manual_label_workflow.md.

Added in WP55. Tests only docs/schema content. Does not import source implementation.
No parser, no automated extraction, no scorer integration, no feature extraction,
no CLI/export/report, no LLM/provider, no network, no trading.
"""

from __future__ import annotations

import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "docs" / "resolution_ambiguity_taxonomy_manual_label_workflow.md"


def _read() -> str:
    return DOC.read_text(encoding="utf-8")


# ── Document existence ────────────────────────────────────────────────────────

def test_doc_exists():
    assert DOC.is_file()


# ── Docs/schema/tests only ────────────────────────────────────────────────────

def test_doc_states_no_src_change():
    assert "NO_SRC_CHANGE" in _read()


def test_doc_states_no_runtime_change():
    assert "NO_RUNTIME_CHANGE" in _read()


def test_doc_states_no_dependency_change():
    assert "NO_DEPENDENCY_CHANGE" in _read()


def test_doc_states_no_network():
    assert "NO_RUNTIME_NETWORK" in _read()


def test_doc_states_no_trading():
    assert "NO_TRADING_EXECUTION" in _read()


def test_doc_states_no_hermes():
    assert "NO_HERMES_INSTALL_OR_RUNTIME" in _read()


def test_doc_states_docs_schema_tests_only():
    text = _read()
    assert "Docs/schema/tests only: YES" in text


# ── WP55 identity ─────────────────────────────────────────────────────────────

def test_doc_states_wp55():
    assert "WP55" in _read()


# ── Taxonomy categories ───────────────────────────────────────────────────────

def test_taxonomy_missing_resolution_source():
    assert "missing_resolution_source" in _read()


def test_taxonomy_unclear_source_hierarchy():
    assert "unclear_source_hierarchy" in _read()


def test_taxonomy_cutoff_time_ambiguity():
    assert "cutoff_time_ambiguity" in _read()


def test_taxonomy_timezone_ambiguity():
    assert "timezone_ambiguity" in _read()


def test_taxonomy_title_rules_mismatch():
    assert "title_rules_mismatch" in _read()


def test_taxonomy_entity_definition_ambiguity():
    assert "entity_definition_ambiguity" in _read()


def test_taxonomy_event_definition_ambiguity():
    assert "event_definition_ambiguity" in _read()


def test_taxonomy_measurement_definition_ambiguity():
    assert "measurement_definition_ambiguity" in _read()


def test_taxonomy_outcome_mapping_ambiguity():
    assert "outcome_mapping_ambiguity" in _read()


def test_taxonomy_source_conflict():
    assert "source_conflict" in _read()


def test_taxonomy_finality_or_revision_ambiguity():
    assert "finality_or_revision_ambiguity" in _read()


def test_taxonomy_duplicate_or_overlap_risk():
    assert "duplicate_or_overlap_risk" in _read()


def test_taxonomy_insufficient_local_evidence():
    assert "insufficient_local_evidence" in _read()


def test_taxonomy_other_manual_review_issue():
    assert "other_manual_review_issue" in _read()


# ── Review status values ──────────────────────────────────────────────────────

def test_review_status_not_reviewed():
    assert "NOT_REVIEWED" in _read()


def test_review_status_reviewed_clear():
    assert "REVIEWED_CLEAR" in _read()


def test_review_status_reviewed_low_ambiguity():
    assert "REVIEWED_LOW_AMBIGUITY" in _read()


def test_review_status_reviewed_medium_ambiguity():
    assert "REVIEWED_MEDIUM_AMBIGUITY" in _read()


def test_review_status_reviewed_high_ambiguity():
    assert "REVIEWED_HIGH_AMBIGUITY" in _read()


def test_review_status_insufficient_local_evidence():
    assert "INSUFFICIENT_LOCAL_EVIDENCE" in _read()


def test_forbidden_tradeable_status_values():
    text = _read()
    # The doc must forbid trade-like status values; check for explicit forbidden wording
    section5 = ""
    lines = text.splitlines()
    in_section = False
    for line in lines:
        if "## 5. Review Status Values" in line:
            in_section = True
        if in_section and line.startswith("## 6."):
            break
        if in_section:
            section5 += line + "\n"
    assert "Forbidden status values" in section5 or "forbidden" in section5.lower()
    # The allowed table rows must only contain the allowed status tokens
    allowed_tokens = {
        "NOT_REVIEWED", "REVIEWED_CLEAR", "REVIEWED_LOW_AMBIGUITY",
        "REVIEWED_MEDIUM_AMBIGUITY", "REVIEWED_HIGH_AMBIGUITY",
        "INSUFFICIENT_LOCAL_EVIDENCE",
    }
    for token in allowed_tokens:
        assert token in section5


# ── Severity and confidence separation ───────────────────────────────────────

def test_severity_none():
    assert "`NONE`" in _read()


def test_severity_low():
    assert "`LOW`" in _read()


def test_severity_medium():
    assert "`MEDIUM`" in _read()


def test_severity_high():
    assert "`HIGH`" in _read()


def test_severity_unknown():
    assert "`UNKNOWN`" in _read()


def test_reviewer_confidence_values_present():
    text = _read()
    assert "reviewer_confidence" in text
    assert "confidence in the label" in text.lower() or "confidence in the accuracy" in text.lower()


def test_confidence_not_market_outcome():
    text = _read()
    assert "not confidence in any market outcome" in text or "not confidence in any trading outcome" in text


# ── Manual label schema fields ────────────────────────────────────────────────

def test_schema_field_schema_version():
    assert "schema_version" in _read()


def test_schema_field_label_id():
    assert "label_id" in _read()


def test_schema_field_market_id():
    assert "market_id" in _read()


def test_schema_field_question_snapshot():
    assert "question_snapshot" in _read()


def test_schema_field_resolution_text_snapshot():
    assert "resolution_text_snapshot" in _read()


def test_schema_field_review_status():
    assert "review_status" in _read()


def test_schema_field_ambiguity_categories():
    assert "ambiguity_categories" in _read()


def test_schema_field_ambiguity_severity():
    assert "ambiguity_severity" in _read()


def test_schema_field_reviewer_confidence():
    assert "reviewer_confidence" in _read()


def test_schema_field_manual_review_required():
    assert "manual_review_required" in _read()


def test_schema_field_reviewed_at_utc():
    assert "reviewed_at_utc" in _read()


def test_schema_field_reviewer_id_or_role():
    assert "reviewer_id_or_role" in _read()


def test_schema_field_source_artifact_refs():
    assert "source_artifact_refs" in _read()


def test_schema_field_evidence_notes():
    assert "evidence_notes" in _read()


def test_schema_field_limitations():
    assert "limitations" in _read()


def test_schema_field_advisory_label():
    assert "advisory_label" in _read()


def test_schema_field_forbidden_use_notice():
    assert "forbidden_use_notice" in _read()


# ── Advisory-only labels ──────────────────────────────────────────────────────

def test_advisory_label_value_present():
    assert "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED" in _read()


def test_advisory_label_not_suppressible():
    text = _read()
    assert "not optional" in text or "not be optional" in text or "must not be optional" in text


def test_forbidden_use_notice_required():
    text = _read()
    assert "forbidden_use_notice" in text
    assert "not a trading signal" in text


# ── Non-signal boundary ───────────────────────────────────────────────────────

def test_non_signal_boundary_section_present():
    text = _read()
    assert "Non-Signal Boundary" in text or "non-signal" in text.lower()


def test_no_profitability_claim():
    text = _read()
    assert "profitability" in text or "not imply" in text


def test_no_expected_return_claim():
    text = _read()
    assert "expected return" in text  # must appear in forbidden/non-goal section


def test_safe_framing_terms_present():
    text = _read()
    assert "resolution_ambiguity_review" in text or "research_data_quality" in text


# ── No parser / no automated extraction / no LLM / no network ────────────────

def test_no_parser_in_wp55():
    text = _read()
    assert "no automated resolution-rule parser is added in WP55" in text or \
           "No parser: YES" in text


def test_no_automated_extraction_in_wp55():
    text = _read()
    assert "No automated extraction: YES" in text or \
           "no automated ambiguity extraction is added in WP55" in text


def test_no_llm_in_wp55():
    text = _read()
    assert "No LLM/provider: YES" in text or "no LLM or Hermes provider is used" in text


def test_no_network_in_wp55():
    text = _read()
    assert "No network: YES" in text or "NO_RUNTIME_NETWORK" in text


def test_no_scorer_integration_in_wp55():
    text = _read()
    assert "No scorer integration: YES" in text or \
           "scorer integration is deferred" in text


def test_no_feature_extraction_in_wp55():
    text = _read()
    assert "No feature extraction: YES" in text or \
           "feature extraction from ambiguity labels is deferred" in text


# ── Future integration gate ───────────────────────────────────────────────────

def test_future_integration_gate_section_present():
    text = _read()
    assert "Future Integration Gate" in text or "future approved work package" in text.lower()


def test_no_feature_extraction_implemented_in_wp55():
    text = _read()
    assert "No feature extraction is implemented in WP55" in text or \
           "no feature extraction" in text.lower()


# ── Invalid examples ──────────────────────────────────────────────────────────

def test_invalid_examples_section_present():
    text = _read()
    assert "Invalid Example" in text or "invalid example" in text.lower()


def test_invalid_examples_explain_forbidden_semantics():
    text = _read()
    assert "Why invalid" in text


# ── Valid examples ────────────────────────────────────────────────────────────

def test_valid_examples_section_present():
    text = _read()
    assert "Valid Example" in text


def test_valid_examples_use_research_data_quality_wording():
    text = _read()
    assert "research-data-quality metadata" in text or \
           "research_data_quality" in text


# ── Deferred items ────────────────────────────────────────────────────────────

def test_deferred_items_section_present():
    text = _read()
    assert "Deferred Items" in text or "WP55-D001" in text


def test_wp55_d001_present():
    assert "WP55-D001" in _read()


def test_wp55_d002_present():
    assert "WP55-D002" in _read()


def test_automated_parser_deferred():
    text = _read()
    assert "automated" in text.lower() and ("parser" in text.lower() or "extraction" in text.lower())
    assert "deferred" in text.lower() or "not started" in text.lower()


# ── Local/offline/read-only only ──────────────────────────────────────────────

def test_local_offline_requirement():
    text = _read()
    assert "local/offline" in text or "local, offline" in text


def test_no_live_api_in_labels():
    text = _read()
    assert "not reference live API" in text or "no live API" in text.lower() or \
           "must not reference live API" in text


# ── WP56 cross-reference ──────────────────────────────────────────────────────

def test_doc_references_wp56():
    assert "WP56" in _read()


def test_doc_references_wp56_schema_validator():
    text = _read()
    assert "resolution_ambiguity_labels.py" in text


def test_wp55_merged_in_status():
    text = _read()
    # WP55 must be shown as merged in the status section
    assert "merged" in text.lower()
    assert "b019bb825924d52057225455886c3ca45af9e925" in text or "WP55" in text


def test_wp56_on_branch_in_status():
    text = _read()
    assert "on branch" in text.lower() or "WP56" in text


def test_wp56_d001_present():
    assert "WP56-D001" in _read()


def test_wp56_validator_scope_does_not_include_feature_extraction():
    text = _read()
    assert "WP56 does not implement" in text or "no feature extraction" in text.lower()
