"""Deterministic local/offline/read-only advisory consumer prototype.

Consumes only explicitly provided local agent context exports and analyst
reports from ignored local_data paths. Produces advisory-only briefs for human
review. Makes no network calls, executes no commands, and imports no project
runtime modules.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Any


SUMMARY_SCHEMA_VERSION = "local-advisory-consumer.v1"
MODE = "local_offline_read_only_advisory_consumer"

CONTEXT_EXPORT_PREFIX = "local_data/agent_context_exports/"
ANALYST_REPORT_PREFIX = "local_data/agent_context_reports/"
ADVISORY_OUTPUT_PREFIX = "local_data/advisory_outputs/"

REQUIRED_REPO_ROOT_FILES = (
    "AGENTS.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
)

REPO_TRUTH_ALLOWLIST = (
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/local_advisory_handoff_package.md",
    "docs/advisory_runtime_boundary_consumption_design.md",
    "docs/security_and_secrets.md",
    "docs/live_trading_authorization.md",
)

FORBIDDEN_OUTPUT_REMINDER = (
    "No executable trading signals, order instructions, position sizing, "
    "liquidation-sensitive bot parameters, copy-trading instructions, live or "
    "paper trading decisions, config mutations, merge-readiness claims, or "
    "implementation approvals are produced by this advisory brief."
)

REPO_TRUTH_REMINDER = (
    "Repo truth and current merged state override local exports, reports, and "
    "this advisory brief."
)

VALIDATION_REMINDER = (
    "This advisory brief is not validation, not a security check, not repo "
    "truth, and not PR approval. Required tests, security checks, changed-file "
    "inspection, and human review remain mandatory."
)

HUMAN_REVIEW_CHECKLIST = (
    "Verify current repo truth directly.",
    "Inspect the explicit local inputs before acting on the brief.",
    "Confirm no credentials, account data, private endpoint material, or raw trading instructions are present.",
    "Treat review themes as questions for humans, not implementation approval.",
    "Use a separate approved Codex work package for any repo or runtime change.",
)

SENSITIVE_PATTERNS = (
    re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----.*?"
        r"-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(r"(?i)\b(API_KEY\s*[=:]\s*)[^\"'\s,\}\]]+"),
    re.compile(r"(?i)\b(PRIVATE_KEY\s*[=:]\s*)[^\"'\s,\}\]]+"),
    re.compile(r"(?i)\b(CLOB_SECRET\s*[=:]\s*)[^\"'\s,\}\]]+"),
    re.compile(r"(?i)\b(CLOB_PASS_PHRASE\s*[=:]\s*)[^\"'\s,\}\]]+"),
    re.compile(r"(?i)\b(MNEMONIC\s*[=:]\s*)[^\n\r]+"),
    re.compile(r"(?i)\b(TOKEN\s*[=:]\s*)[^\"'\s,\}\]]+"),
    re.compile(r"(?i)\b(Bearer\s+)[A-Za-z0-9\-._~+/]{12,}=*"),
)

TRADING_LANGUAGE_PATTERNS = (
    re.compile(r"(?i)\bbuy\s+now\b"),
    re.compile(r"(?i)\bsell\s+now\b"),
    re.compile(r"(?i)\bplace\s+(?:an?\s+)?order\b"),
    re.compile(r"(?i)\bshort\s*/\s*long\s+entry\b"),
    re.compile(r"(?i)\bcopy\s+wallet\b"),
    re.compile(r"(?i)\bleverage\b"),
    re.compile(r"(?i)\bliquidation\s+price\b"),
    re.compile(r"(?i)\bposition\s+sizing\b"),
    re.compile(r"(?i)\b(order|trade)\s+instruction\b"),
)

REPORT_HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
REPORT_BULLET_PATTERN = re.compile(r"^\s{0,4}[-*]\s+(.+?)\s*$")
WARNING_LINE_PATTERN = re.compile(r"(?i)\b(warning|caution|risk|uncertain|blocked|forbidden|stale)\b")
PROVENANCE_LINE_PATTERN = re.compile(r"(?i)\b(provenance|source|generated|created|commit|schema|mode)\b")


class UsageError(ValueError):
    """CLI usage or input validation error."""


def _norm(path: str) -> str:
    value = path.replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value


def _is_absolute(path: str) -> bool:
    norm = _norm(path)
    return os.path.isabs(path) or norm.startswith("/") or (len(norm) >= 2 and norm[1] == ":")


def _reject_unsafe_relpath(path: str, label: str) -> str:
    norm = _norm(path)
    if not norm:
        raise UsageError(f"{label} path is required.")
    if _is_absolute(path):
        raise UsageError(f"{label} must be repo-relative, not absolute: {path}")
    if ".." in norm.split("/"):
        raise UsageError(f"{label} must not contain path traversal: {path}")
    return norm


def _resolve_repo_root(repo_root_arg: str) -> pathlib.Path:
    root = pathlib.Path(repo_root_arg).resolve()
    missing = [rel for rel in REQUIRED_REPO_ROOT_FILES if not (root / rel).is_file()]
    if missing:
        raise UsageError(
            f"--repo-root is missing required repo files: {', '.join(missing)}"
        )
    return root


def _resolve_allowed_input(
    path_arg: str,
    *,
    repo_root: pathlib.Path,
    allowed_prefix: str,
    label: str,
    allowed_suffixes: tuple[str, ...],
) -> pathlib.Path:
    norm = _reject_unsafe_relpath(path_arg, label)
    if not norm.startswith(allowed_prefix):
        raise UsageError(f"{label} must be under {allowed_prefix}")
    requested = repo_root / norm
    resolved = requested.resolve()
    allowed_dir = (repo_root / allowed_prefix).resolve()
    try:
        resolved.relative_to(allowed_dir)
    except ValueError as exc:
        raise UsageError(f"{label} resolves outside {allowed_prefix}") from exc
    if resolved == allowed_dir or not resolved.is_file():
        raise UsageError(f"{label} must be an existing file under {allowed_prefix}")
    if resolved.suffix.lower() not in allowed_suffixes:
        raise UsageError(f"{label} has unsupported file type: {path_arg}")
    return resolved


def _resolve_output(path_arg: str, *, repo_root: pathlib.Path) -> pathlib.Path:
    norm = _reject_unsafe_relpath(path_arg, "--output")
    if not norm.startswith(ADVISORY_OUTPUT_PREFIX):
        raise UsageError(f"--output must be under {ADVISORY_OUTPUT_PREFIX}")
    resolved = (repo_root / norm).resolve()
    allowed_dir = (repo_root / ADVISORY_OUTPUT_PREFIX).resolve()
    try:
        resolved.relative_to(allowed_dir)
    except ValueError as exc:
        raise UsageError("--output resolves outside local_data/advisory_outputs/") from exc
    if resolved == allowed_dir:
        raise UsageError("--output must be a file path.")
    return resolved


def _read_bounded(path: pathlib.Path, max_bytes: int) -> tuple[str, bool]:
    with path.open("rb") as handle:
        raw = handle.read(max_bytes + 1)
    truncated = len(raw) > max_bytes
    if truncated:
        raw = raw[:max_bytes]
    return raw.decode("utf-8", errors="replace"), truncated


def _redact_sensitive(text: str) -> tuple[str, bool, bool]:
    detected = False
    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(redacted):
            detected = True
            if "PRIVATE KEY-----" in pattern.pattern:
                redacted = pattern.sub("[REDACTED PEM PRIVATE KEY BLOCK]", redacted)
            else:
                redacted = pattern.sub(lambda m: f"{m.group(1)}[REDACTED]", redacted)
    return redacted, detected, detected


def _contains_trading_language(text: str) -> bool:
    return any(pattern.search(text) for pattern in TRADING_LANGUAGE_PATTERNS)


def _safe_str(value: Any, *, max_chars: int = 180) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text, _, _ = _redact_sensitive(text)
    if _contains_trading_language(text):
        return "trading-like language detected; content withheld"
    if len(text) > max_chars:
        return text[: max_chars - 3].rstrip() + "..."
    return text


def _cap(items: list[Any], max_items: int) -> list[Any]:
    return items[:max_items]


def _extract_context_summary(
    rel_path: str,
    text: str,
    *,
    truncated: bool,
    max_items: int,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return (
            {
                "path": rel_path,
                "input_type": "context_export_json",
                "parse_status": "invalid_json",
                "truncated": truncated,
                "metadata": {},
                "summary_points": [],
            },
            [f"{rel_path}: context export JSON parse failed: {exc.msg}"],
        )
    if not isinstance(payload, dict):
        return (
            {
                "path": rel_path,
                "input_type": "context_export_json",
                "parse_status": "not_json_object",
                "truncated": truncated,
                "metadata": {},
                "summary_points": [],
            },
            [f"{rel_path}: context export JSON root is not an object."],
        )

    metadata_keys = (
        "schema_version",
        "summary_schema_version",
        "export_created_at_utc",
        "generated_at_utc",
        "export_mode",
        "producer",
        "source_commit",
        "source_files",
        "included_local_artifacts",
        "repo_truth_summary",
        "data_quality_summary",
        "safety_boundaries",
        "deferred_items",
        "warnings",
        "provenance",
        "quality",
        "human_review_requirements",
    )
    metadata: dict[str, Any] = {}
    points: list[str] = []
    for key in metadata_keys:
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, dict):
            metadata[key] = {
                _safe_str(k, max_chars=80): _safe_str(v)
                for k, v in list(value.items())[:max_items]
            }
        elif isinstance(value, list):
            metadata[key] = [_summarize_list_item(item) for item in value[:max_items]]
        else:
            metadata[key] = _safe_str(value)

    for key in ("repo_truth_summary", "data_quality_summary", "safety_boundaries"):
        if isinstance(payload.get(key), dict):
            points.append(f"{key}: {len(payload[key])} field(s) present")
    if isinstance(payload.get("included_local_artifacts"), list):
        points.append(f"included_local_artifacts: {len(payload['included_local_artifacts'])} item(s)")
    if isinstance(payload.get("deferred_items"), list):
        points.append(f"deferred_items: {len(payload['deferred_items'])} item(s)")
    if truncated:
        warnings.append(f"{rel_path}: input was truncated at max-input-bytes.")

    return (
        {
            "path": rel_path,
            "input_type": "context_export_json",
            "parse_status": "parsed",
            "truncated": truncated,
            "metadata": metadata,
            "summary_points": _cap(points, max_items),
        },
        warnings,
    )


def _summarize_list_item(item: Any) -> Any:
    if isinstance(item, dict):
        preferred = {}
        for key in (
            "path",
            "type",
            "artifact_type",
            "provenance",
            "provenance_classification",
            "generated_at",
            "status",
            "id",
            "title",
            "source",
            "warning",
        ):
            if key in item:
                preferred[key] = _safe_str(item[key])
        return preferred or {"keys": sorted(_safe_str(key, max_chars=80) for key in item)[:8]}
    return _safe_str(item)


def _extract_report_summary(
    rel_path: str,
    text: str,
    *,
    truncated: bool,
    max_items: int,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    headings: list[str] = []
    bullets: list[str] = []
    warning_lines: list[str] = []
    provenance_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading_match = REPORT_HEADING_PATTERN.match(line)
        bullet_match = REPORT_BULLET_PATTERN.match(line)
        if heading_match and len(headings) < max_items:
            headings.append(_safe_str(heading_match.group(1)))
        elif bullet_match and len(bullets) < max_items:
            bullets.append(_safe_str(bullet_match.group(1)))
        if WARNING_LINE_PATTERN.search(stripped) and len(warning_lines) < max_items:
            warning_lines.append(_safe_str(stripped))
        if PROVENANCE_LINE_PATTERN.search(stripped) and len(provenance_lines) < max_items:
            provenance_lines.append(_safe_str(stripped))

    if truncated:
        warnings.append(f"{rel_path}: input was truncated at max-input-bytes.")
    return (
        {
            "path": rel_path,
            "input_type": "analyst_report_text",
            "parse_status": "parsed",
            "truncated": truncated,
            "headings": headings,
            "short_bullets": bullets,
            "warnings_or_risk_lines": warning_lines,
            "provenance_lines": provenance_lines,
        },
        warnings,
    )


def _read_repo_truth_reminders(repo_root: pathlib.Path) -> dict[str, Any]:
    source_files: list[str] = []
    status_lines: dict[str, str] = {}
    for rel in REPO_TRUTH_ALLOWLIST:
        path = repo_root / rel
        if not path.is_file():
            continue
        source_files.append(rel)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if rel == "docs/project_status.md":
            for label in (
                "Live trading status",
                "Credentials status",
                "Execution status",
                "Hermes status",
                "Agent runtime status",
                "Agent execution authority",
                "Fully autonomous trading agent status",
                "Scheduler status",
                "Bot loop status",
            ):
                value = _extract_status_line(text, label)
                if value:
                    status_lines[label] = _safe_str(value)
        if rel == "docs/live_trading_authorization.md" and "LIVE TRADING STATUS: DISABLED" in text:
            status_lines["Live trading authorization"] = "DISABLED"
    return {
        "source_files_used": source_files,
        "status_lines": status_lines,
        "reminder": REPO_TRUTH_REMINDER,
    }


def _extract_status_line(text: str, label: str) -> str | None:
    prefix = f"- {label}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def _build_advisory_brief(
    summaries: list[dict[str, Any]],
    *,
    trading_language_detected: bool,
) -> dict[str, list[str]]:
    observed = [
        f"{len(summaries)} explicit local input file(s) were provided.",
        "Inputs were read only from allowlisted local_data advisory paths.",
    ]
    for summary in summaries:
        observed.append(
            f"{summary['path']}: {summary['input_type']} with parse status {summary['parse_status']}."
        )

    review_themes = [
        "Compare local context claims against current repo-truth docs.",
        "Review provenance, freshness, warnings, and deferred item references.",
        "Identify whether any future action belongs in a separate approved work package.",
    ]
    if trading_language_detected:
        review_themes.append(
            "Input contained trading-like language; human review required before any use."
        )

    questions = [
        "Do the local inputs match the current merged repo truth?",
        "Are any warnings, stale context, or deferred items material to interpretation?",
        "Is the next repo-safe action documentation, test coverage, or no action?",
    ]
    risks = [
        "Local exports and reports can be stale immediately after repo changes.",
        "This deterministic summary can miss nuance in unknown or future schema fields.",
        "Sensitive redaction is best-effort and does not replace security scanning.",
    ]
    next_actions = [
        "Read current repo-truth files directly before relying on this brief.",
        "Keep generated advisory outputs under ignored local_data/advisory_outputs/ only.",
        "Use normal Codex work-package review for any repository change.",
    ]

    return {
        "Observed local context": observed,
        "Potential review themes": review_themes,
        "Questions for human review": questions,
        "Risk and uncertainty notes": risks,
        "Next repo-safe actions": next_actions,
    }


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    if args.max_input_bytes < 1000:
        raise UsageError("--max-input-bytes must be at least 1000.")
    if args.max_items < 1:
        raise UsageError("--max-items must be at least 1.")
    if not args.context_export and not args.analyst_report:
        raise UsageError("At least one --context-export or --analyst-report is required.")

    repo_root = _resolve_repo_root(args.repo_root)
    warnings: list[str] = []
    sensitive_detected = False
    redaction_applied = False
    trading_language_detected = False
    input_files: list[dict[str, str]] = []
    summaries: list[dict[str, Any]] = []

    for path_arg in args.context_export:
        path = _resolve_allowed_input(
            path_arg,
            repo_root=repo_root,
            allowed_prefix=CONTEXT_EXPORT_PREFIX,
            label="--context-export",
            allowed_suffixes=(".json",),
        )
        rel = path.relative_to(repo_root).as_posix()
        text, truncated = _read_bounded(path, args.max_input_bytes)
        trading_language_detected = trading_language_detected or _contains_trading_language(text)
        _, detected, redacted = _redact_sensitive(text)
        sensitive_detected = sensitive_detected or detected
        redaction_applied = redaction_applied or redacted
        summary, local_warnings = _extract_context_summary(
            rel,
            text,
            truncated=truncated,
            max_items=args.max_items,
        )
        input_files.append({"path": rel, "type": "context_export"})
        summaries.append(summary)
        warnings.extend(local_warnings)

    for path_arg in args.analyst_report:
        path = _resolve_allowed_input(
            path_arg,
            repo_root=repo_root,
            allowed_prefix=ANALYST_REPORT_PREFIX,
            label="--analyst-report",
            allowed_suffixes=(".md", ".txt"),
        )
        rel = path.relative_to(repo_root).as_posix()
        text, truncated = _read_bounded(path, args.max_input_bytes)
        trading_language_detected = trading_language_detected or _contains_trading_language(text)
        text, detected, redacted = _redact_sensitive(text)
        sensitive_detected = sensitive_detected or detected
        redaction_applied = redaction_applied or redacted
        summary, local_warnings = _extract_report_summary(
            rel,
            text,
            truncated=truncated,
            max_items=args.max_items,
        )
        input_files.append({"path": rel, "type": "analyst_report"})
        summaries.append(summary)
        warnings.extend(local_warnings)

    if trading_language_detected:
        warnings.append("Input contained trading-like language; human review required.")
    if sensitive_detected:
        warnings.append("Sensitive-like content was detected and redacted from output.")

    repo_truth = _read_repo_truth_reminders(repo_root)
    checklist = list(HUMAN_REVIEW_CHECKLIST) if args.include_review_checklist else []

    return {
        "summary_schema_version": SUMMARY_SCHEMA_VERSION,
        "mode": MODE,
        "advisory_only": True,
        "repo_truth_reminder": repo_truth,
        "human_review_required": True,
        "validation_reminder": VALIDATION_REMINDER,
        "input_files": input_files,
        "input_file_summaries": summaries,
        "boundary_status": {
            "local_offline_read_only": True,
            "network": "NO_NETWORK",
            "command_execution": "NO_COMMAND_EXECUTION",
            "agent_runtime": "NO_AGENT_RUNTIME",
            "runtime_assistant": "NO_HERMES_INSTALL_OR_RUNTIME",
            "llm_provider": "NO_LLM_PROVIDER_RUNTIME",
            "trading": "NO_TRADING_EXECUTION",
            "credentials": "NOT_USED",
            "advisory_authority": "ADVISORY_ONLY_HUMAN_REVIEW_REQUIRED",
        },
        "advisory_brief": _build_advisory_brief(
            summaries,
            trading_language_detected=trading_language_detected,
        ),
        "research_questions": [
            "What facts in the local inputs require verification against current repo truth?",
            "Which deferred items limit interpretation of the local advisory context?",
            "What future work, if any, can remain local/offline/read-only?",
        ],
        "risk_uncertainty_notes": [
            "The brief is deterministic and bounded; it is not semantic validation.",
            "Source context may be incomplete, stale, or generated from older commits.",
            "Human review is required before any repo or operational action.",
        ],
        "human_review_checklist": checklist,
        "forbidden_output_reminder": FORBIDDEN_OUTPUT_REMINDER,
        "sensitive_content_detected": sensitive_detected,
        "redaction_applied": redaction_applied,
        "warnings": sorted(set(warnings)),
    }


def render_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_text(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("LOCAL ADVISORY CONSUMER BRIEF")
    lines.append("Mode: local/offline/read-only")
    lines.append("Advisory-only: yes")
    lines.append("Human review required: yes")
    lines.append("")
    lines.append("Repo-truth reminder:")
    lines.append(f"- {summary['repo_truth_reminder']['reminder']}")
    lines.append(f"- {summary['validation_reminder']}")
    lines.append("")
    lines.append("Boundary status:")
    for key, value in summary["boundary_status"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("Input provenance:")
    for item in summary["input_files"]:
        lines.append(f"- {item['type']}: {item['path']}")
    lines.append("")
    for section, items in summary["advisory_brief"].items():
        lines.append(f"{section}:")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")
    lines.append("Research questions:")
    for item in summary["research_questions"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Risk and uncertainty notes:")
    for item in summary["risk_uncertainty_notes"]:
        lines.append(f"- {item}")
    lines.append("")
    if summary["human_review_checklist"]:
        lines.append("Human-review checklist:")
        for item in summary["human_review_checklist"]:
            lines.append(f"- {item}")
        lines.append("")
    if summary["warnings"]:
        lines.append("Warnings:")
        for warning in summary["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")
    lines.append("Forbidden output reminder:")
    lines.append(f"- {summary['forbidden_output_reminder']}")
    lines.append("")
    lines.append("This output is advisory-only, not repo truth, not validation, and requires human review.")
    return "\n".join(lines).rstrip() + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Consume explicitly provided local context exports and analyst reports "
            "and produce a bounded advisory-only brief. Default behavior writes no file."
        )
    )
    parser.add_argument("--context-export", action="append", default=[], metavar="PATH")
    parser.add_argument("--analyst-report", action="append", default=[], metavar="PATH")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", default=None, metavar="PATH")
    parser.add_argument("--repo-root", default=".", metavar="DIR")
    parser.add_argument("--max-input-bytes", type=int, default=200000, metavar="N")
    parser.add_argument("--max-items", type=int, default=20, metavar="N")
    parser.add_argument("--include-review-checklist", action="store_true", default=False)
    parser.add_argument("--fail-on-sensitive-hit", action="store_true", default=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        repo_root = _resolve_repo_root(args.repo_root)
        if args.output:
            output_path = _resolve_output(args.output, repo_root=repo_root)
        else:
            output_path = None
        summary = build_summary(args)
    except UsageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = render_json(summary) if args.format == "json" else render_text(summary)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    print(output, end="")
    if summary["sensitive_content_detected"] and args.fail_on_sensitive_hit:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
