"""Focused docs/schema tests for WP77 wallet intelligence contracts."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARCH_DOC = ROOT / "docs" / "wallet_intelligence_architecture_and_signal_contract.md"
PROFILE_SCHEMA = ROOT / "docs" / "schemas" / "wallet_intelligence_profile_v1.example.json"
SIGNAL_SCHEMA = ROOT / "docs" / "schemas" / "wallet_intelligence_signal_contract_v1.example.json"
STATUS_DOC = ROOT / "docs" / "project_status.md"
REPO_TRUTH_DOC = ROOT / "docs" / "repo_truth_index.md"
DEFERRED_DOC = ROOT / "docs" / "deferred_items_log.md"

SAFETY_FLAGS = (
    "manual_research_only",
    "not_automated_copy_trading",
    "no_live_execution",
    "no_order_placement",
    "no_position_sizing",
    "no_risk_override",
    "no_parameter_auto_change",
)

FORBIDDEN_EXACT_KEYS = {
    "buy",
    "sell",
    "entry",
    "exit",
    "position_size",
    "expected_return",
    "profit_target",
    "stop_loss",
    "take_profit",
    "live_signal",
    "execute",
    "auto_copy",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict[str, Any]:
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


def test_architecture_doc_exists() -> None:
    assert ARCH_DOC.is_file()


def test_profile_example_schema_exists() -> None:
    assert PROFILE_SCHEMA.is_file()


def test_signal_contract_example_schema_exists() -> None:
    assert SIGNAL_SCHEMA.is_file()


def test_architecture_doc_states_advisory_research_only() -> None:
    text = _read(ARCH_DOC)
    assert "advisory research-signal architecture" in text
    assert "does not authorize automatic copy-trading" in text
    assert "explicit-path loader" in text
    assert "fetches network data" in text


def test_architecture_doc_forbids_direct_protected_connections() -> None:
    text = _read(ARCH_DOC)
    for phrase in (
        "credentials",
        "authenticated account endpoints",
        "order placement",
        "order cancellation",
        "position sizing",
        "risk override",
        "live execution",
    ):
        assert phrase in text


def test_architecture_doc_defines_registry_concept() -> None:
    text = _read(ARCH_DOC)
    assert "future wallet registry" in text
    assert "classifies wallets for research review" in text


def test_architecture_doc_lists_allowed_registry_statuses() -> None:
    text = _read(ARCH_DOC)
    for status in (
        "ACTIVE_RESEARCH_WATCH",
        "WATCH_ONLY_LOW_SAMPLE",
        "WATCH_ONLY_UNCOPYABLE",
        "WATCH_ONLY_SUSPICIOUS_FLOW",
        "DEPRECATED_DO_NOT_USE",
    ):
        assert status in text


def test_architecture_doc_lists_forbidden_registry_statuses() -> None:
    text = _read(ARCH_DOC)
    for status in (
        "AUTO_COPY",
        "LIVE_TRADE",
        "EXECUTE",
        "POSITION_SIZE_FROM_WALLET",
        "RISK_OVERRIDE_FROM_WALLET",
    ):
        assert status in text


def test_architecture_doc_defines_profile_field_groups() -> None:
    text = _read(ARCH_DOC)
    for group in (
        "identity",
        "sample_size",
        "profitability",
        "specialization",
        "entry_quality",
        "copyability",
        "risk",
        "signal_policy",
        "review",
        "safety",
    ):
        assert f"`{group}`" in text
    assert "Raw PnL is not enough" in text


def test_architecture_doc_defines_signal_fields() -> None:
    text = _read(ARCH_DOC)
    for field in (
        "signal_id",
        "wallet_id_or_address",
        "market_id",
        "condition_id",
        "observed_at_utc",
        "signal_category",
        "market_category",
        "wallet_specialization_match",
        "direction_observed",
        "entry_price_observed",
        "size_observed",
        "liquidity_context_available",
        "copyability_context_available",
        "suspicious_flow_flag",
        "human_review_required",
        "research_priority_effect",
        "advisory_only_notice",
    ):
        assert f"`{field}`" in text
    assert "must not be interpreted as a buy/sell instruction" in text


def test_architecture_doc_lists_allowed_signal_categories() -> None:
    text = _read(ARCH_DOC)
    for category in (
        "SPECIALIST_ENTRY",
        "MULTI_WALLET_CLUSTER",
        "EARLY_ENTRY_BEFORE_PRICE_MOVE",
        "LATE_CHASER",
        "MARKET_MAKER_FLOW",
        "ARBITRAGE_FLOW",
        "SUSPICIOUS_TIMING",
        "LOW_SAMPLE_OUTLIER",
        "UNCOPYABLE_FAST_FLOW",
    ):
        assert category in text


def test_architecture_doc_lists_allowed_research_priority_effects() -> None:
    text = _read(ARCH_DOC)
    for effect in (
        "NO_CHANGE",
        "LOW_RESEARCH_BOOST",
        "MEDIUM_RESEARCH_BOOST",
        "HIGH_RESEARCH_BOOST",
        "CAP_RESEARCH_PRIORITY",
        "REQUIRE_HUMAN_REVIEW",
        "BLOCK_FROM_AUTOMATION",
    ):
        assert effect in text


def test_architecture_doc_lists_forbidden_trade_like_values() -> None:
    text = _read(ARCH_DOC)
    for value in (
        "BUY",
        "SELL",
        "TRADE",
        "EXECUTE",
        "OPEN_POSITION",
        "CLOSE_POSITION",
        "POSITION_SIZE",
        "EXPECTED_RETURN",
        "PROFIT_TARGET",
        "STOP_LOSS",
        "LIVE_SIGNAL",
        "AUTO_COPY",
    ):
        assert value in text


def test_architecture_doc_lists_allowed_copyability_statuses() -> None:
    text = _read(ARCH_DOC)
    for status in (
        "NOT_EVALUATED",
        "COPYABILITY_UNPROVEN",
        "COPYABILITY_RESEARCH_PROMISING",
        "COPYABILITY_PAPER_ELIGIBLE",
        "UNCOPYABLE_FAST_FLOW",
        "UNCOPYABLE_TOO_ILLIQUID",
        "UNCOPYABLE_TOO_LATE",
        "SUSPICIOUS_FLOW_DO_NOT_COPY",
    ):
        assert status in text
    assert "No status may imply current live permission" in text


def test_architecture_doc_includes_suspicious_flow_boundary() -> None:
    text = _read(ARCH_DOC)
    assert "suspicious timing" in text
    assert "research-watch-only" in text
    assert "must not build a strategy" in text
    assert "privileged-information flow" in text


def test_architecture_doc_includes_safety_flags() -> None:
    text = _read(ARCH_DOC)
    for flag in SAFETY_FLAGS:
        assert flag in text


def test_architecture_doc_includes_future_wp_sequence_wp78_wp82() -> None:
    text = _read(ARCH_DOC)
    for wp in ("WP78", "WP79", "WP80", "WP81", "WP82"):
        assert wp in text


def test_profile_example_has_required_top_level_sections() -> None:
    data = _json(PROFILE_SCHEMA)
    for section in (
        "_notice",
        "_schema_version",
        "_status",
        "identity",
        "sample_size",
        "profitability",
        "specialization",
        "entry_quality",
        "copyability",
        "risk",
        "signal_policy",
        "review",
        "safety",
    ):
        assert section in data
    assert data["_notice"] == "ADVISORY_ONLY_WALLET_INTELLIGENCE_PROFILE"
    assert data["_schema_version"] == "WALLET_INTELLIGENCE_PROFILE_V1"
    assert data["_status"] == "DESIGN_EXAMPLE_ONLY"


def test_profile_example_uses_placeholder_wallet_identity_only() -> None:
    data = _json(PROFILE_SCHEMA)
    assert data["identity"]["wallet_id_or_address"] == "0x0000000000000000000000000000000000000000"


def test_profile_example_has_safety_flags_all_true() -> None:
    safety = _json(PROFILE_SCHEMA)["safety"]
    for flag in SAFETY_FLAGS:
        assert safety.get(flag) is True


def test_profile_example_does_not_contain_forbidden_trade_like_keys() -> None:
    keys = set(_walk_keys(_json(PROFILE_SCHEMA)))
    assert keys.isdisjoint(FORBIDDEN_EXACT_KEYS)


def test_signal_example_has_required_top_level_sections() -> None:
    data = _json(SIGNAL_SCHEMA)
    for section in (
        "_notice",
        "_schema_version",
        "_status",
        "signal",
        "wallet_reference",
        "market_reference",
        "observation",
        "classification",
        "research_priority_effect",
        "copyability_context",
        "safety",
    ):
        assert section in data
    assert data["_notice"] == "ADVISORY_ONLY_WALLET_INTELLIGENCE_SIGNAL"
    assert data["_schema_version"] == "WALLET_INTELLIGENCE_SIGNAL_CONTRACT_V1"
    assert data["_status"] == "DESIGN_EXAMPLE_ONLY"


def test_signal_example_has_safety_flags_all_true() -> None:
    safety = _json(SIGNAL_SCHEMA)["safety"]
    for flag in SAFETY_FLAGS:
        assert safety.get(flag) is True


def test_signal_example_does_not_contain_forbidden_trade_like_keys() -> None:
    keys = set(_walk_keys(_json(SIGNAL_SCHEMA)))
    assert keys.isdisjoint(FORBIDDEN_EXACT_KEYS)


def test_signal_example_states_direction_observed_is_not_buy_sell_instruction() -> None:
    data = _json(SIGNAL_SCHEMA)
    notice = data["signal"]["direction_observed_notice"]
    assert "historical behavior only" in notice
    assert "not a buy/sell instruction" in notice


def test_repo_truth_index_references_new_docs_schema_test_files() -> None:
    text = _read(REPO_TRUTH_DOC)
    for path in (
        "docs/wallet_intelligence_architecture_and_signal_contract.md",
        "docs/schemas/wallet_intelligence_profile_v1.example.json",
        "docs/schemas/wallet_intelligence_signal_contract_v1.example.json",
        "tests/test_wallet_intelligence_architecture_contract_docs.py",
    ):
        assert path in text


def test_deferred_items_log_contains_wp77_deferred_items() -> None:
    text = _read(DEFERRED_DOC)
    for item_id in (
        "WP77-D001",
        "WP77-D002",
        "WP77-D003",
        "WP77-D004",
        "WP77-D005",
        "WP77-D006",
        "WP77-D007",
        "WP77-D008",
    ):
        assert item_id in text


def test_project_status_marks_wp79_current_branch_phase() -> None:
    text = _read(STATUS_DOC)
    current_phase = next(line for line in text.splitlines() if line.startswith("- Current phase:"))
    assert any(wp in current_phase for wp in ("WP79", "WP80", "WP81", "WP82", "WP83", "WP84", "WP86", "WP87", "WP88", "WP89", "WP90", "WP91", "WP92", "WP93", "WP94", "WP95", "WP96", "WP97", "WP98", "WP99", "WP100", "WP101", "WP102", "WP103", "WP104", "WP105", "WP106", "WP107", "WP108", "WP109", "WP125", "WP128", "WP130", "WP138", "WP139", "WP149"))
    # wp79 branch or later still referenced somewhere in the document
    assert any(s in text for s in (
        "wp79-wallet-skill-niche-profiler-research-queue-integration",
        "wp80-copyability-delay-simulator-design-wallet-report-contract",
        "wp81-local-copyability-delay-evaluation-from-fixtures",
        "workflow/wp86-execution-package-discipline-adoption",
        "wp86",
    ))
    assert "WP76" in next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "WP78" in next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "91cd26e4fe16d492fa2f7b319fba176ee60cd9d5" in text
    assert "24badbfb7a9da06ee4c8ae94795e1f2c862af913" in text
    assert "7ff117f6caf78eab62e6a116db72b60d76d305f5" in text


def test_only_allowed_wallet_src_files_changed() -> None:
    changed = _changed_files()
    src_changes = sorted(path for path in changed if path.startswith("src/"))
    if "docs/status_entries/WP168.md" in changed:
        # WP168 authorizes exactly its offline NautilusTrader research-runtime package.
        assert set(src_changes) == {
            "src/research_runtime/README.md",
            "src/research_runtime/nautilus_offline/__init__.py",
            "src/research_runtime/nautilus_offline/runtime_compatibility.py",
            "src/research_runtime/nautilus_offline/instruments.py",
            "src/research_runtime/nautilus_offline/conversion.py",
            "src/research_runtime/nautilus_offline/catalog.py",
            "src/research_runtime/nautilus_offline/replay.py",
        }
        return
    if "docs/status_entries/WP167.md" in changed:
        # WP167 authorizes exactly its analytical research source package.
        assert set(src_changes) == {
        "src/data_layer/analytical_research/__init__.py",
        "src/data_layer/analytical_research/external_dataset.py",
        "src/data_layer/analytical_research/pmxt_v2.py",
        "src/data_layer/analytical_research/research_dataset.py",
    }
        return
    allowed_src_changes = {
        "src/data_layer/wallet_trade_event_fixtures.py",
        "src/data_layer/wallet_signal_research_profile.py",
        "src/data_layer/wallet_copyability_delay_evaluation.py",
        "src/data_layer/wallet_intelligence_report_generator.py",
        "src/data_layer/wallet_signal_paper_strategy_contract_validator.py",
        "src/data_layer/wallet_signal_paper_strategy_candidate_fixture_loader.py",
        "src/data_layer/wallet_signal_candidate_review_report.py",
        "src/data_layer/wallet_signal_candidate_review_report_export.py",
        "src/data_layer/hermes_advisory_output_validator.py",
        "src/data_layer/hermes_context_packet_exporter.py",
        "src/data_layer/hermes_context_packet_dry_run_receipt.py",
        "src/data_layer/hermes_manual_research_dry_run_review.py",
        # WP103: local/offline/read-only deterministic candidate-review context packet adapter
        "src/data_layer/hermes_candidate_review_context_packet_integration.py",
        # WP104: local/offline/read-only in-memory candidate-review manual chain smoke helper
        "src/data_layer/hermes_candidate_review_manual_chain_smoke.py",
        # WP106: local/offline/read-only in-memory candidate-review operator handoff object
        "src/data_layer/hermes_candidate_review_operator_handoff.py",
        # WP108: local/offline/read-only in-memory candidate-review handoff manual export artifact builder
        "src/data_layer/hermes_candidate_review_handoff_manual_export_artifact.py",
        # WP109: local/offline/manual-only explicit file writer for valid WP108 artifacts
        "src/data_layer/hermes_candidate_review_handoff_manual_export_writer.py",
        # WP121: local/offline/read-only in-memory candidate-review research question record validator
        "src/data_layer/hermes_candidate_review_research_question_record.py",
        # WP122: local/offline/read-only in-memory candidate-review advisory output validation receipt validator
        "src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py",
        # WP123: local/offline/read-only in-memory candidate-review human decision/follow-up validator
        "src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py",
        "src/data_layer/hermes_candidate_review_manual_research_session_package.py",
            # WP126: local/offline/read-only in-memory research candidate queue validator
            "src/data_layer/hermes_candidate_review_research_candidate_queue.py",
            # WP128: explicit-human-selection-only in-memory queue selection/question handoff validator
            "src/data_layer/hermes_candidate_review_manual_queue_selection_handoff.py",
            "src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py",
            # WP132: explicit-caller-content-only in-memory manual research request validator
            "src/data_layer/hermes_candidate_review_manual_research_request.py",
            # WP133: explicit-caller-content-only in-memory manual research response validator
            "src/data_layer/hermes_candidate_review_manual_research_response.py",
            # WP145: one-case local/offline test-oriented deterministic no-network harness
            "src/data_layer/hermes_candidate_review_assisted_research_local_dry_run_harness.py",
            # WP152: bounded local/offline deterministic Wave 1 measurement harness
                "src/data_layer/local_research_value_measurement/__init__.py",
                "src/data_layer/local_research_value_measurement/harness.py",
                # WP156: bounded local/offline deterministic point-in-time validator
                "src/data_layer/point_in_time_market_research/__init__.py",
                "src/data_layer/point_in_time_market_research/records.py",
                "src/data_layer/point_in_time_market_research/synthetic_corpus.py",
                # WP157: bounded in-memory point-in-time as-of query implementation
                "src/data_layer/point_in_time_market_research/as_of_query.py",
                "src/data_layer/point_in_time_market_research/as_of_synthetic_cases.py",
                # WP160: bounded in-memory manifest chain and dataset snapshot reference validator
                "src/data_layer/point_in_time_market_research/manifest_reference.py",
                # WP161: bounded local SQLite manifest store
                "src/data_layer/point_in_time_market_research/manifest_store.py",
                # WP162: bounded WP156/WP157 -> WP160 -> WP161 dataset persistence adapter
                "src/data_layer/point_in_time_market_research/dataset_persistence_adapter.py",
                # WP163: bounded durable local SQLite point-in-time record store
                "src/data_layer/point_in_time_market_research/record_store.py",
                # WP164: bounded real/public initial Polymarket point-in-time population
                "src/data_layer/point_in_time_market_research/polymarket_public_population.py",
                # WP165: bounded incremental/repeated public Polymarket cumulative cross-run lineage capture
                "src/data_layer/point_in_time_market_research/polymarket_incremental_population.py",
                # WP166: bounded scalable one-page keyset lineage-delta public Polymarket capture,
                # plus the read-only Gamma keyset client endpoint and its conservative polling budget.
                "src/data_layer/point_in_time_market_research/polymarket_scaled_population.py",
                "src/data_layer/polymarket/public_client.py",
                "src/data_layer/polymarket/polling_policy.py",
        }
    assert set(src_changes) <= allowed_src_changes, (
        f"Unexpected src/ changes: {set(src_changes) - allowed_src_changes}"
    )


def _spec_authorized_tool_paths(changed) -> set[str]:
    """Governance-tool paths authorized by the current WP machine spec(s).

    Any WP whose status entry is in ``changed`` contributes the ``tools/`` paths declared
    in its machine-spec ``required_changed_files``. Bounded and deterministic; replaces
    the earlier WP159-only tool-scope exception so future governance tooling needs no
    bespoke per-WP allowance.
    """
    authorized: set[str] = set()
    for path in changed:
        match = re.fullmatch(r"docs/status_entries/(WP[0-9A-Za-z]+)\.md", path)
        if match is None:
            continue
        spec_path = ROOT / "docs" / "wp_specs" / match.group(1) / "wp_spec.json"
        if not spec_path.is_file():
            continue
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for changed_file in spec.get("scope", {}).get("required_changed_files", []):
            if isinstance(changed_file, str) and changed_file.startswith("tools/"):
                authorized.add(changed_file)
    return authorized


def test_wallet_tool_scope_guard_uses_current_wp_spec_authority() -> None:
    authorized = _spec_authorized_tool_paths({"docs/status_entries/WP168G.md"})
    assert "tools/wp/wp_readiness_gate.py" in authorized
    assert "tools/wp/wp_spec_guard.py" in authorized
    wp159_authorized = _spec_authorized_tool_paths({"docs/status_entries/WP159.md"})
    assert "tools/wp/wp_spec_guard.py" in wp159_authorized
    assert _spec_authorized_tool_paths({"docs/project_status.md"}) == set()


def test_no_tools_files_changed() -> None:
    changed = _changed_files()
    allowed_tools_changes = {
        "tools/hermes_candidate_review_manual_export_cli.py",
    }
    if "docs/status_entries/WP159.md" in changed:
        expected = set(json.loads(
            (ROOT / "docs/wp_specs/WP159/wp_spec.json").read_text(
                encoding="utf-8"
            )
        )["scope"]["required_changed_files"])
        assert len(expected) == 23
        assert set(changed) == expected
    # Authorize governance-tool changes from the current WP machine spec rather than a
    # bespoke WP159-only exception (WP159 and later governance WPs, including WP168G,
    # are covered because their specs declare their own tools).
    allowed_tools_changes.update(_spec_authorized_tool_paths(changed))
    tools_changes = {path for path in changed if path.startswith("tools/")}
    assert tools_changes <= allowed_tools_changes, (
        f"Unexpected tools/ changes: {tools_changes - allowed_tools_changes}"
    )


def test_no_dependency_or_lock_files_changed() -> None:
    changed = _changed_files()
    if "docs/status_entries/WP168.md" in changed or "docs/status_entries/WP167.md" in changed:
        # WP167 and WP168 each authorize exactly one dependency file, pyproject.toml, and no lock file.
        dep_changes = {Path(path).name for path in changed if Path(path).name in {
            "requirements.txt", "requirements-dev.txt", "pyproject.toml", "package.json",
            "package-lock.json", "poetry.lock", "uv.lock", "pdm.lock", "Pipfile.lock",
        }}
        assert dep_changes == {"pyproject.toml"}
        return
    forbidden_names = {
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "poetry.lock",
        "uv.lock",
        "pdm.lock",
        "Pipfile.lock",
    }
    assert not any(Path(path).name in forbidden_names for path in changed)


def _changed_files() -> list[str]:
    diff_result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    untracked_result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    lines = diff_result.stdout.splitlines() + untracked_result.stdout.splitlines()
    return sorted({line.strip().replace("\\", "/") for line in lines if line.strip()})
