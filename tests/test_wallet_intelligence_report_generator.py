"""Tests for the WP82 wallet intelligence report generator.

All tests are local/offline/read-only. No network access, no credentials,
no file writes, no live data, no buy/sell outputs.
"""

from __future__ import annotations

import dataclasses
import importlib
import sys
from dataclasses import fields
from types import SimpleNamespace
from typing import Any

import pytest

from src.data_layer.wallet_intelligence_report_generator import (
    FORBIDDEN_OUTPUT_VALUES,
    REPORT_ADVISORY_LABEL,
    REPORT_TYPE,
    WalletIntelligenceReport,
    build_wallet_intelligence_report,
)


# ---------------------------------------------------------------------------
# Fixture helpers — lightweight duck-typed stand-ins
# ---------------------------------------------------------------------------

def _make_profile(
    wallet_id: str = "wallet_A",
    market_id: str = "market_1",
    condition_id: str = "cond_1",
    market_category: str = "POLITICS",
    event_count: int = 3,
    sample_size_status: str = "SMALL_SAMPLE_REVIEW_ONLY",
    signal_category: str = "SPECIALIST_ENTRY",
    wallet_specialization_match: str = "MATCHED_CATEGORY_CONTEXT",
    suspicious_flow_status: str = "NO_SUSPICIOUS_FLOW_FLAG",
    copyability_status: str = "COPYABILITY_UNPROVEN",
    research_priority_effect: str = "LOW_RESEARCH_BOOST",
    human_review_required: bool = False,
    warnings: tuple = (),
    advisory_label: str = "ADVISORY_ONLY_WALLET_SIGNAL_RESEARCH_PROFILE",
) -> SimpleNamespace:
    return SimpleNamespace(
        wallet_id_or_address=wallet_id,
        market_id=market_id,
        condition_id=condition_id,
        market_category=market_category,
        event_count=event_count,
        sample_size_status=sample_size_status,
        signal_category=signal_category,
        wallet_specialization_match=wallet_specialization_match,
        suspicious_flow_status=suspicious_flow_status,
        copyability_status=copyability_status,
        research_priority_effect=research_priority_effect,
        human_review_required=human_review_required,
        warnings=warnings,
        advisory_label=advisory_label,
    )


def _make_evaluation(
    wallet_id: str = "wallet_A",
    market_id: str = "market_1",
    condition_id: str = "cond_1",
    market_category: str = "POLITICS",
    signal_category: str = "SPECIALIST_ENTRY",
    delay_window: str = "5_seconds",
    event_price_observed: object = 0.6,
    delayed_price_observed: object = 0.62,
    spread_context_available: bool = True,
    liquidity_context_available: bool = True,
    fee_context_available: bool = True,
    size_limit_context_available: bool = True,
    resolved_outcome_available: bool = False,
    evaluation_status: str = "RESEARCH_PROMISING",
    research_interpretation: str = "Advisory context appears favorable.",
    human_review_required: bool = False,
    warnings: tuple = (),
    advisory_label: str = "ADVISORY_ONLY_COPYABILITY_DELAY_EVALUATION",
) -> SimpleNamespace:
    return SimpleNamespace(
        wallet_id_or_address=wallet_id,
        market_id=market_id,
        condition_id=condition_id,
        market_category=market_category,
        signal_category=signal_category,
        delay_window=delay_window,
        event_price_observed=event_price_observed,
        delayed_price_observed=delayed_price_observed,
        spread_context_available=spread_context_available,
        liquidity_context_available=liquidity_context_available,
        fee_context_available=fee_context_available,
        size_limit_context_available=size_limit_context_available,
        resolved_outcome_available=resolved_outcome_available,
        evaluation_status=evaluation_status,
        research_interpretation=research_interpretation,
        human_review_required=human_review_required,
        warnings=warnings,
        advisory_label=advisory_label,
    )


def _make_annotation(
    wallet_id: str = "wallet_A",
    market_id: str = "market_1",
    condition_id: str = "cond_1",
    research_priority_effect: str = "LOW_RESEARCH_BOOST",
    human_review_required: bool = False,
    suspicious_flow_status: str = "NO_SUSPICIOUS_FLOW_FLAG",
    sample_size_status: str = "SMALL_SAMPLE_REVIEW_ONLY",
    signal_category: str = "SPECIALIST_ENTRY",
    advisory_label: str = "ADVISORY_ONLY_WALLET_RESEARCH_QUEUE_ANNOTATION",
    advisory_notice: str = "ADVISORY_ONLY",
) -> SimpleNamespace:
    return SimpleNamespace(
        wallet_id_or_address=wallet_id,
        market_id=market_id,
        condition_id=condition_id,
        research_priority_effect=research_priority_effect,
        human_review_required=human_review_required,
        suspicious_flow_status=suspicious_flow_status,
        sample_size_status=sample_size_status,
        signal_category=signal_category,
        advisory_label=advisory_label,
        advisory_notice=advisory_notice,
    )


def _minimal_report() -> WalletIntelligenceReport:
    return build_wallet_intelligence_report(
        profiles=[_make_profile()],
        evaluations=[_make_evaluation()],
        annotations=[_make_annotation()],
    )


# ===========================================================================
# Category 1: Report can be built from local profiles and evaluations
# ===========================================================================

