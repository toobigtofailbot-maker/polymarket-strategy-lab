from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ARCHITECTURE_DOCS = [
    "docs/architecture_skeleton.md",
    "docs/runtime_boundaries.md",
    "docs/interface_contracts.md",
    "docs/mode_separation.md",
    "docs/security_tooling_requirements.md",
]

SRC_READMES = [
    "src/README.md",
    "src/execution_gateway/README.md",
    "src/risk_engine/README.md",
    "src/strategy_modules/README.md",
    "src/data_layer/README.md",
    "src/paper_trading/README.md",
    "src/monitoring/README.md",
    "src/shared/README.md",
]


def test_architecture_docs_exist():
    missing = [path for path in ARCHITECTURE_DOCS if not (ROOT / path).is_file()]
    assert missing == []


def test_required_src_readmes_exist():
    missing = [path for path in SRC_READMES if not (ROOT / path).is_file()]
    assert missing == []



# WP8 approves executable source files under src/data_layer/polymarket/.
# WP23 approves executable local/offline exporter source under src/data_layer/agent_context/.
# WP49 approves the local/offline/read-only core scorer at src/data_layer/market_research_priority_scoring.py.
# WP51 approves the local/offline/read-only feature extraction foundation at src/data_layer/market_research_priority_features.py.
# WP56 approves the local/offline/read-only label schema validator at src/data_layer/resolution_ambiguity_labels.py.
# WP64 approves the local/offline/read-only research queue/report/session packet at src/data_layer/market_research_priority_review_queue.py.
# WP67 approves the local/offline/read-only calibration record schema validator at src/data_layer/calibration_record_validation.py.
# WP68 approves the local/offline/read-only resolved outcome fixture loader at src/data_layer/resolved_outcome_fixture_loader.py.
# WP70 approves the local/offline/read-only calibration metric computation helper at src/data_layer/calibration_metric_computation.py.
# WP71 approves the local/offline/read-only calibration report generator at src/data_layer/calibration_report_generator.py.
# WP74 approves the local/offline/read-only human review label record validator at src/data_layer/human_review_label_validation.py.
# WP75 approves the local/offline/read-only human review label fixture loader at src/data_layer/human_review_label_fixture_loader.py.
# WP78 approves the local/offline/read-only wallet trade event fixture loader at src/data_layer/wallet_trade_event_fixtures.py.
# WP79 approves the local/offline/read-only wallet signal research profile builder at src/data_layer/wallet_signal_research_profile.py.
# WP81 approves the local/offline/read-only copyability delay evaluator at src/data_layer/wallet_copyability_delay_evaluation.py.
# WP82 approves the local/offline/read-only wallet intelligence report generator at src/data_layer/wallet_intelligence_report_generator.py.
# WP84 approves the local/offline/read-only wallet signal paper strategy contract validator at src/data_layer/wallet_signal_paper_strategy_contract_validator.py.
# WP87 approves the local/offline/read-only wallet signal paper strategy candidate fixture loader at src/data_layer/wallet_signal_paper_strategy_candidate_fixture_loader.py.
# WP89 approves the local/offline/read-only wallet signal candidate review report at src/data_layer/wallet_signal_candidate_review_report.py.
APPROVED_SRC_SCOPES = (
    "src/data_layer/polymarket",
    "src/data_layer/agent_context",
    "src/data_layer/market_research_priority_scoring.py",
    "src/data_layer/market_research_priority_features.py",
    "src/data_layer/resolution_ambiguity_labels.py",
    "src/data_layer/market_research_priority_review_queue.py",
    "src/data_layer/calibration_record_validation.py",
    "src/data_layer/resolved_outcome_fixture_loader.py",
    "src/data_layer/calibration_metric_computation.py",
    "src/data_layer/calibration_report_generator.py",
    "src/data_layer/human_review_label_validation.py",
    "src/data_layer/human_review_label_fixture_loader.py",
    "src/data_layer/wallet_trade_event_fixtures.py",
    "src/data_layer/wallet_signal_research_profile.py",
    "src/data_layer/wallet_copyability_delay_evaluation.py",
    "src/data_layer/wallet_intelligence_report_generator.py",
    "src/data_layer/wallet_signal_paper_strategy_contract_validator.py",
    "src/data_layer/wallet_signal_paper_strategy_candidate_fixture_loader.py",
    "src/data_layer/wallet_signal_candidate_review_report.py",
)


