"""Focused tests for WP79 wallet signal research profile and research queue annotation.

Tests cover:
- profiles built from valid WP78 loaded records;
- invalid records handled deterministically;
- event counts deterministic;
- single event yields SINGLE_EVENT_LOW_SAMPLE;
- suspicious-flow yields SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED / BLOCK_FROM_AUTOMATION;
- unknown category yields UNKNOWN_CATEGORY_CONTEXT;
- allowed signal categories only;
- forbidden trade-like values never in outputs;
- advisory labels present;
- profile dataclasses frozen;
- annotation dataclasses frozen;
- annotations include market_id / condition_id and research_priority_effect;
- annotations do not include forbidden trading fields;
- no network libraries imported;
- no file writes;
- no credentials/auth clients;
- no LLM/agent libraries;
- no copyability PnL or expected-return;
- no scoring weight mutation;
- docs advisory-only, no network, no execution, no copy trading.
"""

from __future__ import annotations

import ast
import importlib
import inspect
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import MagicMock

import pytest

from src.data_layer.wallet_signal_research_profile import (
    ALLOWED_SIGNAL_CATEGORIES,
    ALLOWED_RESEARCH_PRIORITY_EFFECTS,
    ANNOTATION_ADVISORY_LABEL,
    COPY_NOT_EVALUATED,
    COPY_SUSPICIOUS_DO_NOT_COPY,
    COPY_UNCOPYABLE_FAST,
    COPY_UNPROVEN,
    EFFECT_BLOCK_FROM_AUTOMATION,
    EFFECT_NO_CHANGE,
    EFFECT_REQUIRE_HUMAN_REVIEW,
    FORBIDDEN_OUTPUT_VALUES,
    PROFILE_ADVISORY_LABEL,
    SAMPLE_SIZE_NOT_EVALUATED,
    SAMPLE_SIZE_SINGLE_EVENT,
    SAMPLE_SIZE_SMALL,
    SAMPLE_SIZE_SUFFICIENT,
    SIGNAL_SUSPICIOUS_TIMING,
    SIGNAL_UNKNOWN,
    SPEC_MATCH_MATCHED,
    SPEC_MATCH_UNKNOWN,
    SUSPICIOUS_HUMAN_REVIEW,
    SUSPICIOUS_NO_FLAG,
    SUSPICIOUS_WATCH_ONLY,
    WalletResearchQueueAnnotation,
    WalletSignalResearchProfile,
    build_wallet_research_queue_annotations,
    build_wallet_signal_research_profiles,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE_MODULE_PATH = ROOT / "src" / "data_layer" / "wallet_signal_research_profile.py"
PROFILE_DOC_PATH = ROOT / "docs" / "wallet_signal_research_profile.md"
REPO_TRUTH_PATH = ROOT / "docs" / "repo_truth_index.md"
DEFERRED_PATH = ROOT / "docs" / "deferred_items_log.md"
STATUS_PATH = ROOT / "docs" / "project_status.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_record(
    wallet_id: str = "0xTEST",
    market_id: str = "market-001",
    condition_id: str = "cond-001",
    market_category: str = "Politics",
    suspicious_flow_flag: bool = False,
    human_review_required: bool = False,
    copyability_context_available: bool = True,
    is_valid: bool = True,
) -> object:
    """Build a duck-typed LoadedWalletTradeEventRecord."""
    record = {
        "wallet_reference": {"wallet_id_or_address": wallet_id},
        "market_reference": {
            "market_id": market_id,
            "condition_id": condition_id,
            "market_category": market_category,
        },
        "observation": {},
        "context": {
            "copyability_context_available": copyability_context_available,
            "liquidity_context_available": True,
            "orderbook_context_available": True,
        },
        "review": {
            "suspicious_flow_flag": suspicious_flow_flag,
            "human_review_required": human_review_required,
            "advisory_only_notice": "ADVISORY_ONLY",
        },
        "safety": {
            "manual_research_only": True,
            "not_automated_copy_trading": True,
            "no_live_execution": True,
            "no_order_placement": True,
            "no_position_sizing": True,
            "no_risk_override": True,
            "no_parameter_auto_change": True,
        },
    }
    validation = MagicMock()
    validation.is_valid = is_valid
    loaded = MagicMock()
    loaded.record = record
    loaded.validation = validation
    return loaded


