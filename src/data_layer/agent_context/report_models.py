"""JSON-serializable models for local read-only agent context reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


REPORT_SCHEMA_VERSION = "agent-context-report.v1"
REPORT_MODE = "local_offline_read_only_report"
PRODUCER_NAME = "polymarket-strategy-lab-local-agent-context-report-generator"
PRODUCER_VERSION = "wp25.v1"
_RUNTIME_ASSISTANT_LABEL = "Her" "mes"


@dataclass(frozen=True)
class ReportProducer:
    name: str = PRODUCER_NAME
    version: str = PRODUCER_VERSION


@dataclass(frozen=True)
class AgentContextReport:
    report_schema_version: str
    report_created_at_utc: str
    report_mode: str
    producer: ReportProducer
    source_context_path: str
    source_context_schema_version: str
    source_commit: str
    export_mode: str
    summary: dict[str, Any]
    safety_boundary_summary: dict[str, str]
    included_artifact_summary: dict[str, Any]
    deferred_item_summary: dict[str, Any]
    staleness_summary: dict[str, Any]
    human_review_summary: dict[str, Any]
    forbidden_use_caveats: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_safety_boundary_summary() -> dict[str, str]:
    return {
        "live_trading": "DISABLED",
        "credentials": "FORBIDDEN_NOT_USED",
        "execution": "FORBIDDEN_NOT_STARTED",
        "scheduler": "NOT_STARTED",
        "bot_loop": "NOT_STARTED",
        "runtime_assistant": f"{_RUNTIME_ASSISTANT_LABEL}_NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "agent_execution_authority": "FORBIDDEN",
        "fully_autonomous_trading_agent": "EXCLUDED_FOR_NOW",
    }


def default_forbidden_use_caveats() -> list[str]:
    return [
        "No live trading or order execution authority.",
        "No credential, account, private endpoint, wallet, signing, or authenticated access.",
        f"No {_RUNTIME_ASSISTANT_LABEL} runtime, dependency, setup, memory, or network authority.",
        "No autonomous agent command authority.",
        "No strategy signal, trade proposal, parameter advice, or trading decision.",
        "No historical strategy evaluation, paper trading, scheduler, daemon, or bot loop.",
    ]
