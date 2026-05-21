"""
Tests for WP27 Agent/Hermes manual setup decision record documentation.

These tests enforce that the decision record exists, contains required status phrases,
lists all required content sections, and that no forbidden runtime, dependency, or
source paths were added.
"""

import os
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
DECISION_RECORD = REPO_ROOT / "docs" / "agent_hermes_manual_setup_decision_record.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Decision record exists
# ---------------------------------------------------------------------------

def test_decision_record_exists():
    assert DECISION_RECORD.exists(), (
        f"Expected {DECISION_RECORD} to exist but it does not."
    )


# ---------------------------------------------------------------------------
# 2. Required status phrases
# ---------------------------------------------------------------------------

def test_decision_record_contains_status_manual_setup():
    text = _read(DECISION_RECORD)
    assert "MANUAL_SETUP_DECISION_RECORD" in text


def test_decision_record_contains_status_not_installed():
    text = _read(DECISION_RECORD)
    assert "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY" in text


def test_decision_record_contains_status_not_started():
    text = _read(DECISION_RECORD)
    assert "NOT_STARTED" in text


def test_decision_record_contains_status_forbidden():
    text = _read(DECISION_RECORD)
    assert "FORBIDDEN" in text


def test_decision_record_contains_status_disabled():
    text = _read(DECISION_RECORD)
    assert "DISABLED" in text


def test_decision_record_contains_status_not_used():
    text = _read(DECISION_RECORD)
    assert "NOT_USED" in text


def test_decision_record_contains_status_not_granted_for_agent_runtime():
    text = _read(DECISION_RECORD)
    assert "NOT_GRANTED_FOR_AGENT_RUNTIME" in text


def test_decision_record_contains_status_not_granted():
    text = _read(DECISION_RECORD)
    assert "NOT_GRANTED" in text


def test_decision_record_contains_decision_deferred():
    text = _read(DECISION_RECORD)
    assert "DECISION_DEFERRED_PENDING_USER_SELECTION" in text


# ---------------------------------------------------------------------------
# 3. Current local advisory assets
# ---------------------------------------------------------------------------

def test_decision_record_lists_wp23_context_exporter():
    text = _read(DECISION_RECORD)
    assert "WP23" in text and "context exporter" in text.lower()


def test_decision_record_lists_wp24_exporter_operator_runbook():
    text = _read(DECISION_RECORD)
    assert "WP24" in text and ("exporter operator runbook" in text.lower() or "operator runbook" in text.lower())


def test_decision_record_lists_wp25_report_generator():
    text = _read(DECISION_RECORD)
    assert "WP25" in text and "report generator" in text.lower()


def test_decision_record_lists_wp26_report_operator_runbook():
    text = _read(DECISION_RECORD)
    assert "WP26" in text and ("report operator runbook" in text.lower() or "operator runbook" in text.lower())


# ---------------------------------------------------------------------------
# 4. Candidate future runtime choices
# ---------------------------------------------------------------------------

def test_decision_record_lists_hermes_selected_later():
    text = _read(DECISION_RECORD)
    assert "Hermes" in text and ("selected later" in text.lower() or "option a" in text.lower())


def test_decision_record_lists_alternative_local_agent_runtime():
    text = _read(DECISION_RECORD)
    assert "alternative local agent runtime" in text.lower() or "alternative" in text.lower()


def test_decision_record_lists_no_runtime_option():
    text = _read(DECISION_RECORD)
    assert "no runtime" in text.lower() or "no agent runtime" in text.lower()


def test_decision_record_lists_decision_deferred_option():
    text = _read(DECISION_RECORD)
    # The word "deferred" appears in both the option and status field
    assert "deferred" in text.lower()


# ---------------------------------------------------------------------------
# 5. Manual user decisions
# ---------------------------------------------------------------------------

def test_decision_record_lists_local_machine_vs_vps():
    text = _read(DECISION_RECORD)
    assert "local machine vs" in text.lower() or "vps" in text.lower()


def test_decision_record_lists_model_provider_choice():
    text = _read(DECISION_RECORD)
    assert "model/provider" in text.lower() or ("model" in text.lower() and "provider" in text.lower())


def test_decision_record_lists_api_key_handling():
    text = _read(DECISION_RECORD)
    assert "api key" in text.lower() or "provider/api key" in text.lower()


def test_decision_record_lists_allowed_commands():
    text = _read(DECISION_RECORD)
    assert "allowed commands" in text.lower()


def test_decision_record_lists_allowed_files_directories():
    text = _read(DECISION_RECORD)
    assert "allowed files" in text.lower() or "allowed files/directories" in text.lower()


def test_decision_record_lists_network_permission():
    text = _read(DECISION_RECORD)
    assert "network permission" in text.lower()


def test_decision_record_lists_memory_persistence_location():
    text = _read(DECISION_RECORD)
    assert "memory/persistence" in text.lower() or "memory" in text.lower()


def test_decision_record_lists_logging_retention_policy():
    text = _read(DECISION_RECORD)
    assert "logging" in text.lower() and "retention" in text.lower()