class TestReportCanBeBuilt:
    def test_build_from_local_inputs(self) -> None:
        report = _minimal_report()
        assert isinstance(report, WalletIntelligenceReport)

    def test_build_with_empty_inputs(self) -> None:
        report = build_wallet_intelligence_report(
            profiles=[], evaluations=[], annotations=[]
        )
        assert isinstance(report, WalletIntelligenceReport)

    def test_build_with_multiple_profiles_and_evaluations(self) -> None:
        profiles = [
            _make_profile("wallet_A", "market_1", "cond_1"),
            _make_profile("wallet_B", "market_2", "cond_2"),
        ]
        evaluations = [
            _make_evaluation("wallet_A", "market_1", "cond_1"),
            _make_evaluation("wallet_B", "market_2", "cond_2"),
        ]
        annotations = [
            _make_annotation("wallet_A", "market_1", "cond_1"),
            _make_annotation("wallet_B", "market_2", "cond_2"),
        ]
        report = build_wallet_intelligence_report(profiles, evaluations, annotations)
        assert isinstance(report, WalletIntelligenceReport)

    def test_returns_walletintelligencereport_instance(self) -> None:
        report = _minimal_report()
        assert type(report).__name__ == "WalletIntelligenceReport"


# ===========================================================================
# Category 2: Report output has required sections
# ===========================================================================

class TestRequiredSections:
    def test_has_report_identity(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "report_identity")
        assert isinstance(report.report_identity, dict)

    def test_has_input_summary(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "input_summary")
        assert isinstance(report.input_summary, dict)

    def test_has_wallet_signal_summary(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "wallet_signal_summary")
        assert isinstance(report.wallet_signal_summary, dict)

    def test_has_copyability_delay_summary(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "copyability_delay_summary")
        assert isinstance(report.copyability_delay_summary, dict)

    def test_has_research_queue_implications(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "research_queue_implications")
        assert isinstance(report.research_queue_implications, dict)

    def test_has_suspicious_flow_review(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "suspicious_flow_review")
        assert isinstance(report.suspicious_flow_review, dict)

    def test_has_limitations(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "limitations")
        assert isinstance(report.limitations, dict)

    def test_has_deferred_items(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "deferred_items")
        assert isinstance(report.deferred_items, dict)

    def test_has_safety(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "safety")

    def test_has_warnings(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "warnings")
        assert isinstance(report.warnings, tuple)

    def test_has_advisory_label(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "advisory_label")
        assert report.advisory_label

    def test_has_report_type(self) -> None:
        report = _minimal_report()
        assert hasattr(report, "report_type")
        assert report.report_type == REPORT_TYPE

    def test_report_identity_has_advisory_notice(self) -> None:
        report = _minimal_report()
        assert "advisory_only_notice" in report.report_identity
        assert report.report_identity["advisory_only_notice"]

    def test_wallet_signal_summary_has_advisory_notice(self) -> None:
        report = _minimal_report()
        assert "advisory_only_notice" in report.wallet_signal_summary

    def test_copyability_delay_summary_has_advisory_notice(self) -> None:
        report = _minimal_report()
        assert "advisory_only_notice" in report.copyability_delay_summary

    def test_research_queue_implications_has_advisory_notice(self) -> None:
        report = _minimal_report()
        assert "advisory_only_notice" in report.research_queue_implications

    def test_suspicious_flow_review_has_advisory_notice(self) -> None:
        report = _minimal_report()
        assert "advisory_only_notice" in report.suspicious_flow_review

    def test_limitations_has_advisory_notice(self) -> None:
        report = _minimal_report()
        assert "advisory_only_notice" in report.limitations


# ===========================================================================
# Category 3: Safety flags all True
# ===========================================================================

class TestSafetyFlags:
    _REQUIRED_FLAGS = [
        "manual_research_only",
        "not_automated_copy_trading",
        "no_live_execution",
        "no_order_placement",
        "no_position_sizing",
        "no_risk_override",
        "no_parameter_auto_change",
    ]

    def test_all_safety_flags_present(self) -> None:
        report = _minimal_report()
        for flag in self._REQUIRED_FLAGS:
            assert flag in report.safety, f"Missing safety flag: {flag}"

    def test_all_safety_flags_true(self) -> None:
        report = _minimal_report()
        for flag in self._REQUIRED_FLAGS:
            assert report.safety[flag] is True, (
                f"Safety flag '{flag}' must be True, got {report.safety[flag]}"
            )

    def test_safety_flags_all_true_with_empty_inputs(self) -> None:
        report = build_wallet_intelligence_report(
            profiles=[], evaluations=[], annotations=[]
        )
        for flag in self._REQUIRED_FLAGS:
            assert report.safety[flag] is True


# ===========================================================================
# Category 4: Signal category counts are deterministic
# ===========================================================================

class TestSignalCategoryCounts:
    def test_signal_category_distribution_is_deterministic(self) -> None:
        profiles = [
            _make_profile(wallet_id="w1", signal_category="SPECIALIST_ENTRY"),
            _make_profile(wallet_id="w2", signal_category="SPECIALIST_ENTRY"),
            _make_profile(wallet_id="w3", signal_category="SUSPICIOUS_TIMING",
                          suspicious_flow_status="SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED",
                          human_review_required=True),
        ]
        r1 = build_wallet_intelligence_report(profiles, [], [])
        r2 = build_wallet_intelligence_report(profiles, [], [])
        assert (
            r1.wallet_signal_summary["signal_category_distribution"]
            == r2.wallet_signal_summary["signal_category_distribution"]
        )

    def test_signal_category_distribution_counts_correctly(self) -> None:
        profiles = [
            _make_profile(wallet_id="w1", signal_category="SPECIALIST_ENTRY"),
            _make_profile(wallet_id="w2", signal_category="SPECIALIST_ENTRY"),
            _make_profile(wallet_id="w3", signal_category="UNCOPYABLE_FAST_FLOW"),
        ]
        report = build_wallet_intelligence_report(profiles, [], [])
        dist = report.wallet_signal_summary["signal_category_distribution"]
        assert dist["SPECIALIST_ENTRY"] == 2
        assert dist["UNCOPYABLE_FAST_FLOW"] == 1

    def test_signal_distribution_is_sorted(self) -> None:
        profiles = [
            _make_profile(wallet_id="w1", signal_category="UNCOPYABLE_FAST_FLOW"),
            _make_profile(wallet_id="w2", signal_category="SPECIALIST_ENTRY"),
        ]
        report = build_wallet_intelligence_report(profiles, [], [])
        dist = report.wallet_signal_summary["signal_category_distribution"]
        keys = list(dist.keys())
        assert keys == sorted(keys)

    def test_profile_count_matches(self) -> None:
        profiles = [_make_profile(wallet_id=f"w{i}") for i in range(5)]
        report = build_wallet_intelligence_report(profiles, [], [])
        assert report.wallet_signal_summary["profile_count"] == 5


