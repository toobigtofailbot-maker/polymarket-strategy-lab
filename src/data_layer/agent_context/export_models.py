"""JSON-serializable models for the local read-only agent context export."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = "agent-context-export.v1"
EXPORT_MODE = "local_offline_read_only"
PRODUCER_NAME = "polymarket-strategy-lab-local-agent-context-exporter"
PRODUCER_VERSION = "wp23.v1"


@dataclass(frozen=True)
class Producer:
    name: str = PRODUCER_NAME
    version: str = PRODUCER_VERSION


@dataclass(frozen=True)
class IncludedLocalArtifact:
    path: str
    artifact_type: str
    provenance_classification: str
    size_bytes: int
    sha256: str
    generated_at: str | None
    included_content: bool
    sanitized_excerpt: str | None = None


@dataclass(frozen=True)
class AgentContextExport:
    schema_version: str
    export_created_at_utc: str
    export_mode: str
    producer: Producer
    source_commit: str
    repo_truth_summary: dict[str, Any]
    included_local_artifacts: list[IncludedLocalArtifact]
    data_quality_summary: dict[str, Any]
    safety_boundaries: dict[str, str]
    deferred_items: list[dict[str, str]]
    allowed_agent_uses: list[str]
    forbidden_agent_uses: list[str]
    redaction_policy: dict[str, Any]
    staleness_policy: dict[str, str]
    human_review_requirements: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_safety_boundaries() -> dict[str, str]:
    return {
        "live_trading": "DISABLED",
        "credentials": "FORBIDDEN_NOT_USED",
        "execution": "FORBIDDEN_NOT_STARTED",
        "scheduler": "NOT_STARTED",
        "bot_loop": "NOT_STARTED",
        "hermes": "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "agent_execution_authority": "FORBIDDEN",
        "fully_autonomous_trading_agent": "EXCLUDED_FOR_NOW",
        "network": "NOT_USED_BY_EXPORTER",
        "account_connection": "FORBIDDEN",
    }


def default_allowed_agent_uses() -> list[str]:
    return [
        "observe_local_repo_approved_context",
        "summarize_repo_truth_status",
        "research_open_questions_using_local_evidence",
        "propose_human_review_items",
        "draft_future_codex_wp_candidates_for_human_review",
    ]


def default_forbidden_agent_uses() -> list[str]:
    return [
        "order_placement",
        "order_cancellation",
        "order_signing",
        "order_submission",
        "trade_execution",
        "read_credentials",
        "connect_accounts",
        "call_private_endpoints",
        "perform_network_scanning",
        "mutate_configs",
        "activate_scheduler",
        "start_bot_loop",
        "run_historical_strategy_evaluation",
        "run_paper_trading",
        "make_live_trading_decisions",
        "apply_parameters_autonomously",
        "bypass_human_review",
    ]


def default_redaction_policy() -> dict[str, Any]:
    return {
        "raw_secrets_allowed": False,
        "account_data_allowed": False,
        "private_endpoint_data_allowed": False,
        "env_files_allowed": False,
        "redaction_action": "block_forbidden_paths_and_redact_secret_like_excerpts",
        "max_excerpt_chars_default": 1200,
    }


def default_staleness_policy() -> dict[str, str]:
    return {
        "repo_truth_precedence": "current_repo_truth_overrides_exported_context",
        "current_state_precedence": "current_merged_state_overrides_stale_exports",
        "stale_export_rule": "exports_have_no_authority_after_repo_truth_changes",
    }


def default_human_review_requirements() -> dict[str, str]:
    return {
        "repo_changes": "normal_codex_work_package_and_human_review_required",
        "runtime_changes": "future_approved_wp_and_human_review_required",
        "configuration_changes": "human_approved_config_change_or_codex_wp_required",
        "agent_outputs": "advisory_untrusted_until_reviewed",
    }
