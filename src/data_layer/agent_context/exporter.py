"""Local offline read-only agent context exporter."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .export_models import (
    EXPORT_MODE,
    SCHEMA_VERSION,
    AgentContextExport,
    IncludedLocalArtifact,
    Producer,
    default_allowed_agent_uses,
    default_forbidden_agent_uses,
    default_human_review_requirements,
    default_redaction_policy,
    default_safety_boundaries,
    default_staleness_policy,
)


DEFAULT_DOC_ALLOWLIST = (
    "docs/project_status.md",
    "docs/deferred_items_log.md",
    "docs/repo_truth_index.md",
    "docs/ai_agent_integration_policy.md",
    "docs/hermes_readonly_boundary.md",
    "docs/agent_context_export_schema.md",
    "docs/review_checklist.md",
    "docs/testing_requirements.md",
)

LOCAL_REPORT_METADATA_ALLOWLIST = (
    "local_data/polymarket/reports",
    "local_data/polymarket/exports",
    "local_data/polymarket/polling_runs",
)

AGENT_CONTEXT_OUTPUT_DIR = "local_data/agent_context_exports"

DEFERRED_ITEM_IDS = (
    "WP8-D002",
    "WP16-D002",
    "WP17-D001",
    "WP17-D002",
    "WP20-D001",
    "WP20-D003",
    "WP21-D001",
    "WP21-D002",
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

_SECRET_LIKE_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|credential|pass[_-]?phrase)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
    re.compile(r"(?i)(private\s+key|mne" r"monic)\s*[:=]\s*['\"]?[^'\"\n]{8,}"),
)

_GENERATED_AT_PATTERNS = (
    re.compile(r'"(?:generated_at|generated_at_utc|captured_at_utc)"\s*:\s*"([^"]+)"'),
    re.compile(r"(?i)(?:generated_at|generated_at_utc|captured_at_utc)\s*[:=]\s*([0-9TZ:.\-+]+)"),
)


def build_agent_context_export(
    *,
    repo_root: Path | None = None,
    include_local_report_metadata: bool = False,
    include_excerpts: bool = False,
    max_excerpt_chars: int = 1200,
    source_commit: str | None = None,
) -> dict:
    root = _repo_root(repo_root)
    artifacts = _collect_default_doc_artifacts(
        root,
        include_excerpts=include_excerpts,
        max_excerpt_chars=max_excerpt_chars,
    )
    if include_local_report_metadata:
        artifacts.extend(_collect_local_report_metadata(root))

    export = AgentContextExport(
        schema_version=SCHEMA_VERSION,
        export_created_at_utc=_utc_now_iso(),
        export_mode=EXPORT_MODE,
        producer=Producer(),
        source_commit=source_commit or _git_head_commit(root),
        repo_truth_summary=_build_repo_truth_summary(root),
        included_local_artifacts=artifacts,
        data_quality_summary=_build_data_quality_summary(include_local_report_metadata),
        safety_boundaries=default_safety_boundaries(),
        deferred_items=_parse_deferred_items(root),
        allowed_agent_uses=default_allowed_agent_uses(),
        forbidden_agent_uses=default_forbidden_agent_uses(),
        redaction_policy={
            **default_redaction_policy(),
            "max_excerpt_chars": max(0, max_excerpt_chars),
        },
        staleness_policy=default_staleness_policy(),
        human_review_requirements=default_human_review_requirements(),
    )
    return export.to_dict()


def write_agent_context_export(export_data: dict, output_path: Path, *, repo_root: Path | None = None) -> Path:
    root = _repo_root(repo_root)
    path = validate_agent_context_output_path(output_path, repo_root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(export_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def validate_agent_context_output_path(output_path: Path, *, repo_root: Path | None = None) -> Path:
    root = _repo_root(repo_root)
    requested = Path(output_path)
    if any(part == ".." for part in requested.parts):
        raise ValueError("Agent context export path may not contain '..'.")
    resolved = (root / requested).resolve() if not requested.is_absolute() else requested.resolve()
    allowed_dir = (root / AGENT_CONTEXT_OUTPUT_DIR).resolve()
    try:
        resolved.relative_to(allowed_dir)
    except ValueError as exc:
        raise ValueError(
            f"Agent context export output must be under {AGENT_CONTEXT_OUTPUT_DIR}/."
        ) from exc
    if resolved == allowed_dir or resolved.name in {"", ".", ".."}:
        raise ValueError("Agent context export output must be a file path.")
    return resolved


def _collect_default_doc_artifacts(
    root: Path,
    *,
    include_excerpts: bool,
    max_excerpt_chars: int,
) -> list[IncludedLocalArtifact]:
    tracked = set(_git_tracked_files(root))
    artifacts: list[IncludedLocalArtifact] = []
    for relative in DEFAULT_DOC_ALLOWLIST:
        if relative not in tracked:
            continue
        path = _safe_repo_path(root, relative)
        if not path.is_file():
            continue
        artifacts.append(
            _artifact_metadata(
                root,
                path,
                artifact_type="repo_truth_doc",
                provenance="tracked_repo_truth_doc",
                include_excerpt=include_excerpts,
                max_excerpt_chars=max_excerpt_chars,
            )
        )
    return artifacts


def _collect_local_report_metadata(root: Path) -> list[IncludedLocalArtifact]:
    artifacts: list[IncludedLocalArtifact] = []
    for relative_dir in LOCAL_REPORT_METADATA_ALLOWLIST:
        directory = _safe_repo_path(root, relative_dir)
        if not directory.exists():
            continue
        for path in sorted(p for p in directory.rglob("*") if p.is_file()):
            if _is_forbidden_path(path.relative_to(root).as_posix()):
                continue
            artifacts.append(
                _artifact_metadata(
                    root,
                    path,
                    artifact_type=_local_artifact_type(path),
                    provenance="ignored_local_repo_tool_output_metadata_only",
                    include_excerpt=False,
                    max_excerpt_chars=0,
                )
            )
    return artifacts


def _artifact_metadata(
    root: Path,
    path: Path,
    *,
    artifact_type: str,
    provenance: str,
    include_excerpt: bool,
    max_excerpt_chars: int,
) -> IncludedLocalArtifact:
    relative = path.relative_to(root).as_posix()
    if _is_forbidden_path(relative):
        raise ValueError(f"Forbidden agent context input path: {relative}")
    content = path.read_bytes()
    excerpt = None
    if include_excerpt and max_excerpt_chars > 0:
        text = content.decode("utf-8", errors="replace")
        excerpt = _redact_secret_like_text(text[:max_excerpt_chars])
    return IncludedLocalArtifact(
        path=relative,
        artifact_type=artifact_type,
        provenance_classification=provenance,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        generated_at=_parse_generated_at(content),
        included_content=excerpt is not None,
        sanitized_excerpt=excerpt,
    )


def _build_repo_truth_summary(root: Path) -> dict[str, str]:
    project_status = _read_optional_text(root / "docs/project_status.md")
    summary = {
        "live_trading": "DISABLED",
        "credentials": "NOT_USED",
        "execution": "NOT_STARTED",
        "scheduler": "NOT_STARTED",
        "bot_loop": "NOT_STARTED",
        "hermes": "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY",
        "agent_runtime": "NOT_STARTED",
        "agent_execution_authority": "FORBIDDEN",
        "fully_autonomous_trading_agent": "EXCLUDED_FOR_NOW",
    }
    for label, key in (
        ("Agent context exporter status", "agent_context_exporter"),
        ("Agent report generation status", "agent_report_generation"),
        ("Agent context export schema status", "agent_context_export_schema"),
    ):
        value = _extract_status_line(project_status, label)
        if value:
            summary[key] = value
    return summary


def _build_data_quality_summary(include_local_report_metadata: bool) -> dict[str, object]:
    return {
        "source": "repo_truth_docs_and_optional_allowlisted_local_report_metadata",
        "local_report_metadata_requested": include_local_report_metadata,
        "raw_large_payloads_included": False,
        "credentials_included": False,
        "private_endpoint_data_included": False,
    }


def _parse_deferred_items(root: Path) -> list[dict[str, str]]:
    text = _read_optional_text(root / "docs/deferred_items_log.md")
    items: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("| WP"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        item_id, title, status, priority, reason, required_before, resolution = cells[:7]
        if item_id in DEFERRED_ITEM_IDS:
            items.append(
                {
                    "id": item_id,
                    "title": title,
                    "status": status,
                    "priority": priority,
                    "reason": reason,
                    "required_before": required_before,
                    "resolution_condition": resolution,
                }
            )
    return items


def _git_head_commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unknown"
    return result.stdout.strip() or "unknown"


def _git_tracked_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return list(DEFAULT_DOC_ALLOWLIST)
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def _safe_repo_path(root: Path, relative: str) -> Path:
    if _is_forbidden_path(relative):
        raise ValueError(f"Forbidden agent context input path: {relative}")
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Agent context input path leaves repository: {relative}") from exc
    return path


def _is_forbidden_path(relative: str) -> bool:
    lowered = relative.replace("\\", "/").lower()
    parts = [part for part in lowered.split("/") if part]
    if any(part in {".env", "secrets"} for part in parts):
        return True
    filename = parts[-1] if parts else lowered
    return any(fragment in filename for fragment in _FORBIDDEN_PATH_FRAGMENTS)


def _parse_generated_at(content: bytes) -> str | None:
    text = content[:4096].decode("utf-8", errors="replace")
    for pattern in _GENERATED_AT_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def _redact_secret_like_text(text: str) -> str:
    redacted = text
    for pattern in _SECRET_LIKE_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET_LIKE_VALUE]", redacted)
    return redacted


def _extract_status_line(text: str, label: str) -> str | None:
    prefix = f"- {label}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _local_artifact_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "local_generated_report_metadata"
    if suffix == ".md":
        return "local_generated_report_markdown_metadata"
    if suffix in {".jsonl", ".csv"}:
        return "local_snapshot_summary_metadata"
    return "local_generated_artifact_metadata"


def _read_optional_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _repo_root(repo_root: Path | None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    return Path(__file__).resolve().parents[3]


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