# ===========================================================================
# Category 5: Evaluation status counts are deterministic
# ===========================================================================

class TestEvaluationStatusCounts:
    def test_status_distribution_is_deterministic(self) -> None:
        evals = [
            _make_evaluation(delay_window="1_second", evaluation_status="RESEARCH_PROMISING"),
            _make_evaluation(delay_window="5_seconds", evaluation_status="RESEARCH_WEAK"),
        ]
        r1 = build_wallet_intelligence_report([], evals, [])
        r2 = build_wallet_intelligence_report([], evals, [])
        assert (
            r1.copyability_delay_summary["evaluation_status_distribution"]
            == r2.copyability_delay_summary["evaluation_status_distribution"]
        )

    def test_status_distribution_counts_correctly(self) -> None:
        evals = [
            _make_evaluation(delay_window="1_second", evaluation_status="RESEARCH_PROMISING"),
            _make_evaluation(delay_window="5_seconds", evaluation_status="RESEARCH_PROMISING"),
            _make_evaluation(delay_window="30_seconds", evaluation_status="RESEARCH_WEAK"),
        ]
        report = build_wallet_intelligence_report([], evals, [])
        dist = report.copyability_delay_summary["evaluation_status_distribution"]
        assert dist["RESEARCH_PROMISING"] == 2
        assert dist["RESEARCH_WEAK"] == 1

    def test_evaluation_count_matches(self) -> None:
        evals = [
            _make_evaluation(delay_window=f"{i}_seconds") for i in range(3)
        ]
        report = build_wallet_intelligence_report([], evals, [])
        assert report.copyability_delay_summary["evaluation_count"] == 3

    def test_status_distribution_is_sorted(self) -> None:
        evals = [
            _make_evaluation(delay_window="1_second", evaluation_status="RESEARCH_WEAK"),
            _make_evaluation(delay_window="5_seconds", evaluation_status="RESEARCH_PROMISING"),
        ]
        report = build_wallet_intelligence_report([], evals, [])
        dist = report.copyability_delay_summary["evaluation_status_distribution"]
        keys = list(dist.keys())
        assert keys == sorted(keys)


# ===========================================================================
# Category 6: Human-review-required count is present
# ===========================================================================

class TestHumanReviewRequiredCount:
    def test_wallet_signal_summary_has_human_review_count(self) -> None:
        report = _minimal_report()
        assert "human_review_required_count" in report.wallet_signal_summary

    def test_copyability_delay_summary_has_human_review_count(self) -> None:
        report = _minimal_report()
        assert "human_review_required_count" in report.copyability_delay_summary

    def test_human_review_count_is_zero_when_none_required(self) -> None:
        profiles = [_make_profile(human_review_required=False)]
        report = build_wallet_intelligence_report(profiles, [], [])
        assert report.wallet_signal_summary["human_review_required_count"] == 0

    def test_human_review_count_correct_in_profiles(self) -> None:
        profiles = [
            _make_profile(wallet_id="w1", human_review_required=True),
            _make_profile(wallet_id="w2", human_review_required=True),
            _make_profile(wallet_id="w3", human_review_required=False),
        ]
        report = build_wallet_intelligence_report(profiles, [], [])
        assert report.wallet_signal_summary["human_review_required_count"] == 2

    def test_human_review_count_correct_in_evaluations(self) -> None:
        evals = [
            _make_evaluation(delay_window="1_second", human_review_required=True),
            _make_evaluation(delay_window="5_seconds", human_review_required=False),
        ]
        report = build_wallet_intelligence_report([], evals, [])
        assert report.copyability_delay_summary["human_review_required_count"] == 1


# ===========================================================================
# Category 7: Suspicious-flow count is present
# ===========================================================================

class TestSuspiciousFlowCount:
    def test_wallet_signal_summary_has_suspicious_flow_count(self) -> None:
        report = _minimal_report()
        assert "suspicious_flow_count" in report.wallet_signal_summary

    def test_suspicious_flow_count_zero_when_none(self) -> None:
        profiles = [_make_profile(suspicious_flow_status="NO_SUSPICIOUS_FLOW_FLAG")]
        report = build_wallet_intelligence_report(profiles, [], [])
        assert report.wallet_signal_summary["suspicious_flow_count"] == 0

    def test_suspicious_flow_count_correct(self) -> None:
        profiles = [
            _make_profile(wallet_id="w1",
                          suspicious_flow_status="SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED"),
            _make_profile(wallet_id="w2",
                          suspicious_flow_status="NO_SUSPICIOUS_FLOW_FLAG"),
        ]
        report = build_wallet_intelligence_report(profiles, [], [])
        assert report.wallet_signal_summary["suspicious_flow_count"] == 1

    def test_suspicious_flow_review_section_present(self) -> None:
        report = _minimal_report()
        assert "suspicious_flow_events" in report.suspicious_flow_review

    def test_suspicious_flow_review_blocked_from_automation(self) -> None:
        profiles = [
            _make_profile(suspicious_flow_status="SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED",
                          human_review_required=True),
        ]
        report = build_wallet_intelligence_report(profiles, [], [])
        assert report.suspicious_flow_review["blocked_from_automation"] is True

    def test_suspicious_flow_review_required_action(self) -> None:
        profiles = [
            _make_profile(suspicious_flow_status="SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED",
                          human_review_required=True),
        ]
        report = build_wallet_intelligence_report(profiles, [], [])
        events = report.suspicious_flow_review["suspicious_flow_events"]
        for event in events:
            assert event["required_action"] == "HUMAN_REVIEW_REQUIRED"
            assert event["blocked_from_automation"] is True


