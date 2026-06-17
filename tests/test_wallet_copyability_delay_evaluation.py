"""Focused tests for WP81 wallet copyability delay evaluation from validated fixtures.

Tests cover:
1.  valid wallet event + matching delay fixture produces advisory evaluation;
2.  all five delay windows are supported;
3.  missing delay context yields INSUFFICIENT_CONTEXT;
4.  missing liquidity/spread/fee/size context creates warnings;
5.  suspicious-flow input yields SUSPICIOUS_FLOW_DO_NOT_COPY status;
6.  no dollar PnL field exists on evaluation dataclass;
7.  no expected-return field exists on evaluation dataclass;
8.  no buy/sell/entry/exit/position-size fields exist;
9.  no trade-ready/copy-ready/live-ready advisory labels;
10. dataclasses are frozen;
11. deterministic ordering for multiple records;
12. invalid loaded records are ignored or surfaced as warnings;
13. no network libraries imported;
14. no file writes in module source;
15. no credentials/auth clients referenced;
16. no LLM/Hermes imports;
17. no scoring weight mutation;
18. docs/status updates present and consistent;
19. full module import and evaluation pipeline works end-to-end.
"""

from __future__ import annotations

import ast
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import MagicMock

import pytest

from src.data_layer.wallet_copyability_delay_evaluation import (
    ALLOWED_EVALUATION_STATUSES,
    DELAY_WINDOW_ORDER,
    EVAL_ADVISORY_LABEL,
    EVAL_UNAVAILABLE_LABEL,
    FORBIDDEN_OUTPUT_VALUES,
    STATUS_HUMAN_REVIEW_REQUIRED,
    STATUS_INSUFFICIENT_CONTEXT,
    STATUS_NOT_EVALUATED,
    STATUS_RESEARCH_PROMISING,
    STATUS_RESEARCH_WEAK,
    STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY,
    STATUS_UNCOPYABLE_FAST_FLOW,
    STATUS_UNCOPYABLE_TOO_ILLIQUID,
    VALID_DELAY_WINDOWS,
    DelayWindowObservation,
    WalletCopyabilityDelayEvaluation,
    evaluate_copyability_delay,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "data_layer" / "wallet_copyability_delay_evaluation.py"
STATUS_PATH = ROOT / "docs" / "project_status.md"
DEFERRED_PATH = ROOT / "docs" / "deferred_items_log.md"
REPO_TRUTH_PATH = ROOT / "docs" / "repo_truth_index.md"
SIMULATOR_DESIGN_PATH = ROOT / "docs" / "wallet_copyability_delay_simulator_design.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    wallet_id: str = "wallet_abc",
    market_id: str = "market_001",
    condition_id: str = "cond_001",
    market_category: str = "POLITICS",
    price_observed: float = 0.65,
    suspicious_flow_flag: bool = False,
    human_review_required: bool = False,
    copyability_context_available: bool = True,
    is_valid: bool = True,
) -> MagicMock:
    """Build a duck-typed LoadedWalletTradeEventRecord for testing."""
    record: dict[str, Any] = {
        "wallet_reference": {"wallet_id_or_address": wallet_id},
        "market_reference": {
            "market_id": market_id,
            "condition_id": condition_id,
            "market_category": market_category,
        },
        "observation": {"price_observed": price_observed},
        "context": {"copyability_context_available": copyability_context_available},
        "review": {
            "suspicious_flow_flag": suspicious_flow_flag,
            "human_review_required": human_review_required,
        },
    }
    validation_mock = MagicMock()
    validation_mock.is_valid = is_valid
    loaded = MagicMock()
    loaded.record = record
    loaded.validation = validation_mock
    return loaded


def _make_obs(
    wallet_id: str = "wallet_abc",
    market_id: str = "market_001",
    condition_id: str = "cond_001",
    delay_window: str = "1_second",
    delayed_price_observed: float | None = 0.66,
    spread_context_available: bool = True,
    liquidity_context_available: bool = True,
    fee_context_available: bool = True,
    size_limit_context_available: bool = True,
    resolved_outcome_available: bool = False,
    suspicious_flow_flag: bool = False,
    fast_flow_flag: bool = False,
    liquidity_insufficient_flag: bool = False,
) -> DelayWindowObservation:
    return DelayWindowObservation(
        wallet_id_or_address=wallet_id,
        market_id=market_id,
        condition_id=condition_id,
        delay_window=delay_window,
        delayed_price_observed=delayed_price_observed,
        spread_context_available=spread_context_available,
        liquidity_context_available=liquidity_context_available,
        fee_context_available=fee_context_available,
        size_limit_context_available=size_limit_context_available,
        resolved_outcome_available=resolved_outcome_available,
        suspicious_flow_flag=suspicious_flow_flag,
        fast_flow_flag=fast_flow_flag,
        liquidity_insufficient_flag=liquidity_insufficient_flag,
    )


