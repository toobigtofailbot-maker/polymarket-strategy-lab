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


# ── WP175M: Hermes draft prompt contract alignment and schema diagnostics ──────


def test_wp175m_repo_truth_registers_draft_contract_alignment() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "WP175M.md").read_text(
        encoding="utf-8"
    )
    contract = (
        ROOT / "docs" / "hermes_controlled_research_runtime_contract.md"
    ).read_text(encoding="utf-8")
    combined = "\n".join((index, status, deferred, fragment, contract))
    # WP175M is the current review target; WP175L is reconciled as merged.
    assert "WP175M Hermes Draft Prompt Contract Alignment And Schema Diagnostics" in index
    assert "current review target" in index
    assert "S10-HERMES-01E" in combined
    assert "15-file" in combined
    assert "WP175L / PR #185 merged" in combined
    # Confirmed H1 #3 incident + root cause.
    assert "Historical real H1 research invocations consumed = 3" in combined
    assert "PROMPT_OUTPUT_CONTRACT_SCHEMA_NOT_ACTUALLY_EMBEDDED" in combined
    assert "OUTPUT_SCHEMA_INVALID" in combined and "DRAFT_FIELD_MISSING" in combined
    assert "advisory_only" in combined
    # Web tool wording does not overclaim remote Firecrawl HTTP telemetry.
    assert "UNAVAILABLE_ON_PINNED_V0_21_3" in combined
    assert "web_search" in combined and "web_extract" in combined
    assert "not independently proven" in combined.lower()
    assert "title_generation" in combined
    # Contract + diagnostics + receipt design.
    assert "build_research_draft_output_schema" in combined
    assert "DRAFT_REQUIRED_TOP_LEVEL_FIELDS" in combined
    assert "CONTRACT_VALIDATOR_DRIFT" in combined
    assert "hermes-research-system-instruction/1.1.0" in combined
    assert "hermes-research-run-receipt/1.3.0" in combined
    assert "usage_session_id_digest" in combined
    assert "prompt_envelope_sha256" in combined
    # No substantive repair, no authority-flag injection.
    assert "post-hoc repair" in combined.lower() or "post-hoc substantive repair" in combined.lower()
    assert "injection is DECLINED" in combined or "injection is declined" in combined.lower()
    # Frozen request id preserved.
    assert "d977b2073c685c64a6398475ba437aa9cc63be517b2260c513ffd4e9ba795b69" in combined
    # Current WP175M truth names the FOURTH real H1 run (H1 #4), not third.
    wp175m_section = index.split("## WP175M", 1)[1].split("## WP175L", 1)[0]
    assert "Historical real H1 research invocations consumed = 3" in wp175m_section
    assert "fourth real\nS10-GATE-H1 run (H1 #4)" in wp175m_section or "fourth real S10-GATE-H1 run (H1 #4)" in wp175m_section.replace("\n", " ")
    assert "H1 #4 is\nNOT AUTHORIZED" in wp175m_section or "H1 #4 is NOT AUTHORIZED" in wp175m_section.replace("\n", " ")
    # Current WP175M deferred rows name H1 #4 / fourth run; historical WP175L/WP175K rows preserved.
    assert "Fourth real S10-GATE-H1 run (H1 #4) decision" in deferred
    assert "WP175M-D001" in deferred and "WP175M-D002" in deferred
    assert "BLOCKED_PENDING_SEPARATE_HUMAN_GOVERNANCE_DECISION" in deferred
    assert "WP175L-D002 | Third real S10-GATE-H1 run (H1 #3) decision" in deferred
    assert "WP175K-D001 | Second real S10-GATE-H1 run decision" in deferred
    # Wallet-intelligence roadmap anchor persisted; not global; no live shortcut.
    assert "Wallet-Intelligence Roadmap Anchor" in deferred
    assert "WALLET-01" in deferred and "GATE-WALLET-01" in deferred
    assert "wallet gate is wallet-specific and not global" in deferred
    assert "no wallet live shortcut created" in deferred.lower()
    # Authority + successor boundary.
    assert "H1 #4 is NOT AUTHORIZED" in combined
    assert "S10-ALPHA-01" in combined and "BLOCKED" in combined
    assert "Gate C" in combined and "NOT AUTHORIZED" in combined
    assert "Alpha Factory" in combined and "NOT STARTED" in combined
    assert "WP176" in combined and "NOT STARTED" in combined
    assert "merge is NOT AUTHORIZED" in combined or "Merge authorized: NO" in combined