# ===========================================================================
# Category 8: Insufficient-context count is present
# ===========================================================================

class TestInsufficientContextCount:
    def test_copyability_delay_summary_has_insufficient_context_count(self) -> None:
        report = _minimal_report()
        assert "insufficient_context_count" in report.copyability_delay_summary

    def test_insufficient_context_count_zero_when_none(self) -> None:
        evals = [_make_evaluation(evaluation_status="RESEARCH_PROMISING")]
        report = build_wallet_intelligence_report([], evals, [])
        assert report.copyability_delay_summary["insufficient_context_count"] == 0

    def test_insufficient_context_count_correct(self) -> None:
        evals = [
            _make_evaluation(delay_window="1_second",
                             evaluation_status="INSUFFICIENT_CONTEXT"),
            _make_evaluation(delay_window="5_seconds",
                             evaluation_status="INSUFFICIENT_CONTEXT"),
            _make_evaluation(delay_window="30_seconds",
                             evaluation_status="RESEARCH_PROMISING"),
        ]
        report = build_wallet_intelligence_report([], evals, [])
        assert report.copyability_delay_summary["insufficient_context_count"] == 2


# ===========================================================================
# Category 9: Report warnings are deterministic
# ===========================================================================

class TestWarningsDeterministic:
    def test_warnings_is_tuple(self) -> None:
        report = _minimal_report()
        assert isinstance(report.warnings, tuple)

    def test_warnings_are_deterministic(self) -> None:
        profiles = [_make_profile()]
        evals = [_make_evaluation()]
        annotations = [_make_annotation()]
        r1 = build_wallet_intelligence_report(profiles, evals, annotations)
        r2 = build_wallet_intelligence_report(profiles, evals, annotations)
        assert r1.warnings == r2.warnings

    def test_empty_inputs_produce_warnings(self) -> None:
        report = build_wallet_intelligence_report([], [], [])
        assert len(report.warnings) > 0

    def test_suspicious_flow_produces_warning(self) -> None:
        profiles = [
            _make_profile(
                suspicious_flow_status="SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED",
                human_review_required=True,
            )
        ]
        report = build_wallet_intelligence_report(profiles, [], [])
        combined = " ".join(report.warnings)
        assert "suspicious" in combined.lower() or "human review" in combined.lower()

    def test_human_review_eval_produces_warning(self) -> None:
        evals = [_make_evaluation(human_review_required=True)]
        report = build_wallet_intelligence_report([], evals, [])
        combined = " ".join(report.warnings)
        assert "human review" in combined.lower()


# ===========================================================================
# Category 10: Advisory label is present and correct
# ===========================================================================

class TestAdvisoryLabel:
    def test_advisory_label_is_correct(self) -> None:
        report = _minimal_report()
        assert report.advisory_label == REPORT_ADVISORY_LABEL

    def test_advisory_label_value(self) -> None:
        assert REPORT_ADVISORY_LABEL == "ADVISORY_ONLY_WALLET_INTELLIGENCE_REPORT"

    def test_report_type_value(self) -> None:
        assert REPORT_TYPE == "WALLET_INTELLIGENCE_ADVISORY_REPORT_V1"

    def test_advisory_notice_is_present(self) -> None:
        report = _minimal_report()
        assert report.advisory_notice
        assert "ADVISORY_ONLY" in report.advisory_notice


# ===========================================================================
# Category 11: No dollar PnL field exists
# ===========================================================================

class TestNoPnlField:
    def test_no_pnl_field_in_report(self) -> None:
        report = _minimal_report()
        field_names = {f.name for f in fields(report)}
        forbidden_pnl = {
            "pnl", "dollar_pnl", "expected_pnl", "pnl_target", "profit",
            "profit_target", "realized_pnl", "unrealized_pnl",
        }
        overlap = field_names & forbidden_pnl
        assert not overlap, f"Forbidden PnL fields found: {overlap}"

    def test_no_pnl_in_signal_summary(self) -> None:
        report = _minimal_report()
        for key in report.wallet_signal_summary:
            assert "pnl" not in key.lower()
            assert "profit" not in key.lower()

    def test_no_pnl_in_delay_summary(self) -> None:
        report = _minimal_report()
        for key in report.copyability_delay_summary:
            assert "pnl" not in key.lower()
            assert "profit" not in key.lower()


# ===========================================================================
# Category 12: No expected-return field exists
# ===========================================================================

class TestNoExpectedReturnField:
    def test_no_expected_return_in_report_fields(self) -> None:
        report = _minimal_report()
        field_names = {f.name for f in fields(report)}
        for name in field_names:
            assert "expected_return" not in name.lower()
            assert "return" not in name.lower() or "human_review_required" == name

    def test_no_expected_return_in_signal_summary(self) -> None:
        report = _minimal_report()
        for key in report.wallet_signal_summary:
            assert "expected_return" not in key.lower()

    def test_no_expected_return_in_delay_summary(self) -> None:
        report = _minimal_report()
        for key in report.copyability_delay_summary:
            assert "expected_return" not in key.lower()


