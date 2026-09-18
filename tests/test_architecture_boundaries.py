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
    # WP168 introduces the research-runtime boundary (offline Nautilus replay kernel).
    "src/research_runtime/README.md",
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
# WP90 approves the local/offline/read-only candidate review report export layer at src/data_layer/wallet_signal_candidate_review_report_export.py.
# WP99 approves the local/offline/read-only Hermes advisory output validator at src/data_layer/hermes_advisory_output_validator.py.
# WP100 approves the local/offline/read-only in-memory Hermes context-packet builder at src/data_layer/hermes_context_packet_exporter.py.
# WP101 approves the local/offline/read-only in-memory Hermes context-packet dry-run receipt at src/data_layer/hermes_context_packet_dry_run_receipt.py.
# WP102 approves the local/offline/read-only in-memory Hermes manual research dry-run operator review at src/data_layer/hermes_manual_research_dry_run_review.py.
# WP103 approves the local/offline/read-only in-memory Hermes candidate-review context packet integration adapter at src/data_layer/hermes_candidate_review_context_packet_integration.py.
# WP121 approves the local/offline/read-only in-memory Hermes candidate-review research question record validator at src/data_layer/hermes_candidate_review_research_question_record.py.
# WP122 approves the local/offline/read-only in-memory Hermes candidate-review advisory output validation receipt validator at src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py.
# WP123 approves the local/offline/read-only in-memory Hermes candidate-review human decision and follow-up record validator at src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py.
# WP124 approves the local/offline/read-only in-memory Hermes candidate-review manual research session package validator at src/data_layer/hermes_candidate_review_manual_research_session_package.py.
# WP126 approves the local/offline/read-only in-memory Hermes candidate-review research candidate queue validator at src/data_layer/hermes_candidate_review_research_candidate_queue.py.
# WP128 approves the local/offline/read-only in-memory manual queue selection and research-question handoff validator at src/data_layer/hermes_candidate_review_manual_queue_selection_handoff.py.
# WP130 approves the local/offline/read-only in-memory manual research briefing packet validator at src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py.
# WP132 approves the local/offline/read-only in-memory manual research request validator at src/data_layer/hermes_candidate_review_manual_research_request.py.
# WP133 approves the local/offline/read-only in-memory manual research response validator at src/data_layer/hermes_candidate_review_manual_research_response.py.
# WP145 approves the local/offline/test-oriented deterministic no-network harness at src/data_layer/hermes_candidate_review_assisted_research_local_dry_run_harness.py.
# WP152 approves the local/offline deterministic temporary Wave 1 measurement harness namespace.
# WP156 approves the local/offline deterministic point-in-time record validator and synthetic corpus namespace.
# WP167 approves the local/offline/read-only-against-canonical derived analytical research
# namespace at src/data_layer/analytical_research/ (PyArrow/DuckDB/Polars materialization,
# external pmxt v2 provenance descriptor, and analytical query helpers with no execution authority).
# WP172 approves the local/offline executable-edge research namespace. It adapts existing
# WP168/WP170 evidence and has no network, credentials, paper, order, execution, or live authority.
# WP173 approves deterministic simulated-paper runtime/accounting/risk/reconciliation only.
# It reads WP169 locally, extends the loopback read-only cockpit, and has no real/live authority.
# WP174 approves the protected Gate-A-only auth/signing/execution gateway. It can
# reach only A0/A1/A2 and cannot invoke SDK venue mutations without later Gate B.
# WP175H approves the local/offline dormant-by-default controlled Hermes research
# runtime core at src/research_runtime/hermes_controlled_runtime/. It owns a
# deterministic request/policy/response-capture/runner/controller boundary around one
# bounded external one-shot web-only research session and has no trading, paper,
# execution, live, credential, scheduler, or merge authority; the real provider
# call count is zero and remote activation is separately gated (S10-GATE-H1).
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
    "src/data_layer/wallet_signal_candidate_review_report_export.py",
    "src/data_layer/hermes_advisory_output_validator.py",
    "src/data_layer/hermes_context_packet_exporter.py",
    "src/data_layer/hermes_context_packet_dry_run_receipt.py",
    "src/data_layer/hermes_manual_research_dry_run_review.py",
    "src/data_layer/hermes_candidate_review_context_packet_integration.py",
    # WP104 approves the local/offline/read-only in-memory Hermes candidate-review manual chain smoke at src/data_layer/hermes_candidate_review_manual_chain_smoke.py.
    "src/data_layer/hermes_candidate_review_manual_chain_smoke.py",
    # WP106 approves the local/offline/read-only in-memory Hermes candidate-review operator handoff object at src/data_layer/hermes_candidate_review_operator_handoff.py.
    "src/data_layer/hermes_candidate_review_operator_handoff.py",
    # WP108 approves the local/offline/read-only in-memory Hermes candidate-review handoff manual export artifact builder at src/data_layer/hermes_candidate_review_handoff_manual_export_artifact.py.
    "src/data_layer/hermes_candidate_review_handoff_manual_export_artifact.py",
    # WP109 approves the local/offline/manual-only Hermes candidate-review handoff manual export file writer at src/data_layer/hermes_candidate_review_handoff_manual_export_writer.py.
    "src/data_layer/hermes_candidate_review_handoff_manual_export_writer.py",
    # WP121 approves the local/offline/read-only in-memory Hermes candidate-review research question record validator at src/data_layer/hermes_candidate_review_research_question_record.py.
    "src/data_layer/hermes_candidate_review_research_question_record.py",
    # WP122 approves the local/offline/read-only in-memory Hermes candidate-review advisory output validation receipt validator at src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py.
    "src/data_layer/hermes_candidate_review_advisory_output_validation_receipt.py",
    # WP123 approves the local/offline/read-only in-memory Hermes candidate-review human decision and follow-up record validator at src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py.
    "src/data_layer/hermes_candidate_review_human_decision_follow_up_record.py",
    # WP124 approves the local/offline/read-only in-memory Hermes candidate-review manual research session package validator.
    "src/data_layer/hermes_candidate_review_manual_research_session_package.py",
    # WP126 approves the local/offline/read-only in-memory research candidate queue validator.
    "src/data_layer/hermes_candidate_review_research_candidate_queue.py",
    "src/data_layer/hermes_candidate_review_manual_queue_selection_handoff.py",
    "src/data_layer/hermes_candidate_review_manual_research_briefing_packet.py",
    "src/data_layer/hermes_candidate_review_manual_research_request.py",
    "src/data_layer/hermes_candidate_review_manual_research_response.py",
    "src/data_layer/hermes_candidate_review_assisted_research_local_dry_run_harness.py",
    "src/data_layer/local_research_value_measurement",
    "src/data_layer/point_in_time_market_research",
    "src/data_layer/analytical_research",
    # WP168 approves the local/offline/read-only NautilusTrader offline replay kernel,
    # ParquetDataCatalog adoption, and deterministic replay package (no live/auth clients,
    # no Polymarket extra, no Redis, no network, no strategy/order/fill/paper/live), plus
    # the new research-runtime boundary README.
    "src/research_runtime/nautilus_offline",
    "src/research_runtime/executable_edge",
    "src/research_runtime/hermes_controlled_runtime",
    "src/research_runtime/README.md",
    "src/paper_trading",
    "src/execution_gateway",
    # WP171 approves one local, read-only cockpit and its browser source. It reads
    # caller-selected WP169/WP170 SQLite evidence and has no trading authority.
    "src/operator_cockpit.py",
    "src/operator_cockpit_frontend",
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
    WP90 permits wallet_signal_candidate_review_report_export.py for the local/offline/read-only
    candidate review report export layer.
    WP99 permits hermes_advisory_output_validator.py for local/offline/read-only
    advisory output validation.
    WP100 permits hermes_context_packet_exporter.py for local/offline/read-only
    in-memory context-packet construction.
    WP101 permits hermes_context_packet_dry_run_receipt.py for local/offline/read-only
    in-memory context-packet dry-run receipt construction.
    WP102 permits hermes_manual_research_dry_run_review.py for local/offline/read-only
    in-memory manual research dry-run operator review record construction.
    WP103 permits hermes_candidate_review_context_packet_integration.py for local/offline/read-only
    in-memory candidate-review context packet integration adapter construction.
    WP104 permits hermes_candidate_review_manual_chain_smoke.py for local/offline/read-only
    in-memory candidate-review manual chain smoke helper construction.
    WP121 permits hermes_candidate_review_research_question_record.py for
    local/offline/read-only in-memory research question record validation.
    WP122 permits hermes_candidate_review_advisory_output_validation_receipt.py
    for local/offline/read-only in-memory advisory output receipt validation.
    WP123 permits hermes_candidate_review_human_decision_follow_up_record.py
    for local/offline/read-only in-memory human decision and follow-up task
    record validation.
    WP124 permits hermes_candidate_review_manual_research_session_package.py
    for local/offline/read-only in-memory manual research session package validation.
    WP126 permits hermes_candidate_review_research_candidate_queue.py for
    local/offline/read-only in-memory research candidate queue validation.
    WP128 permits hermes_candidate_review_manual_queue_selection_handoff.py for
    explicit-human-selection-only in-memory queue selection and question handoff validation.
    WP130 permits hermes_candidate_review_manual_research_briefing_packet.py for
    explicit-caller-content-only in-memory manual research briefing packet validation.
    WP132 permits hermes_candidate_review_manual_research_request.py for
        explicit-caller-content-only in-memory manual research request validation.
    WP133 permits hermes_candidate_review_manual_research_response.py for
        explicit-caller-content-only in-memory manual research response validation.
    WP145 permits hermes_candidate_review_assisted_research_local_dry_run_harness.py
    for the one-case local/offline test-oriented deterministic no-network harness.
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