def test_s10_hermes_ctx_repo_truth_is_stable_and_non_authorizing():
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "S10-HERMES-CTX-01.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "long_term_bot_completion_roadmap.md").read_text(encoding="utf-8")
    combined = index + fragment + roadmap
    assert "the exact 34-path machine\npackage" in index
    assert "the exact 29-path machine\npackage" not in index
    assert "7495427820c892497e9c195a8b130c2d32102c67" in combined
    assert "S10-WALLET-01" in combined and "COMPLETE" in combined
    assert "S10-WALLET-02" in combined and "S10-ALPHA-02" in combined
    assert "H1 #5" in combined and "NOT AUTHORIZED" in combined
    assert "Merge authorized: NO" in fragment
    assert "Current live PR head" not in fragment


def test_s10_wallet02_repo_truth_and_successor() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "wallet_profile_snapshot_contract.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "S10-WALLET-02.md").read_text(encoding="utf-8")
    combined = "\n".join((index, contract, fragment))
    assert "S10-WALLET-02 PIT Wallet Profiles (merged historical truth)" in index
    assert "S10-HERMES-CTX-01 Blind-First Context Broker (merged historical truth)" in index
    assert "docs/wallet_profile_snapshot_contract.md" in index
    assert "src/data_layer/wallet_intelligence/profile.py" in index
    assert "tests/data_layer/wallet_intelligence/test_profile.py" in index
    for record in ("WalletProfileMarketContext", "WalletDiscoveryCohortSnapshot", "WalletProfileSnapshot"):
        assert record in combined
    assert "WP79" in combined and "fixture" in combined.lower() and "not canonical" in combined.lower()
    assert "WALLET-03" in combined and "WALLET-04" in combined
    assert "S10-ALPHA-02" in combined and "current" in combined
    assert "H1 #5" in combined and "NOT AUTHORIZED" in combined
    assert "Gate C: NOT AUTHORIZED" in combined
    assert "PR #190" in combined


def test_s10_alpha02_repo_truth_and_successor() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "alpha_discovery_control_plane_contract.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "S10-ALPHA-02.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    combined = "\n".join((index, contract, fragment, deferred))
    assert "S10-ALPHA-02 PIT Alpha Discovery Control Plane (merged historical truth)" in index
    for path in (
        "docs/alpha_discovery_control_plane_contract.md",
        "src/data_layer/analytical_research/alpha_discovery.py",
        "src/data_layer/analytical_research/alpha_discovery_registry.py",
        "tests/data_layer/analytical_research/test_alpha_discovery.py",
        "tests/data_layer/analytical_research/test_alpha_discovery_registry.py",
        "tests/data_layer/analytical_research/test_alpha_discovery_boundaries.py",
        "docs/wp_specs/S10-ALPHA-02/",
        "docs/status_entries/S10-ALPHA-02.md",
    ):
        assert path in index
    assert "a2fba4d770cd6fac1cfb551419d040d65768a8e9" in combined
    assert "2d53af9b3a51f8f9a27334e8bc3b2c40efe6864a" in combined
    assert "BOUNDED_OBSERVED_UNIVERSE" in combined and "UNPROVEN" in combined
    assert "s10-alpha-discovery-registry" in combined and "1464877426" in combined
    assert "S10-GATE-AF1" in combined and "S10-ALPHA-03" in combined and "S10-ALPHA-04" in combined
    assert "H1 #5" in combined and "NOT AUTHORIZED" in combined
    assert "Merge authorized: NO" in fragment
    assert "RESOLVED_BY_S10_ALPHA_02_BOUNDED_SCOPE" in deferred


def test_wp156a_repo_truth_and_successor_boundary() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    contract = (
        ROOT
        / "docs"
        / "point_in_time_observation_schema_validator_and_synthetic_fixture_implementation.md"
    ).read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "WP156A.md").read_text(
        encoding="utf-8"
    )
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((index, contract, fragment, deferred))
    assert "WP156A Large Canonical Payload Batch Fingerprint Correction" in index
    assert "46bc862018208b30971228ed719c7e9337142b41" in combined
    assert "WP164A_PUBLIC_SMOKE_BATCH_INVALID" in combined
    assert "PAYLOAD_STRING_LIMIT_EXCEEDED" in combined
    assert "canonical_payload_json_sha256" in combined
    assert "canonical_payload_json_byte_length" in combined
    assert "Attempt-02" in combined and "permanently consumed" in combined
    assert "Product/public network calls: 0" in fragment
    assert "AF1 Attempt-03: unauthorized" in fragment
    assert "Merge authorized: YES, conditionally" in fragment
    assert "SIDE12 WP156A final one-shot" in combined
    assert "WP164A" in fragment and "separately authorized" in fragment