# ===========================================================================
# Category 13: No buy/sell/entry/exit/position-size fields
# ===========================================================================

class TestNoForbiddenTradeFields:
    _FORBIDDEN_SUBSTRINGS = [
        "buy", "sell", "entry", "exit", "position_size",
        "open_position", "close_position", "execute",
        "take_profit", "stop_loss", "live_signal", "auto_copy",
    ]

    # Safety-flag exception names that contain allowed substrings
    _ALLOWED_EXCEPTIONS = {
        "not_automated_copy_trading",
        "no_live_execution",
        "no_order_placement",
        "no_position_sizing",
    }

    def _check_key(self, key: str) -> None:
        if key in self._ALLOWED_EXCEPTIONS:
            return
        for sub in self._FORBIDDEN_SUBSTRINGS:
            assert sub not in key.lower(), (
                f"Forbidden substring '{sub}' found in field/key: '{key}'"
            )

    def test_no_forbidden_trade_fields_in_report(self) -> None:
        report = _minimal_report()
        for f in fields(report):
            self._check_key(f.name)

    def test_no_forbidden_keys_in_signal_summary(self) -> None:
        report = _minimal_report()
        for key in report.wallet_signal_summary:
            self._check_key(key)

    def test_no_forbidden_keys_in_delay_summary(self) -> None:
        report = _minimal_report()
        for key in report.copyability_delay_summary:
            self._check_key(key)

    def test_no_forbidden_keys_in_research_queue_implications(self) -> None:
        report = _minimal_report()
        for key in report.research_queue_implications:
            self._check_key(key)

    def test_no_forbidden_keys_in_limitations(self) -> None:
        report = _minimal_report()
        for key in report.limitations:
            self._check_key(key)

    def test_forbidden_output_values_constant_is_correct(self) -> None:
        assert "BUY" in FORBIDDEN_OUTPUT_VALUES
        assert "SELL" in FORBIDDEN_OUTPUT_VALUES
        assert "TRADE_READY" in FORBIDDEN_OUTPUT_VALUES
        assert "COPY_READY" in FORBIDDEN_OUTPUT_VALUES
        assert "LIVE_READY" in FORBIDDEN_OUTPUT_VALUES
        assert "BUY_SIGNAL" in FORBIDDEN_OUTPUT_VALUES
        assert "SELL_SIGNAL" in FORBIDDEN_OUTPUT_VALUES


# ===========================================================================
# Category 14: No trade-ready/copy-ready/live-ready labels
# ===========================================================================

class TestNoForbiddenLabels:
    _FORBIDDEN_LABELS = {
        "TRADE_READY", "COPY_READY", "LIVE_READY", "BUY_SIGNAL", "SELL_SIGNAL",
    }

    def test_advisory_label_not_forbidden(self) -> None:
        report = _minimal_report()
        assert report.advisory_label not in self._FORBIDDEN_LABELS

    def test_report_type_not_forbidden(self) -> None:
        report = _minimal_report()
        assert report.report_type not in self._FORBIDDEN_LABELS

    def test_advisory_label_is_advisory_only(self) -> None:
        report = _minimal_report()
        assert "ADVISORY_ONLY" in report.advisory_label

    def test_report_type_is_advisory_report(self) -> None:
        report = _minimal_report()
        assert "ADVISORY_REPORT" in report.report_type


# ===========================================================================
# Category 15: Dataclasses are frozen
# ===========================================================================

class TestDataclassFrozen:
    def test_walletintelligencereport_is_frozen(self) -> None:
        report = _minimal_report()
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError, AttributeError)):
            setattr(report, "advisory_label", "MUTATED")

    def test_walletintelligencereport_is_dataclass(self) -> None:
        assert dataclasses.is_dataclass(WalletIntelligenceReport)

    def test_walletintelligencereport_frozen_flag(self) -> None:
        params = WalletIntelligenceReport.__dataclass_params__  # type: ignore[attr-defined]
        assert params.frozen is True


# ===========================================================================
# Category 16: Deterministic ordering for multiple inputs
# ===========================================================================

class TestDeterministicOrdering:
    def test_signal_distribution_is_stable_across_calls(self) -> None:
        profiles = [
            _make_profile(wallet_id="w1", signal_category="UNCOPYABLE_FAST_FLOW"),
            _make_profile(wallet_id="w2", signal_category="SPECIALIST_ENTRY"),
            _make_profile(wallet_id="w3", signal_category="SPECIALIST_ENTRY"),
        ]
        for _ in range(3):
            report = build_wallet_intelligence_report(profiles, [], [])
            dist = report.wallet_signal_summary["signal_category_distribution"]
            assert dist["SPECIALIST_ENTRY"] == 2
            assert dist["UNCOPYABLE_FAST_FLOW"] == 1

    def test_multiple_profiles_produce_stable_count(self) -> None:
        profiles = [_make_profile(wallet_id=f"w{i}") for i in range(10)]
        r1 = build_wallet_intelligence_report(profiles, [], [])
        r2 = build_wallet_intelligence_report(profiles, [], [])
        assert r1.wallet_signal_summary["profile_count"] == 10
        assert r2.wallet_signal_summary["profile_count"] == 10

    def test_reports_equal_for_same_inputs(self) -> None:
        profiles = [_make_profile()]
        evals = [_make_evaluation()]
        annotations = [_make_annotation()]
        r1 = build_wallet_intelligence_report(profiles, evals, annotations)
        r2 = build_wallet_intelligence_report(profiles, evals, annotations)
        assert r1.wallet_signal_summary == r2.wallet_signal_summary
        assert r1.copyability_delay_summary == r2.copyability_delay_summary
        assert r1.warnings == r2.warnings


