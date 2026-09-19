from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    ".gitignore",
    "pyproject.toml",
    "docs/repo_truth_index.md",
    "docs/project_charter.md",
    "docs/project_status.md",
    "docs/source_repo_registry.md",
    "docs/repo_reuse_strategy.md",
    "docs/architecture_principles.md",
    "docs/strategy_module_registry.md",
    "docs/data_semantics.md",
    "docs/wallet_copy_trading_semantics.md",
    "docs/risk_semantics.md",
    "docs/live_trading_authorization.md",
    "docs/security_and_secrets.md",
    "docs/codex_execution_guidelines.md",
    "docs/work_package_template.md",
    "docs/review_checklist.md",
    "docs/testing_requirements.md",
    ".github/pull_request_template.md",
    "audits/source_repos/README.md",
    "tests/test_repo_truth_docs.py",
    "tests/test_no_live_mode_by_default.py",
    "tests/test_no_secret_placeholders.py",
]


def test_required_repo_truth_files_exist():
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
    assert missing == []


def test_wp171g_repo_truth_transition_is_registered():
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    assert "WP171 merged: PR #172" in index
    assert "a650c08ab233e47beca7565a5bb8df11a4f41d02" in index
    assert "d6a15e4007fe3ced5a7d059ec3fcdec496d2dc7d" in index
    assert "FAST, RUNTIME, and PROTECTED" in index
    assert "Historical valid certified packages remain accepted" in index
    assert "normative machine-readable authority mirror" in index
    assert "all sixteen authority booleans" in index
    assert "certificate/package guard as not run" in index
    assert "WP172 — Alpha + Executable Edge MVP" in index
    assert "not started by WP171G" in index
    assert "WP171G Lean Agent Execution Governance Deferred Items" in deferred
    assert "parked local WP172 worktree remains separate and" in deferred
    assert "untouched" in deferred
    assert "authority-divergence finding is resolved" in deferred


def test_wp173_repo_truth_and_successor_are_consistent():
    status = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "long_term_bot_completion_roadmap.md").read_text(
        encoding="utf-8"
    )
    fragment = (ROOT / "docs" / "status_entries" / "WP173.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((status, index, deferred, roadmap, fragment))
    assert "WP172 merged: YES" in status
    assert "WP172 PR: 174" in status
    assert "39363e5a081b6737104260725b1b0c8fcffe9196" in combined
    assert "418bae72f24b0694eccc657ed5dc3f90a3f38f2a" in combined
    assert "WP173 current review target" in status
    assert "Exact changed-file scope: 31" in status
    assert "an exact 31-file scope" in index
    assert "an exact 29-file scope" not in index
    assert "RESOLVED_BOUNDED_WP173_SERIOUS_PAPER" in deferred
    assert "obsolete Hermes-labelled WP172 remains superseded" in index
    assert "WP174 — Auth / Signing / Execution Gateway" in combined
    assert "WP175 — Restricted Live Canary" in roadmap
    assert "WP176 — Mature Controlled Live" in roadmap
    assert "WP174" in fragment and "unstarted" in fragment
    assert "SIMULATED_PAPER_ONLY" in combined


def test_wp174_repo_truth_registers_gate_a_without_live_authority():
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "WP174.md").read_text(
        encoding="utf-8"
    )
    assert "62z333." in index and "62z334." in index and "62z335." in index
    assert "A0 DISABLED, A1 READ ONLY, or A2 SHADOW" in index
    assert "constructor-locked behind Gate B" in index
    assert "real secret is loaded" in index
    assert "two backend-only bounded GET projections" in index
    assert "A3_RESTRICTED_LIVE: ABSENT" in fragment
    assert "Capital at risk: USD 0" in fragment
    assert "WP175 Restricted Live Canary" in fragment
    assert "not started" in fragment