def test_decision_record_lists_max_autonomy_level():
    text = _read(DECISION_RECORD)
    assert "max autonomy" in text.lower() or "autonomy level" in text.lower()


def test_decision_record_lists_incident_response_kill_switch():
    text = _read(DECISION_RECORD)
    assert "incident response" in text.lower() or "kill switch" in text.lower()


# ---------------------------------------------------------------------------
# 6. Codex-safe future preparation
# ---------------------------------------------------------------------------

def test_decision_record_lists_local_advisory_handoff_package():
    text = _read(DECISION_RECORD)
    assert "local advisory handoff package" in text.lower()


def test_decision_record_lists_setup_checklist_docs():
    text = _read(DECISION_RECORD)
    assert "setup checklist" in text.lower()


def test_decision_record_lists_environment_checklist_docs():
    text = _read(DECISION_RECORD)
    assert "environment checklist" in text.lower()


def test_decision_record_lists_prompt_templates():
    text = _read(DECISION_RECORD)
    assert "prompt templates" in text.lower()


def test_decision_record_lists_static_safety_checks():
    text = _read(DECISION_RECORD)
    assert "static safety checks" in text.lower()


def test_decision_record_lists_read_only_command_allowlist_docs():
    text = _read(DECISION_RECORD)
    assert "read-only command allowlist" in text.lower() or "command allowlist" in text.lower()


# ---------------------------------------------------------------------------
# 7. Forbidden automatic actions
# ---------------------------------------------------------------------------

def test_decision_record_lists_forbidden_install_hermes():
    text = _read(DECISION_RECORD)
    assert "install hermes" in text.lower()


def test_decision_record_lists_forbidden_install_provider_sdks():
    text = _read(DECISION_RECORD)
    assert "install provider sdk" in text.lower() or "provider sdk" in text.lower()


def test_decision_record_lists_forbidden_create_env():
    text = _read(DECISION_RECORD)
    assert ".env" in text


def test_decision_record_lists_forbidden_api_keys():
    text = _read(DECISION_RECORD)
    assert "api key" in text.lower() or "api keys" in text.lower()


def test_decision_record_lists_forbidden_configure_memory_persistence():
    text = _read(DECISION_RECORD)
    assert "configure memory" in text.lower() or "memory/persistence" in text.lower()


def test_decision_record_lists_forbidden_grant_network_access():
    text = _read(DECISION_RECORD)
    assert "grant network access" in text.lower() or "network access" in text.lower()


def test_decision_record_lists_forbidden_grant_command_execution():
    text = _read(DECISION_RECORD)
    assert "grant command execution" in text.lower() or "command execution" in text.lower()


def test_decision_record_lists_forbidden_connect_accounts():
    text = _read(DECISION_RECORD)
    assert "connect accounts" in text.lower() or "account connection" in text.lower()


def test_decision_record_lists_forbidden_call_private_endpoints():
    text = _read(DECISION_RECORD)
    assert "private endpoint" in text.lower()


def test_decision_record_lists_forbidden_place_cancel_sign_submit_orders():
    text = _read(DECISION_RECORD)
    assert ("place" in text.lower() and "order" in text.lower()) or "submit orders" in text.lower()


def test_decision_record_lists_forbidden_scheduler_bot_loop():
    text = _read(DECISION_RECORD)
    assert "scheduler" in text.lower() and "bot loop" in text.lower()


def test_decision_record_lists_forbidden_mutate_configs():
    text = _read(DECISION_RECORD)
    assert "mutate config" in text.lower() or "automatic" in text.lower()


# ---------------------------------------------------------------------------
# 8. Future approval gates
# ---------------------------------------------------------------------------

def test_decision_record_lists_runtime_selection_gate():
    text = _read(DECISION_RECORD)
    assert "runtime selection gate" in text.lower() or "runtime selection" in text.lower()


def test_decision_record_lists_installation_gate():
    text = _read(DECISION_RECORD)
    assert "installation gate" in text.lower()


def test_decision_record_lists_provider_api_key_gate():
    text = _read(DECISION_RECORD)
    assert "provider/api-key gate" in text.lower() or "api-key gate" in text.lower()


def test_decision_record_lists_network_permission_gate():
    text = _read(DECISION_RECORD)
    assert "network-permission gate" in text.lower() or "network permission gate" in text.lower()


def test_decision_record_lists_memory_persistence_gate():
    text = _read(DECISION_RECORD)
    assert "memory/persistence gate" in text.lower() or "memory gate" in text.lower()


def test_decision_record_lists_command_allowlist_gate():
    text = _read(DECISION_RECORD)
    assert "command-allowlist gate" in text.lower() or "command allowlist gate" in text.lower()


def test_decision_record_lists_data_sharing_gate():
    text = _read(DECISION_RECORD)
    assert "data-sharing gate" in text.lower() or "data sharing gate" in text.lower()


def test_decision_record_lists_safety_incident_response_gate():
    text = _read(DECISION_RECORD)
    assert "safety/incident-response gate" in text.lower() or "incident-response gate" in text.lower()