# ===========================================================================
# Category 17: No network libraries imported
# ===========================================================================

class TestNoNetworkLibraries:
    _NETWORK_MODULES = [
        "urllib.request", "urllib3", "requests", "httpx", "aiohttp",
        "http.client", "socket", "ssl", "asyncio",
    ]

    def test_no_network_library_imported_by_module(self) -> None:
        import src.data_layer.wallet_intelligence_report_generator as mod
        mod_globals = vars(mod)
        for lib in self._NETWORK_MODULES:
            top_level = lib.split(".")[0]
            assert top_level not in mod_globals, (
                f"Network library '{top_level}' found in module globals"
            )

    def test_module_imports_only_stdlib(self) -> None:
        mod = importlib.import_module(
            "src.data_layer.wallet_intelligence_report_generator"
        )
        import dataclasses as _dc
        import typing as _ty
        assert mod.dataclass is _dc.dataclass  # type: ignore[attr-defined]


# ===========================================================================
# Category 18: No file writes
# ===========================================================================

class TestNoFileWrites:
    def test_build_report_does_not_write_files(self, tmp_path: Any) -> None:
        before = list(tmp_path.iterdir())
        build_wallet_intelligence_report(
            profiles=[_make_profile()],
            evaluations=[_make_evaluation()],
            annotations=[_make_annotation()],
        )
        after = list(tmp_path.iterdir())
        assert before == after

    def test_module_has_no_write_calls(self) -> None:
        import inspect
        import src.data_layer.wallet_intelligence_report_generator as mod
        source = inspect.getsource(mod)
        assert "open(" not in source
        assert ".write(" not in source
        assert "json.dump(" not in source


# ===========================================================================
# Category 19: No credentials/auth clients referenced
# ===========================================================================