def test_no_executable_files_exist_under_src_except_approved_scope():
    """Executable files under src/ are forbidden except in approved scopes.

    WP8 explicitly permits .py files under src/data_layer/polymarket/ for the
    read-only public data adapter. WP23 permits .py files under
    src/data_layer/agent_context/ for the local/offline/read-only exporter.
    WP64 permits market_research_priority_review_queue.py for the local/offline/read-only
    research queue/report/session packet module.
    WP67 permits calibration_record_validation.py for the local/offline/read-only
    calibration record schema validator.
    WP68 permits resolved_outcome_fixture_loader.py for the local/offline/read-only
    resolved outcome fixture loader.
    WP70 permits calibration_metric_computation.py for the local/offline/read-only
    calibration metric computation helper.
    WP71 permits calibration_report_generator.py for the local/offline/read-only
    calibration report generator.
    WP74 permits human_review_label_validation.py for the local/offline/read-only
    human review label record validator.
    WP75 permits human_review_label_fixture_loader.py for the local/offline/read-only
    human review label fixture loader.
    WP78 permits wallet_trade_event_fixtures.py for the local/offline/read-only
    wallet trade event fixture validator/loader.
    WP79 permits wallet_signal_research_profile.py for the local/offline/read-only
    wallet signal research profile builder and annotation builder.
    WP81 permits wallet_copyability_delay_evaluation.py for the local/offline/read-only
    copyability delay evaluator from validated fixtures.
    WP82 permits wallet_intelligence_report_generator.py for the local/offline/read-only
    wallet intelligence report generator.
    WP84 permits wallet_signal_paper_strategy_contract_validator.py for the local/offline/read-only
    wallet signal paper strategy contract validator.
    WP87 permits wallet_signal_paper_strategy_candidate_fixture_loader.py for the local/offline/read-only
    wallet signal paper strategy candidate fixture loader.
    WP89 permits wallet_signal_candidate_review_report.py for the local/offline/read-only
    wallet signal candidate review report.
    All other src/ subdirectories must remain README-only.
    """
    src = ROOT / "src"
    executable_suffixes = {".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".sh", ".ps1"}
    findings = []
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "README.md":
            continue
        rel = path.relative_to(ROOT).as_posix()
        if any(rel.startswith(scope + "/") or rel == scope for scope in APPROVED_SRC_SCOPES):
            continue
        if path.suffix.lower() in executable_suffixes:
            findings.append(rel)
    assert findings == [], (
        f"Unexpected executable files outside approved scopes ({APPROVED_SRC_SCOPES}): {findings}"
    )


def test_architecture_docs_forbid_direct_strategy_order_placement():
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ["docs/architecture_skeleton.md", "docs/runtime_boundaries.md"]
    )
    assert "Strategies produce proposals only." in combined
    assert "Strategies cannot place orders directly." in combined


def test_live_trading_remains_disabled():
    text = (ROOT / "docs" / "live_trading_authorization.md").read_text(encoding="utf-8")
    assert "LIVE TRADING STATUS: DISABLED" in text
    assert "LIVE TRADING STATUS: ENABLED" not in text


def test_security_tools_are_mandatory_before_runtime_dependency_integration():
    text = (ROOT / "docs" / "security_tooling_requirements.md").read_text(encoding="utf-8")
    assert "mandatory before runtime dependency integration" in text
    assert "vendoring" in text
    assert "live/API execution" in text


# ── WP88: Evidence Architecture Repair ───────────────────────────────────────


def test_wp88_evidence_architecture_doc_exists():
    path = ROOT / "docs" / "ai" / "codex" / "EVIDENCE_ARCHITECTURE.md"
    assert path.is_file(), "docs/ai/codex/EVIDENCE_ARCHITECTURE.md must exist after WP88"


def test_wp88_result_output_invariant_standard_doc_exists():
    path = ROOT / "docs" / "ai" / "codex" / "RESULT_OUTPUT_INVARIANT_STANDARD.md"
    assert path.is_file(), "docs/ai/codex/RESULT_OUTPUT_INVARIANT_STANDARD.md must exist after WP88"


def test_wp88_followup_prompt_standard_doc_exists():
    path = ROOT / "docs" / "ai" / "codex" / "FOLLOWUP_PROMPT_STANDARD.md"
    assert path.is_file(), "docs/ai/codex/FOLLOWUP_PROMPT_STANDARD.md must exist after WP88"


def test_wp88_status_fragment_exists():
    path = ROOT / "docs" / "status_entries" / "WP88.md"
    assert path.is_file(), "docs/status_entries/WP88.md must exist after WP88"


def test_wp88_does_not_add_new_src_files():
    """WP88 is workflow-docs-tests-only; it must not add new src/ modules."""
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    changed = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    new_src = [f for f in changed if f.startswith("src/") and not any(
        f.startswith(scope + "/") or f == scope for scope in APPROVED_SRC_SCOPES
    )]
    assert new_src == [], f"WP88 must not add new src/ files outside approved scopes: {new_src}"