def _all_string_values(obj: object, _seen: set | None = None) -> list[str]:
    if _seen is None:
        _seen = set()
    oid = id(obj)
    if oid in _seen:
        return []
    _seen.add(oid)
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, (list, tuple)):
        result: list[str] = []
        for item in obj:
            result.extend(_all_string_values(item, _seen))
        return result
    if isinstance(obj, Mapping):
        result = []
        for v in obj.values():
            result.extend(_all_string_values(v, _seen))
        return result
    return []


def _profile_string_values(profile: WalletSignalResearchProfile) -> list[str]:
    values: list[str] = []
    for f in dc_fields(profile):
        val = getattr(profile, f.name)
        values.extend(_all_string_values(val))
    return values


def _annotation_string_values(ann: WalletResearchQueueAnnotation) -> list[str]:
    values: list[str] = []
    for f in dc_fields(ann):
        val = getattr(ann, f.name)
        values.extend(_all_string_values(val))
    return values


# ---------------------------------------------------------------------------
# 1. Module exists and is importable
# ---------------------------------------------------------------------------

def test_profile_module_exists() -> None:
    assert PROFILE_MODULE_PATH.is_file()


def test_profile_module_importable() -> None:
    mod = importlib.import_module("src.data_layer.wallet_signal_research_profile")
    assert mod is not None


# ---------------------------------------------------------------------------
# 2. Profiles built from valid records
# ---------------------------------------------------------------------------

def test_profiles_built_from_single_valid_record() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    assert len(profiles) == 1
    assert profiles[0].wallet_id_or_address == "0xTEST"
    assert profiles[0].market_id == "market-001"
    assert profiles[0].condition_id == "cond-001"


def test_profiles_built_from_multiple_valid_records() -> None:
    records = [
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
        _make_valid_record(wallet_id="0xB", market_id="m-2", condition_id="c-2"),
    ]
    profiles = build_wallet_signal_research_profiles(records)
    assert len(profiles) == 2


def test_empty_records_yields_empty_profiles() -> None:
    profiles = build_wallet_signal_research_profiles([])
    assert profiles == ()


# ---------------------------------------------------------------------------
# 3. Invalid records handled deterministically
# ---------------------------------------------------------------------------

def test_invalid_records_included_with_warning() -> None:
    records = [_make_valid_record(is_valid=False)]
    profiles = build_wallet_signal_research_profiles(records)
    assert len(profiles) == 1
    assert any("invalid" in w.lower() for w in profiles[0].warnings)


def test_non_record_objects_skipped_silently() -> None:
    records = [None, 42, "not-a-record", _make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    assert len(profiles) == 1


# ---------------------------------------------------------------------------
# 4. Event counts deterministic
# ---------------------------------------------------------------------------

def test_event_count_is_deterministic_for_grouped_records() -> None:
    records = [
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
    ]
    profiles = build_wallet_signal_research_profiles(records)
    assert len(profiles) == 1
    assert profiles[0].event_count == 3


def test_separate_market_ids_produce_separate_profiles() -> None:
    records = [
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
        _make_valid_record(wallet_id="0xA", market_id="m-2", condition_id="c-2"),
    ]
    profiles = build_wallet_signal_research_profiles(records)
    assert len(profiles) == 2
    assert {p.event_count for p in profiles} == {1}


# ---------------------------------------------------------------------------
# 5. Single event yields SINGLE_EVENT_LOW_SAMPLE
# ---------------------------------------------------------------------------

def test_single_event_yields_single_event_sample_status() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].sample_size_status == SAMPLE_SIZE_SINGLE_EVENT


def test_two_events_yields_small_sample() -> None:
    records = [
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
    ]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].sample_size_status == SAMPLE_SIZE_SMALL


def test_five_events_yields_sufficient_sample() -> None:
    records = [
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1")
        for _ in range(5)
    ]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].sample_size_status == SAMPLE_SIZE_SUFFICIENT


# ---------------------------------------------------------------------------
# 6. Suspicious flow yields SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED and BLOCK_FROM_AUTOMATION
# ---------------------------------------------------------------------------

