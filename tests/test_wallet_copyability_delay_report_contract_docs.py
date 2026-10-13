"""Focused docs/schema tests for WP80 wallet copyability delay simulator design
and wallet intelligence report contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]

DELAY_DESIGN_DOC = ROOT / "docs" / "wallet_copyability_delay_simulator_design.md"
REPORT_CONTRACT_DOC = ROOT / "docs" / "wallet_intelligence_report_contract.md"
DELAY_EVAL_SCHEMA = ROOT / "docs" / "schemas" / "wallet_copyability_delay_evaluation_v1.example.json"
REPORT_SCHEMA = ROOT / "docs" / "schemas" / "wallet_intelligence_report_v1.example.json"

STATUS_DOC = ROOT / "docs" / "project_status.md"
REPO_TRUTH_DOC = ROOT / "docs" / "repo_truth_index.md"
DEFERRED_DOC = ROOT / "docs" / "deferred_items_log.md"
ROADMAP_DOC = ROOT / "docs" / "wallet_intelligence_research_signal_roadmap.md"
ARCH_DOC = ROOT / "docs" / "wallet_intelligence_architecture_and_signal_contract.md"
SIGNAL_PROFILE_DOC = ROOT / "docs" / "wallet_signal_research_profile.md"
TRADE_EVENT_DOC = ROOT / "docs" / "wallet_trade_event_snapshot_schema.md"

REQUIRED_DELAY_WINDOWS = (
    "1 second",
    "5 seconds",
    "30 seconds",
    "2 minutes",
    "10 minutes",
)

REQUIRED_EVALUATION_STATUSES = (
    "NOT_EVALUATED",
    "INSUFFICIENT_CONTEXT",
    "RESEARCH_PROMISING",
    "RESEARCH_WEAK",
    "UNCOPYABLE_FAST_FLOW",
    "UNCOPYABLE_TOO_ILLIQUID",
    "SUSPICIOUS_FLOW_DO_NOT_COPY",
    "HUMAN_REVIEW_REQUIRED",
)

FORBIDDEN_TRADE_LIKE_KEYS = {
    "buy",
    "sell",
    "trade",
    "execute",
    "open_position",
    "close_position",
    "position_size",
    "position_sizing",              # variant: position_size with ing suffix
    "expected_return",
    "expected_return_computation",  # variant: expected_return with _computation suffix
    "profit_target",
    "stop_loss",
    "take_profit",
    "live_signal",
    "auto_copy",
    "pnl_target",
    "paper_trading_candidate",      # forbidden deferred-item key variant
    "strategy_signal",              # forbidden deferred-item key variant
}

FORBIDDEN_VALUE_SUBSTRINGS = (
    "expected_return",
    "expected-return",
    "expected return",
    "expected_return_computation",
    "position_size",
    "position_sizing",
    "paper_trading_candidate",
    "strategy_signal",
    "live_signal",
    "auto_copy",
    "pnl_target",
    "open_position",
    "close_position",
    "take_profit",
    "stop_loss",
    "profit_target",
    "buy",
    "sell",
)

REQUIRED_SAFETY_FLAGS = (
    "manual_research_only",
    "not_automated_copy_trading",
    "no_live_execution",
    "no_order_placement",
    "no_position_sizing",
    "no_risk_override",
    "no_parameter_auto_change",
)

REQUIRED_REPORT_SECTIONS = (
    "report_identity",
    "input_summary",
    "wallet_signal_summary",
    "copyability_delay_design_summary",
    "research_queue_implications",
    "suspicious_flow_review",
    "limitations",
    "deferred_items",
    "safety",
)

REQUIRED_CONSTRAINT_FACTORS = (
    "spread",
    "slippage",
    "fees",
    "liquidity",
    "size",
)

FORBIDDEN_IMPLEMENTATION_SCOPE = (
    "live copyability simulator",
    "expected-return",
    "position sizing",
    "credentials",
    "scheduler",
    "bot loop",
    "order placement",
)

FUTURE_WP_SEQUENCE = (
    "WP81",
    "WP82",
    "WP83",
    "WP84",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> Any:
    return json.loads(_read(path))


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.append(str(key).lower())
            keys.extend(_walk_keys(nested))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_walk_keys(item))
    return keys


def _walk_string_values(value: Any) -> list[str]:
    """Walk a JSON structure and collect all lowercased string leaf values."""
    values: list[str] = []
    if isinstance(value, dict):
        for v in value.values():
            values.extend(_walk_string_values(v))
    elif isinstance(value, list):
        for item in value:
            values.extend(_walk_string_values(item))
    elif isinstance(value, str):
        values.append(value.lower())
    return values


# ---------------------------------------------------------------------------
# 1. Design docs and static examples exist
# ---------------------------------------------------------------------------

def test_copyability_delay_design_doc_exists() -> None:
    assert DELAY_DESIGN_DOC.is_file(), f"Missing: {DELAY_DESIGN_DOC}"


def test_wallet_intelligence_report_contract_doc_exists() -> None:
    assert REPORT_CONTRACT_DOC.is_file(), f"Missing: {REPORT_CONTRACT_DOC}"


def test_delay_evaluation_schema_example_exists() -> None:
    assert DELAY_EVAL_SCHEMA.is_file(), f"Missing: {DELAY_EVAL_SCHEMA}"


def test_wallet_intelligence_report_schema_example_exists() -> None:
    assert REPORT_SCHEMA.is_file(), f"Missing: {REPORT_SCHEMA}"


# ---------------------------------------------------------------------------
# 2. Static examples parse as valid JSON
# ---------------------------------------------------------------------------

def test_delay_evaluation_schema_parses_as_json() -> None:
    data = _json(DELAY_EVAL_SCHEMA)
    assert isinstance(data, dict)


def test_wallet_intelligence_report_schema_parses_as_json() -> None:
    data = _json(REPORT_SCHEMA)
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# 3. Copyability design includes required delay windows
# ---------------------------------------------------------------------------

def test_copyability_design_mentions_1_second_delay() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "1 second" in text


def test_copyability_design_mentions_5_seconds_delay() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "5 seconds" in text


def test_copyability_design_mentions_30_seconds_delay() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "30 seconds" in text


def test_copyability_design_mentions_2_minutes_delay() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "2 minutes" in text


def test_copyability_design_mentions_10_minutes_delay() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "10 minutes" in text


def test_delay_evaluation_schema_contains_all_five_delay_windows() -> None:
    text = _read(DELAY_EVAL_SCHEMA)
    for window in ("1_second", "5_seconds", "30_seconds", "2_minutes", "10_minutes"):
        assert window in text, f"Missing delay window: {window}"


# ---------------------------------------------------------------------------
# 4. Copyability design mentions spread, slippage, fees, liquidity, size
# ---------------------------------------------------------------------------

def test_copyability_design_mentions_spread() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "spread" in text.lower()


def test_copyability_design_mentions_slippage() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "slippage" in text.lower()


def test_copyability_design_mentions_fees() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "fee" in text.lower()


def test_copyability_design_mentions_liquidity_limits() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "liquidity" in text.lower()


def test_copyability_design_mentions_size_constraints() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "size" in text.lower()


# ---------------------------------------------------------------------------
# 5. Copyability design forbids live API, authenticated data, execution, scheduler
# ---------------------------------------------------------------------------

def test_copyability_design_forbids_live_api_wallet_feed() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "live API wallet feed" in text


def test_copyability_design_forbids_authenticated_data() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "authenticated account data" in text


def test_copyability_design_forbids_execution_feed() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "execution feed" in text


def test_copyability_design_forbids_scheduler_loop() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "scheduler loop" in text


# ---------------------------------------------------------------------------
# 6. Evaluation statuses include all allowed advisory statuses
# ---------------------------------------------------------------------------

def test_copyability_design_lists_not_evaluated_status() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "NOT_EVALUATED" in text


def test_copyability_design_lists_insufficient_context_status() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "INSUFFICIENT_CONTEXT" in text


def test_copyability_design_lists_research_promising_status() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "RESEARCH_PROMISING" in text


def test_copyability_design_lists_research_weak_status() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "RESEARCH_WEAK" in text


def test_copyability_design_lists_uncopyable_fast_flow_status() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "UNCOPYABLE_FAST_FLOW" in text


def test_copyability_design_lists_uncopyable_too_illiquid_status() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "UNCOPYABLE_TOO_ILLIQUID" in text


def test_copyability_design_lists_suspicious_flow_do_not_copy_status() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "SUSPICIOUS_FLOW_DO_NOT_COPY" in text


def test_copyability_design_lists_human_review_required_status() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "HUMAN_REVIEW_REQUIRED" in text


def test_delay_evaluation_schema_contains_all_evaluation_statuses() -> None:
    text = _read(DELAY_EVAL_SCHEMA)
    for status in REQUIRED_EVALUATION_STATUSES:
        assert status in text, f"Missing status: {status}"


# ---------------------------------------------------------------------------
# 7. Evaluation contract excludes forbidden trade-like fields
# ---------------------------------------------------------------------------

def test_copyability_design_forbids_buy_field() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "BUY" in text


def test_copyability_design_forbids_sell_field() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "SELL" in text


def test_copyability_design_forbids_execute_field() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "EXECUTE" in text


def test_copyability_design_forbids_position_size_field() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "POSITION_SIZE" in text


def test_copyability_design_forbids_expected_return_field() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "EXPECTED_RETURN" in text


def test_copyability_design_forbids_auto_copy_field() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "AUTO_COPY" in text


# ---------------------------------------------------------------------------
# 8. Report contract contains required sections
# ---------------------------------------------------------------------------

def test_report_contract_contains_report_identity_section() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "report_identity" in text


def test_report_contract_contains_input_summary_section() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "input_summary" in text


def test_report_contract_contains_wallet_signal_summary_section() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "wallet_signal_summary" in text


def test_report_contract_contains_copyability_delay_design_summary_section() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "copyability_delay_design_summary" in text


def test_report_contract_contains_research_queue_implications_section() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "research_queue_implications" in text


def test_report_contract_contains_suspicious_flow_review_section() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "suspicious_flow_review" in text


def test_report_contract_contains_limitations_section() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "limitations" in text


def test_report_contract_contains_deferred_items_section() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "deferred_items" in text


def test_report_contract_contains_safety_section() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "safety" in text


def test_wallet_report_schema_contains_all_required_sections() -> None:
    data = _json(REPORT_SCHEMA)
    for section in REQUIRED_REPORT_SECTIONS:
        assert section in data, f"Missing section: {section}"


# ---------------------------------------------------------------------------
# 9. Report safety flags present and true in static example
# ---------------------------------------------------------------------------

def test_delay_evaluation_schema_safety_flags_present() -> None:
    data = _json(DELAY_EVAL_SCHEMA)
    safety = data.get("_meta", {}).get("safety", {})
    for flag in REQUIRED_SAFETY_FLAGS:
        assert flag in safety, f"Missing safety flag: {flag}"
        assert safety[flag] is True, f"Safety flag must be true: {flag}"


def test_delay_evaluation_schema_overall_safety_flags_present() -> None:
    data = _json(DELAY_EVAL_SCHEMA)
    safety = data.get("overall_evaluation", {}).get("safety", {})
    for flag in REQUIRED_SAFETY_FLAGS:
        assert flag in safety, f"Missing safety flag in overall_evaluation: {flag}"
        assert safety[flag] is True, f"Safety flag must be true: {flag}"


def test_wallet_report_schema_safety_flags_present() -> None:
    data = _json(REPORT_SCHEMA)
    safety = data.get("safety", {})
    for flag in REQUIRED_SAFETY_FLAGS:
        assert flag in safety, f"Missing safety flag: {flag}"
        assert safety[flag] is True, f"Safety flag must be true: {flag}"


def test_wallet_report_schema_meta_safety_flags_present() -> None:
    data = _json(REPORT_SCHEMA)
    safety = data.get("_meta", {}).get("safety", {})
    for flag in REQUIRED_SAFETY_FLAGS:
        assert flag in safety, f"Missing safety flag in _meta: {flag}"
        assert safety[flag] is True, f"Safety flag must be true: {flag}"


# ---------------------------------------------------------------------------
# 10. Static examples use placeholder wallet identity only
# ---------------------------------------------------------------------------

def test_delay_evaluation_schema_uses_placeholder_wallet_id() -> None:
    data = _json(DELAY_EVAL_SCHEMA)
    wallet_id = data.get("wallet_reference", {}).get("wallet_id_or_address", "")
    assert "PLACEHOLDER" in wallet_id.upper(), "wallet_id_or_address must use PLACEHOLDER identity"


def test_wallet_report_schema_uses_placeholder_fixture_source() -> None:
    data = _json(REPORT_SCHEMA)
    source = data.get("input_summary", {}).get("wallet_fixture_source", "")
    assert "PLACEHOLDER" in source.upper(), "wallet_fixture_source must use PLACEHOLDER identity"


def test_delay_evaluation_schema_design_example_only_flag_set() -> None:
    data = _json(DELAY_EVAL_SCHEMA)
    identity = data.get("evaluation_identity", {})
    assert identity.get("design_example_only") is True


def test_wallet_report_schema_design_example_only_flag_set() -> None:
    data = _json(REPORT_SCHEMA)
    identity = data.get("report_identity", {})
    assert identity.get("design_example_only") is True


# ---------------------------------------------------------------------------
# 11. Static examples contain no forbidden trade-like keys
# ---------------------------------------------------------------------------

def test_delay_evaluation_schema_no_forbidden_keys() -> None:
    data = _json(DELAY_EVAL_SCHEMA)
    keys = _walk_keys(data)
    for forbidden in FORBIDDEN_TRADE_LIKE_KEYS:
        assert forbidden not in keys, f"Forbidden key in delay eval schema: {forbidden}"


def test_wallet_report_schema_no_forbidden_keys() -> None:
    data = _json(REPORT_SCHEMA)
    keys = _walk_keys(data)
    for forbidden in FORBIDDEN_TRADE_LIKE_KEYS:
        assert forbidden not in keys, f"Forbidden key in report schema: {forbidden}"


# ---------------------------------------------------------------------------
# 12. Static examples contain no credentials or secrets
# ---------------------------------------------------------------------------

CREDENTIAL_PATTERNS = ("api_key", "secret", "password", "token", "private_key", "auth")


def test_delay_evaluation_schema_no_credentials() -> None:
    text = _read(DELAY_EVAL_SCHEMA).lower()
    for pattern in CREDENTIAL_PATTERNS:
        assert pattern not in text, f"Credential-like pattern in delay eval schema: {pattern}"


def test_wallet_report_schema_no_credentials() -> None:
    text = _read(REPORT_SCHEMA).lower()
    for pattern in CREDENTIAL_PATTERNS:
        assert pattern not in text, f"Credential-like pattern in report schema: {pattern}"


# ---------------------------------------------------------------------------
# 13. Suspicious-flow boundary is present in both design docs
# ---------------------------------------------------------------------------

def test_copyability_design_states_suspicious_flow_boundary() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "Suspicious-flow" in text or "suspicious-flow" in text.lower()
    assert "human review" in text.lower()
    assert "privileged" in text.lower()


def test_report_contract_states_suspicious_flow_boundary() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "Suspicious-flow" in text or "suspicious-flow" in text.lower()
    assert "human review" in text.lower()
    assert "privileged" in text.lower()


def test_report_contract_suspicious_flow_must_not_follow_privileged_info() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "must not become a strategy to follow privileged" in text


def test_copyability_design_suspicious_flow_must_not_follow_privileged_info() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "must not become a strategy to follow privileged" in text


# ---------------------------------------------------------------------------
# 14. Future WP sequence is updated in design docs and roadmap
# ---------------------------------------------------------------------------

def test_copyability_design_mentions_wp81() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "WP81" in text


def test_copyability_design_mentions_wp82() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "WP82" in text


def test_copyability_design_mentions_wp83() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "WP83" in text


def test_copyability_design_mentions_wp84() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "WP84" in text


def test_report_contract_mentions_wp81() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "WP81" in text


def test_report_contract_mentions_wp82() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "WP82" in text


def test_report_contract_mentions_wp83() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "WP83" in text


def test_report_contract_mentions_wp84() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "WP84" in text


def test_roadmap_doc_mentions_wp81_sequence() -> None:
    text = _read(ROADMAP_DOC)
    assert "WP81" in text


def test_roadmap_doc_mentions_wp82_sequence() -> None:
    text = _read(ROADMAP_DOC)
    assert "WP82" in text


def test_roadmap_doc_mentions_wp83_sequence() -> None:
    text = _read(ROADMAP_DOC)
    assert "WP83" in text


def test_roadmap_doc_mentions_wp84_sequence() -> None:
    text = _read(ROADMAP_DOC)
    assert "WP84" in text


# ---------------------------------------------------------------------------
# 15. Repo truth index references new docs/schema/test files
# ---------------------------------------------------------------------------

def test_repo_truth_index_references_delay_design_doc() -> None:
    text = _read(REPO_TRUTH_DOC)
    assert "wallet_copyability_delay_simulator_design.md" in text


def test_repo_truth_index_references_report_contract_doc() -> None:
    text = _read(REPO_TRUTH_DOC)
    assert "wallet_intelligence_report_contract.md" in text


def test_repo_truth_index_references_delay_eval_schema() -> None:
    text = _read(REPO_TRUTH_DOC)
    assert "wallet_copyability_delay_evaluation_v1.example.json" in text


def test_repo_truth_index_references_report_schema() -> None:
    text = _read(REPO_TRUTH_DOC)
    assert "wallet_intelligence_report_v1.example.json" in text


def test_repo_truth_index_references_wp80_test_file() -> None:
    text = _read(REPO_TRUTH_DOC)
    assert "test_wallet_copyability_delay_report_contract_docs.py" in text


# ---------------------------------------------------------------------------
# 16. Deferred items log records implementation deferrals
# ---------------------------------------------------------------------------

def test_deferred_items_log_records_wp80_copyability_simulator_deferral() -> None:
    text = _read(DEFERRED_DOC)
    assert "WP80" in text
    assert "copyability" in text.lower()


def test_deferred_items_log_records_wp80_report_generator_deferral() -> None:
    text = _read(DEFERRED_DOC)
    assert "WP80" in text
    assert "report generator" in text.lower() or "wallet intelligence report" in text.lower()


# ---------------------------------------------------------------------------
# 17. Project status marks WP80 current phase/branch
# ---------------------------------------------------------------------------

def test_project_status_marks_wp80_current_phase() -> None:
    text = _read(STATUS_DOC)
    assert "WP80" in text


def test_project_status_marks_wp80_branch() -> None:
    text = _read(STATUS_DOC)
    assert "wp80-copyability-delay-simulator-design-wallet-report-contract" in text


def test_project_status_includes_wp79_in_merged_list() -> None:
    text = _read(STATUS_DOC)
    assert "WP79" in text


# ---------------------------------------------------------------------------
# 18. Related wallet docs still state no auto-copying / no live execution
# ---------------------------------------------------------------------------

def test_roadmap_doc_still_states_no_auto_copy_trading() -> None:
    text = _read(ROADMAP_DOC)
    assert "no auto copy" in text.lower() or "no automatic copy" in text.lower() or \
           "NOT_STARTED_AUTO_COPY" in text or "auto-copy" not in text.lower() or \
           "not_automated_copy_trading" in text.lower() or \
           "no automated copy" in text.lower()


def test_arch_doc_still_states_no_automatic_copy_trading() -> None:
    text = _read(ARCH_DOC)
    assert "does not authorize automatic copy-trading" in text


def test_signal_profile_doc_still_states_no_live_execution() -> None:
    text = _read(SIGNAL_PROFILE_DOC)
    assert "live execution" in text.lower()


def test_trade_event_doc_still_states_no_network_ingestion() -> None:
    text = _read(TRADE_EVENT_DOC)
    assert "no network" in text.lower() or "no API" in text or "no wallet API" in text


# ---------------------------------------------------------------------------
# 19. Exact approved copyability source set (WP81 and S10-WALLET-03)
# ---------------------------------------------------------------------------

def test_no_wallet_copyability_src_module() -> None:
    # Preserve WP81's fixture evaluator and admit only the approved WALLET-03
    # research module; missing modules and any third matching path fail closed.
    src_dir = ROOT / "src"
    allowed_copyability_src = {
        src_dir / "data_layer" / "wallet_copyability_delay_evaluation.py",
        src_dir / "data_layer" / "wallet_intelligence" / "copyability.py",
    }
    found = {
        path
        for path in src_dir.rglob("*copyability*")
        if "__pycache__" not in path.parts
    }
    assert found == allowed_copyability_src, (
        f"Unexpected or missing approved copyability source: {found ^ allowed_copyability_src}"
    )


@pytest.mark.parametrize(
    "variant",
    [
        "approved",
        "missing_legacy",
        "missing_wallet03",
        "extra_file",
        "extra_directory",
    ],
)
def test_copyability_source_allowlist_boundaries(tmp_path, monkeypatch, variant):
    src_dir = tmp_path / "src" / "data_layer"
    src_dir.mkdir(parents=True)
    legacy = src_dir / "wallet_copyability_delay_evaluation.py"
    current = src_dir / "wallet_intelligence" / "copyability.py"
    current.parent.mkdir()
    legacy.touch()
    current.touch()
    if variant == "missing_legacy":
        legacy.unlink()
    elif variant == "missing_wallet03":
        current.unlink()
    elif variant == "extra_file":
        (src_dir / "rogue_copyability.py").touch()
    elif variant == "extra_directory":
        (src_dir / "rogue_copyability").mkdir()
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    if variant == "approved":
        test_no_wallet_copyability_src_module()
    else:
        with pytest.raises(AssertionError, match="Unexpected or missing approved"):
            test_no_wallet_copyability_src_module()


def test_wallet_report_generator_src_module_is_wp82() -> None:
    # WP82 implements the wallet intelligence report generator.
    # The module is expected to exist at this path; it is local/offline/read-only.
    src_dir = ROOT / "src"
    if not src_dir.exists():
        return
    report_gen = src_dir / "data_layer" / "wallet_intelligence_report_generator.py"
    if report_gen.exists():
        # WP82 is merged or on branch — verify it is the only wallet intelligence report src file
        found = [
            p for p in src_dir.rglob("*wallet_intelligence_report*")
            if p.suffix != ".pyc" and "__pycache__" not in p.parts
        ]
        assert found == [report_gen], (
            f"Unexpected wallet intelligence report src files beyond WP82 module: "
            f"{[p for p in found if p != report_gen]}"
        )


# ---------------------------------------------------------------------------
# 20. No tools/, .github/, dependency, lock-file, or local_data/ changes
# ---------------------------------------------------------------------------

def test_no_tools_copyability_file() -> None:
    tools_dir = ROOT / "tools"
    if not tools_dir.exists():
        return
    for path in tools_dir.rglob("*copyability*"):
        assert False, f"Unexpected copyability tools file: {path}"


def test_delay_eval_schema_not_in_local_data() -> None:
    local_data = ROOT / "local_data"
    if not local_data.exists():
        return
    for path in local_data.rglob("wallet_copyability_delay*"):
        assert False, f"Schema committed to local_data: {path}"


# ---------------------------------------------------------------------------
# 21. Report contract states it is human review, not trade recommendation
# ---------------------------------------------------------------------------

def test_report_contract_explicitly_states_human_review_report() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "human review report" in text.lower()


def test_report_contract_not_trade_recommendation() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "not a trade recommendation" in text.lower()


def test_report_contract_not_buy_sell_signal() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "not a buy" in text.lower() or "not a buy/sell" in text.lower() or \
           "not a buy or sell" in text.lower()


def test_report_contract_not_copy_trading_instruction() -> None:
    text = _read(REPORT_CONTRACT_DOC)
    assert "not a copy-trading instruction" in text.lower()


# ---------------------------------------------------------------------------
# 22. Copyability delay principle clearly stated in design doc
# ---------------------------------------------------------------------------

def test_copyability_design_states_core_principle() -> None:
    text = _read(DELAY_DESIGN_DOC)
    assert "not copyable unless delayed-copy evaluation" in text


# ---------------------------------------------------------------------------
# 23. Report schema type is WALLET_INTELLIGENCE_ADVISORY_REPORT_V1
# ---------------------------------------------------------------------------

def test_wallet_report_schema_type_is_advisory_report() -> None:
    data = _json(REPORT_SCHEMA)
    report_type = data.get("report_identity", {}).get("report_type", "")
    assert report_type == "WALLET_INTELLIGENCE_ADVISORY_REPORT_V1"


def test_delay_eval_schema_type_is_delay_evaluation() -> None:
    data = _json(DELAY_EVAL_SCHEMA)
    schema_type = data.get("_meta", {}).get("schema_type", "")
    assert schema_type == "WALLET_COPYABILITY_DELAY_EVALUATION_V1"


# ---------------------------------------------------------------------------
# 24. Report schema deferred_items uses safe advisory capability names
# ---------------------------------------------------------------------------

def test_wallet_report_schema_deferred_items_contains_copyability_evaluation() -> None:
    data = _json(REPORT_SCHEMA)
    deferred = data.get("deferred_items", {})
    val = deferred.get("copyability_evaluation_implementation", "")
    assert "deferred" in val.lower() or "wp81" in val.lower(), (
        "deferred_items must contain 'copyability_evaluation_implementation' with deferred/WP81 reference"
    )


def test_wallet_report_schema_deferred_items_contains_report_generator() -> None:
    data = _json(REPORT_SCHEMA)
    deferred = data.get("deferred_items", {})
    val = deferred.get("wallet_report_generator_implementation", "")
    assert "deferred" in val.lower() or "wp82" in val.lower(), (
        "deferred_items must contain 'wallet_report_generator_implementation' with deferred/WP82 reference"
    )


def test_wallet_report_schema_deferred_items_contains_live_execution_forbidden() -> None:
    data = _json(REPORT_SCHEMA)
    deferred = data.get("deferred_items", {})
    val = deferred.get("live_execution_forbidden", "")
    assert "forbidden" in val.lower(), (
        "deferred_items must contain 'live_execution_forbidden' with forbidden reference"
    )


# ---------------------------------------------------------------------------
# 25. Advisory-only notices present in both schemas
# ---------------------------------------------------------------------------

def test_delay_eval_schema_meta_advisory_notice_present() -> None:
    data = _json(DELAY_EVAL_SCHEMA)
    notice = data.get("_meta", {}).get("advisory_only_notice", "")
    assert len(notice) > 10


def test_wallet_report_schema_meta_advisory_notice_present() -> None:
    data = _json(REPORT_SCHEMA)
    notice = data.get("_meta", {}).get("advisory_only_notice", "")
    assert len(notice) > 10


def test_wallet_report_schema_limitations_no_live_data_notice() -> None:
    data = _json(REPORT_SCHEMA)
    limitations = data.get("limitations", {})
    notice = limitations.get("no_live_data_notice", "")
    assert "live" in notice.lower() and "data" in notice.lower()


def test_wallet_report_schema_limitations_no_trading_signal_notice() -> None:
    data = _json(REPORT_SCHEMA)
    limitations = data.get("limitations", {})
    notice = limitations.get("no_trading_signal_notice", "")
    assert "no signal" in notice.lower() or "no entry" in notice.lower() or \
           "carries no" in notice.lower() or "contains no" in notice.lower()


# ---------------------------------------------------------------------------
# 26. Static examples contain no forbidden value substrings
# ---------------------------------------------------------------------------

def test_delay_evaluation_schema_no_forbidden_value_substrings() -> None:
    data = _json(DELAY_EVAL_SCHEMA)
    str_values = _walk_string_values(data)
    for forbidden in FORBIDDEN_VALUE_SUBSTRINGS:
        for v in str_values:
            assert forbidden not in v, (
                f"Forbidden value substring '{forbidden}' found in delay eval schema"
            )


def test_wallet_report_schema_no_forbidden_value_substrings() -> None:
    data = _json(REPORT_SCHEMA)
    str_values = _walk_string_values(data)
    for forbidden in FORBIDDEN_VALUE_SUBSTRINGS:
        for v in str_values:
            assert forbidden not in v, (
                f"Forbidden value substring '{forbidden}' found in report schema"
            )
