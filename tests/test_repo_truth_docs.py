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
    assert "evidence state: FINALIZED" in project
    assert "Real public population, Hermes-provider" in index


def test_s10_gate_af1_correction_is_registered_without_runtime_authority() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    assert "S10-GATE-AF1 research-system gate (finalized: AF1_PASS; Attempt-04 CONSUMED)" in index
    assert "retry_limit=0" in index
    assert "public_population_result_sha256" in index
    assert "No new population or provider call" in index
    assert "70f867bdcd5e97b0dc05d4008c2c023feb461658" in index
    assert "complete 38-field WP164A population" in index
    assert "AF1_ATTEMPT04_RUNTIME_AUTHORIZATION_REQUIRED" not in index
    assert "af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2" in index and "dead42658e8fc9139d82f772e1f2fff67ba07674" in index
    assert "all ten dimensions\nPASS" in index or "all ten dimensions PASS" in " ".join(index.split())
    assert "research-system gate success\nonly" in index or "research-system gate success only" in " ".join(index.split())
    assert "none is authorized" in " ".join(index.split())
    fragment = (ROOT / "docs" / "status_entries" / "S10-GATE-AF1.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "alpha_factory_research_system_gate_contract.md").read_text(encoding="utf-8")
    assert "Base: `1ccf42df0e95586b98c79a0bf912343f9c34df31`" in fragment
    assert "PR #195 / `S10-HERMES-CTX-03`" in fragment and "PR #194 / `S10-HERMES-CTX-02`" in fragment
    assert "15097f70f5f5358879fde73b2b30d26ecdb80402" in index and "Post-S10-HERMES-CTX-02 reconciliation" in index
    assert "1ccf42df0e95586b98c79a0bf912343f9c34df31" in index and "Post-S10-HERMES-CTX-03 reconciliation" in index
    assert "PR #193 / `WP164A`" in fragment
    # Attempt-03 is consumed historical evidence with no gate result; Attempt-04 is the successor.
    assert "AF1 Attempt-03 NOT AUTHORIZED" not in fragment
    assert "AF1 Attempt-03 CONSUMED" in fragment and "AF1 gate result NONE" in fragment
    assert "AF1 Attempt-04 UNCONSUMED" not in fragment
    assert "AF1 Attempt-04 CONSUMED" in fragment
    assert "Final AF1 outcome: `AF1_PASS`" in fragment and "af1gate:sha256:281c5e05f5e4f8e30687f232e0289b99b0719c87fab61c8b1d1d417dc0b5cbb2" in fragment
    assert "Runtime execution head: `dead42658e8fc9139d82f772e1f2fff67ba07674`" in fragment
    assert "additional AF1 attempt NOT" in " ".join(fragment.split()) or "No additional AF1 attempt is" in " ".join(fragment.split())
    assert "Merge authorized: NO" in fragment
    assert "`s10-gate-af1-attempt-04`" in fragment and "attempt-04" in index
    assert "AF1 Attempt-03 is permanently CONSUMED" in index and "AF1 gate result NONE" in index
    assert "never reuses Attempt-03 stores" in index
    assert "Post-WP164A reconciliation and Phase-A recertification" in contract
    assert "Post-S10-HERMES-CTX-03 reconciliation and Attempt-04 Phase-A refreeze" in contract
    assert "Attempt-03 (historical, permanently CONSUMED)" in contract
    assert "Attempt-04 (successor, NOT AUTHORIZED)" in contract
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


def test_s10_qual_01_repo_truth_registers_non_qualifying_packet() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "S10-QUAL-01.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "qualification_candidate_contract.md").read_text(encoding="utf-8")
    alpha = (ROOT / "docs" / "alpha_factory_core_contract.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "long_term_bot_completion_roadmap.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    section_start = index.index("## S10-QUAL-01 ")
    section = " ".join(index[section_start : index.index("\n## ", section_start + 1)].split())
    assert "(merged historical predecessor: PR #197)" in section
    assert "b5cfb9846ff78af2d1a260843d5f2f1a67639305" in section
    assert "docs/qualification_candidate_contract.md" in section
    assert "src/data_layer/analytical_research/qualification.py" in section
    assert "3b877a01ed797d26fddf81a8936c880692573028" in section
    assert "S10-QUAL-01 itself produces NO qualification PASS/FAIL/INCONCLUSIVE decision" in section
    assert "AF1_PASS remains research-system gate success only" in section
    assert "feature/model implementation remains WP170" in section
    assert "S10-GATE-QUAL-01" in section and "NOT AUTHORIZED" in section
    # AF1 predecessor truth is preserved, not rewritten.
    assert "## S10-GATE-AF1 research-system gate (finalized: AF1_PASS; Attempt-04 CONSUMED)" in index
    flat_fragment = " ".join(fragment.split())
    assert "Base: `3b877a01ed797d26fddf81a8936c880692573028`" in fragment
    assert "PR #196 / `S10-GATE-AF1`" in fragment
    assert "S10-QUAL-01 itself produces NO QUAL PASS/FAIL/INCONCLUSIVE decision" in flat_fragment
    assert "No real candidate is qualified by this implementation WP" in flat_fragment
    assert "Merge authorized: NO" in fragment
    assert "S10-GATE-QUAL-01: NOT AUTHORIZED" in flat_fragment
    assert "Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`" in fragment
    flat_contract = " ".join(contract.split())
    for text in (
        "NOT a qualification PASS", "NOT claimed to be current WP170 FeatureDefinition ids",
        "PIT_MARKET_PROBABILITY_V1", "WALLET_GATE_REQUIRED", "EVIDENCE AVAILABILITY only",
        "WP170 remains the preregistration/OOS authority", "Merge: NOT AUTHORIZED",
    ):
        assert text in flat_contract, text
    assert "## 28. S10-QUAL-01 Consumer Boundary" in alpha
    assert "S10-QUAL-01 (base 3b877a01ed797d26fddf81a8936c880692573028" in roadmap
    for item in ("S10-QUAL-01-D001", "S10-QUAL-01-D002", "S10-QUAL-01-D003", "S10-QUAL-01-D004"):
        assert f"| {item} |" in deferred, item



def test_s10_gate_qual_01_repo_truth_registers_acceptance_gate() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "S10-GATE-QUAL-01.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "qualification_gate_contract.md").read_text(encoding="utf-8")
    candidate_contract = (ROOT / "docs" / "qualification_candidate_contract.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "long_term_bot_completion_roadmap.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    section_start = index.index("## S10-GATE-QUAL-01 ")
    section = " ".join(index[section_start : index.index("\n## ", section_start + 1)].split())
    assert "(merged historical predecessor: PR #198)" in section
    assert "d7891ed63b4c58c9cc150cd0c750c262ca8e5a74" in section
    for text in (
        "docs/qualification_gate_contract.md",
        "src/data_layer/analytical_research/qualification_gate.py",
        "b5cfb9846ff78af2d1a260843d5f2f1a67639305", "652a2181926ac6f92f72d0013af99ec5e24ba892",
        "QUAL_PASS / QUAL_FAIL / QUAL_INCONCLUSIVE",
        "No real candidate was created or evaluated",
        "synthetic outcomes are test fixtures only", "merge NOT AUTHORIZED",
    ):
        assert text in section, text
    assert index.index("## S10-GATE-QUAL-01 ") < index.index("## S10-QUAL-01 ")
    flat_fragment = " ".join(fragment.split())
    for text in (
        "Base: `b5cfb9846ff78af2d1a260843d5f2f1a67639305`", "PR #197 / `S10-QUAL-01`",
        "REAL QUALIFICATION CANDIDATE EVALUATED: NO", "REAL QUALIFICATION GATE RECEIPT PERSISTED: NO",
        "Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`", "Merge authorized: NO",
        "first real candidate/evaluation: NOT AUTHORIZED BY THIS WP",
    ):
        assert text in flat_fragment, text
    flat_contract = " ".join(contract.split())
    for text in (
        "QUAL_PASS is NOT predictive edge", "ALPHA_ANCESTRY_INVALID", "MAY be older than the current head",
        "does NOT claim that PUBLIC_NON_MARKET B1 qualification feature refs are valid WP170 FeatureDefinition ids",
        "any FAIL -> QUAL_FAIL; else any INCONCLUSIVE -> QUAL_INCONCLUSIVE; else QUAL_PASS",
        "Merge: NOT AUTHORIZED",
    ):
        assert text in flat_contract, text
    assert "## 13. Merged Predecessor And Qualification Gate Consumer (S10-GATE-QUAL-01)" in candidate_contract
    assert "S10-GATE-QUAL-01 (base b5cfb9846ff78af2d1a260843d5f2f1a67639305" in roadmap
    d001 = next(line for line in deferred.splitlines() if line.startswith("| S10-QUAL-01-D001 |"))
    assert "CAPABILITY_RESOLVED_BY_S10_GATE_QUAL_01_IMPLEMENTATION" in d001
    assert "No real candidate has been evaluated or has passed" in d001
    for item in ("S10-QUAL-01-D002", "S10-QUAL-01-D003", "S10-QUAL-01-D004", "S10-GATE-QUAL-01-D001"):
        assert f"| {item} |" in deferred, item
    assert "DEFERRED_NOT_AUTHORIZED" in next(
        line for line in deferred.splitlines() if line.startswith("| S10-QUAL-01-D004 |"))



def test_s10_test_ws_01_repo_truth_registers_tests_only_sync_repair() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    fragment = (ROOT / "docs" / "status_entries" / "S10-TEST-WS-01.md").read_text(encoding="utf-8")
    section_start = index.index("## S10-TEST-WS-01 ")
    section = " ".join(index[section_start : index.index("\n## ", section_start + 1)].split())
    assert "(merged historical predecessor: PR #199)" in section
    assert "f74e183a514d21a28013bf433c79126a68c72389" in section
    for text in (
        "docs/status_entries/S10-TEST-WS-01.md",
        "tests/data_layer/polymarket/test_market_truth_websocket.py",
        "d7891ed63b4c58c9cc150cd0c750c262ca8e5a74", "ec97a25b3e3174bfa71e3799110e729247dfa026",
        "no src/ change", "no `_BACKOFF_SCHEDULE` change", "no injection API", "merge NOT AUTHORIZED",
    ):
        assert text in section, text
    assert index.index("## S10-TEST-WS-01 ") < index.index("## S10-GATE-QUAL-01 ")
    flat_fragment = " ".join(fragment.split())
    for text in (
        "Base: `d7891ed63b4c58c9cc150cd0c750c262ca8e5a74`", "PR #198 / `S10-GATE-QUAL-01`",
        "`src/` changes: 0", "`_BACKOFF_SCHEDULE`: UNCHANGED", "backoff/sleeper injection API: NONE",
        "Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`", "Merge authorized: NO",
        "20/20 runs passed",
    ):
        assert text in flat_fragment, text



def test_s10_alpha_real_01_repo_truth() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "alpha_real_non_wallet_seed_contract.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "long_term_bot_completion_roadmap.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    section_start = index.index("## S10-ALPHA-REAL-01 ")
    section = " ".join(index[section_start : index.index("\n## ", section_start + 1)].split())
    assert "(merged historical predecessor: PR #200)" in section
    assert "3d3e3b673e53dae4d2e3b28a6816264b205bb015" in section
    for text in (
        "docs/alpha_real_non_wallet_seed_contract.md", "tools/alpha/run_s10_alpha_real_01.py",
        "docs/status_entries/S10-ALPHA-REAL-01.md", "docs/wp_specs/S10-ALPHA-REAL-01/",
        "f74e183a514d21a28013bf433c79126a68c72389", "99c300421f3404a68b573674d1d6d09e8c363412",
        "no src/ change", "at most one controlled Hermes v0.21.3 research-child launch",
        "RESEARCH_SUPPORTIVE is not qualification", "S10-QUAL-REAL-01 is NOT AUTHORIZED",
        "merge NOT AUTHORIZED",
    ):
        assert text in section, text
    for claim in ("S10-QUAL-REAL-01 is AUTHORIZED", "qualified: YES", "is profitable", "paper ready: YES",
                  "live ready: YES", "Gate C is AUTHORIZED"):
        assert claim not in section, claim
    assert index.index("## S10-ALPHA-REAL-01 ") < index.index("## S10-TEST-WS-01 ")
    flat_contract = " ".join(contract.split())
    for text in (
        "RESEARCH_SUPPORTIVE is NOT qualified", "DRAFT_REVALIDATION_MISMATCH",
        "REVIEW_STATE_EVIDENCE_MISMATCH", "IDEMPOTENT_FINALIZED_SUCCESS", "ALPHA_FINALIZATION_CONFLICT",
        "HUMAN_CREDENTIAL_SETUP_REQUIRED", "`content_sha256` is null", "not invoice-attested",
        "Merge: NOT AUTHORIZED",
    ):
        assert text in flat_contract, text
    assert "S10-ALPHA-REAL-01 (base f74e183a514d21a28013bf433c79126a68c72389" in roadmap
    for item in ("S10-ALPHA-REAL-01-D001", "S10-ALPHA-REAL-01-D002", "S10-ALPHA-REAL-01-D003",
                 "S10-ALPHA-REAL-01-D004"):
        assert f"| {item} |" in deferred, item



def test_s10_ndfd_grib_01_repo_truth() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "long_term_bot_completion_roadmap.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    security = (ROOT / "docs" / "security_tooling_status.md").read_text(encoding="utf-8")
    section_start = index.index("## S10-NDFD-GRIB-01 ")
    section = " ".join(index[section_start : index.index("\n## ", section_start + 1)].split())
    assert "(merged historical predecessor: PR #201)" in section
    assert "77738717fee422fe83d8bb2b7765c36dfbe6b283" in section and "cd70800d40f60f4ec20f5b17e107cc56643562a2" in section
    for text in (
        "docs/ndfd_grib_decoder_dependency_contract.md", "docs/status_entries/S10-NDFD-GRIB-01.md",
        "docs/wp_specs/S10-NDFD-GRIB-01/", "3d3e3b673e53dae4d2e3b28a6816264b205bb015",
        "80faf1dcb32d760a15c5de3c008cd2aefa3a6f12", "no src/ change",
        "S10-NDFD-GRIB-01 enables optional offline NDFD GRIB2 decoding only",
        "global Python support remains 3.12-3.14",
        "proven only on ubuntu-24.04 / windows-2022 Python 3.12",
        "S10-QUAL-DATA-01 may be redrafted/resumed next",
        "S10-QUAL-DATA-01 itself remains unimplemented by this WP",
        "No QualificationCandidate exists yet", "no real qualification gate receipt exists yet",
        "WP170/WP172/WP173 remain not started", "Gate C is NOT AUTHORIZED", "merge NOT AUTHORIZED",
    ):
        assert text in section, text
    for claim in ("Gate C is AUTHORIZED", "S10-QUAL-DATA-01 is implemented", "qualified: YES", "live ready: YES"):
        assert claim not in section, claim
    assert index.index("## S10-NDFD-GRIB-01 ") < index.index("## S10-ALPHA-REAL-01 ")
    assert "S10-NDFD-GRIB-01 (base 3d3e3b673e53dae4d2e3b28a6816264b205bb015" in roadmap
    assert "Historical predecessor (PR #200 merged at 3d3e3b673e53dae4d2e3b28a6816264b205bb015)" in roadmap
    for item in ("S10-NDFD-GRIB-01-D001", "S10-NDFD-GRIB-01-D002", "S10-NDFD-GRIB-01-D003"):
        assert f"| {item} |" in deferred, item
    assert "## S10-NDFD-GRIB-01 Optional NDFD GRIB2 Decoder Security Posture" in security
    assert "never PASS" in security



def test_s10_qual_data_01_repo_truth() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "long_term_bot_completion_roadmap.md").read_text(encoding="utf-8")
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    section_start = index.index("## S10-QUAL-DATA-01 ")
    section = " ".join(index[section_start : index.index("\n## ", section_start + 1)].split())
    assert "(merged historical predecessor: PR #202)" in section
    assert "6f67bac990d8ab338f1b87140ae077e9df4172dd" in section and "33c031f41626550294eb6667620b4ce75589d719" in section
    for text in (
        "docs/qualification_weather_data_readiness_contract.md", "tools/qualification/run_s10_qual_data_01.py",
        "docs/status_entries/S10-QUAL-DATA-01.md", "docs/wp_specs/S10-QUAL-DATA-01/",
        "77738717fee422fe83d8bb2b7765c36dfbe6b283", "cd70800d40f60f4ec20f5b17e107cc56643562a2",
        "exact 20-path scope", "make zero network calls", "only network owner",
        "THIRD_PARTY_NATIVE_FRAME_ARCHIVE / EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION", "never canonical PIT",
        "EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION", "QUAL_DATA_READY or QUAL_DATA_INSUFFICIENT",
        "No QualificationCandidate is created and no qualification gate is run",
        "WP170/WP172/WP173 remain not started", "Gate C is NOT AUTHORIZED", "merge NOT AUTHORIZED",
    ):
        assert text in section, text
    for claim in ("Gate C is AUTHORIZED", "canonical PIT is available", "qualified: YES", "live ready: YES", "QUAL_PASS"):
        assert claim not in section, claim
    assert index.index("## S10-QUAL-DATA-01 ") < index.index("## S10-NDFD-GRIB-01 ") < index.index("## S10-ALPHA-REAL-01 ")
    assert ("Historical predecessor (PR #202 merged at 6f67bac990d8ab338f1b87140ae077e9df4172dd), formerly the bounded "
            "implementation target: S10-QUAL-DATA-01 (base 77738717fee422fe83d8bb2b7765c36dfbe6b283") in " ".join(roadmap.split())
    assert "Historical predecessor (PR #201 merged at 77738717fee422fe83d8bb2b7765c36dfbe6b283)" in roadmap
    for item in ("S10-QUAL-DATA-01-D001", "S10-QUAL-DATA-01-D002", "S10-QUAL-DATA-01-D003", "S10-QUAL-DATA-01-D004",
                 "S10-QUAL-DATA-01-D005", "S10-QUAL-DATA-01-D006", "S10-QUAL-DATA-01-D007", "S10-QUAL-DATA-01-D008",
                 "S10-QUAL-DATA-01-D009", "S10-QUAL-DATA-01-D010"):
        assert f"| {item} |" in deferred, item
    assert "DEFERRED_TO_SEPARATE_COMPATIBILITY_DECISION" in deferred
    # The authoritative replacement terminal and the retained superseded defective run are both recorded.
    assert "replacement run terminated QUAL_DATA_INSUFFICIENT (FROZEN_BUDGET_EXHAUSTED" in section
    assert "SUPERSEDED_DEFECTIVE_RUN_D008_D009" in section and "S10-QUAL-DATA-01-D008" in section
    for item in ("S10-QUAL-DATA-01-D011", "S10-QUAL-DATA-01-D012"):
        assert f"| {item} |" in deferred, item
    assert "RESOLVED_BY_SIDE14_CORRECTION_A456D2E_REPLACEMENT_RUN_0_UNSUPPORTED" in deferred


def test_s10_qual_data_02_repo_truth() -> None:
    index = (ROOT / "docs" / "repo_truth_index.md").read_text(encoding="utf-8")
    roadmap = " ".join((ROOT / "docs" / "long_term_bot_completion_roadmap.md").read_text(encoding="utf-8").split())
    deferred = (ROOT / "docs" / "deferred_items_log.md").read_text(encoding="utf-8")
    section_start = index.index("## S10-QUAL-DATA-02 ")
    section = " ".join(index[section_start : index.index("\n## ", section_start + 1)].split())
    assert "(current bounded implementation target)" in section
    for text in (
        "docs/qualification_weather_corpus_completion_contract.md", "tools/qualification/run_s10_qual_data_02.py",
        "docs/status_entries/S10-QUAL-DATA-02.md", "docs/wp_specs/S10-QUAL-DATA-02/",
        "6f67bac990d8ab338f1b87140ae077e9df4172dd", "33c031f41626550294eb6667620b4ce75589d719",
        "exact 15-path scope", "only network owner", "LABEL_V3_SOURCE_READ_FAILED",
        "failed seed entries are never admitted", "never canonical PIT",
        "EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION", "QUAL_DATA_READY or QUAL_DATA_INSUFFICIENT",
        "No QualificationCandidate is created and no qualification gate is run",
        "WP170/WP172/WP173 remain not started", "Gate C is NOT AUTHORIZED", "merge NOT AUTHORIZED",
    ):
        assert text in section, text
    for claim in ("Gate C is AUTHORIZED", "canonical PIT is available", "qualified: YES", "live ready: YES", "QUAL_PASS"):
        assert claim not in section, claim
    assert index.index("## S10-QUAL-DATA-02 ") < index.index("## S10-QUAL-DATA-01 ") < index.index("## S10-NDFD-GRIB-01 ")
    assert "Current bounded implementation target: S10-QUAL-DATA-02 (base 6f67bac990d8ab338f1b87140ae077e9df4172dd" in roadmap
    for item in ("S10-QUAL-DATA-02-D001", "S10-QUAL-DATA-02-D002", "S10-QUAL-DATA-02-D003"):
        assert f"| {item} |" in deferred, item
    # The D011/D012 predecessor items are dispositioned by this completion package, never silently dropped.
    for item in ("S10-QUAL-DATA-01-D011", "S10-QUAL-DATA-01-D012"):
        row = next(line for line in deferred.splitlines() if line.startswith(f"| {item} |"))
        assert "S10_QUAL_DATA_02" in row, item
    # The NDFD D003 row is whole again (no spliced table inside it).
    ndfd = next(line for line in deferred.splitlines() if line.startswith("| S10-NDFD-GRIB-01-D003 |"))
    assert ndfd.endswith("no QualificationCandidate or real gate receipt exists. |")