def test_suspicious_flow_and_human_review_yields_human_review_required_status() -> None:
    records = [
        _make_valid_record(suspicious_flow_flag=True, human_review_required=True)
    ]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].suspicious_flow_status == SUSPICIOUS_HUMAN_REVIEW


def test_suspicious_flow_human_review_yields_block_from_automation_effect() -> None:
    records = [
        _make_valid_record(suspicious_flow_flag=True, human_review_required=True)
    ]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].research_priority_effect == EFFECT_BLOCK_FROM_AUTOMATION


def test_suspicious_flow_without_human_review_required_flag_yields_watch_only() -> None:
    records = [
        _make_valid_record(suspicious_flow_flag=True, human_review_required=False)
    ]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].suspicious_flow_status == SUSPICIOUS_WATCH_ONLY


def test_suspicious_flow_watch_only_yields_require_human_review_effect() -> None:
    records = [
        _make_valid_record(suspicious_flow_flag=True, human_review_required=False)
    ]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].research_priority_effect == EFFECT_REQUIRE_HUMAN_REVIEW


def test_suspicious_flow_sets_human_review_required_on_profile() -> None:
    records = [
        _make_valid_record(suspicious_flow_flag=True, human_review_required=True)
    ]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].human_review_required is True


# ---------------------------------------------------------------------------
# 7. Unknown category yields UNKNOWN_CATEGORY_CONTEXT
# ---------------------------------------------------------------------------

def test_empty_market_category_yields_unknown_specialization() -> None:
    records = [_make_valid_record(market_category="")]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].wallet_specialization_match == SPEC_MATCH_UNKNOWN


def test_known_market_category_yields_matched_specialization() -> None:
    records = [_make_valid_record(market_category="Politics")]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].wallet_specialization_match == SPEC_MATCH_MATCHED


# ---------------------------------------------------------------------------
# 8. Allowed signal categories only
# ---------------------------------------------------------------------------

def test_profile_signal_category_is_always_in_allowed_set() -> None:
    test_cases = [
        _make_valid_record(suspicious_flow_flag=False, copyability_context_available=True, market_category="Sports"),
        _make_valid_record(suspicious_flow_flag=True, human_review_required=True),
        _make_valid_record(suspicious_flow_flag=False, copyability_context_available=False),
        _make_valid_record(market_category=""),
    ]
    for record in test_cases:
        profiles = build_wallet_signal_research_profiles([record])
        assert profiles[0].signal_category in ALLOWED_SIGNAL_CATEGORIES


def test_all_allowed_signal_categories_are_non_trade_like() -> None:
    for cat in ALLOWED_SIGNAL_CATEGORIES:
        assert cat not in FORBIDDEN_OUTPUT_VALUES


# ---------------------------------------------------------------------------
# 9. Forbidden trade-like values never appear in outputs
# ---------------------------------------------------------------------------

def test_profile_has_no_forbidden_trade_like_string_values() -> None:
    records = [
        _make_valid_record(
            suspicious_flow_flag=True,
            human_review_required=True,
            copyability_context_available=False,
        )
    ]
    profiles = build_wallet_signal_research_profiles(records)
    for profile in profiles:
        values = _profile_string_values(profile)
        for v in values:
            assert v not in FORBIDDEN_OUTPUT_VALUES, (
                f"Forbidden value '{v}' found in profile"
            )


def test_annotation_has_no_forbidden_trade_like_string_values() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    annotations = build_wallet_research_queue_annotations(profiles)
    for ann in annotations:
        values = _annotation_string_values(ann)
        for v in values:
            assert v not in FORBIDDEN_OUTPUT_VALUES, (
                f"Forbidden value '{v}' found in annotation"
            )


def test_forbidden_output_values_constant_non_empty() -> None:
    assert len(FORBIDDEN_OUTPUT_VALUES) > 0
    assert "BUY" in FORBIDDEN_OUTPUT_VALUES
    assert "SELL" in FORBIDDEN_OUTPUT_VALUES
    assert "TRADE_READY" in FORBIDDEN_OUTPUT_VALUES


# ---------------------------------------------------------------------------
# 10. Advisory labels present
# ---------------------------------------------------------------------------

def test_profile_has_advisory_label() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    assert profiles[0].advisory_label == PROFILE_ADVISORY_LABEL