def test_wp173_paper_runtime_is_separate_from_live_and_external_clients():
    paper = ROOT / "src" / "paper_trading"
    assert paper.is_dir()
    imports = "\n".join(
        path.read_text(encoding="utf-8").lower() for path in paper.glob("*.py")
    )
    for forbidden in (
        "import requests",
        "import httpx",
        "import websockets",
        "py_clob_client",
        "src.execution_gateway",
        "src.oms",
        "src.risk_engine",
    ):
        assert forbidden not in imports
    contract = (ROOT / "docs" / "serious_paper_trading_contract.md").read_text(
        encoding="utf-8"
    )
    assert "SIMULATED_PAPER_ONLY" in contract
    assert "WP174 Auth / Signing / Execution Gateway" in contract
    assert "does not authorize" in contract


def test_wp174_gateway_boundary_preserves_wp173_and_excludes_wp175():
    gateway = ROOT / "src" / "execution_gateway"
    assert gateway.is_dir()
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in gateway.glob("*.py")
    )
    assert 'AUTHORITY_STATES = ("A0_DISABLED", "A1_READ_ONLY", "A2_SHADOW", "A3_RESTRICTED_LIVE")' in source
    assert "from polymarket import AsyncSecureClient, SecureClient" in source
    # WP174B replaced the Gate-B-locked stub with a real production mutation
    # boundary while keeping every real economic create/post Gate-C unreachable.
    assert "class _ProductionSdkMutationTransport" in source
    assert "class ProductionSdkMutationAdapter" not in source
    assert "def mutation_adapter" not in source
    for sdk_cancel in (
        "self._client.cancel_order(",
        "self._client.cancel_orders(",
        "self._client.cancel_market_orders(",
        "self._client.cancel_all(",
    ):
        assert source.count(sdk_cancel) == 1
    assert "class GateCLivePermit" in source
    assert 'raise GatewayError("GATE_C_REQUIRED")' in source
    # The Gate-A state machine's own mutation entry points still fail closed.
    assert 'raise GatewayError("GATE_B_REQUIRED")' in source
    # WP175 adds A3 only in the separately gated Gate-C module; Gate-A's
    # generic authority setter still cannot enter it.
    assert "A3_RESTRICTED_LIVE" in source
    assert 'authority_state == "A3_RESTRICTED_LIVE"' in source
    assert "class GateBSession" in source
    for forbidden in (
        "os.environ",
        "load_dotenv",
        "import requests",
        "import httpx",
        "while True",
        "time.sleep",
    ):
        assert forbidden not in source
    paper = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in (ROOT / "src" / "paper_trading").glob("*.py")
    )
    assert "src.execution_gateway" not in paper


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