def test_wp174b_repo_truth_registers_gate_b_without_live_authority():
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "WP174B.md").read_text(
        encoding="utf-8"
    )
    assert "62z336." in index and "62z337." in index and "62z338." in index
    assert "WP174B is the current PROTECTED-track review target" in index
    assert "6fff7fefd8f936824a7586f94d452ca073b225dd" in index
    assert "dbb4ee0e21e409c4639edc44cce17696a5b15156" in index
    assert "the certified 22-path XL implementation" in index
    assert "closes WP174-D001 and does not start WP174-D002 / WP175" in index
    assert "src/execution_gateway/gate_b.py" in index
    assert "signature type 3" in index
    assert "GATE_C_REQUIRED" in index
    assert "A3 RESTRICTED LIVE is absent" in index
    assert "empty-wallet `cancel_all`" in index
    assert "A3_RESTRICTED_LIVE: ABSENT" in fragment
    assert "Capital at risk: USD 0" in fragment
    assert "Real economic CREATE/POST: FORBIDDEN_GATE_C" in fragment
    assert "WP175" in fragment and "separately gated and not started" in fragment


def test_wp175_repo_truth_registers_pending_gate_c_activation() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "WP175.md").read_text(
        encoding="utf-8"
    )
    for text in (index, status, fragment):
        assert "WP175" in text
        assert "LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE" in text
        assert "capital" in text.lower()
        assert "WP176" in text


def test_wp175d_repo_truth_registers_research_bridge() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "WP175D.md").read_text(
        encoding="utf-8"
    )
    contract = (
        ROOT / "docs" / "external_historical_research_bridge_contract.md"
    ).read_text(encoding="utf-8")
    combined = "\n".join((index, status, fragment, contract))
    for text in (index, status, fragment):
        assert "WP175D" in text
        assert "S10-DATA-02" in text
    # WP175 merged dormant at the exact merge commit; WP175D is the current bridge.
    assert "489c6f9548c39cb3bcb2196a81d5352a0d1dd653" in combined
    assert "External Historical Research Bridge" in combined
    assert "ExternalDatasetBinding" in combined
    assert "DATASET_BINDING" in combined
    assert "WP167_EXTERNAL_DATASET_DESCRIPTOR" in combined
    assert "SOURCE_KIND_CANONICAL_PIT" in combined
    assert "Canonical PIT authority unchanged: YES" in combined
    # Live activation stays blocked; WP176 preserved and not started; merge not authorized.
    assert "LIVE_ACTIVATION_PREREQUISITE_NOT_YET_AVAILABLE" in combined
    assert "WP176" in combined
    assert "NOT STARTED" in fragment
    assert "Merge authorized: NO" in fragment
    assert "Capital at risk: USD 0" in fragment


def test_wp175e_repo_truth_registers_native_continuity_without_live_authority() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(
        encoding="utf-8"
    )
    roadmap = (ROOT / "docs" / "long_term_bot_completion_roadmap.md").read_text(
        encoding="utf-8"
    )
    fragment = (ROOT / "docs" / "status_entries" / "WP175E.md").read_text(
        encoding="utf-8"
    )
    contract = (
        ROOT / "docs" / "native_continuity_attested_market_truth_bridge_contract.md"
    ).read_text(encoding="utf-8")
    combined = "\n".join((index, status, deferred, roadmap, fragment, contract))
    assert "WP175E Native Continuity-Attested Market Truth Bridge" in index
    assert "S10-DATA-03" in combined
    assert "EVIDENCE_INCONCLUSIVE" in combined
    assert "genuine pmxt" in combined.lower()
    assert "AS_CAPTURED" in combined
    assert "NativeContinuityAttestation" in combined
    assert "NativeMarketTruthWindow" in combined
    assert "PARTIALLY_RESOLVED_WP175E_NATIVE_BRIDGE" in deferred
    assert "generic PIT -> Nautilus adapter remains open" in deferred
    assert "LIVE_PATH_EVIDENCE_READY" in combined
    assert "NOT CLAIMED" in status
    assert "Gate C" in combined and "NOT AUTHORIZED" in combined
    assert "WP176" in combined and "NOT STARTED" in combined
    assert "Credentials: 0" in fragment
    assert "real orders: 0" in fragment
    assert "capital at risk: USD 0" in fragment
    assert "Merge authorized: NO" in combined