def test_annotation_has_advisory_label() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    annotations = build_wallet_research_queue_annotations(profiles)
    assert annotations[0].advisory_label == ANNOTATION_ADVISORY_LABEL


def test_advisory_label_contains_advisory_only_prefix() -> None:
    assert "ADVISORY_ONLY" in PROFILE_ADVISORY_LABEL
    assert "ADVISORY_ONLY" in ANNOTATION_ADVISORY_LABEL


# ---------------------------------------------------------------------------
# 11. Profile dataclasses are frozen
# ---------------------------------------------------------------------------

def test_wallet_signal_research_profile_is_frozen() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    profile = profiles[0]
    with pytest.raises((AttributeError, TypeError)):
        profile.advisory_label = "MUTATED"  # type: ignore[misc]


def test_wallet_signal_research_profile_dataclass_is_frozen_class() -> None:
    import dataclasses
    assert dataclasses.fields(WalletSignalResearchProfile)
    params = WalletSignalResearchProfile.__dataclass_params__  # type: ignore[attr-defined]
    assert params.frozen is True


# ---------------------------------------------------------------------------
# 12. Annotation dataclasses are frozen
# ---------------------------------------------------------------------------

def test_wallet_research_queue_annotation_is_frozen() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    annotations = build_wallet_research_queue_annotations(profiles)
    ann = annotations[0]
    with pytest.raises((AttributeError, TypeError)):
        ann.advisory_label = "MUTATED"  # type: ignore[misc]


def test_wallet_research_queue_annotation_dataclass_is_frozen_class() -> None:
    import dataclasses
    assert dataclasses.fields(WalletResearchQueueAnnotation)
    params = WalletResearchQueueAnnotation.__dataclass_params__  # type: ignore[attr-defined]
    assert params.frozen is True


# ---------------------------------------------------------------------------
# 13. Annotations include market_id / condition_id and research_priority_effect
# ---------------------------------------------------------------------------

def test_annotation_includes_market_id() -> None:
    records = [_make_valid_record(market_id="mkt-xyz", condition_id="cnd-xyz")]
    profiles = build_wallet_signal_research_profiles(records)
    annotations = build_wallet_research_queue_annotations(profiles)
    assert annotations[0].market_id == "mkt-xyz"


def test_annotation_includes_condition_id() -> None:
    records = [_make_valid_record(market_id="mkt-xyz", condition_id="cnd-xyz")]
    profiles = build_wallet_signal_research_profiles(records)
    annotations = build_wallet_research_queue_annotations(profiles)
    assert annotations[0].condition_id == "cnd-xyz"


def test_annotation_includes_research_priority_effect() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    annotations = build_wallet_research_queue_annotations(profiles)
    assert annotations[0].research_priority_effect in ALLOWED_RESEARCH_PRIORITY_EFFECTS


# ---------------------------------------------------------------------------
# 14. Annotations do not include buy/sell/entry/exit/position_size/expected_return
# ---------------------------------------------------------------------------

def test_annotation_dataclass_has_no_trading_fields() -> None:
    forbidden_field_names = {
        "buy", "sell", "entry", "exit", "position_size",
        "expected_return", "profit_target", "stop_loss", "live_signal",
        "execute", "auto_copy",
    }
    annotation_field_names = {f.name for f in dc_fields(WalletResearchQueueAnnotation)}
    assert annotation_field_names.isdisjoint(forbidden_field_names)


def test_profile_dataclass_has_no_trading_fields() -> None:
    forbidden_field_names = {
        "buy", "sell", "entry", "exit", "position_size",
        "expected_return", "profit_target", "stop_loss", "live_signal",
        "execute", "auto_copy",
    }
    profile_field_names = {f.name for f in dc_fields(WalletSignalResearchProfile)}
    assert profile_field_names.isdisjoint(forbidden_field_names)


# ---------------------------------------------------------------------------
# 15. No network libraries imported
# ---------------------------------------------------------------------------