def _all_obs_for(
    wallet_id: str = "wallet_abc",
    market_id: str = "market_001",
    condition_id: str = "cond_001",
    delayed_price: float = 0.66,
) -> list[DelayWindowObservation]:
    """Return one observation for each of the five delay windows."""
    return [
        _make_obs(
            wallet_id=wallet_id,
            market_id=market_id,
            condition_id=condition_id,
            delay_window=dw,
            delayed_price_observed=delayed_price,
        )
        for dw in DELAY_WINDOW_ORDER
    ]


# ---------------------------------------------------------------------------
# 1. Valid event + matching delay fixture produces advisory evaluation
# ---------------------------------------------------------------------------

class TestValidEventProducesEvaluation:
    def test_one_event_one_window_produces_five_evaluations(self):
        """For one event group, evaluate_copyability_delay emits one per window."""
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        assert len(result) == 5

    def test_result_is_tuple(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        assert isinstance(result, tuple)

    def test_all_results_are_evaluations(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert isinstance(ev, WalletCopyabilityDelayEvaluation)

    def test_advisory_label_present_on_all(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert ev.advisory_label in (EVAL_ADVISORY_LABEL, EVAL_UNAVAILABLE_LABEL)

    def test_wallet_id_preserved(self):
        records = [_make_record(wallet_id="wallet_xyz")]
        obs = _all_obs_for(wallet_id="wallet_xyz")
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert ev.wallet_id_or_address == "wallet_xyz"

    def test_market_id_preserved(self):
        records = [_make_record(market_id="mkt_99")]
        obs = _all_obs_for(market_id="mkt_99")
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert ev.market_id == "mkt_99"

    def test_condition_id_preserved(self):
        records = [_make_record(condition_id="cond_99")]
        obs = _all_obs_for(condition_id="cond_99")
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert ev.condition_id == "cond_99"

    def test_evaluation_status_in_allowed_set(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert ev.evaluation_status in ALLOWED_EVALUATION_STATUSES

    def test_close_price_yields_research_promising(self):
        """Price within 5% of event price → RESEARCH_PROMISING."""
        records = [_make_record(price_observed=0.65)]
        obs = [_make_obs(delay_window="1_second", delayed_price_observed=0.66)]
        result = evaluate_copyability_delay(records, obs)
        # Only 1_second has an obs; others will be INSUFFICIENT_CONTEXT
        window_results = {ev.delay_window: ev for ev in result}
        assert window_results["1_second"].evaluation_status == STATUS_RESEARCH_PROMISING

    def test_far_price_yields_research_weak(self):
        """Price more than 5% from event price → RESEARCH_WEAK."""
        records = [_make_record(price_observed=0.50)]
        obs = [_make_obs(delay_window="1_second", delayed_price_observed=0.80)]
        result = evaluate_copyability_delay(records, obs)
        window_results = {ev.delay_window: ev for ev in result}
        assert window_results["1_second"].evaluation_status == STATUS_RESEARCH_WEAK

    def test_research_interpretation_is_nonempty(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert isinstance(ev.research_interpretation, str)
            assert len(ev.research_interpretation.strip()) > 0

    def test_empty_records_returns_empty_tuple(self):
        result = evaluate_copyability_delay([], [])
        assert result == ()

    def test_empty_obs_returns_insufficient_context_for_all_windows(self):
        records = [_make_record()]
        result = evaluate_copyability_delay(records, [])
        assert len(result) == 5
        for ev in result:
            assert ev.evaluation_status == STATUS_INSUFFICIENT_CONTEXT


# ---------------------------------------------------------------------------
# 2. All five delay windows are supported
# ---------------------------------------------------------------------------

class TestAllDelayWindowsSupported:
    def test_five_windows_defined(self):
        assert len(VALID_DELAY_WINDOWS) == 5

    def test_required_window_labels_present(self):
        required = {"1_second", "5_seconds", "30_seconds", "2_minutes", "10_minutes"}
        assert required == VALID_DELAY_WINDOWS

    def test_window_order_has_five_entries(self):
        assert len(DELAY_WINDOW_ORDER) == 5

    def test_window_order_covers_all_valid_windows(self):
        assert set(DELAY_WINDOW_ORDER) == VALID_DELAY_WINDOWS

    def test_all_five_windows_in_output(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        windows_in_output = {ev.delay_window for ev in result}
        assert windows_in_output == VALID_DELAY_WINDOWS

    def test_each_window_appears_once_per_group(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        window_counts: dict[str, int] = {}
        for ev in result:
            window_counts[ev.delay_window] = window_counts.get(ev.delay_window, 0) + 1
        for dw in VALID_DELAY_WINDOWS:
            assert window_counts.get(dw, 0) == 1

    def test_obs_with_invalid_delay_window_is_ignored(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="INVALID_WINDOW")]
        result = evaluate_copyability_delay(records, obs)
        # All windows should be INSUFFICIENT_CONTEXT
        for ev in result:
            assert ev.evaluation_status == STATUS_INSUFFICIENT_CONTEXT

    def test_1_second_window_evaluated(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second")]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert "1_second" in windows
        assert windows["1_second"].evaluation_status != STATUS_INSUFFICIENT_CONTEXT

    def test_5_seconds_window_evaluated(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="5_seconds")]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["5_seconds"].evaluation_status != STATUS_INSUFFICIENT_CONTEXT

    def test_30_seconds_window_evaluated(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="30_seconds")]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["30_seconds"].evaluation_status != STATUS_INSUFFICIENT_CONTEXT

    def test_2_minutes_window_evaluated(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="2_minutes")]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["2_minutes"].evaluation_status != STATUS_INSUFFICIENT_CONTEXT

    def test_10_minutes_window_evaluated(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="10_minutes")]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["10_minutes"].evaluation_status != STATUS_INSUFFICIENT_CONTEXT


# ---------------------------------------------------------------------------
# 3. Missing delay context yields INSUFFICIENT_CONTEXT
# ---------------------------------------------------------------------------

class TestMissingContextYieldsInsufficient:
    def test_no_obs_for_window_is_insufficient(self):
        records = [_make_record()]
        # provide obs for 1_second only, others should be INSUFFICIENT_CONTEXT
        obs = [_make_obs(delay_window="1_second")]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        for dw in ("5_seconds", "30_seconds", "2_minutes", "10_minutes"):
            assert windows[dw].evaluation_status == STATUS_INSUFFICIENT_CONTEXT

    def test_insufficient_context_advisory_label(self):
        records = [_make_record()]
        result = evaluate_copyability_delay(records, [])
        for ev in result:
            assert ev.evaluation_status == STATUS_INSUFFICIENT_CONTEXT
            assert ev.advisory_label in (EVAL_ADVISORY_LABEL, EVAL_UNAVAILABLE_LABEL)

    def test_no_obs_has_false_context_flags(self):
        records = [_make_record()]
        result = evaluate_copyability_delay(records, [])
        for ev in result:
            assert ev.spread_context_available is False
            assert ev.liquidity_context_available is False
            assert ev.fee_context_available is False
            assert ev.size_limit_context_available is False

    def test_no_obs_delayed_price_is_none(self):
        records = [_make_record()]
        result = evaluate_copyability_delay(records, [])
        for ev in result:
            assert ev.delayed_price_observed is None

    def test_null_delayed_price_yields_insufficient(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second", delayed_price_observed=None)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["1_second"].evaluation_status == STATUS_INSUFFICIENT_CONTEXT


# ---------------------------------------------------------------------------
# 4. Missing context creates warnings
# ---------------------------------------------------------------------------

class TestMissingContextCreatesWarnings:
    def test_missing_spread_context_creates_warning(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second", spread_context_available=False)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        ev = windows["1_second"]
        assert any("spread" in w for w in ev.warnings)

    def test_missing_liquidity_context_creates_warning(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second", liquidity_context_available=False)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        ev = windows["1_second"]
        assert any("liquidity" in w for w in ev.warnings)

    def test_missing_fee_context_creates_warning(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second", fee_context_available=False)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        ev = windows["1_second"]
        assert any("fee" in w for w in ev.warnings)

    def test_missing_size_limit_context_creates_warning(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second", size_limit_context_available=False)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        ev = windows["1_second"]
        assert any("size_limit" in w for w in ev.warnings)

    def test_missing_context_yields_insufficient_status(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second", spread_context_available=False)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["1_second"].evaluation_status == STATUS_INSUFFICIENT_CONTEXT

    def test_warnings_is_tuple(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert isinstance(ev.warnings, tuple)

    def test_all_context_available_no_context_warnings(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second")]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        ev = windows["1_second"]
        context_warnings = [w for w in ev.warnings if "context_available is False" in w]
        assert len(context_warnings) == 0


# ---------------------------------------------------------------------------
# 5. Suspicious-flow yields human review / do-not-copy status
# ---------------------------------------------------------------------------

class TestSuspiciousFlow:
    def test_suspicious_flow_yields_do_not_copy_status(self):
        records = [_make_record(suspicious_flow_flag=True)]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert ev.evaluation_status == STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY

    def test_suspicious_flow_sets_human_review_required(self):
        records = [_make_record(suspicious_flow_flag=True)]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert ev.human_review_required is True

    def test_suspicious_flow_includes_warning(self):
        records = [_make_record(suspicious_flow_flag=True)]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert len(ev.warnings) >= 1
            assert any("suspicious" in w.lower() or "SUSPICIOUS" in w for w in ev.warnings)

    def test_suspicious_flow_advisory_label_present(self):
        records = [_make_record(suspicious_flow_flag=True)]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert ev.advisory_label in (EVAL_ADVISORY_LABEL, EVAL_UNAVAILABLE_LABEL)

    def test_fast_flow_yields_uncopyable_fast_flow(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second", fast_flow_flag=True)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["1_second"].evaluation_status == STATUS_UNCOPYABLE_FAST_FLOW

    def test_illiquid_yields_uncopyable_too_illiquid(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second", liquidity_insufficient_flag=True)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["1_second"].evaluation_status == STATUS_UNCOPYABLE_TOO_ILLIQUID

    def test_human_review_required_flag_yields_human_review_status(self):
        records = [_make_record(human_review_required=True)]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            if ev.evaluation_status not in (STATUS_INSUFFICIENT_CONTEXT,):
                assert ev.human_review_required is True

    def test_obs_suspicious_flow_yields_do_not_copy(self):
        """Observation-level suspicious_flow_flag=True must yield SUSPICIOUS_FLOW_DO_NOT_COPY."""
        records = [_make_record(suspicious_flow_flag=False)]
        obs = [_make_obs(delay_window="1_second", suspicious_flow_flag=True)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["1_second"].evaluation_status == STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY

    def test_obs_suspicious_flow_sets_human_review_required(self):
        """Observation-level suspicious_flow_flag=True must set human_review_required=True."""
        records = [_make_record(suspicious_flow_flag=False)]
        obs = [_make_obs(delay_window="1_second", suspicious_flow_flag=True)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["1_second"].human_review_required is True

    def test_obs_suspicious_flow_includes_warning(self):
        """Observation-level suspicious_flow_flag=True must include a suspicious-flow warning."""
        records = [_make_record(suspicious_flow_flag=False)]
        obs = [_make_obs(delay_window="1_second", suspicious_flow_flag=True)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        ev = windows["1_second"]
        assert any("suspicious" in w.lower() or "SUSPICIOUS" in w for w in ev.warnings)

    def test_both_event_and_obs_suspicious_flow_yields_do_not_copy(self):
        """Both event and observation suspicious_flow_flag=True must yield SUSPICIOUS_FLOW_DO_NOT_COPY."""
        records = [_make_record(suspicious_flow_flag=True)]
        obs = [_make_obs(delay_window="1_second", suspicious_flow_flag=True)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["1_second"].evaluation_status == STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY

    def test_obs_suspicious_flow_takes_precedence_over_fast_flow(self):
        """Observation suspicious_flow_flag must block before fast_flow_flag is checked."""
        records = [_make_record(suspicious_flow_flag=False)]
        obs = [_make_obs(delay_window="1_second", suspicious_flow_flag=True, fast_flow_flag=True)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["1_second"].evaluation_status == STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY

    def test_obs_suspicious_flow_takes_precedence_over_illiquid(self):
        """Observation suspicious_flow_flag must block before liquidity_insufficient_flag is checked."""
        records = [_make_record(suspicious_flow_flag=False)]
        obs = [_make_obs(delay_window="1_second", suspicious_flow_flag=True, liquidity_insufficient_flag=True)]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["1_second"].evaluation_status == STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY

    def test_obs_suspicious_flow_takes_precedence_over_research_promising(self):
        """Observation suspicious_flow_flag must block even when price would yield RESEARCH_PROMISING."""
        records = [_make_record(price_observed=0.65, suspicious_flow_flag=False)]
        obs = [_make_obs(
            delay_window="1_second",
            delayed_price_observed=0.66,
            suspicious_flow_flag=True,
        )]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        assert windows["1_second"].evaluation_status == STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY


# ---------------------------------------------------------------------------
# 6–9. Forbidden fields and labels
# ---------------------------------------------------------------------------

class TestForbiddenFieldsAndLabels:
    def test_no_dollar_pnl_field(self):
        """WalletCopyabilityDelayEvaluation must not have dollar_pnl field."""
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "dollar_pnl" not in field_names

    def test_no_pnl_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "pnl" not in field_names

    def test_no_expected_return_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "expected_return" not in field_names

    def test_no_buy_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "buy" not in field_names

    def test_no_sell_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "sell" not in field_names

    def test_no_entry_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "entry" not in field_names

    def test_no_exit_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "exit" not in field_names

    def test_no_position_size_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "position_size" not in field_names

    def test_no_profit_target_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "profit_target" not in field_names

    def test_no_stop_loss_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "stop_loss" not in field_names

    def test_no_take_profit_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "take_profit" not in field_names

    def test_no_live_signal_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "live_signal" not in field_names

    def test_no_auto_copy_field(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert "auto_copy" not in field_names

    def test_forbidden_output_values_set_is_nonempty(self):
        assert len(FORBIDDEN_OUTPUT_VALUES) > 0

    def test_trade_ready_not_in_advisory_labels(self):
        """TRADE_READY must not be a valid advisory label."""
        assert "TRADE_READY" not in (EVAL_ADVISORY_LABEL, EVAL_UNAVAILABLE_LABEL)
        assert "TRADE_READY" in FORBIDDEN_OUTPUT_VALUES

    def test_copy_ready_not_in_advisory_labels(self):
        assert "COPY_READY" not in (EVAL_ADVISORY_LABEL, EVAL_UNAVAILABLE_LABEL)
        assert "COPY_READY" in FORBIDDEN_OUTPUT_VALUES

    def test_live_ready_not_in_advisory_labels(self):
        assert "LIVE_READY" not in (EVAL_ADVISORY_LABEL, EVAL_UNAVAILABLE_LABEL)
        assert "LIVE_READY" in FORBIDDEN_OUTPUT_VALUES

    def test_buy_signal_not_in_advisory_labels(self):
        assert "BUY_SIGNAL" not in (EVAL_ADVISORY_LABEL, EVAL_UNAVAILABLE_LABEL)

    def test_sell_signal_not_in_advisory_labels(self):
        assert "SELL_SIGNAL" not in (EVAL_ADVISORY_LABEL, EVAL_UNAVAILABLE_LABEL)

    def test_no_forbidden_values_in_statuses(self):
        """Allowed statuses must not overlap with forbidden output values."""
        for status in ALLOWED_EVALUATION_STATUSES:
            assert status not in FORBIDDEN_OUTPUT_VALUES

    def test_no_forbidden_values_in_output_advisory_labels(self):
        for label in (EVAL_ADVISORY_LABEL, EVAL_UNAVAILABLE_LABEL):
            for forbidden in FORBIDDEN_OUTPUT_VALUES:
                assert forbidden not in label

    def test_evaluation_outputs_no_forbidden_values_in_status(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert ev.evaluation_status not in FORBIDDEN_OUTPUT_VALUES

    def test_evaluation_outputs_no_forbidden_values_in_advisory_label(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            for forbidden in FORBIDDEN_OUTPUT_VALUES:
                assert forbidden not in ev.advisory_label


# ---------------------------------------------------------------------------
# 10. Dataclasses are frozen
# ---------------------------------------------------------------------------

class TestFrozenDataclasses:
    def test_evaluation_is_frozen(self):
        records = [_make_record()]
        obs = [_make_obs(delay_window="1_second")]
        result = evaluate_copyability_delay(records, obs)
        ev = next(e for e in result if e.delay_window == "1_second")
        with pytest.raises((TypeError, AttributeError)):
            ev.evaluation_status = "MUTATED"  # type: ignore[misc]

    def test_delay_window_observation_is_frozen(self):
        obs = _make_obs()
        with pytest.raises((TypeError, AttributeError)):
            obs.delay_window = "MUTATED"  # type: ignore[misc]

    def test_evaluation_warnings_tuple_immutable(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert isinstance(ev.warnings, tuple)


# ---------------------------------------------------------------------------
# 11. Deterministic ordering for multiple records
# ---------------------------------------------------------------------------

class TestDeterministicOrdering:
    def test_two_groups_sorted_by_wallet_market_condition(self):
        records = [
            _make_record(wallet_id="wallet_z", market_id="mkt_1", condition_id="cond_1"),
            _make_record(wallet_id="wallet_a", market_id="mkt_1", condition_id="cond_1"),
        ]
        obs = (
            _all_obs_for(wallet_id="wallet_z", market_id="mkt_1", condition_id="cond_1") +
            _all_obs_for(wallet_id="wallet_a", market_id="mkt_1", condition_id="cond_1")
        )
        result = evaluate_copyability_delay(records, obs)
        wallets = [ev.wallet_id_or_address for ev in result]
        assert wallets == sorted(wallets)

    def test_same_group_windows_appear_in_order(self):
        records = [_make_record()]
        obs = _all_obs_for()
        result = evaluate_copyability_delay(records, obs)
        windows = [ev.delay_window for ev in result]
        assert windows == sorted(windows)

    def test_same_input_produces_same_output(self):
        records = [
            _make_record(wallet_id="wallet_a"),
            _make_record(wallet_id="wallet_b"),
        ]
        obs = (
            _all_obs_for(wallet_id="wallet_a") +
            _all_obs_for(wallet_id="wallet_b")
        )
        result1 = evaluate_copyability_delay(records, obs)
        result2 = evaluate_copyability_delay(records, obs)
        assert result1 == result2

    def test_multiple_events_in_same_group_aggregated(self):
        """Two events for the same (wallet, market, condition) → still 5 evaluations."""
        records = [
            _make_record(wallet_id="wallet_a"),
            _make_record(wallet_id="wallet_a"),
        ]
        obs = _all_obs_for(wallet_id="wallet_a")
        result = evaluate_copyability_delay(records, obs)
        assert len(result) == 5


# ---------------------------------------------------------------------------
# 12. Invalid loaded records are ignored or surfaced as warnings
# ---------------------------------------------------------------------------

class TestInvalidRecords:
    def test_none_record_ignored(self):
        result = evaluate_copyability_delay([None], [])
        assert result == ()

    def test_string_record_ignored(self):
        result = evaluate_copyability_delay(["not_a_record"], [])
        assert result == ()

    def test_int_record_ignored(self):
        result = evaluate_copyability_delay([42], [])
        assert result == ()

    def test_record_without_record_attr_ignored(self):
        obj = MagicMock(spec=[])
        result = evaluate_copyability_delay([obj], [])
        assert result == ()

    def test_record_with_non_mapping_record_attr_ignored(self):
        obj = MagicMock()
        obj.record = "not a mapping"
        result = evaluate_copyability_delay([obj], [])
        assert result == ()

    def test_invalid_wp78_record_surfaces_warning(self):
        """An invalid WP78 record (is_valid=False) should surface in warnings."""
        records = [_make_record(is_valid=False)]
        obs = [_make_obs(delay_window="1_second")]
        result = evaluate_copyability_delay(records, obs)
        windows = {ev.delay_window: ev for ev in result}
        ev = windows["1_second"]
        assert any("invalid" in w.lower() for w in ev.warnings)

    def test_mix_of_valid_and_none_records(self):
        records = [None, _make_record(wallet_id="wallet_v"), None]
        obs = _all_obs_for(wallet_id="wallet_v")
        result = evaluate_copyability_delay(records, obs)
        assert len(result) == 5
        for ev in result:
            assert ev.wallet_id_or_address == "wallet_v"


# ---------------------------------------------------------------------------
# 13. No network libraries imported
# ---------------------------------------------------------------------------

class TestNoNetworkLibraries:
    NETWORK_MODULES = (
        "requests",
        "urllib.request",
        "urllib3",
        "httpx",
        "aiohttp",
        "socket",
        "asyncio",
        "websockets",
        "boto3",
    )

    def _parse_imports(self) -> list[str]:
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module)
        return imported

    def test_no_requests_import(self):
        imported = self._parse_imports()
        assert "requests" not in imported

    def test_no_urllib_request_import(self):
        imported = self._parse_imports()
        assert not any("urllib.request" in m for m in imported)

    def test_no_httpx_import(self):
        imported = self._parse_imports()
        assert "httpx" not in imported

    def test_no_aiohttp_import(self):
        imported = self._parse_imports()
        assert "aiohttp" not in imported

    def test_no_websockets_import(self):
        imported = self._parse_imports()
        assert "websockets" not in imported

    def test_no_boto3_import(self):
        imported = self._parse_imports()
        assert "boto3" not in imported

    def test_no_socket_import(self):
        imported = self._parse_imports()
        assert "socket" not in imported


# ---------------------------------------------------------------------------
# 14. No file writes in module source
# ---------------------------------------------------------------------------

class TestNoFileWrites:
    def test_no_open_write_calls(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        assert "open(" not in source or all(
            "write" not in line
            for line in source.splitlines()
            if "open(" in line
        )

    def test_no_write_text_calls(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        assert ".write_text(" not in source

    def test_no_write_bytes_calls(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        assert ".write_bytes(" not in source

    def test_no_json_dump_to_file(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        assert "json.dump(" not in source


# ---------------------------------------------------------------------------
# 15. No credentials/auth clients referenced
# ---------------------------------------------------------------------------

class TestNoCredentialsOrAuthClients:
    CRED_TERMS = (
        "api_key",
        "apikey",
        "private_key",
        "secret_key",
        "auth_token",
        "bearer_token",
        "access_token",
        "seed_phrase",
        "passphrase",
    )

    def test_no_credential_terms_in_source(self):
        source = MODULE_PATH.read_text(encoding="utf-8").lower()
        for term in self.CRED_TERMS:
            assert term not in source, f"Forbidden credential term '{term}' found in module source"

    def test_no_py_clob_client_import(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        assert "py_clob_client" not in source
        assert "py-clob-client" not in source

    def test_no_auth_import(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        assert "import auth" not in source.lower()


# ---------------------------------------------------------------------------
# 16. No LLM/Hermes imports
# ---------------------------------------------------------------------------

class TestNoLLMOrHermesImports:
    def _get_import_names(self) -> list[str]:
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name.lower())
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module.lower())
        return names

    def test_no_hermes_import(self):
        imports = self._get_import_names()
        assert not any("hermes" in name for name in imports)

    def test_no_openai_import(self):
        imports = self._get_import_names()
        assert not any("openai" in name for name in imports)

    def test_no_anthropic_import(self):
        imports = self._get_import_names()
        assert not any("anthropic" in name for name in imports)

    def test_no_langchain_import(self):
        imports = self._get_import_names()
        assert not any("langchain" in name for name in imports)

    def test_no_llm_import(self):
        imports = self._get_import_names()
        assert not any(name == "llm" or name.startswith("llm.") for name in imports)


# ---------------------------------------------------------------------------
# 17. No scoring weight mutation
# ---------------------------------------------------------------------------

class TestNoScoringWeightMutation:
    def test_no_scoring_weight_attribute_assignment(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        assert "scoring_weight" not in source
        assert "weight_score" not in source
        assert "research_priority_score" not in source

    def _get_import_names(self) -> list[str]:
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.append(alias.name.lower())
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module.lower())
        return names

    def test_no_pnl_computation_imports(self):
        """Module must not import any PnL computation library."""
        imports = self._get_import_names()
        assert not any("pnl" in name for name in imports)

    def test_no_pnl_field_in_dataclass(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert not any("pnl" in name.lower() for name in field_names)

    def test_no_expected_return_field_in_dataclass(self):
        field_names = {f.name for f in dc_fields(WalletCopyabilityDelayEvaluation)}
        assert not any("expected_return" in name.lower() for name in field_names)


# ---------------------------------------------------------------------------
# 18. Docs/status updates pass
# ---------------------------------------------------------------------------

class TestDocsUpdates:
    def test_project_status_file_exists(self):
        assert STATUS_PATH.exists(), "docs/project_status.md must exist"

    def test_project_status_mentions_wp81(self):
        text = STATUS_PATH.read_text(encoding="utf-8")
        assert "WP81" in text, "docs/project_status.md must mention WP81"

    def test_deferred_items_file_exists(self):
        assert DEFERRED_PATH.exists(), "docs/deferred_items_log.md must exist"

    def test_deferred_items_still_open_report_generator(self):
        text = DEFERRED_PATH.read_text(encoding="utf-8")
        assert "WP82" in text or "wallet intelligence report generator" in text.lower(), (
            "docs/deferred_items_log.md should reference WP82 or wallet intelligence "
            "report generator as a deferred item"
        )

    def test_simulator_design_doc_exists(self):
        assert SIMULATOR_DESIGN_PATH.exists(), (
            "docs/wallet_copyability_delay_simulator_design.md must exist"
        )

    def test_simulator_design_doc_mentions_wp81_implementation(self):
        text = SIMULATOR_DESIGN_PATH.read_text(encoding="utf-8")
        assert "WP81" in text, (
            "wallet_copyability_delay_simulator_design.md must mention WP81"
        )

    def test_simulator_design_doc_mentions_local_offline_evaluator(self):
        text = SIMULATOR_DESIGN_PATH.read_text(encoding="utf-8").lower()
        assert "local" in text and "offline" in text, (
            "simulator design doc must mention local/offline evaluator"
        )

    def test_repo_truth_index_exists(self):
        assert REPO_TRUTH_PATH.exists(), "docs/repo_truth_index.md must exist"

    def test_simulator_design_doc_no_buy_sell_in_wp81_section(self):
        text = SIMULATOR_DESIGN_PATH.read_text(encoding="utf-8")
        wp81_idx = text.find("WP81")
        if wp81_idx < 0:
            pytest.skip("WP81 section not found in simulator design doc")
        wp81_section = text[wp81_idx:wp81_idx + 1000]
        assert "BUY" not in wp81_section or "does not" in wp81_section.lower()


# ---------------------------------------------------------------------------
# 19. End-to-end pipeline
# ---------------------------------------------------------------------------

class TestEndToEndPipeline:
    def test_full_five_window_evaluation_all_promising(self):
        records = [_make_record(price_observed=0.60)]
        obs = [
            _make_obs(delay_window=dw, delayed_price_observed=0.61)
            for dw in DELAY_WINDOW_ORDER
        ]
        result = evaluate_copyability_delay(records, obs)
        assert len(result) == 5
        for ev in result:
            assert ev.evaluation_status == STATUS_RESEARCH_PROMISING

    def test_multi_wallet_multi_window_correct_count(self):
        records = [
            _make_record(wallet_id="wallet_a"),
            _make_record(wallet_id="wallet_b"),
            _make_record(wallet_id="wallet_c"),
        ]
        obs = (
            _all_obs_for(wallet_id="wallet_a") +
            _all_obs_for(wallet_id="wallet_b") +
            _all_obs_for(wallet_id="wallet_c")
        )
        result = evaluate_copyability_delay(records, obs)
        assert len(result) == 15  # 3 wallets * 5 windows

    def test_all_forbidden_values_absent_from_status_and_label(self):
        """Forbidden values must not appear as evaluation_status or advisory_label."""
        records = [
            _make_record(wallet_id="wallet_a"),
            _make_record(wallet_id="wallet_b", suspicious_flow_flag=True),
        ]
        obs = (
            _all_obs_for(wallet_id="wallet_a") +
            _all_obs_for(wallet_id="wallet_b")
        )
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            for forbidden in FORBIDDEN_OUTPUT_VALUES:
                assert ev.evaluation_status != forbidden, (
                    f"Forbidden value '{forbidden}' appeared as evaluation_status"
                )
                assert ev.advisory_label != forbidden, (
                    f"Forbidden value '{forbidden}' appeared as advisory_label"
                )

    def test_not_evaluated_status_in_allowed_set(self):
        assert STATUS_NOT_EVALUATED in ALLOWED_EVALUATION_STATUSES

    def test_insufficient_context_status_in_allowed_set(self):
        assert STATUS_INSUFFICIENT_CONTEXT in ALLOWED_EVALUATION_STATUSES

    def test_research_promising_status_in_allowed_set(self):
        assert STATUS_RESEARCH_PROMISING in ALLOWED_EVALUATION_STATUSES

    def test_research_weak_status_in_allowed_set(self):
        assert STATUS_RESEARCH_WEAK in ALLOWED_EVALUATION_STATUSES

    def test_uncopyable_fast_flow_status_in_allowed_set(self):
        assert STATUS_UNCOPYABLE_FAST_FLOW in ALLOWED_EVALUATION_STATUSES

    def test_uncopyable_too_illiquid_status_in_allowed_set(self):
        assert STATUS_UNCOPYABLE_TOO_ILLIQUID in ALLOWED_EVALUATION_STATUSES

    def test_suspicious_flow_do_not_copy_status_in_allowed_set(self):
        assert STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY in ALLOWED_EVALUATION_STATUSES

    def test_human_review_required_status_in_allowed_set(self):
        assert STATUS_HUMAN_REVIEW_REQUIRED in ALLOWED_EVALUATION_STATUSES

    def test_exactly_eight_allowed_statuses(self):
        assert len(ALLOWED_EVALUATION_STATUSES) == 8

    def test_suspicious_flow_propagates_through_group(self):
        """Suspicious flow on any event in the group → all windows do-not-copy."""
        records = [
            _make_record(wallet_id="wallet_a", suspicious_flow_flag=False),
            _make_record(wallet_id="wallet_a", suspicious_flow_flag=True),
        ]
        obs = _all_obs_for(wallet_id="wallet_a")
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            assert ev.evaluation_status == STATUS_SUSPICIOUS_FLOW_DO_NOT_COPY

    def test_human_review_propagates_through_group(self):
        """Human review on any event in the group → human_review_required=True."""
        records = [
            _make_record(wallet_id="wallet_a", human_review_required=False),
            _make_record(wallet_id="wallet_a", human_review_required=True),
        ]
        obs = _all_obs_for(wallet_id="wallet_a")
        result = evaluate_copyability_delay(records, obs)
        for ev in result:
            if ev.evaluation_status != STATUS_INSUFFICIENT_CONTEXT:
                assert ev.human_review_required is True