def test_wp175h_repo_truth_registers_controlled_runtime_without_live_authority() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "long_term_bot_completion_roadmap.md").read_text(
        encoding="utf-8"
    )
    fragment = (ROOT / "docs" / "status_entries" / "WP175H.md").read_text(
        encoding="utf-8"
    )
    contract = (
        ROOT / "docs" / "hermes_controlled_research_runtime_contract.md"
    ).read_text(encoding="utf-8")
    combined = "\n".join((index, status, deferred, roadmap, fragment, contract))
    assert "WP175H Controlled Hermes Research Runtime Core" in index
    assert "S10-HERMES-01" in combined
    assert "Hermes Agent v0.21.3" in combined
    assert "CODE COMPLETE: YES" in combined
    assert "RUNTIME ACTIVATED: NO" in combined
    assert "S10-GATE-H1" in combined
    assert "S10-ALPHA-01" in combined
    # Hermes prose is untrusted research content, never canonical economic truth.
    assert "untrusted research" in combined.lower()
    assert "advisory_only" in contract
    assert "web_search" in contract and "web_extract" in contract
    assert "Gate C" in combined and "NOT AUTHORIZED" in combined
    assert "WP176" in combined and "NOT STARTED" in combined
    assert "Credentials: 0" in fragment
    assert "real orders: 0" in fragment
    assert "Real provider/model call count: 0" in fragment
    assert "capital at risk: USD 0" in fragment
    assert "Merge authorized: NO" in combined


def test_wp175j_repo_truth_registers_bounded_parser_correction() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "WP175J.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((index, status, deferred, fragment))
    assert "WP175J Hermes Version Banner Preflight Parser Correction" in index
    assert "S10-HERMES-01B" in combined
    assert "exact 12-file" in combined
    assert "Hermes Agent v0.21.3 (2026.9.14)" in combined
    assert "2026.9.14" in combined and "release date" in combined
    assert "WP175I / PR #182 merged" in combined
    assert "BLOCKED_BY_WP175J_VERSION_PREFLIGHT_PARSER_CORRECTION" in deferred
    assert "real H1 research invocations 0" in index
    assert "fresh-human-authorized S10-GATE-H1" in combined
    assert "immediate successor is resumed" in index
    assert "genuine H1 PASS plus Side11 review unlocks S10-ALPHA-01" in index
    assert "Gate C" in combined and "NOT AUTHORIZED" in combined
    assert "Alpha Factory" in combined and "NOT STARTED" in combined
    assert "WP176" in combined and "NOT STARTED" in combined
    assert "Merge authorized: NO" in combined


def test_wp175k_repo_truth_registers_sanitized_failure_evidence_hardening() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "WP175K.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((index, status, deferred, fragment))
    assert "WP175K Sanitized Hermes Failure-Evidence Capture Hardening" in index
    assert "current review target" in index
    assert "S10-HERMES-01C" in combined
    assert "exact 14-file" in combined
    assert "WP175J / PR #183 merged" in combined or "WP175J / PR #183 merged: YES" in combined
    # Incident + diagnostics truth (the one authorized H1 run was consumed and failed).
    assert "S10-GATE-H1 single authorized real invocation consumed = 1" in combined
    assert "EXIT_CODE_NONZERO" in combined
    assert "ROOT_CAUSE_NARROWED_NOT_CONFIRMED" in combined
    assert "PREACCOUNTING_PATHS_PASS_ROOT_CAUSE_STILL_UNRECOVERABLE" in combined
    # Evidence-hardening contract truth.
    assert "hermes-research-run-receipt/1.2.0" in combined
    assert "MAX_SANITIZED_STDERR_EXCERPT_BYTES = 4096" in combined
    assert "raw stderr" in combined.lower()
    assert "stderr_excerpt" in combined
    # The dedicated WP175K deferred section blocks any second H1 run behind governance.
    assert "BLOCKED_PENDING_SEPARATE_HUMAN_GOVERNANCE_DECISION" in deferred
    # Authority + successor boundary.
    assert "H1 rerun" in combined and "NOT AUTHORIZED" in combined
    assert "S10-ALPHA-01" in combined and "BLOCKED" in combined
    assert "Gate C" in combined and "NOT AUTHORIZED" in combined
    assert "Alpha Factory" in combined and "NOT STARTED" in combined
    assert "WP176" in combined and "NOT STARTED" in combined
    assert "separate human/governance decision" in combined.lower()
    assert "Merge authorized: NO" in combined