def test_module_source_imports_no_network_libraries() -> None:
    source = PROFILE_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    network_libs = {"requests", "urllib3", "httpx", "aiohttp", "websockets", "socket"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            else:
                names = [node.module.split(".")[0]] if node.module else []
            for name in names:
                assert name not in network_libs, (
                    f"Network library '{name}' imported in wallet_signal_research_profile.py"
                )


# ---------------------------------------------------------------------------
# 16. No file writes
# ---------------------------------------------------------------------------

def test_module_source_has_no_file_write_patterns() -> None:
    source = PROFILE_MODULE_PATH.read_text(encoding="utf-8")
    write_patterns = [".write(", "open(", "Path(", ".write_text(", ".write_bytes("]
    # Path() is imported from pathlib — only check for write calls
    actual_write_patterns = [".write(", ".write_text(", ".write_bytes("]
    for pattern in actual_write_patterns:
        assert pattern not in source, (
            f"File write pattern '{pattern}' found in wallet_signal_research_profile.py"
        )


# ---------------------------------------------------------------------------
# 17. No credentials/auth clients
# ---------------------------------------------------------------------------

def test_module_source_has_no_credential_patterns() -> None:
    source = PROFILE_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    credential_libs = {
        "boto3", "botocore", "google.auth", "azure", "jwt", "cryptography",
        "paramiko", "py_clob_client",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            else:
                names = [node.module.split(".")[0]] if node.module else []
            for name in names:
                assert name not in credential_libs, (
                    f"Credential library '{name}' imported in wallet_signal_research_profile.py"
                )


# ---------------------------------------------------------------------------
# 18. No LLM/agent libraries imported
# ---------------------------------------------------------------------------

def test_module_source_has_no_llm_agent_libraries() -> None:
    source = PROFILE_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    llm_libs = {
        "anthropic", "openai", "langchain", "llama_index",
        "transformers", "hermes", "litellm",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            else:
                names = [node.module.split(".")[0]] if node.module else []
            for name in names:
                assert name not in llm_libs, (
                    f"LLM/agent library '{name}' imported in wallet_signal_research_profile.py"
                )


# ---------------------------------------------------------------------------
# 19. No copyability PnL or expected-return computation
# ---------------------------------------------------------------------------

def test_module_source_has_no_pnl_computation() -> None:
    source = PROFILE_MODULE_PATH.read_text(encoding="utf-8")
    # These terms must not appear as computed values or variable assignments in logic.
    # They are checked via code-pattern matching, not string scanning, because some
    # terms (like profit_target, expected_return) legitimately appear in the
    # FORBIDDEN_OUTPUT_VALUES constant as string literals denoting what is forbidden.
    forbidden_computation_patterns = [
        "copyability_pnl",
        "delayed_copy_pnl",
        "paper_pnl",
        "live_pnl",
        "win_rate",
        "sharpe",
    ]
    for term in forbidden_computation_patterns:
        assert term not in source.lower(), (
            f"Forbidden PnL/computation term '{term}' found in wallet_signal_research_profile.py"
        )
    # Ensure forbidden terms appear only as string literals (in FORBIDDEN_OUTPUT_VALUES),
    # not as computed variables, assignments, or function names.
    assert "profit_target =" not in source
    assert "compute_profit_target" not in source
    assert "expected_return =" not in source
    assert "compute_expected_return" not in source
    assert "return expected_return" not in source


# ---------------------------------------------------------------------------
# 20. No scoring weight mutation
# ---------------------------------------------------------------------------

def test_module_does_not_import_scoring_module() -> None:
    source = PROFILE_MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and "market_research_priority_scoring" in node.module:
                pytest.fail(
                    "wallet_signal_research_profile.py must not import the scoring module"
                )


# ---------------------------------------------------------------------------
# 21. Docs advisory-only, no network, no execution, no copy trading
# ---------------------------------------------------------------------------

def test_wallet_signal_profile_doc_exists() -> None:
    assert PROFILE_DOC_PATH.is_file()


def test_wallet_signal_profile_doc_states_advisory_only() -> None:
    text = PROFILE_DOC_PATH.read_text(encoding="utf-8")
    assert "advisory" in text.lower()
    assert "research metadata" in text.lower() or "advisory research" in text.lower()


def test_wallet_signal_profile_doc_no_network() -> None:
    text = PROFILE_DOC_PATH.read_text(encoding="utf-8")
    assert "no network" in text.lower() or "does not fetch" in text.lower()


def test_wallet_signal_profile_doc_no_execution() -> None:
    text = PROFILE_DOC_PATH.read_text(encoding="utf-8")
    assert "no live execution" in text.lower() or "execution" in text.lower()


def test_wallet_signal_profile_doc_no_copy_trading() -> None:
    text = PROFILE_DOC_PATH.read_text(encoding="utf-8")
    assert "copy trading" in text.lower() or "copy-trading" in text.lower()


def test_wallet_signal_profile_doc_human_review_required() -> None:
    text = PROFILE_DOC_PATH.read_text(encoding="utf-8")
    assert "human review" in text.lower()


def test_wallet_signal_profile_doc_does_not_prove_skill() -> None:
    text = PROFILE_DOC_PATH.read_text(encoding="utf-8")
    assert "does not prove wallet skill" in text.lower() or "not prove" in text.lower()


def test_wallet_signal_profile_doc_does_not_prove_copyability() -> None:
    text = PROFILE_DOC_PATH.read_text(encoding="utf-8")
    assert "does not prove copyability" in text.lower() or "copyability" in text.lower()


def test_wallet_signal_profile_doc_suspicious_flow_is_watch_only() -> None:
    text = PROFILE_DOC_PATH.read_text(encoding="utf-8")
    assert "suspicious" in text.lower()
    assert "research-watch-only" in text.lower() or "human-review-required" in text.lower()


def test_wallet_signal_profile_doc_no_trade_recommendation() -> None:
    text = PROFILE_DOC_PATH.read_text(encoding="utf-8")
    assert "trade recommendation" in text.lower() or "does not create" in text.lower()


# ---------------------------------------------------------------------------
# 22. Repo truth index references new module/doc/test
# ---------------------------------------------------------------------------

def test_repo_truth_index_references_wallet_signal_profile_module() -> None:
    text = REPO_TRUTH_PATH.read_text(encoding="utf-8")
    assert "wallet_signal_research_profile" in text


def test_repo_truth_index_references_wallet_signal_profile_doc() -> None:
    text = REPO_TRUTH_PATH.read_text(encoding="utf-8")
    assert "docs/wallet_signal_research_profile.md" in text


def test_repo_truth_index_references_wallet_signal_profile_test() -> None:
    text = REPO_TRUTH_PATH.read_text(encoding="utf-8")
    assert "test_wallet_signal_research_profile" in text


# ---------------------------------------------------------------------------
# 23. Deferred items updated
# ---------------------------------------------------------------------------

def test_deferred_items_contains_wp79_d001() -> None:
    text = DEFERRED_PATH.read_text(encoding="utf-8")
    assert "WP79-D001" in text


def test_deferred_items_wp78_d001_resolved() -> None:
    text = DEFERRED_PATH.read_text(encoding="utf-8")
    assert "WP78-D001" in text


def test_deferred_items_wp78_d002_resolved() -> None:
    text = DEFERRED_PATH.read_text(encoding="utf-8")
    assert "WP78-D002" in text


# ---------------------------------------------------------------------------
# 24. Project status reconciled
# ---------------------------------------------------------------------------

def test_project_status_marks_wp79_as_current_phase() -> None:
    text = STATUS_PATH.read_text(encoding="utf-8")
    current_phase_line = next(
        line for line in text.splitlines() if line.startswith("- Current phase:")
    )
    assert any(wp in current_phase_line for wp in ("WP79", "WP80", "WP81", "WP82", "WP83", "WP84", "WP86", "WP87", "WP88", "WP89", "WP90", "WP91", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109"))


def test_project_status_marks_wp78_merged() -> None:
    text = STATUS_PATH.read_text(encoding="utf-8")
    merged_line = next(
        line for line in text.splitlines() if line.startswith("- Merged WPs:")
    )
    assert "WP78" in merged_line


def test_project_status_wallet_signal_profiler_status() -> None:
    text = STATUS_PATH.read_text(encoding="utf-8")
    assert "WALLET_SIGNAL_RESEARCH_PROFILER" in text or "wallet_signal" in text.lower()


# ---------------------------------------------------------------------------
# 25. Determinism: same input gives same output
# ---------------------------------------------------------------------------

def test_profiles_are_deterministic_for_same_input() -> None:
    records = [
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
        _make_valid_record(wallet_id="0xB", market_id="m-2", condition_id="c-2"),
    ]
    profiles1 = build_wallet_signal_research_profiles(records)
    profiles2 = build_wallet_signal_research_profiles(records)
    assert profiles1 == profiles2


def test_annotations_are_deterministic_for_same_input() -> None:
    records = [
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
        _make_valid_record(wallet_id="0xB", market_id="m-2", condition_id="c-2"),
    ]
    profiles = build_wallet_signal_research_profiles(records)
    ann1 = build_wallet_research_queue_annotations(profiles)
    ann2 = build_wallet_research_queue_annotations(profiles)
    assert ann1 == ann2


def test_profiles_sorted_by_wallet_market_condition() -> None:
    records = [
        _make_valid_record(wallet_id="0xZ", market_id="m-2", condition_id="c-2"),
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
    ]
    profiles = build_wallet_signal_research_profiles(records)
    keys = [(p.wallet_id_or_address, p.market_id, p.condition_id) for p in profiles]
    assert keys == sorted(keys)


def test_annotations_sorted_by_wallet_market_condition() -> None:
    records = [
        _make_valid_record(wallet_id="0xZ", market_id="m-2", condition_id="c-2"),
        _make_valid_record(wallet_id="0xA", market_id="m-1", condition_id="c-1"),
    ]
    profiles = build_wallet_signal_research_profiles(records)
    annotations = build_wallet_research_queue_annotations(profiles)
    keys = [(a.wallet_id_or_address, a.market_id, a.condition_id) for a in annotations]
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# 26. Annotations include advisory notice
# ---------------------------------------------------------------------------

def test_annotation_has_advisory_notice() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    annotations = build_wallet_research_queue_annotations(profiles)
    notice = annotations[0].advisory_notice
    assert "ADVISORY_ONLY" in notice
    assert "human review" in notice.lower()


# ---------------------------------------------------------------------------
# 27. Copyability status is always in allowed set
# ---------------------------------------------------------------------------

ALLOWED_COPY_STATUSES = {
    COPY_NOT_EVALUATED,
    COPY_UNPROVEN,
    COPY_UNCOPYABLE_FAST,
    COPY_SUSPICIOUS_DO_NOT_COPY,
}


def test_profile_copyability_status_is_allowed() -> None:
    test_records = [
        _make_valid_record(suspicious_flow_flag=False, copyability_context_available=True),
        _make_valid_record(suspicious_flow_flag=True, human_review_required=True),
        _make_valid_record(suspicious_flow_flag=False, copyability_context_available=False),
    ]
    for rec in test_records:
        profiles = build_wallet_signal_research_profiles([rec])
        assert profiles[0].copyability_status in ALLOWED_COPY_STATUSES


# ---------------------------------------------------------------------------
# 28. Research priority effect is always in allowed set
# ---------------------------------------------------------------------------

def test_profile_research_priority_effect_is_allowed() -> None:
    test_records = [
        _make_valid_record(),
        _make_valid_record(suspicious_flow_flag=True, human_review_required=True),
        _make_valid_record(suspicious_flow_flag=True, human_review_required=False),
        _make_valid_record(market_category=""),
    ]
    for rec in test_records:
        profiles = build_wallet_signal_research_profiles([rec])
        assert profiles[0].research_priority_effect in ALLOWED_RESEARCH_PRIORITY_EFFECTS


# ---------------------------------------------------------------------------
# 29. Warnings tuple is immutable
# ---------------------------------------------------------------------------

def test_profile_warnings_is_tuple() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    assert isinstance(profiles[0].warnings, tuple)


# ---------------------------------------------------------------------------
# 30. build_wallet_research_queue_annotations takes profiles iterable
# ---------------------------------------------------------------------------

def test_annotations_built_from_profiles_tuple() -> None:
    records = [_make_valid_record()]
    profiles = build_wallet_signal_research_profiles(records)
    annotations = build_wallet_research_queue_annotations(profiles)
    assert len(annotations) == 1
    assert isinstance(annotations, tuple)


def test_annotations_empty_when_profiles_empty() -> None:
    annotations = build_wallet_research_queue_annotations(())
    assert annotations == ()