def test_wp164a_repo_truth_is_merged_runtime_certified_dependency() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "WP164A.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((index, fragment))
    assert (
        "WP164A Public Population Compatibility Repair (merged runtime-certified dependency)"
        in index
    )
    assert "docs/wp_specs/WP164A/" in index
    assert "9332aa2b2591d7e3fb015ae10165f063aeb8fa1d" in combined
    assert "complete typed WP156 batch" in combined
    assert "25-market/1-book" in combined
    assert "zero real public-product calls" in combined
    assert "exact governed scope from 11 to 13 paths" in combined
    assert "WP165/WP166 test fixtures" in combined
    assert "active=True" in combined and "closed=False" in combined
    assert "31379495e70dee1a0d698300e3371911af62de3a" in combined
    assert "17ce49aa96c798244d852fc5daf16299bee79ef9" in combined
    assert "WP164A_PUBLIC_SMOKE_LOCAL_EVIDENCE_DEFECT" in combined
    assert "six additive build fields" in combined
    assert "PAYLOAD_SEQUENCE_LIMIT_EXCEEDED" in combined
    assert "Attempt-02 is permanently consumed" in combined
    assert "exact package from 13 to 14 paths" in combined
    assert "tools/polymarket/run_wp164a_public_smoke.py" in combined
    assert "wp164a-public-smoke-authorization-envelope/1.0.0" in combined
    assert "5a7044147c018389402e71f35a759e1d621c4b25" in combined
    # Frozen historical pre-smoke authorization evidence stays in the fragment.
    assert "S10-GATE-AF1 remains blocked" in fragment
    assert "WP164A_PUBLIC_SMOKE_AUTHORIZATION_REQUIRED" in fragment
    assert "I_AUTHORIZE_EXACT_WP164A_PUBLIC_SMOKE_ATTEMPT_03" in fragment
    # Current truth in the index is post-smoke and post-merge.
    assert "S10-GATE-AF1 remains blocked" not in index
    assert "1c7de22f31cd093771d6bc0748c440ad5284b105" in index
    assert "70f867bdcd5e97b0dc05d4008c2c023feb461658" in index
    assert "WP164A_PUBLIC_SMOKE_COMPLETE_SUCCESS" in index
    assert "EVENT_TIME_MISSING_ALLOWED" in index
    assert "historical runtime evidence, not future guarantees" in index
    assert "WP164A dependency certification is COMPLETE" in index
    assert "S10-GATE-AF1 is no longer blocked by WP164A" in index
    assert "AF1 Attempt-03 itself remains NOT AUTHORIZED" in index
    assert "There is no WP164A Attempt-04" in index


def test_s10_gate_af1_contract_and_phase_a_evidence_are_registered() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    project = (ROOT / "docs" / "project_status.md").read_text(encoding="utf-8")
    contract = ROOT / "docs" / "alpha_factory_research_system_gate_contract.md"
    evidence = ROOT / "docs" / "gate_evidence" / "S10-GATE-AF1" / "af1_gate_evidence.json"
    assert contract.is_file() and evidence.is_file()
    assert "alpha_factory_research_system_gate_contract.md" in index
    assert "PHASE_A_IMPLEMENTED_RUNTIME_NOT_AUTHORIZED" in project
    assert "Real public population, Hermes-provider" in index