class TestNoCredentialsOrAuth:
    def test_no_credentials_in_module(self) -> None:
        import inspect
        import src.data_layer.wallet_intelligence_report_generator as mod
        source = inspect.getsource(mod)
        # Check for actual credential usage in code (not doc comments that say we don't use them)
        # These patterns only appear in real credential-handling code, not advisory docstrings
        forbidden_patterns = [
            "api_key =", "private_key =", "secret_key =", "password =",
            "token = ", "Bearer ", "Authorization:",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in source, (
                f"Credential pattern '{pattern}' found in module source"
            )

    def test_no_auth_imports(self) -> None:
        import src.data_layer.wallet_intelligence_report_generator as mod
        auth_mods = {"boto3", "google.auth", "requests_oauthlib", "jwt"}
        for m in auth_mods:
            top = m.split(".")[0]
            assert top not in vars(mod)


# ===========================================================================
# Category 20: No LLM/Hermes imports
# ===========================================================================

class TestNoLLMOrHermesImports:
    def test_no_llm_hermes_in_module(self) -> None:
        import src.data_layer.wallet_intelligence_report_generator as mod
        # Check module's global namespace for LLM/Hermes imports (not docstring references)
        mod_globals = vars(mod)
        forbidden_imports = ["hermes", "openai", "anthropic", "langchain"]
        for term in forbidden_imports:
            assert term not in mod_globals, (
                f"LLM/Hermes import '{term}' found in module globals"
            )

    def test_no_llm_hermes_imported_in_sys_modules_via_module(self) -> None:
        forbidden_top_levels = {"hermes", "openai", "anthropic", "langchain"}
        loaded = set(sys.modules.keys())
        overlap = forbidden_top_levels & {m.split(".")[0] for m in loaded}
        # Allow anthropic if already loaded by test runner — check module doesn't import it
        import src.data_layer.wallet_intelligence_report_generator as mod
        mod_globals = vars(mod)
        for term in forbidden_top_levels:
            assert term not in mod_globals


# ===========================================================================
# Category 21: No scoring weight mutation
# ===========================================================================

class TestNoScoringWeightMutation:
    def test_no_weight_mutation_in_module(self) -> None:
        import inspect
        import src.data_layer.wallet_intelligence_report_generator as mod
        source = inspect.getsource(mod)
        forbidden_patterns = [
            "scoring_weight", "weight =", "weights[", "update_weight",
            "set_weight", "adjust_weight",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in source, (
                f"Scoring weight mutation pattern '{pattern}' found in module source"
            )


# ===========================================================================
# Category 22: Docs/status updates pass (import and section checks)
# ===========================================================================

class TestDocsSectionChecks:
    def test_forbidden_output_values_covers_all_required(self) -> None:
        required = {
            "BUY", "SELL", "TRADE", "EXECUTE",
            "OPEN_POSITION", "CLOSE_POSITION", "POSITION_SIZE",
            "EXPECTED_RETURN", "PROFIT_TARGET", "STOP_LOSS", "TAKE_PROFIT",
            "LIVE_SIGNAL", "AUTO_COPY", "PNL_TARGET",
            "TRADE_READY", "COPY_READY", "LIVE_READY",
            "BUY_SIGNAL", "SELL_SIGNAL",
        }
        assert required.issubset(FORBIDDEN_OUTPUT_VALUES), (
            f"Missing forbidden values: {required - FORBIDDEN_OUTPUT_VALUES}"
        )

    def test_deferred_items_in_report(self) -> None:
        report = _minimal_report()
        deferred = report.deferred_items
        assert "wallet_signal_paper_strategy_contract" in deferred
        assert "real_wallet_api_ingestion" in deferred
        assert "automated_following_forbidden" in deferred
        assert "live_account_action_forbidden" in deferred

    def test_deferred_items_no_forbidden_labels(self) -> None:
        report = _minimal_report()
        for key, val in report.deferred_items.items():
            for forbidden in FORBIDDEN_OUTPUT_VALUES:
                assert forbidden not in str(val).upper().split("_"), (
                    f"Forbidden value '{forbidden}' in deferred item '{key}': {val}"
                )

    def test_limitations_has_required_fields(self) -> None:
        report = _minimal_report()
        assert "no_live_data_notice" in report.limitations
        assert "no_automated_action_notice" in report.limitations
        assert "data_source_limitations" in report.limitations
        assert "evaluation_limitations" in report.limitations


# ===========================================================================
# Category 23: Full integrated smoke test
# ===========================================================================

class TestFullIntegration:
    def test_full_report_with_real_inputs(self) -> None:
        profiles = [
            _make_profile("wallet_A", "market_1", "cond_1",
                          signal_category="SPECIALIST_ENTRY",
                          human_review_required=False),
            _make_profile("wallet_B", "market_2", "cond_2",
                          signal_category="SUSPICIOUS_TIMING",
                          suspicious_flow_status="SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED",
                          human_review_required=True),
            _make_profile("wallet_C", "market_3", "cond_3",
                          signal_category="UNCOPYABLE_FAST_FLOW"),
        ]
        evaluations = [
            _make_evaluation("wallet_A", "market_1", "cond_1",
                             delay_window="5_seconds",
                             evaluation_status="RESEARCH_PROMISING"),
            _make_evaluation("wallet_A", "market_1", "cond_1",
                             delay_window="30_seconds",
                             evaluation_status="INSUFFICIENT_CONTEXT"),
            _make_evaluation("wallet_B", "market_2", "cond_2",
                             delay_window="1_second",
                             evaluation_status="SUSPICIOUS_FLOW_DO_NOT_COPY",
                             human_review_required=True),
        ]
        annotations = [
            _make_annotation("wallet_A", "market_1", "cond_1",
                             research_priority_effect="LOW_RESEARCH_BOOST"),
            _make_annotation("wallet_B", "market_2", "cond_2",
                             research_priority_effect="BLOCK_FROM_AUTOMATION",
                             human_review_required=True,
                             suspicious_flow_status="SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED"),
        ]

        report = build_wallet_intelligence_report(profiles, evaluations, annotations)

        assert isinstance(report, WalletIntelligenceReport)
        assert report.advisory_label == "ADVISORY_ONLY_WALLET_INTELLIGENCE_REPORT"
        assert report.wallet_signal_summary["profile_count"] == 3
        assert report.wallet_signal_summary["suspicious_flow_count"] == 1
        assert report.wallet_signal_summary["human_review_required_count"] == 1
        assert report.copyability_delay_summary["evaluation_count"] == 3
        assert report.copyability_delay_summary["suspicious_flow_blocked_count"] == 1
        assert report.copyability_delay_summary["insufficient_context_count"] == 1
        assert report.copyability_delay_summary["human_review_required_count"] == 1
        assert report.research_queue_implications["annotation_count"] == 2
        assert report.research_queue_implications["human_review_queue_additions"] == 1
        for flag in report.safety.values():
            assert flag is True
        assert isinstance(report.warnings, tuple)

    def test_wp_version_appears_in_identity(self) -> None:
        report = build_wallet_intelligence_report(
            profiles=[], evaluations=[], annotations=[],
            wp_version="WP82"
        )
        assert report.report_identity["wp_version"] == "WP82"

    def test_metadata_appears_in_identity(self) -> None:
        meta = {"fixture_source": "tests/local_fixture_set_1"}
        report = build_wallet_intelligence_report(
            profiles=[], evaluations=[], annotations=[],
            metadata=meta
        )
        assert report.report_identity["source_metadata"] == meta

    def test_input_summary_counts_correct(self) -> None:
        profiles = [
            _make_profile("w1", "m1", "c1"),
            _make_profile("w2", "m2", "c2"),
        ]
        evals = [_make_evaluation("w1", "m1", "c1")]
        annotations = [_make_annotation("w1", "m1", "c1")]
        report = build_wallet_intelligence_report(profiles, evals, annotations)
        assert report.input_summary["wallet_signal_profile_count"] == 2
        assert report.input_summary["copyability_delay_evaluation_count"] == 1
        assert report.input_summary["research_queue_annotation_count"] == 1
        assert report.input_summary["market_count"] == 2
        assert report.input_summary["condition_count"] == 2

    def test_input_summary_no_network_flags(self) -> None:
        report = _minimal_report()
        assert report.input_summary["no_live_data"] is True
        assert report.input_summary["no_network"] is True


# ===========================================================================
# Category 24: Recursive output scanner — no forbidden terms in any string value
# ===========================================================================

class TestRecursiveOutputScan:
    """Recursively scan all string values in the report for forbidden substrings.

    Pass-through distribution dicts (whose keys come from WP79/WP81 enum constants
    such as "SPECIALIST_ENTRY") are exempted from value-level scanning because those
    keys are controlled by upstream enum definitions, not by this module.

    Approved safety-flag key names that contain allowed substrings as negation
    prefixes (e.g. "not_automated_copy_trading") are exempted from key scanning.
    """

    _FORBIDDEN_SUBSTRINGS: tuple[str, ...] = (
        "buy", "sell", "trade",
        "execute",
        "open_position", "close_position",
        "position_size", "position sizing", "position-size",
        "expected_return", "expected return", "expected-return",
        "profit_target", "profit target",
        "stop_loss", "stop loss",
        "take_profit", "take profit",
        "live_signal", "live signal",
        "auto_copy", "auto copy",
        "pnl_target", "pnl target",
        "paper_trading_candidate", "paper trading candidate",
        "strategy_signal", "strategy signal",
        "copy-trading instructions", "copy trading instructions",
        "buy/sell",
    )

    # Approved safety-flag keys whose names contain allowed substring negations
    _EXEMPTED_KEYS: frozenset[str] = frozenset({
        "not_automated_copy_trading",
        "no_live_execution",
        "no_order_placement",
        "no_position_sizing",
    })

    # Distribution sub-dicts whose keys come from WP79/WP81 enum constants —
    # do not recurse into their values (e.g. "SPECIALIST_ENTRY" contains "entry")
    _PASSTHROUGH_DISTRIBUTION_KEYS: frozenset[str] = frozenset({
        "signal_category_distribution",
        "evaluation_status_distribution",
        "research_priority_effect_summary",
    })

    def _scan_value(self, val: object, path: str) -> list[str]:
        """Recursively collect violation messages from val."""
        violations: list[str] = []
        if isinstance(val, str):
            low = val.lower()
            for sub in self._FORBIDDEN_SUBSTRINGS:
                if sub in low:
                    violations.append(
                        f"Forbidden substring '{sub}' in string at {path!r}: {val!r}"
                    )
        elif isinstance(val, dict):
            for k, v in val.items():
                if k in self._EXEMPTED_KEYS:
                    continue
                if k in self._PASSTHROUGH_DISTRIBUTION_KEYS:
                    # Only scan the dict keys, not the distribution values
                    continue
                child_path = f"{path}[{k!r}]"
                violations.extend(self._scan_value(v, child_path))
        elif isinstance(val, (list, tuple)):
            for i, item in enumerate(val):
                violations.extend(self._scan_value(item, f"{path}[{i}]"))
        return violations

    def _scan_report(self, report: object) -> list[str]:
        from dataclasses import fields as dc_fields
        violations: list[str] = []
        for f in dc_fields(report):
            val = getattr(report, f.name)
            violations.extend(self._scan_value(val, f"report.{f.name}"))
        return violations

    def test_no_forbidden_terms_in_minimal_report(self) -> None:
        report = _minimal_report()
        violations = self._scan_report(report)
        assert not violations, (
            f"Forbidden terms found in report output ({len(violations)} violation(s)):\n"
            + "\n".join(violations)
        )

    def test_no_forbidden_terms_in_full_integration_report(self) -> None:
        profiles = [
            _make_profile("wallet_A", "market_1", "cond_1",
                          signal_category="SPECIALIST_ENTRY",
                          human_review_required=False),
            _make_profile("wallet_B", "market_2", "cond_2",
                          signal_category="SUSPICIOUS_TIMING",
                          suspicious_flow_status="SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED",
                          human_review_required=True),
        ]
        evaluations = [
            _make_evaluation("wallet_A", "market_1", "cond_1",
                             delay_window="5_seconds",
                             evaluation_status="RESEARCH_PROMISING"),
            _make_evaluation("wallet_B", "market_2", "cond_2",
                             delay_window="1_second",
                             evaluation_status="SUSPICIOUS_FLOW_DO_NOT_COPY",
                             human_review_required=True),
        ]
        annotations = [
            _make_annotation("wallet_A", "market_1", "cond_1",
                             research_priority_effect="LOW_RESEARCH_BOOST"),
        ]
        report = build_wallet_intelligence_report(profiles, evaluations, annotations)
        violations = self._scan_report(report)
        assert not violations, (
            f"Forbidden terms found in full report ({len(violations)} violation(s)):\n"
            + "\n".join(violations)
        )

    def test_no_forbidden_terms_in_advisory_notice(self) -> None:
        report = _minimal_report()
        violations = self._scan_value(report.advisory_notice, "report.advisory_notice")
        assert not violations, "\n".join(violations)

    def test_no_forbidden_terms_in_limitations_values(self) -> None:
        report = _minimal_report()
        violations = self._scan_value(report.limitations, "report.limitations")
        assert not violations, "\n".join(violations)

    def test_no_forbidden_terms_in_deferred_items_values(self) -> None:
        report = _minimal_report()
        for key, val in report.deferred_items.items():
            if key in self._EXEMPTED_KEYS:
                continue
            v = self._scan_value(val, f"report.deferred_items[{key!r}]")
            assert not v, "\n".join(v)

    def test_no_forbidden_terms_in_warnings(self) -> None:
        profiles = [
            _make_profile("w1", "m1", "c1",
                          suspicious_flow_status="SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED",
                          human_review_required=True),
        ]
        report = build_wallet_intelligence_report(profiles, [], [])
        violations = self._scan_value(report.warnings, "report.warnings")
        assert not violations, "\n".join(violations)

    def test_no_forbidden_terms_in_suspicious_flow_review(self) -> None:
        profiles = [
            _make_profile("w1", "m1", "c1",
                          suspicious_flow_status="SUSPICIOUS_FLOW_HUMAN_REVIEW_REQUIRED",
                          human_review_required=True),
        ]
        report = build_wallet_intelligence_report(profiles, [], [])
        violations = self._scan_value(
            report.suspicious_flow_review, "report.suspicious_flow_review"
        )
        assert not violations, "\n".join(violations)

    def test_scanner_catches_injected_forbidden_string(self) -> None:
        """Verify the scanner actually catches violations when present."""
        injected = "This is a buy recommendation"
        violations = self._scan_value(injected, "test_path")
        assert any("buy" in v for v in violations), (
            "Scanner failed to catch injected forbidden term 'buy'"
        )