# ── WP89: Candidate Review Report V1 ─────────────────────────────────────────


def test_wp89_status_fragment_exists():
    path = ROOT / "docs" / "status_entries" / "WP89.md"
    assert path.is_file(), "docs/status_entries/WP89.md must exist after WP89"


def test_wp89_report_module_exists():
    path = ROOT / "src" / "data_layer" / "wallet_signal_candidate_review_report.py"
    assert path.is_file(), "WP89 report module must exist"


# ── WP90: Candidate Review Report Local Export V1 ────────────────────────────


def test_wp90_status_fragment_exists():
    path = ROOT / "docs" / "status_entries" / "WP90.md"
    assert path.is_file(), "docs/status_entries/WP90.md must exist after WP90"


def test_wp90_export_module_exists():
    path = ROOT / "src" / "data_layer" / "wallet_signal_candidate_review_report_export.py"
    assert path.is_file(), "WP90 export module must exist"


# ── WP91: Final Comment Transition Retirement Decision ────────────────────────


def test_wp91_status_fragment_exists():
    path = ROOT / "docs" / "status_entries" / "WP91.md"
    assert path.is_file(), "docs/status_entries/WP91.md must exist after WP91"


def test_wp91_final_comment_policy_doc_exists():
    path = ROOT / "docs" / "ai" / "codex" / "FINAL_COMMENT_POLICY.md"
    assert path.is_file(), "docs/ai/codex/FINAL_COMMENT_POLICY.md must exist after WP91"