def test_wp175l_repo_truth_registers_sanitized_windows_runtime() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "WP175L.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((index, status, deferred, fragment))
    assert "WP175L Sanitized Windows Runtime Envelope And Startup Preflight" in index
    assert "current review target" in index
    assert "S10-HERMES-01D" in combined
    assert "exact 12-file" in combined
    assert "WP175K / PR #184 merged" in combined
    # Confirmed root cause + why --version missed it.
    assert "Historical real H1 research invocations consumed = 2" in combined
    assert (
        "CONTROLLED_WINDOWS_RUNTIME_ENVIRONMENT_INSUFFICIENT_FOR_HERMES_PROFILE_INITIALIZATION"
        in combined
    )
    assert "Could not determine home directory" in combined
    assert "fast-version path" in combined
    assert "_get_platform_default_hermes_home" in combined
    # Runtime-envelope + preflight contract truth (hybrid design, Finding E).
    assert "SANITIZED RUNTIME ENVELOPE" in combined
    assert "os.environ.copy()" in combined
    assert "LOCALAPPDATA" in combined
    assert "STARTUP_PREFLIGHT_FAILED" in combined
    assert "transport_attempt_count" in combined
    assert "Finding E" in combined
    assert "HYBRID SANITIZED\nRUNTIME ENVELOPE" in index or "HYBRID SANITIZED RUNTIME ENVELOPE" in combined.replace("\n", " ")
    assert "active_profile" in combined
    assert "SYNTHESIZES" in combined or "synthetic" in combined.lower()
    # Finding F: current WP175L truth names the THIRD real H1 run (H1 #3), not "second".
    wp175l_section = index.split("## WP175L", 1)[1].split("## WP175K", 1)[0]
    assert "Historical real H1 research invocations consumed = 2" in wp175l_section
    assert "third real S10-GATE-H1 run (H1 #3)" in wp175l_section
    assert "second real S10-GATE-H1 run" not in wp175l_section
    # Current WP175L deferred rows name H1 #3 / third run.
    assert "Third real S10-GATE-H1 run (H1 #3) decision" in deferred
    assert "H1 #3 / third-run governance decision" in deferred
    # Historical WP175K rows are preserved unchanged (history is not rewritten).
    assert "WP175K-D001 | Second real S10-GATE-H1 run decision" in deferred
    # The WP175L deferred section blocks any second H1 run behind governance.
    assert "BLOCKED_PENDING_SEPARATE_HUMAN_GOVERNANCE_DECISION" in deferred
    assert "WP175L-D001" in deferred and "WP175L-D002" in deferred
    # Wallet-intelligence roadmap anchor persisted; not global; no live shortcut.
    assert "Wallet-Intelligence Roadmap Anchor" in deferred
    assert "WALLET-01" in deferred and "GATE-WALLET-01" in deferred
    assert "wallet gate is wallet-specific and not global" in deferred
    assert "no wallet live shortcut created" in deferred.lower()
    # Authority + successor boundary.
    assert "H1 #3 is NOT AUTHORIZED" in combined
    assert "S10-ALPHA-01" in combined and "BLOCKED" in combined
    assert "Gate C" in combined and "NOT AUTHORIZED" in combined
    assert "Alpha Factory" in combined and "NOT STARTED" in combined
    assert "WP176" in combined and "NOT STARTED" in combined
    assert "Merge authorized: NO" in combined or "merge is NOT AUTHORIZED" in combined
