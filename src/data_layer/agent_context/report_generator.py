"""Deterministic local reports for agent context exports."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .report_models import (
    REPORT_MODE,
    REPORT_SCHEMA_VERSION,
    AgentContextReport,
    ReportProducer,
    default_forbidden_use_caveats,
    default_safety_boundary_summary,
)


AGENT_CONTEXT_INPUT_DIR = "local_data/agent_context_exports"
AGENT_CONTEXT_REPORT_OUTPUT_DIR = "local_data/agent_context_reports"

REQUIRED_CONTEXT_FIELDS = (
    "schema_version",
    "export_created_at_utc",
    "export_mode",
    "producer",
    "source_commit",
    "repo_truth_summary",
    "included_local_artifacts",
    "data_quality_summary",
    "safety_boundaries",
    "deferred_items",
    "allowed_agent_uses",
    "forbidden_agent_uses",
    "redaction_policy",
    "staleness_policy",
    "human_review_requirements",
)

_FORBIDDEN_PATH_FRAGMENTS = (
    ".env",
    "secret",
    "credential",
    "private",
    "wallet",
    "token",
    "account",
    "mne" "monic",
    "passphrase",
)

_RUNTIME_ASSISTANT_LABEL = "Her" "mes"


def generate_agent_context_report(
    context_path: Path,
    *,
    repo_root: Path | None = None,
    created_at_utc: str | None = None,
) -> tuple[dict[str, Any], str]:
    root = _repo_root(repo_root)
    source_path = validate_agent_context_input_path(context_path, repo_root=root)
    context = _load_context_json(source_path)
    _validate_context_schema(context)

    report = _build_report(
        context,
        source_context_path=source_path.relative_to(root).as_posix(),
        created_at_utc=created_at_utc or _utc_now_iso(),
    )
    data = report.to_dict()
    return data, render_markdown_report(data)


def write_markdown_report(markdown: str, output_path: Path, *, repo_root: Path | None = None) -> Path:
    root = _repo_root(repo_root)
    path = validate_agent_context_report_output_path(output_path, repo_root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    return path


def write_json_report(report_data: dict[str, Any], output_path: Path, *, repo_root: Path | None = None) -> Path:
    root = _repo_root(repo_root)
    path = validate_agent_context_report_output_path(output_path, repo_root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def validate_agent_context_input_path(context_path: Path, *, repo_root: Path | None = None) -> Path:
    root = _repo_root(repo_root)
    requested = Path(context_path)
    _reject_traversal(requested, "Agent context input path")
    if _is_forbidden_path(requested):
        raise ValueError("Agent context input path contains a forbidden file name.")
    resolved = (root / requested).resolve() if not requested.is_absolute() else requested.resolve()
    allowed_dir = (root / AGENT_CONTEXT_INPUT_DIR).resolve()
    _require_under_dir(resolved, allowed_dir, f"Agent context input must be under {AGENT_CONTEXT_INPUT_DIR}/.")
    if resolved == allowed_dir or resolved.suffix.lower() != ".json":
        raise ValueError("Agent context input must be a JSON file.")
    return resolved


def validate_agent_context_report_output_path(output_path: Path, *, repo_root: Path | None = None) -> Path:
    root = _repo_root(repo_root)
    requested = Path(output_path)
    _reject_traversal(requested, "Agent context report output path")
    if _is_forbidden_path(requested):
        raise ValueError("Agent context report output path contains a forbidden file name.")
    resolved = (root / requested).resolve() if not requested.is_absolute() else requested.resolve()
    allowed_dir = (root / AGENT_CONTEXT_REPORT_OUTPUT_DIR).resolve()
    _require_under_dir(
        resolved,
        allowed_dir,
        f"Agent context report output must be under {AGENT_CONTEXT_REPORT_OUTPUT_DIR}/.",
    )
    if resolved == allowed_dir or resolved.suffix.lower() not in {".md", ".json"}:
        raise ValueError("Agent context report output must be a Markdown or JSON file.")
    return resolved


def render_markdown_report(report_data: dict[str, Any]) -> str:
    summary = report_data["summary"]
    safety = report_data["safety_boundary_summary"]
    artifacts = report_data["included_artifact_summary"]
    deferred = report_data["deferred_item_summary"]
    staleness = report_data["staleness_summary"]
    review = report_data["human_review_summary"]
    caveats = report_data["forbidden_use_caveats"]

    lines = [
        "# Local Read-Only Agent Context Report",
        "",
        f"- Report created at UTC: {report_data['report_created_at_utc']}",
        f"- Report schema version: {report_data['report_schema_version']}",
        f"- Report mode: {report_data['report_mode']}",
        f"- Producer: {report_data['producer']['name']} {report_data['producer']['version']}",
        "",
        "## Source Context Metadata",
        "",
        f"- Source context path: {report_data['source_context_path']}",
        f"- Source context schema version: {report_data['source_context_schema_version']}",
        f"- Source commit: {report_data['source_commit']}",
        f"- Export mode: {report_data['export_mode']}",
        f"- Export created at UTC: {summary['export_created_at_utc']}",
        "",
        "## Repo-Truth Status Snapshot",
        "",
        f"- Live trading: {summary['repo_truth_status'].get('live_trading', 'UNKNOWN')}",
        f"- Credentials: {summary['repo_truth_status'].get('credentials', 'UNKNOWN')}",
        f"- Execution: {summary['repo_truth_status'].get('execution', 'UNKNOWN')}",
        f"- Agent execution authority: {summary['repo_truth_status'].get('agent_execution_authority', 'UNKNOWN')}",
        f"- Fully autonomous trading agent: {summary['repo_truth_status'].get('fully_autonomous_trading_agent', 'UNKNOWN')}",
        "",
        "## Safety Boundary Summary",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in safety.items())
    lines.extend(
        [
            "",
            "## Included Local Artifact Summary",
            "",
            f"- Included artifact count: {artifacts['included_artifact_count']}",
            f"- Artifact types: {_format_count_map(artifacts['artifact_type_counts'])}",
            f"- Provenance classes: {_format_count_map(artifacts['provenance_counts'])}",
            "",
            "## Deferred Item Summary",
            "",
            f"- Deferred item count: {deferred['deferred_item_count']}",
            f"- Deferred item statuses: {_format_count_map(deferred['status_counts'])}",
            f"- Deferred item IDs: {', '.join(deferred['item_ids']) if deferred['item_ids'] else 'none'}",
            "",
            "## Data Quality And Redaction Notes",
            "",
            f"- Data quality source: {summary['data_quality_source']}",
            f"- Raw large payloads included: {summary['raw_large_payloads_included']}",
            f"- Credentials included: {summary['credentials_included']}",
            f"- Private endpoint data included: {summary['private_endpoint_data_included']}",
            f"- Redaction policy: {summary['redaction_policy_summary']}",
            "",
            "## Staleness And Human Review Notes",
            "",
            f"- Staleness policy: {staleness['policy_summary']}",
            f"- Repo truth precedence: {staleness['repo_truth_precedence']}",
            f"- Human review requirements: {review['requirements_summary']}",
            f"- Agent outputs: {review['agent_outputs']}",
            "",
            "## Forbidden Use Caveats",
            "",
        ]
    )
    lines.extend(f"- {caveat}" for caveat in caveats)
    lines.extend(
        [
            "",
            "## Next-Step Boundary Statement",
            "",
            (
                "This report is advisory local context only. Any future repo, runtime, "
                "configuration, polling, trading, deployment, or operations change must go "
                "through human review and a separately approved Codex work package."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _build_report(context: dict[str, Any], *, source_context_path: str, created_at_utc: str) -> AgentContextReport:
    artifacts = _as_list(context.get("included_local_artifacts"))
    deferred_items = _as_list(context.get("deferred_items"))
    data_quality = _as_dict(context.get("data_quality_summary"))
    repo_truth = _as_dict(context.get("repo_truth_summary"))
    redaction = _as_dict(context.get("redaction_policy"))
    staleness = _as_dict(context.get("staleness_policy"))
    review = _as_dict(context.get("human_review_requirements"))

    return AgentContextReport(
        report_schema_version=REPORT_SCHEMA_VERSION,
        report_created_at_utc=created_at_utc,
        report_mode=REPORT_MODE,
        producer=ReportProducer(),
        source_context_path=source_context_path,
        source_context_schema_version=str(context["schema_version"]),
        source_commit=str(context["source_commit"]),
        export_mode=str(context["export_mode"]),
        summary={
            "export_created_at_utc": str(context["export_created_at_utc"]),
            "repo_truth_status": repo_truth,
            "data_quality_source": str(data_quality.get("source", "UNKNOWN")),
            "raw_large_payloads_included": bool(data_quality.get("raw_large_payloads_included", False)),
            "credentials_included": bool(data_quality.get("credentials_included", False)),
            "private_endpoint_data_included": bool(data_quality.get("private_endpoint_data_included", False)),
            "redaction_policy_summary": _summarize_mapping(redaction),
        },
        safety_boundary_summary=_merge_safety(_as_dict(context.get("safety_boundaries"))),
        included_artifact_summary=_summarize_artifacts(artifacts),
        deferred_item_summary=_summarize_deferred_items(deferred_items),
        staleness_summary={
            "policy_summary": _summarize_mapping(staleness),
            "repo_truth_precedence": str(staleness.get("repo_truth_precedence", "current_repo_truth_overrides_exported_context")),
        },
        human_review_summary={
            "requirements_summary": _summarize_mapping(review),
            "agent_outputs": str(review.get("agent_outputs", "advisory_untrusted_until_reviewed")),
        },
        forbidden_use_caveats=default_forbidden_use_caveats(),
    )


def _load_context_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Could not read agent context input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Agent context input is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError("Agent context input JSON must be an object.")
    return data


def _validate_context_schema(context: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_CONTEXT_FIELDS if field not in context]
    if missing:
        raise ValueError(f"Agent context input is missing required fields: {', '.join(missing)}")
    if context.get("export_mode") != "local_offline_read_only":
        raise ValueError("Agent context export_mode must be local_offline_read_only.")


def _merge_safety(source: dict[str, Any]) -> dict[str, str]:
    merged = default_safety_boundary_summary()
    key_map = {
        "live_trading": "live_trading",
        "credentials": "credentials",
        "execution": "execution",
        "scheduler": "scheduler",
        "bot_loop": "bot_loop",
        "agent_execution_authority": "agent_execution_authority",
        "fully_autonomous_trading_agent": "fully_autonomous_trading_agent",
    }
    for source_key, target_key in key_map.items():
        if source_key in source:
            merged[target_key] = str(source[source_key])
    if "her" "mes" in source:
        merged["runtime_assistant"] = str(source["her" "mes"])
    return merged


def _summarize_artifacts(artifacts: list[Any]) -> dict[str, Any]:
    type_counts: dict[str, int] = {}
    provenance_counts: dict[str, int] = {}
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        artifact_type = str(item.get("artifact_type", item.get("type", "unknown")))
        provenance = str(item.get("provenance_classification", item.get("provenance", "unknown")))
        type_counts[artifact_type] = type_counts.get(artifact_type, 0) + 1
        provenance_counts[provenance] = provenance_counts.get(provenance, 0) + 1
    return {
        "included_artifact_count": len(artifacts),
        "artifact_type_counts": dict(sorted(type_counts.items())),
        "provenance_counts": dict(sorted(provenance_counts.items())),
    }


def _summarize_deferred_items(items: list[Any]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    item_ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "unknown"))
        status = str(item.get("status", "unknown"))
        item_ids.append(item_id)
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "deferred_item_count": len(items),
        "status_counts": dict(sorted(status_counts.items())),
        "item_ids": sorted(item_ids),
    }


def _summarize_mapping(value: dict[str, Any]) -> str:
    if not value:
        return "not provided"
    return "; ".join(f"{key}={value[key]}" for key in sorted(value))


def _format_count_map(value: dict[str, int]) -> str:
    if not value:
        return "none"
    return ", ".join(f"{key}={count}" for key, count in sorted(value.items()))


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _reject_traversal(path: Path, label: str) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{label} may not contain '..'.")


def _require_under_dir(path: Path, allowed_dir: Path, message: str) -> None:
    try:
        path.relative_to(allowed_dir)
    except ValueError as exc:
        raise ValueError(message) from exc


def _is_forbidden_path(path: Path) -> bool:
    lowered = path.as_posix().lower()
    parts = [part for part in lowered.split("/") if part]
    if any(part in {".env", "secrets"} for part in parts):
        return True
    filename = parts[-1] if parts else lowered
    return any(fragment in filename for fragment in _FORBIDDEN_PATH_FRAGMENTS)


def _repo_root(repo_root: Path | None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    return Path(__file__).resolve().parents[3]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