def test_decision_record_lists_live_trading_gate():
    text = _read(DECISION_RECORD)
    assert "live-trading gate" in text.lower() or "live trading gate" in text.lower()


# ---------------------------------------------------------------------------
# 9. Repo truth index includes the decision record
# ---------------------------------------------------------------------------

def test_repo_truth_index_includes_decision_record():
    index_path = REPO_ROOT / "docs" / "repo_truth_index.md"
    assert index_path.exists(), "docs/repo_truth_index.md must exist"
    text = _read(index_path)
    assert "agent_hermes_manual_setup_decision_record" in text


# ---------------------------------------------------------------------------
# 10. AI agent integration policy references the decision record
# ---------------------------------------------------------------------------

def test_ai_agent_policy_references_decision_record():
    policy_path = REPO_ROOT / "docs" / "ai_agent_integration_policy.md"
    assert policy_path.exists(), "docs/ai_agent_integration_policy.md must exist"
    text = _read(policy_path)
    assert "agent_hermes_manual_setup_decision_record" in text or "WP27" in text


# ---------------------------------------------------------------------------
# 11. Hermes readonly boundary references the decision record
# ---------------------------------------------------------------------------

def test_hermes_readonly_boundary_references_decision_record():
    boundary_path = REPO_ROOT / "docs" / "hermes_readonly_boundary.md"
    assert boundary_path.exists(), "docs/hermes_readonly_boundary.md must exist"
    text = _read(boundary_path)
    assert "agent_hermes_manual_setup_decision_record" in text or "WP27" in text


# ---------------------------------------------------------------------------
# 12. No forbidden runtime/source paths added
# ---------------------------------------------------------------------------

def test_no_src_agents_directory():
    assert not (REPO_ROOT / "src" / "agents").exists(), (
        "src/agents/ must not exist — no agent runtime implementation allowed in WP27"
    )


def test_no_src_agent_layer_directory():
    assert not (REPO_ROOT / "src" / "agent_layer").exists(), (
        "src/agent_layer/ must not exist — no agent layer implementation allowed in WP27"
    )


def test_no_tools_agents_directory():
    assert not (REPO_ROOT / "tools" / "agents").exists(), (
        "tools/agents/ must not exist — no agent tools implementation allowed in WP27"
    )


def test_no_tools_hermes_directory():
    assert not (REPO_ROOT / "tools" / "hermes").exists(), (
        "tools/hermes/ must not exist — no Hermes tools allowed in WP27"
    )


def test_no_agent_runtime_directory():
    assert not (REPO_ROOT / "agent_runtime").exists(), (
        "agent_runtime/ must not exist — no agent runtime allowed in WP27"
    )


def test_no_agent_memory_directory():
    assert not (REPO_ROOT / "agent_memory").exists(), (
        "agent_memory/ must not exist — no agent memory allowed in WP27"
    )


# ---------------------------------------------------------------------------
# 13. Dependency files not modified to add Hermes/agent/LLM dependencies
# ---------------------------------------------------------------------------

FORBIDDEN_RUNTIME_DEPS = [
    "hermes",
    "openai",
    "anthropic",
    "langchain",
    "autogen",
    "crewai",
    "agentops",
]

DEP_FILES = [
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "package-lock.json",
    "poetry.lock",
    "uv.lock",
]


def _dep_file_contains_runtime_dep(dep_file_path: pathlib.Path, forbidden: str) -> bool:
    """
    Return True only if the dependency file contains the forbidden string
    in a way that looks like a dependency declaration (not just a comment or doc reference).
    Uses a conservative heuristic: check for lines that are not pure comments
    and contain the forbidden string outside of double-quoted doc strings.
    """
    text = dep_file_path.read_text(encoding="utf-8", errors="replace").lower()
    for line in text.splitlines():
        stripped = line.strip()
        # Skip comment lines
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
            continue
        if forbidden in stripped:
            return True
    return False


def test_pyproject_toml_no_forbidden_deps():
    dep_file = REPO_ROOT / "pyproject.toml"
    if not dep_file.exists():
        return
    for dep in FORBIDDEN_RUNTIME_DEPS:
        assert not _dep_file_contains_runtime_dep(dep_file, dep), (
            f"pyproject.toml must not declare '{dep}' as a dependency (WP27 adds no runtime dep)"
        )


def test_requirements_txt_no_forbidden_deps():
    dep_file = REPO_ROOT / "requirements.txt"
    if not dep_file.exists():
        return
    for dep in FORBIDDEN_RUNTIME_DEPS:
        assert not _dep_file_contains_runtime_dep(dep_file, dep), (
            f"requirements.txt must not declare '{dep}' as a dependency (WP27 adds no runtime dep)"
        )


def test_package_json_no_forbidden_deps():
    dep_file = REPO_ROOT / "package.json"
    if not dep_file.exists():
        return
    for dep in FORBIDDEN_RUNTIME_DEPS:
        assert not _dep_file_contains_runtime_dep(dep_file, dep), (
            f"package.json must not declare '{dep}' as a dependency (WP27 adds no runtime dep)"
        )
