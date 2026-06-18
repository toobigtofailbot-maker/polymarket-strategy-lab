"""
Focused docs/schema tests for WP83 wallet signal paper strategy contract.

Requirement-to-test mapping:
  JSON parses                       -> test_example_json_parses
  Required sections exist           -> test_required_sections_present
  Safety flags all true             -> test_safety_flags_all_true
  Allowed statuses only             -> test_allowed_statuses_only
  Forbidden statuses absent         -> test_forbidden_statuses_absent
  Recursive JSON key/value scan     -> test_json_has_no_forbidden_output_terms_recursive
  Markdown forbidden terms isolated -> test_markdown_forbidden_terms_only_in_ban_list
  No raw metadata policy            -> test_contract_forbids_raw_metadata_passthrough
  Precedence table present          -> test_safety_precedence_table_present
  Deferred items present            -> test_deferred_items_present
  Placeholder-only identifiers      -> test_static_example_uses_placeholders_only
  No src/ implementation files      -> test_no_src_implementation_for_wp83_contract
  Repo truth updated                -> test_repo_truth_index_references_wp83_docs
  Project status updated            -> test_project_status_reflects_wp83
  Deferred items log updated        -> test_deferred_items_log_resolves_wp83_items
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = ROOT / "docs" / "wallet_signal_paper_strategy_contract.md"
CONTRACT_SCHEMA = ROOT / "docs" / "schemas" / "wallet_signal_paper_strategy_contract_v1.example.json"
STATUS_DOC = ROOT / "docs" / "project_status.md"
REPO_TRUTH_DOC = ROOT / "docs" / "repo_truth_index.md"
DEFERRED_DOC = ROOT / "docs" / "deferred_items_log.md"


REQUIRED_CONTRACT_SECTIONS = (
    "contract_identity",
    "source_report_reference",
    "source_signal_context",
    "copyability_delay_context",
    "eligibility_review",
    "suspicious_flow_review",
    "insufficient_context_review",
    "human_review",
    "deferred_items",
    "safety",
    "warnings",
    "advisory_notice",
)

ALLOWED_ELIGIBILITY_STATUSES = frozenset({
    "NOT_ELIGIBLE_INSUFFICIENT_CONTEXT",
    "NOT_ELIGIBLE_SUSPICIOUS_FLOW",
    "NOT_ELIGIBLE_SAFETY_FLAG_FAILURE",
    "HUMAN_REVIEW_REQUIRED",
    "RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN",
})

FORBIDDEN_ELIGIBILITY_STATUSES = frozenset({
    "TRADE_READY",
    "COPY_READY",
    "LIVE_READY",
    "ORDER_READY",
    "EXECUTION_READY",
    "BUY_SIGNAL",
    "SELL_SIGNAL",
    "AUTO_APPROVED",
})

REQUIRED_SAFETY_FLAGS = (
    "manual_research_only",
    "not_automated_copy_trading",
    "no_live_execution",
    "no_order_placement",
    "no_position_sizing",
    "no_risk_override",
    "no_parameter_auto_change",
    "no_paper_engine_created",
    "no_account_action",
)

# Allowed safety-flag exception key names: these exact keys may contain
# fragments of forbidden terms and are skipped during key scanning.
ALLOWED_SAFETY_FLAG_EXCEPTION_KEYS: frozenset[str] = frozenset({
    "not_automated_copy_trading",
    "no_live_execution",
    "no_order_placement",
    "no_position_sizing",
})

# Forbidden terms in normalized form (lowercase, underscores/hyphens → spaces).
# Used for recursive JSON key and value scanning.
FORBIDDEN_TERMS_NORMALIZED = (
    "buy",
    "sell",
    "trade",
    "trading",
    "execute",
    "execution",
    "order ready",
    "execution ready",
    "entry",
    "exit",
    "position size",
    "position sizing",
    "expected return",
    "profit target",
    "stop loss",
    "take profit",
    "live signal",
    "auto copy",
    "automatic copy",
    "copy signal",
    "wallet copy instruction",
    "pnl target",
    "paper trading candidate",
    "strategy signal",
)

# Reviewer-trap JSON patterns that must appear only in the ban-list section
# of the markdown contract.
FORBIDDEN_CODE_PATTERNS_IN_MARKDOWN = (
    '"execution_ready"',
    '"order_ready"',
    '"buy_signal"',
    '"sell_signal"',
    '"paper_trading_candidate"',
    '"strategy_signal"',
    '"expected_return"',
    '"position_size"',
    '"live_signal"',
    '"auto_copy"',
    "TRADE_READY",
    "BUY_SIGNAL",
    "SELL_SIGNAL",
    "EXECUTION_READY",
    "COPY_READY",
    "LIVE_READY",
    "ORDER_READY",
    "AUTO_APPROVED",
)

BAN_LIST_SECTION_MARKER = "## 12. Normative Forbidden Output Term Ban List"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> Any:
    return json.loads(_read(path))


def _normalize(s: str) -> str:
    return s.lower().replace("_", " ").replace("-", " ")


def _collect_forbidden_violations(
    value: Any,
    path: str = "",
    violations: list[str] | None = None,
) -> list[str]:
    """Recursively scan JSON value for forbidden output terms.

    Keys in ALLOWED_SAFETY_FLAG_EXCEPTION_KEYS are exempt from the key scan.
    All string values are scanned without exception.
    """
    if violations is None:
        violations = []
    if isinstance(value, dict):
        for k, v in value.items():
            current_path = f"{path}.{k}" if path else k
            # Check key — skip exact safety flag exception keys
            if k not in ALLOWED_SAFETY_FLAG_EXCEPTION_KEYS:
                norm_k = _normalize(str(k))
                for term in FORBIDDEN_TERMS_NORMALIZED:
                    if term in norm_k:
                        violations.append(
                            f"Forbidden term '{term}' in key '{k}' at {current_path}"
                        )
                        break
            _collect_forbidden_violations(v, current_path, violations)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _collect_forbidden_violations(item, f"{path}[{i}]", violations)
    elif isinstance(value, str):
        norm_v = _normalize(value)
        for term in FORBIDDEN_TERMS_NORMALIZED:
            if term in norm_v:
                violations.append(
                    f"Forbidden term '{term}' in value '{value[:80]}' at {path}"
                )
                break
    return violations


def _collect_all_eligibility_statuses(value: Any, found: set[str] | None = None) -> set[str]:
    """Recursively collect all string values that look like eligibility statuses."""
    if found is None:
        found = set()
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "eligibility_status" and isinstance(v, str):
                found.add(v)
            _collect_all_eligibility_statuses(v, found)
    elif isinstance(value, list):
        for item in value:
            _collect_all_eligibility_statuses(item, found)
    return found


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------


def test_contract_doc_exists() -> None:
    assert CONTRACT_DOC.is_file(), f"Missing: {CONTRACT_DOC}"


def test_contract_schema_exists() -> None:
    assert CONTRACT_SCHEMA.is_file(), f"Missing: {CONTRACT_SCHEMA}"


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------


def test_example_json_parses() -> None:
    data = _json(CONTRACT_SCHEMA)
    assert isinstance(data, dict)
    assert len(data) > 0


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------


def test_required_sections_present() -> None:
    data = _json(CONTRACT_SCHEMA)
    missing = [s for s in REQUIRED_CONTRACT_SECTIONS if s not in data]
    assert missing == [], f"Missing required sections in JSON example: {missing}"


def test_required_sections_in_markdown() -> None:
    text = _read(CONTRACT_DOC)
    for section in REQUIRED_CONTRACT_SECTIONS:
        assert section in text, f"Required section '{section}' not mentioned in contract doc"


# ---------------------------------------------------------------------------
# Safety flags
# ---------------------------------------------------------------------------


def test_safety_flags_all_true() -> None:
    data = _json(CONTRACT_SCHEMA)
    safety = data.get("safety", {})
    for flag in REQUIRED_SAFETY_FLAGS:
        assert flag in safety, f"Safety flag '{flag}' missing from safety section"
        assert safety[flag] is True, f"Safety flag '{flag}' must be true, got {safety[flag]}"


def test_meta_safety_flags_all_true() -> None:
    data = _json(CONTRACT_SCHEMA)
    meta_safety = data.get("_meta", {}).get("safety", {})
    for flag in REQUIRED_SAFETY_FLAGS:
        assert flag in meta_safety, f"Safety flag '{flag}' missing from _meta.safety"
        assert meta_safety[flag] is True, f"_meta safety flag '{flag}' must be true"


def test_contract_doc_lists_all_safety_flags() -> None:
    text = _read(CONTRACT_DOC)
    for flag in REQUIRED_SAFETY_FLAGS:
        assert flag in text, f"Safety flag '{flag}' not found in contract doc"


# ---------------------------------------------------------------------------
# Eligibility statuses
# ---------------------------------------------------------------------------


def test_allowed_statuses_only() -> None:
    data = _json(CONTRACT_SCHEMA)
    found_statuses = _collect_all_eligibility_statuses(data)
    disallowed = found_statuses - ALLOWED_ELIGIBILITY_STATUSES
    assert not disallowed, f"Disallowed eligibility statuses found: {disallowed}"


def test_forbidden_statuses_absent() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data)
    for status in FORBIDDEN_ELIGIBILITY_STATUSES:
        assert status not in json_text, (
            f"Forbidden eligibility status '{status}' found in JSON example"
        )


def test_allowed_statuses_listed_in_contract_doc() -> None:
    text = _read(CONTRACT_DOC)
    for status in ALLOWED_ELIGIBILITY_STATUSES:
        assert status in text, f"Allowed status '{status}' not listed in contract doc"


# ---------------------------------------------------------------------------
# Recursive JSON forbidden-term scan (Requirement: test_json_has_no_forbidden_output_terms_recursive)
# ---------------------------------------------------------------------------


def test_json_has_no_forbidden_output_terms_recursive() -> None:
    data = _json(CONTRACT_SCHEMA)
    violations = _collect_forbidden_violations(data)
    assert violations == [], (
        f"Forbidden output terms found in JSON example:\n" + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Forbidden variant matrix (Section 9 reviewer trap tests)
# ---------------------------------------------------------------------------


def test_no_buy_sell_variants_in_json() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data).lower()
    for term in ("buy_signal", "sell_signal"):
        assert term not in json_text, f"Forbidden variant '{term}' in JSON example"


def test_no_execution_variants_in_json() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data).lower()
    for term in ("execution_ready", "order_ready"):
        assert term not in json_text, f"Forbidden variant '{term}' in JSON example"


def test_no_position_sizing_variants_in_json() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data).lower()
    for term in ("position_size", "sizing_input"):
        assert term not in json_text, f"Forbidden variant '{term}' in JSON example"


def test_no_expected_return_variants_in_json() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data).lower()
    for term in ("expected_return", "performance_estimate"):
        assert term not in json_text, f"Forbidden variant '{term}' in JSON example"


def test_no_risk_target_variants_in_json() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data).lower()
    for term in ("profit_target", "stop_loss", "take_profit", "pnl_target"):
        assert term not in json_text, f"Forbidden variant '{term}' in JSON example"


def test_no_auto_behavior_variants_in_json() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data).lower()
    for term in ("auto_copy", "copy_signal"):
        assert term not in json_text, f"Forbidden variant '{term}' in JSON example"


def test_no_strategy_leak_variants_in_json() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data).lower()
    for term in ("strategy_signal", "paper_trading_candidate"):
        assert term not in json_text, f"Forbidden variant '{term}' in JSON example"


def test_no_live_leak_variants_in_json() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data).lower()
    for term in ("live_signal", "live_ready"):
        assert term not in json_text, f"Forbidden variant '{term}' in JSON example"


# ---------------------------------------------------------------------------
# Markdown forbidden terms isolated to ban-list section
# ---------------------------------------------------------------------------


def test_ban_list_section_exists_in_markdown() -> None:
    text = _read(CONTRACT_DOC)
    assert BAN_LIST_SECTION_MARKER in text, (
        f"Ban-list section marker not found in contract doc: '{BAN_LIST_SECTION_MARKER}'"
    )


def test_markdown_forbidden_terms_only_in_ban_list() -> None:
    text = _read(CONTRACT_DOC)
    assert BAN_LIST_SECTION_MARKER in text, "Ban-list section marker not found"
    ban_list_start = text.index(BAN_LIST_SECTION_MARKER)
    pre_ban_list = text[:ban_list_start]

    violations = []
    for pattern in FORBIDDEN_CODE_PATTERNS_IN_MARKDOWN:
        if pattern in pre_ban_list:
            violations.append(pattern)
    assert not violations, (
        f"Forbidden patterns found outside ban-list section: {violations}"
    )


# ---------------------------------------------------------------------------
# Raw metadata policy
# ---------------------------------------------------------------------------


def test_contract_forbids_raw_metadata_passthrough() -> None:
    text = _read(CONTRACT_DOC)
    assert "raw" in text.lower(), "Contract doc must mention raw metadata policy"
    assert "metadata" in text.lower(), "Contract doc must mention raw metadata policy"
    assert "forbidden" in text.lower() or "must not" in text.lower(), (
        "Contract doc must explicitly forbid raw metadata pass-through"
    )


def test_json_example_has_no_generic_metadata_key() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data).lower()
    assert '"metadata"' not in json_text, (
        "JSON example must not contain a generic 'metadata' key (raw metadata pass-through is forbidden)"
    )


# ---------------------------------------------------------------------------
# Safety precedence table
# ---------------------------------------------------------------------------


def test_safety_precedence_table_present() -> None:
    text = _read(CONTRACT_DOC)
    assert "NOT_ELIGIBLE_INSUFFICIENT_CONTEXT" in text
    assert "NOT_ELIGIBLE_SUSPICIOUS_FLOW" in text
    assert "NOT_ELIGIBLE_SAFETY_FLAG_FAILURE" in text
    assert "HUMAN_REVIEW_REQUIRED" in text
    assert "RESEARCH_ONLY_ELIGIBLE_FOR_FUTURE_PAPER_DESIGN" in text


def test_safety_precedence_table_has_human_review_column() -> None:
    text = _read(CONTRACT_DOC)
    assert "Human Review" in text or "human_review" in text.lower()


def test_blocking_gate_precedence_section_present() -> None:
    text = _read(CONTRACT_DOC)
    assert "Blocking Gate Precedence" in text or "blocking" in text.lower()
    assert "source_report_reference" in text
    assert "suspicious_flow" in text or "suspicious flow" in text.lower()
    assert "copyability_delay_context" in text or "copyability delay" in text.lower()


# ---------------------------------------------------------------------------
# Deferred items
# ---------------------------------------------------------------------------


def test_deferred_items_present() -> None:
    data = _json(CONTRACT_SCHEMA)
    deferred = data.get("deferred_items", {})
    assert len(deferred) > 0, "deferred_items section must not be empty"


def test_deferred_items_in_markdown() -> None:
    text = _read(CONTRACT_DOC)
    assert "Deferred Items" in text
    # These must be listed as deferred in the contract
    for item in (
        "paper_strategy_implementation",
        "paper_order_model",
        "paper_portfolio_ledger",
        "paper_fill_model",
        "paper_pnl_computation",
        "network_wallet_ingestion",
        "real_wallet_monitoring",
    ):
        assert item in text or item.replace("_", " ") in text.lower(), (
            f"Deferred item '{item}' not mentioned in contract doc"
        )


# ---------------------------------------------------------------------------
# Placeholder-only identifiers
# ---------------------------------------------------------------------------


def test_static_example_uses_placeholders_only() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data)
    for placeholder in ("wallet_placeholder_001", "market_placeholder_001", "condition_placeholder_001"):
        assert placeholder in json_text, f"Expected placeholder '{placeholder}' not found in JSON example"


def test_no_real_wallet_address_in_json() -> None:
    data = _json(CONTRACT_SCHEMA)
    json_text = json.dumps(data)
    # Real wallet addresses are hex strings starting with 0x; no real addresses should appear
    assert "0x" not in json_text.lower(), "JSON example must not contain real wallet addresses (0x prefix)"


def test_source_reference_advisory_present() -> None:
    data = _json(CONTRACT_SCHEMA)
    ref = data.get("source_report_reference", {})
    assert "source_reference_advisory" in ref, "source_report_reference must include source_reference_advisory"


# ---------------------------------------------------------------------------
# No src/ implementation files for WP83
# ---------------------------------------------------------------------------


def test_no_src_implementation_for_wp83_contract() -> None:
    """WP83 is docs/schema/tests-only. No paper strategy contract implementation
    may exist in src/ beyond the WP84 local validator.

    WP84 adds the local/offline/read-only validator at
    src/data_layer/wallet_signal_paper_strategy_contract_validator.py.
    This file is explicitly allowed; all other paper strategy contract
    implementation files remain forbidden.
    """
    src = ROOT / "src"
    # WP84 local validator and WP87 fixture loader are the only permitted implementation files
    _wp84_validator_name = "wallet_signal_paper_strategy_contract_validator.py"
    _wp87_loader_name = "wallet_signal_paper_strategy_candidate_fixture_loader.py"
    _allowed_wallet_paper_strategy_src = frozenset({_wp84_validator_name, _wp87_loader_name})
    forbidden_names = (
        "paper_strategy_contract",
        "paper_strategy_engine",
        "paper_order",
        "paper_portfolio",
        "paper_fill",
    )
    violations = []
    for path in src.rglob("*.py"):
        # Allow the WP84 validator and WP87 fixture loader
        if path.name in _allowed_wallet_paper_strategy_src:
            continue
        for name in forbidden_names:
            if name in path.name.lower():
                violations.append(str(path.relative_to(ROOT)))
        # wallet_signal_paper_strategy prefix is only allowed for the two permitted files
        if (
            "wallet_signal_paper_strategy" in path.name.lower()
            and path.name not in _allowed_wallet_paper_strategy_src
        ):
            violations.append(str(path.relative_to(ROOT)))
    assert violations == [], (
        f"WP83 is docs-only but found unexpected implementation files: {violations}"
    )


def test_wp84_validator_file_exists() -> None:
    """WP84 adds the local/offline/read-only contract validator."""
    validator = ROOT / "src" / "data_layer" / "wallet_signal_paper_strategy_contract_validator.py"
    assert validator.is_file(), (
        f"WP84 validator not found at expected path: {validator}"
    )


def test_wp84_focused_tests_exist() -> None:
    """WP84 adds focused tests for the contract validator."""
    test_file = ROOT / "tests" / "test_wallet_signal_paper_strategy_contract_validator.py"
    assert test_file.is_file(), (
        f"WP84 focused tests not found at expected path: {test_file}"
    )


# ---------------------------------------------------------------------------
# Repo truth updated
# ---------------------------------------------------------------------------


def test_repo_truth_index_references_wp83_docs() -> None:
    text = _read(REPO_TRUTH_DOC)
    assert "wallet_signal_paper_strategy_contract.md" in text, (
        "repo_truth_index.md must reference the WP83 contract doc"
    )
    assert "wallet_signal_paper_strategy_contract_v1.example.json" in text, (
        "repo_truth_index.md must reference the WP83 schema example"
    )
    assert "test_wallet_signal_paper_strategy_contract_docs.py" in text, (
        "repo_truth_index.md must reference the WP83 focused test file"
    )


# ---------------------------------------------------------------------------
# Project status updated
# ---------------------------------------------------------------------------


def test_project_status_reflects_wp83() -> None:
    text = _read(STATUS_DOC)
    assert "WP83" in text, "project_status.md must mention WP83"


def test_project_status_wp82_in_merged_wps() -> None:
    text = _read(STATUS_DOC)
    merged_line = next(
        (l for l in text.splitlines() if l.startswith("- Merged WPs:")), None
    )
    assert merged_line is not None, "project_status.md must have a Merged WPs line"
    assert "WP82" in merged_line, "WP82 must be in Merged WPs list"


def test_project_status_wallet_paper_strategy_contract_status() -> None:
    text = _read(STATUS_DOC)
    assert "wallet signal paper strategy contract" in text.lower() or (
        "WALLET_SIGNAL_PAPER_STRATEGY_CONTRACT" in text
    ), "project_status.md must reference wallet signal paper strategy contract status"


def test_project_status_live_trading_disabled() -> None:
    text = _read(STATUS_DOC)
    assert "Live trading status: DISABLED" in text


def test_project_status_credentials_not_used() -> None:
    text = _read(STATUS_DOC)
    assert "Credentials status: NOT_USED" in text


# ---------------------------------------------------------------------------
# Deferred items log updated
# ---------------------------------------------------------------------------


def test_deferred_items_log_resolves_wp83_items() -> None:
    text = _read(DEFERRED_DOC)
    assert "WP83" in text, "deferred_items_log.md must mention WP83"
    assert "WP80-D003" in text, "deferred_items_log.md must mention WP80-D003"
    assert "WP81-D002" in text, "deferred_items_log.md must mention WP81-D002"
    assert "WP82-D001" in text, "deferred_items_log.md must mention WP82-D001"


def test_deferred_items_log_marks_paper_strategy_contract_resolved() -> None:
    text = _read(DEFERRED_DOC)
    # The paper strategy contract deferred items should now be marked RESOLVED
    # for contract-definition scope (WP80-D003, WP81-D002, WP82-D001)
    assert "RESOLVED" in text
    assert "contract-definition scope" in text or "contract definition scope" in text.lower()


# ---------------------------------------------------------------------------
# Contract doc advisory purpose statement
# ---------------------------------------------------------------------------


def test_contract_doc_states_advisory_research_only() -> None:
    text = _read(CONTRACT_DOC)
    assert "advisory research queue records only" in text or (
        "advisory" in text and "research queue" in text
    )
    assert "not a strategy instruction" in text.lower() or (
        "not strategy instructions" in text.lower()
    )


def test_contract_doc_states_no_implementation_authorized() -> None:
    text = _read(CONTRACT_DOC)
    assert "does not authorize" in text.lower() or "not authorize" in text.lower()


def test_contract_doc_states_human_review_required() -> None:
    text = _read(CONTRACT_DOC)
    assert "human review" in text.lower() and "required" in text.lower()


# ---------------------------------------------------------------------------
# Protected boundaries unchanged
# ---------------------------------------------------------------------------


def test_live_trading_still_disabled() -> None:
    text = _read(ROOT / "docs" / "live_trading_authorization.md")
    assert "LIVE TRADING STATUS: DISABLED" in text
    assert "LIVE TRADING STATUS: ENABLED" not in text


def test_no_new_dependency_files() -> None:
    assert not (ROOT / "requirements_wp83.txt").exists()
    assert not (ROOT / "pyproject_wp83.toml").exists()