def test_s10_gate_af1_correction_is_registered_without_runtime_authority() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "S10-GATE-AF1 research-system gate (Phase-A correction target; post-WP164A recertification)" in index
    assert "retry_limit=0" in index
    assert "public_population_result_sha256" in index
    assert "No new population or provider call" in index
    assert "70f867bdcd5e97b0dc05d4008c2c023feb461658" in index
    assert "complete 38-field WP164A population" in index
    assert "AF1_RUNTIME_AUTHORIZATION_REQUIRED" in index
    fragment = (ROOT / "docs" / "status_entries" / "S10-GATE-AF1.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "alpha_factory_research_system_gate_contract.md").read_text(encoding="utf-8")
    assert "Base: `70f867bdcd5e97b0dc05d4008c2c023feb461658`" in fragment
    assert "PR #193 / `WP164A`" in fragment and "AF1 Attempt-03 NOT AUTHORIZED" in fragment
    assert "Post-WP164A reconciliation and Phase-A recertification" in contract
    assert "38-field" in contract and "REQUIRED_LANE_NOT_RESEARCH_EXECUTABLE" in contract


def test_s10_hermes_ctx02_repo_truth_registers_exact_stock_only_soul() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "S10-HERMES-CTX-02.md").read_text(
        encoding="utf-8"
    )
    contract = (ROOT / "docs" / "hermes_controlled_research_runtime_contract.md").read_text(
        encoding="utf-8"
    )
    digest = "36c1f5a2e92cd1d018311eaf4c8f1e8886672eae78212e033c681d0e3d5d506f"
    assert (
        "S10-HERMES-CTX-02 Pinned Default SOUL.md Compatibility Repair "
        "(current bounded compatibility repair)"
    ) in index
    assert "docs/wp_specs/S10-HERMES-CTX-02/" in index
    assert "docs/status_entries/S10-HERMES-CTX-02.md" in index
    assert "src/research_runtime/hermes_controlled_runtime/runner.py" in index
    assert "tests/research_runtime/hermes_controlled_runtime/test_runner.py" in index
    assert "docs/hermes_controlled_research_runtime_contract.md" in index
    # Historical package entries remain intact.
    assert "WP164A Public Population Compatibility Repair (merged runtime-certified dependency)" in index
    assert "S10-HERMES-CTX-01 Blind-First Context Broker (merged historical truth)" in index
    for text in (index, fragment, contract):
        assert digest in text and "667" in text
    assert "10 required = 10 allowed = 10 actual paths" in fragment
    assert "AF1 Attempt-03: UNCONSUMED and NOT AUTHORIZED" in fragment
    assert "H1 #5: NOT AUTHORIZED" in fragment and "Merge authorized: NO" in fragment
    assert "does not contain a mutable branch-head SHA" in fragment
    # Contract records exact-stock-only semantics, not a universal SOUL rejection.
    assert "exact-stock-only" in contract
    assert "the exception does NOT mean arbitrary SOUL files are" in contract
    assert "remains fail-closed" in contract
    assert "rejects SOUL/MEMORY" not in contract
    flat = " ".join(contract.replace("\n> ", " ").split())
    assert "whose values this preflight never opens or inspects" in flat
    assert "admission verification only" in flat


def test_s10_hermes_ctx03_repo_truth_registers_public_id_compatibility_rule() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "S10-HERMES-CTX-03.md").read_text(
        encoding="utf-8"
    )
    contract = (ROOT / "docs" / "hermes_controlled_research_runtime_contract.md").read_text(
        encoding="utf-8"
    )
    assert (
        "S10-HERMES-CTX-03 Canonical Public Polymarket Identifier Secret-Scanner "
        "Compatibility Repair (current bounded compatibility repair)"
    ) in index
    for path in (
        "docs/wp_specs/S10-HERMES-CTX-03/",
        "docs/status_entries/S10-HERMES-CTX-03.md",
        "src/research_runtime/hermes_controlled_runtime/models.py",
        "tests/research_runtime/hermes_controlled_runtime/test_models.py",
        "tests/research_runtime/hermes_controlled_runtime/test_context_controller.py",
        "docs/hermes_controlled_research_runtime_contract.md",
    ):
        assert path in index, path
    # Historical package entries remain intact.
    assert (
        "S10-HERMES-CTX-02 Pinned Default SOUL.md Compatibility Repair" in index
    )
    assert "S10-HERMES-CTX-01 Blind-First Context Broker (merged historical truth)" in index
    rule = "`event:polymarket:0x<exactly 64 lowercase hex>`"
    for text in (index, fragment, contract):
        assert rule in text
        assert "public_market_context" in text
    assert "AF1 gate result NONE" in index and "CONSUMED" in index
    assert "authorizes no successor AF1 attempt" in index
    assert "11 required = 11 allowed = 11 actual paths" in fragment
    assert "AF1 Attempt-03: CONSUMED, gate result NONE" in fragment
    assert "Another AF1 attempt: NOT AUTHORIZED" in fragment
    assert "neither an AF1 PASS nor an AF1 FAIL" in fragment
    assert "Network authority: NONE. Credential authority: NONE." in fragment
    assert "H1 #5: NOT AUTHORIZED" in fragment and "Merge authorized: NO" in fragment
    assert "does not contain a mutable branch-head SHA" in fragment
    flat = " ".join(contract.replace("\n> ", " ").split())
    assert "the generic long-hex rule `\\b0x[a-fA-F0-9]{40,}\\b` stays in the global secret rules" in flat
    assert "Inside `public_market_context` ONLY" in flat
    assert "The exception does not authorize wallet, account, or credential material" in flat
    assert "use the original unmasked bytes" in flat
    assert "there is no global or caller-configurable allowlist" in flat
    # Malformed canonical-looking event ids fail closed (no accepted gap remains).
    assert "must begin an exact canonical event id or fail closed" in " ".join(index.split())
    assert "Malformed-event guard" in fragment
    assert "must begin an exact, delimited canonical event id" in flat
    section_start = index.index("## S10-HERMES-CTX-03 ")
    section = index[section_start : index.index("\n## ", section_start + 1)]
    for text in (section, fragment, contract):
        assert "accepted gap" not in text and "parity" not in text