def test_wp91_does_not_add_new_src_files():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "origin/main...HEAD", "--name-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    changed = [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]
    new_src = [f for f in changed if f.startswith("src/") and not any(
        f.startswith(scope + "/") or f == scope for scope in APPROVED_SRC_SCOPES
    )]
    assert new_src == [], f"WP91 must not add new src/ files outside approved scopes: {new_src}"


# ── WP92: Repo-Truth Policy Guard And One-Shot Execution Gate ────────────────


def test_wp92_status_fragment_exists():
    path = ROOT / "docs" / "status_entries" / "WP92.md"
    assert path.is_file(), "docs/status_entries/WP92.md must exist after WP92"


def test_wp92_repo_truth_policy_guard_doc_exists():
    path = ROOT / "docs" / "ai" / "codex" / "REPO_TRUTH_POLICY_GUARD.md"
    assert path.is_file(), "docs/ai/codex/REPO_TRUTH_POLICY_GUARD.md must exist after WP92"


def test_wp92_does_not_add_new_src_files():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "origin/main...HEAD", "--name-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    changed = [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]
    new_src = [f for f in changed if f.startswith("src/") and not any(
        f.startswith(scope + "/") or f == scope for scope in APPROVED_SRC_SCOPES
    )]
    assert new_src == [], f"WP92 must not add new src/ files outside approved scopes: {new_src}"


# -- WP93: Candidate Review Report Operator Runbook V1 ------------------------


def test_wp93_status_fragment_exists():
    path = ROOT / "docs" / "status_entries" / "WP93.md"
    assert path.is_file(), "docs/status_entries/WP93.md must exist after WP93"


def test_wp93_candidate_review_report_operator_runbook_exists():
    path = ROOT / "docs" / "runbooks" / "candidate_review_report_operator_runbook.md"
    assert path.is_file(), "WP93 runbook must exist"


def test_wp93_does_not_add_new_src_files():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "origin/main...HEAD", "--name-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    changed = [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]
    new_src = [f for f in changed if f.startswith("src/") and not any(
        f.startswith(scope + "/") or f == scope for scope in APPROVED_SRC_SCOPES
    )]
    assert new_src == [], f"WP93 must not add new src/ files outside approved scopes: {new_src}"


# -- WP94: Candidate Review Workflow Local Smoke Receipt V1 -------------------


def test_wp94_status_fragment_exists():
    path = ROOT / "docs" / "status_entries" / "WP94.md"
    assert path.is_file(), "docs/status_entries/WP94.md must exist after WP94"


def test_wp94_candidate_review_workflow_smoke_receipt_exists():
    path = ROOT / "docs" / "runbooks" / "candidate_review_workflow_local_smoke_receipt.md"
    assert path.is_file(), "WP94 smoke receipt must exist"


def test_wp94_does_not_add_new_src_files():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "origin/main...HEAD", "--name-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    changed = [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]
    new_src = [f for f in changed if f.startswith("src/") and not any(
        f.startswith(scope + "/") or f == scope for scope in APPROVED_SRC_SCOPES
    )]
    assert new_src == [], f"WP94 must not add new src/ files outside approved scopes: {new_src}"


# -- WP115: Hermes Candidate-Review Local Manual Export CLI Wrapper ------------


def test_wp115_manual_export_cli_tool_exists():
    path = ROOT / "tools" / "hermes_candidate_review_manual_export_cli.py"
    assert path.is_file(), "WP115 CLI wrapper must exist under tools/"


def test_wp115_does_not_add_new_src_files():
    import subprocess
    result = subprocess.run(
        ["git", "diff", "origin/main...HEAD", "--name-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    changed = [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]
    new_src = [f for f in changed if f.startswith("src/") and not any(
        f.startswith(scope + "/") or f == scope for scope in APPROVED_SRC_SCOPES
    )]
    assert new_src == [], f"WP115 must not add new src/ files outside approved scopes: {new_src}"


def test_wp175_boundary_has_no_scheduler_hermes_paper_or_wallet_ops():
    """The canary adds one private limit surface, not a new orchestration stack."""
    source = (ROOT / "src" / "execution_gateway" / "gate_c.py").read_text(
        encoding="utf-8"
    )
    assert "GateCSession" in source
    assert "GATE_C_CREATE_STARTED" in source
    assert "create_market" not in source
    assert "PaperEngine" not in source
    assert "Hermes" not in source
    assert "schedule(" not in source
    assert "wallet_ops" not in source
