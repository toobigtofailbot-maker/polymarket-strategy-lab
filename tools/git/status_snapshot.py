"""
Local offline read-only memory / status snapshot helper.

Reads only allowlisted local repo-truth files and .git metadata.
Makes no network calls. Executes no commands. Modifies no files by default.
Does not replace pytest, security checks, preflight tools, repo truth,
or human review. Advisory only.
"""

import argparse
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timezone
from typing import Any

SUMMARY_SCHEMA_VERSION = "1.0"

# ── Safe input allowlist ─────────────────────────────────────────────────────

SAFE_INPUT_FILES = [
    "AGENTS.md",
    "CODEX_START_HERE.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
    "docs/deferred_items_log.md",
    "docs/review_checklist.md",
    "docs/testing_requirements.md",
    "docs/ai/codex/README.md",
    "docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md",
    "docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md",
    "docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER.md",
    "docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md",
    "docs/security_and_secrets.md",
    "docs/runtime_boundaries.md",
    "docs/live_trading_authorization.md",
]

REQUIRED_REPO_ROOT_FILES = [
    "AGENTS.md",
    "docs/project_status.md",
    "docs/repo_truth_index.md",
]

# ── Prohibited path patterns (for guard checks) ───────────────────────────────

PROHIBITED_PREFIXES = [
    "local_data/",
    ".venv-security/",
    ".venv-official-client/",
    "tools/.bin/",
    "tools/security/.cache/",
    "security-scan-output/",
    "official-client-sandbox-output/",
    ".git/",
    ".pytest_cache/",
    "__pycache__/",
    "src/",
    "agent_runtime/",
    "agent_memory/",
    "tools/hermes/",
]

PROHIBITED_EXACT = [".env", ".coverage"]
PROHIBITED_STARTSWITH = [".env."]

CREDENTIAL_LIKE_NAMES = [
    r"private[_\-.]?key",
    r"wallet[_\-.]?key",
    r"mnemonic",
    r"passphrase",
    r"api[_\-.]?key",
    r"secret[_\-.]?key",
    r"credentials\.json$",
    r"keystore",
    r"id_rsa",
    r"id_ed25519",
    r"\.pem$",
    r"\.p12$",
    r"\.pfx$",
]

# ── Secret-like patterns for output sanitization ──────────────────────────────

SECRET_PATTERNS = [
    (r"(?i)(API_KEY\s*[=:]\s*)(\S+)", r"\1[REDACTED]"),
    (r"(?i)(PRIVATE_KEY\s*[=:]\s*)(\S+)", r"\1[REDACTED]"),
    (r"(?i)(CLOB_SECRET\s*[=:]\s*)(\S+)", r"\1[REDACTED]"),
    (r"(?i)(CLOB_PASS_PHRASE\s*[=:]\s*)(\S+)", r"\1[REDACTED]"),
    (r"(?i)(MNEMONIC\s*[=:]\s*)(\S+)", r"\1[REDACTED]"),
    (r"(?i)(TOKEN\s*[=:]\s*)(\S+)", r"\1[REDACTED]"),
    (r"(?i)(Bearer\s+)([A-Za-z0-9\-._~+/]{20,}=*)", r"\1[REDACTED]"),
    (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
     "[PEM_PRIVATE_KEY_REDACTED]"),
]

SECRET_DETECTION_PATTERNS = [
    r"(?i)API_KEY\s*[=:]",
    r"(?i)PRIVATE_KEY\s*[=:]",
    r"(?i)CLOB_SECRET\s*[=:]",
    r"(?i)CLOB_PASS_PHRASE\s*[=:]",
    r"(?i)MNEMONIC\s*[=:]",
    r"(?i)\bTOKEN\s*[=:]",
    r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]{20,}=*",
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
]

# ── Output restriction ────────────────────────────────────────────────────────

OUTPUT_ALLOWED_PREFIX = "local_data/status_snapshots/"

# ── Reminders ─────────────────────────────────────────────────────────────────

ADVISORY_ONLY_NOTE = (
    "ADVISORY ONLY: This snapshot summarizes repo-truth files for orientation. "
    "It does not replace repo-truth verification, security checks, pytest, "
    "preflight tools, or human review."
)

REPO_TRUTH_VERIFICATION_REMINDER = (
    "REPO-TRUTH REMINDER: Always verify current state by reading "
    "AGENTS.md, docs/project_status.md, docs/repo_truth_index.md, "
    "and active WP text directly. This snapshot may be stale."
)

VALIDATION_HUMAN_REVIEW_REMINDER = (
    "VALIDATION REMINDER: Run all required validation steps "
    "(pytest, preflight_generated_artifact_guard.py, Remote Main Sync Gate, "
    "security checks) and complete human review before requesting merge."
)


# ── Path normalization ────────────────────────────────────────────────────────

def _norm(p: str) -> str:
    s = p.replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s


def _resolve_repo_root(repo_root_arg: str) -> pathlib.Path:
    root = pathlib.Path(repo_root_arg).resolve()
    return root


def _safe_read(path: pathlib.Path, repo_root: pathlib.Path) -> str | None:
    try:
        real = path.resolve()
        # Do not follow symlinks outside repo root
        try:
            real.relative_to(repo_root.resolve())
        except ValueError:
            return None
        if real.is_file():
            return real.read_text(encoding="utf-8", errors="replace")
        return None
    except Exception:
        return None


# ── Git metadata from .git/ files (no command execution) ─────────────────────

def _resolve_git_dir(repo_root: pathlib.Path) -> pathlib.Path:
    """Resolve the actual git directory, handling worktrees where .git is a file."""
    git_path = repo_root / ".git"
    if git_path.is_dir():
        return git_path
    if git_path.is_file():
        try:
            content = git_path.read_text(encoding="utf-8").strip()
            if content.startswith("gitdir:"):
                gitdir_str = content[len("gitdir:"):].strip()
                gitdir = pathlib.Path(gitdir_str)
                if not gitdir.is_absolute():
                    gitdir = (repo_root / gitdir).resolve()
                return gitdir
        except Exception:
            pass
    return git_path


def _resolve_common_git_dir(git_dir: pathlib.Path) -> pathlib.Path:
    """Resolve the common git dir from a worktree git dir (via commondir file)."""
    commondir_file = git_dir / "commondir"
    if commondir_file.is_file():
        try:
            rel = commondir_file.read_text(encoding="utf-8").strip()
            common = (git_dir / rel).resolve()
            return common
        except Exception:
            pass
    return git_dir


def _read_git_head(repo_root: pathlib.Path) -> tuple[str, str]:
    """Return (commit_sha, branch) from .git/HEAD and packed-refs/refs. No git commands."""
    commit_sha = "unknown"
    branch = "unknown"
    git_dir = _resolve_git_dir(repo_root)
    if not git_dir.is_dir():
        return commit_sha, branch
    common_dir = _resolve_common_git_dir(git_dir)

    head_file = git_dir / "HEAD"
    if not head_file.is_file():
        return commit_sha, branch
    try:
        head_content = head_file.read_text(encoding="utf-8").strip()
    except Exception:
        return commit_sha, branch

    if head_content.startswith("ref: "):
        ref = head_content[5:].strip()
        if ref.startswith("refs/heads/"):
            branch = ref[len("refs/heads/"):]
        else:
            branch = ref
        # Try worktree refs first, then common dir refs
        for search_dir in [git_dir, common_dir]:
            ref_file = search_dir / ref.replace("/", os.sep)
            if ref_file.is_file():
                try:
                    commit_sha = ref_file.read_text(encoding="utf-8").strip()[:40]
                    break
                except Exception:
                    pass
        if commit_sha == "unknown":
            # Try packed-refs in common dir
            packed_refs = common_dir / "packed-refs"
            if packed_refs.is_file():
                try:
                    for line in packed_refs.read_text(encoding="utf-8").splitlines():
                        if line.startswith("#"):
                            continue
                        parts = line.split()
                        if len(parts) >= 2 and parts[1] == ref:
                            commit_sha = parts[0][:40]
                            break
                except Exception:
                    pass
    elif re.match(r"^[0-9a-f]{40}$", head_content, re.IGNORECASE):
        commit_sha = head_content
        branch = "HEAD_DETACHED"
    return commit_sha, branch


# ── Secret detection and redaction ────────────────────────────────────────────

def _contains_secrets(text: str) -> bool:
    for pat in SECRET_DETECTION_PATTERNS:
        if re.search(pat, text):
            return True
    return False


def _redact_secrets(text: str) -> tuple[str, bool]:
    redacted = False
    result = text
    for pat, replacement in SECRET_PATTERNS:
        new = re.sub(pat, replacement, result, flags=re.DOTALL)
        if new != result:
            redacted = True
            result = new
    return result, redacted


# ── Prohibited input path guard ───────────────────────────────────────────────

def _is_prohibited_input(rel: str) -> bool:
    r = _norm(rel)
    if r in PROHIBITED_EXACT:
        return True
    for sw in PROHIBITED_STARTSWITH:
        if r.startswith(sw):
            return True
    for prefix in PROHIBITED_PREFIXES:
        if r.startswith(prefix) or r == prefix.rstrip("/"):
            return True
    name = r.rsplit("/", 1)[-1].lower()
    for pat in CREDENTIAL_LIKE_NAMES:
        if re.search(pat, name, re.IGNORECASE):
            return True
    return False


# ── Repo-root validation ──────────────────────────────────────────────────────

def _validate_repo_root(repo_root: pathlib.Path) -> str | None:
    """Return error string or None if valid."""
    for req in REQUIRED_REPO_ROOT_FILES:
        if not (repo_root / req).is_file():
            return (
                f"repo root '{repo_root}' is missing required file '{req}'. "
                f"Required files: {', '.join(REQUIRED_REPO_ROOT_FILES)}"
            )
    return None


# ── Output path validation ────────────────────────────────────────────────────

def _validate_output_path(output_arg: str, repo_root: pathlib.Path) -> tuple[pathlib.Path | None, str | None]:
    """Return (resolved_path, error) pair."""
    norm = _norm(output_arg)
    if os.path.isabs(output_arg) or (len(output_arg) >= 3 and output_arg[1] == ":"):
        return None, f"--output must be a repo-relative path, got absolute: '{output_arg}'"
    if ".." in norm.split("/"):
        return None, f"--output path traversal rejected: '{output_arg}'"
    if not norm.startswith(OUTPUT_ALLOWED_PREFIX):
        return None, (
            f"--output must be under '{OUTPUT_ALLOWED_PREFIX}', got: '{output_arg}'"
        )
    resolved = (repo_root / norm).resolve()
    # Verify resolved is under repo_root / OUTPUT_ALLOWED_PREFIX
    allowed = (repo_root / OUTPUT_ALLOWED_PREFIX).resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError:
        return None, f"--output resolves outside allowed directory: '{output_arg}'"
    return resolved, None


def _validate_check_stale_path(path_arg: str, repo_root: pathlib.Path) -> tuple[pathlib.Path | None, str | None]:
    """Return (resolved_path, error) pair."""
    norm = _norm(path_arg)
    if os.path.isabs(path_arg) or (len(path_arg) >= 3 and path_arg[1] == ":"):
        return None, f"--check-stale must be a repo-relative path, got absolute: '{path_arg}'"
    if ".." in norm.split("/"):
        return None, f"--check-stale path traversal rejected: '{path_arg}'"
    if not norm.startswith(OUTPUT_ALLOWED_PREFIX):
        return None, (
            f"--check-stale must be under '{OUTPUT_ALLOWED_PREFIX}', got: '{path_arg}'"
        )
    resolved = (repo_root / norm).resolve()
    allowed = (repo_root / OUTPUT_ALLOWED_PREFIX).resolve()
    try:
        resolved.relative_to(allowed)
    except ValueError:
        return None, f"--check-stale resolves outside allowed directory: '{path_arg}'"
    return resolved, None


# ── File reading with sanitization ───────────────────────────────────────────

def _read_safe_file(rel: str, repo_root: pathlib.Path) -> tuple[str | None, bool]:
    """Read allowlisted file. Returns (content_or_None, was_redacted)."""
    if _is_prohibited_input(rel):
        return None, False
    path = repo_root / rel
    content = _safe_read(path, repo_root)
    if content is None:
        return None, False
    redacted, was_redacted = _redact_secrets(content)
    return redacted, was_redacted


# ── Project status parsing ────────────────────────────────────────────────────

def _parse_project_status(content: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in content.splitlines():
        stripped = line.strip()
        # Current phase
        if stripped.startswith("- Current phase:"):
            result["current_phase"] = stripped[len("- Current phase:"):].strip()
        # Current branch
        elif stripped.startswith("- Current branch:"):
            val = stripped[len("- Current branch:"):].strip().strip("`")
            result["current_branch_from_repo_truth"] = val
        # Latest merged WP from merged WPs list
        elif stripped.startswith("- Merged WPs:"):
            merged_str = stripped[len("- Merged WPs:"):].strip()
            # Extract all WP identifiers
            wps = re.findall(r"WP\d+(?:-[A-Za-z0-9\-]+)?", merged_str)
            result["merged_wps"] = wps
            if wps:
                result["latest_merged_wp"] = wps[-1]
        # Helper statuses
        elif stripped.startswith("- Memory/status snapshot helper design status:"):
            result["memory_snapshot_design_status"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Memory/status snapshot helper implementation status:"):
            result["memory_snapshot_impl_status"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Diff/scope summary helper implementation status:"):
            result["diff_scope_impl_status"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Validation-output summary helper implementation status:"):
            result["validation_output_impl_status"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Code-index / blast-radius helper implementation status:"):
            result["code_blast_radius_impl_status"] = stripped.split(":", 1)[1].strip()
        # Protected/boundary statuses
        elif stripped.startswith("- Live trading status:"):
            result["live_trading_status"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Credentials status:"):
            result["credentials_status"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Agent execution authority:"):
            result["agent_execution_authority"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Hermes status:"):
            result["hermes_status"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Execution status:"):
            result["execution_status"] = stripped.split(":", 1)[1].strip()
        # Next WP
        elif stripped.startswith("- Next intended WP:"):
            result["next_intended_wp_line"] = stripped[len("- Next intended WP:"):].strip()

    return result


def _extract_next_wp_candidates(next_wp_line: str) -> list[str]:
    """Extract WP candidate names from next intended WP line."""
    if not next_wp_line:
        return []
    candidates = re.findall(r"WP\d+[^,;]* - [^,;\.]+", next_wp_line)
    if not candidates:
        # Fallback: return first 200 chars
        return [next_wp_line[:200]]
    return [c.strip() for c in candidates[:5]]


# ── Deferred item parsing ─────────────────────────────────────────────────────

def _parse_open_deferred_items(content: str, max_items: int) -> list[dict[str, str]]:
    """Extract OPEN deferred items from deferred_items_log.md table rows."""
    items: list[dict[str, str]] = []
    in_table = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("| ID") and "Status" in stripped:
            in_table = True
            continue
        if stripped.startswith("|---"):
            continue
        if in_table and stripped.startswith("|"):
            parts = [p.strip() for p in stripped.split("|")]
            # Remove empty first/last from leading/trailing |
            parts = [p for p in parts if p]
            if len(parts) >= 3:
                item_id = parts[0]
                item_text = parts[1] if len(parts) > 1 else ""
                status = parts[2] if len(parts) > 2 else ""
                priority = parts[3] if len(parts) > 3 else ""
                if "OPEN" in status.upper():
                    items.append({
                        "id": item_id,
                        "item": item_text[:120],
                        "status": "OPEN",
                        "priority": priority,
                    })
                    if len(items) >= max_items:
                        break
        elif in_table and not stripped.startswith("|") and stripped:
            # Table ended
            if stripped.startswith("##"):
                in_table = False
    return items


# ── Helper inventory ──────────────────────────────────────────────────────────

def _build_helper_inventory(repo_root: pathlib.Path, parsed_status: dict[str, Any]) -> dict[str, Any]:
    helpers = {
        "diff_scope_summary": {
            "path": "tools/git/diff_scope_summary.py",
            "doc": "docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER.md",
            "status": parsed_status.get("diff_scope_impl_status", "UNKNOWN"),
            "exists": (repo_root / "tools/git/diff_scope_summary.py").is_file(),
        },
        "validation_output_summary": {
            "path": "tools/validation/validation_output_summary.py",
            "doc": "docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER.md",
            "status": parsed_status.get("validation_output_impl_status", "UNKNOWN"),
            "exists": (repo_root / "tools/validation/validation_output_summary.py").is_file(),
        },
        "code_blast_radius": {
            "path": "tools/git/code_blast_radius.py",
            "doc": "docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md",
            "status": parsed_status.get("code_blast_radius_impl_status", "UNKNOWN"),
            "exists": (repo_root / "tools/git/code_blast_radius.py").is_file(),
        },
        "status_snapshot": {
            "path": "tools/git/status_snapshot.py",
            "doc": "docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md",
            "status": "LOCAL_OFFLINE_READ_ONLY_HELPER_ON_BRANCH",
            "exists": (repo_root / "tools/git/status_snapshot.py").is_file(),
        },
    }
    return helpers


# ── Protected boundary status ─────────────────────────────────────────────────

def _build_protected_boundary_status(parsed_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "live_trading_status": parsed_status.get("live_trading_status", "unknown"),
        "credentials_status": parsed_status.get("credentials_status", "unknown"),
        "agent_execution_authority": parsed_status.get("agent_execution_authority", "unknown"),
        "hermes_status": parsed_status.get("hermes_status", "unknown"),
        "execution_status": parsed_status.get("execution_status", "unknown"),
        "note": (
            "Protected boundary status is derived from repo-truth docs only. "
            "This snapshot cannot authorize protected work. "
            "Security checks, explicit WP text, and human review are always required."
        ),
    }


# ── Snapshot object builder ───────────────────────────────────────────────────

def _build_snapshot(
    repo_root: pathlib.Path,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], list[str], bool, bool]:
    """Build the snapshot dict. Returns (snapshot, warnings, sensitive_detected, redaction_applied)."""
    warnings: list[str] = []
    sensitive_detected = False
    redaction_applied = False

    # Git metadata
    commit_sha, branch = _read_git_head(repo_root)
    if commit_sha == "unknown":
        warnings.append("Could not determine repo commit SHA from .git/HEAD.")
    if branch == "unknown":
        warnings.append("Could not determine repo branch from .git/HEAD.")

    # Read safe input files
    source_files_used: list[str] = []
    missing_source_files: list[str] = []
    file_contents: dict[str, str] = {}

    for rel in SAFE_INPUT_FILES:
        content, was_redacted = _read_safe_file(rel, repo_root)
        if content is not None:
            source_files_used.append(rel)
            file_contents[rel] = content
            if was_redacted:
                redaction_applied = True
                sensitive_detected = True
                warnings.append(f"Sensitive content detected and redacted in: {rel}")
            elif _contains_secrets(content):
                sensitive_detected = True
                redaction_applied = True
                warnings.append(f"Potential sensitive content in: {rel}")
        else:
            missing_source_files.append(rel)

    # Parse project status
    parsed_status: dict[str, Any] = {}
    if "docs/project_status.md" in file_contents:
        parsed_status = _parse_project_status(file_contents["docs/project_status.md"])

    current_phase = parsed_status.get("current_phase", "unknown")
    latest_merged_wp = parsed_status.get("latest_merged_wp", "unknown")
    current_branch_from_repo_truth = parsed_status.get("current_branch_from_repo_truth", "unknown")
    next_wp_line = parsed_status.get("next_intended_wp_line", "")

    # Deferred items
    open_deferred_digest: list[dict[str, str]] = []
    if args.include_deferred and "docs/deferred_items_log.md" in file_contents:
        open_deferred_digest = _parse_open_deferred_items(
            file_contents["docs/deferred_items_log.md"],
            args.max_deferred_items,
        )

    # Helper inventory
    helper_inventory: dict[str, Any] = {}
    if args.include_helper_inventory:
        helper_inventory = _build_helper_inventory(repo_root, parsed_status)

    # Protected boundary
    protected_boundary_status: dict[str, Any] = {}
    if args.include_protected_boundaries:
        protected_boundary_status = _build_protected_boundary_status(parsed_status)

    # Next WP candidates
    next_wp_candidates: list[str] = []
    if args.include_next_wp_candidates:
        next_wp_candidates = _extract_next_wp_candidates(next_wp_line)

    snapshot: dict[str, Any] = {
        "summary_schema_version": SUMMARY_SCHEMA_VERSION,
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_commit_sha": commit_sha,
        "repo_branch": branch,
        "source_files_used": source_files_used,
        "missing_source_files": missing_source_files,
        "current_phase": current_phase,
        "latest_merged_wp": latest_merged_wp,
        "latest_merge_commit": "see docs/project_status.md for authoritative value",
        "current_branch_from_repo_truth": current_branch_from_repo_truth,
        "protected_boundary_status": protected_boundary_status,
        "helper_inventory": helper_inventory,
        "open_deferred_item_digest": open_deferred_digest,
        "next_wp_candidates": next_wp_candidates,
        "validation_reporting_expectations": (
            "Run: pytest, preflight_generated_artifact_guard.py, "
            "preflight_sync_main.py (Remote Main Sync Gate), "
            "security checks (verify_project_gitleaks.py, check_security_tools.py, "
            "run_available_security_checks.py), git diff --check. "
            "Post final PR comment. Complete human review before merge."
        ),
        "generated_artifact_output_rules": (
            "Default: no file written. Optional output only under "
            "local_data/status_snapshots/ when --output is provided. "
            "Never stage or commit generated outputs."
        ),
        "manual_setup_decision_status": (
            "Hermes: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY. "
            "Agent runtime: NOT_STARTED. "
            "See docs/agent_hermes_manual_setup_decision_record.md for decision record."
        ),
        "stale_snapshot_warning": (
            "This snapshot reflects repo state at generation time. "
            "Verify against current repo-truth files before acting on it."
        ),
        "advisory_only_note": ADVISORY_ONLY_NOTE,
        "repo_truth_verification_reminder": REPO_TRUTH_VERIFICATION_REMINDER,
        "validation_human_review_reminder": VALIDATION_HUMAN_REVIEW_REMINDER,
        "sensitive_content_detected": sensitive_detected,
        "redaction_applied": redaction_applied,
        "warnings": warnings,
    }
    return snapshot, warnings, sensitive_detected, redaction_applied


# ── Staleness check ───────────────────────────────────────────────────────────

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}


def _check_stale(
    snapshot_path: pathlib.Path,
    current_commit: str,
    current_branch: str,
) -> tuple[bool, list[str]]:
    """Return (is_stale, reasons). Reads only JSON snapshots under allowed prefix."""
    reasons: list[str] = []
    if not snapshot_path.is_file():
        return True, [f"Snapshot file not found: {snapshot_path}"]
    try:
        saved = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return True, [f"Cannot parse snapshot file: {exc}"]

    schema = saved.get("summary_schema_version", "")
    if not schema:
        reasons.append("Saved snapshot is missing summary_schema_version.")
    elif schema not in SUPPORTED_SCHEMA_VERSIONS:
        reasons.append(f"Saved snapshot has unsupported schema version: '{schema}'.")

    saved_commit = saved.get("repo_commit_sha", "")
    if not saved_commit:
        reasons.append("Saved snapshot is missing repo_commit_sha.")
    elif saved_commit != "unknown" and current_commit != "unknown":
        if saved_commit != current_commit:
            reasons.append(
                f"Commit changed: saved={saved_commit[:12]} current={current_commit[:12]}"
            )

    saved_branch = saved.get("repo_branch", "")
    if not saved_branch:
        reasons.append("Saved snapshot is missing repo_branch.")
    elif saved_branch != "unknown" and current_branch != "unknown":
        if saved_branch != current_branch:
            reasons.append(
                f"Branch changed: saved={saved_branch} current={current_branch}"
            )

    ts = saved.get("generated_timestamp_utc", "")
    if not ts:
        reasons.append("Saved snapshot is missing generated_timestamp_utc.")

    return bool(reasons), reasons


# ── Text output ────────────────────────────────────────────────────────────────

def _render_text(snapshot: dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("MEMORY / STATUS SNAPSHOT (ADVISORY ONLY)")
    lines.append("=" * 72)
    lines.append(f"Schema version:    {snapshot['summary_schema_version']}")
    lines.append(f"Generated (UTC):   {snapshot['generated_timestamp_utc']}")
    lines.append(f"Repo commit SHA:   {snapshot['repo_commit_sha']}")
    lines.append(f"Repo branch:       {snapshot['repo_branch']}")
    lines.append("")
    lines.append(f"Current phase:     {snapshot['current_phase']}")
    lines.append(f"Latest merged WP:  {snapshot['latest_merged_wp']}")
    lines.append(f"Branch (repo truth): {snapshot['current_branch_from_repo_truth']}")
    lines.append("")
    lines.append("Source files used:")
    for f in snapshot["source_files_used"]:
        lines.append(f"  {f}")
    if snapshot["missing_source_files"]:
        lines.append("Missing source files:")
        for f in snapshot["missing_source_files"]:
            lines.append(f"  [missing] {f}")
    lines.append("")

    # Protected boundary
    pb = snapshot.get("protected_boundary_status")
    if pb:
        lines.append("Protected boundary status:")
        for k, v in pb.items():
            if k != "note":
                lines.append(f"  {k}: {v}")
        lines.append(f"  NOTE: {pb.get('note', '')}")
        lines.append("")

    # Helper inventory
    hi = snapshot.get("helper_inventory")
    if hi:
        lines.append("Helper inventory:")
        for name, info in hi.items():
            exists_str = "EXISTS" if info.get("exists") else "MISSING"
            lines.append(
                f"  {name}: path={info.get('path')} status={info.get('status')} [{exists_str}]"
            )
        lines.append("")

    # Deferred digest
    deferred = snapshot.get("open_deferred_item_digest")
    if deferred:
        lines.append(f"Open deferred item digest ({len(deferred)} items shown):")
        for item in deferred:
            lines.append(
                f"  [{item['id']} / {item['priority']}] {item['item'][:80]}"
            )
        lines.append("")

    # Next WP candidates
    nwp = snapshot.get("next_wp_candidates")
    if nwp:
        lines.append("Next WP candidates:")
        for c in nwp:
            lines.append(f"  - {c[:120]}")
        lines.append("")

    lines.append("Validation expectations:")
    lines.append(f"  {snapshot['validation_reporting_expectations']}")
    lines.append("")
    lines.append("Generated artifact rules:")
    lines.append(f"  {snapshot['generated_artifact_output_rules']}")
    lines.append("")
    if snapshot.get("warnings"):
        lines.append("Warnings:")
        for w in snapshot["warnings"]:
            lines.append(f"  WARNING: {w}")
        lines.append("")
    if snapshot.get("sensitive_content_detected"):
        lines.append("  SENSITIVE CONTENT DETECTED — redaction applied to output.")
        lines.append("")
    lines.append(f"ADVISORY: {snapshot['advisory_only_note']}")
    lines.append("")
    lines.append(f"REPO TRUTH: {snapshot['repo_truth_verification_reminder']}")
    lines.append("")
    lines.append(f"VALIDATION: {snapshot['validation_human_review_reminder']}")
    lines.append("=" * 72)
    return "\n".join(lines) + "\n"


# ── CLI ────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Local offline read-only memory / status snapshot helper. "
            "Summarizes repo-truth project state for Claude Code / Codex orientation. "
            "Advisory only. Does not replace repo truth, validation, security checks, "
            "or human review."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0  Snapshot generated or stale check completed without strict failure.\n"
            "  1  --fail-on-stale with stale snapshot, or --fail-on-sensitive-hit with "
            "sensitive content.\n"
            "  2  Usage or config error.\n\n"
            "Output restriction: --output must be repo-relative under "
            "local_data/status_snapshots/.\n\n"
            "ADVISORY ONLY: This helper is not a replacement for repo truth, "
            "validation, security checks, or human review."
        ),
    )
    p.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format. 'markdown' is not implemented and exits 2.",
    )
    p.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help=(
            "Optional repo-relative output path. "
            "Must be under local_data/status_snapshots/. "
            "Default: no file written."
        ),
    )
    p.add_argument(
        "--repo-root",
        metavar="DIR",
        default=".",
        help="Repository root directory. Default: current directory.",
    )
    p.add_argument(
        "--include-deferred",
        action="store_true",
        help="Include open deferred item digest.",
    )
    p.add_argument(
        "--include-helper-inventory",
        action="store_true",
        help="Include local helper tool inventory.",
    )
    p.add_argument(
        "--include-next-wp-candidates",
        action="store_true",
        help="Include next WP candidate digest from project_status.md.",
    )
    p.add_argument(
        "--include-protected-boundaries",
        action="store_true",
        help="Include protected boundary status block.",
    )
    p.add_argument(
        "--max-deferred-items",
        type=int,
        default=20,
        metavar="N",
        help="Maximum deferred items in digest. Must be >= 1. Default: 20.",
    )
    p.add_argument(
        "--check-stale",
        metavar="PATH",
        default=None,
        help=(
            "Check staleness of a previously saved JSON snapshot. "
            "Path must be under local_data/status_snapshots/."
        ),
    )
    p.add_argument(
        "--fail-on-stale",
        action="store_true",
        help="Exit 1 if --check-stale finds the snapshot is stale.",
    )
    p.add_argument(
        "--fail-on-sensitive-hit",
        action="store_true",
        help="Exit 1 if sensitive content is detected in output.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # --format markdown is not implemented
    if args.format == "markdown":
        print(
            "ERROR: --format markdown is not implemented in this version. "
            "Use --format text or --format json.",
            file=sys.stderr,
        )
        return 2

    # --max-deferred-items must be >= 1
    if args.max_deferred_items < 1:
        print(
            f"ERROR: --max-deferred-items must be >= 1, got {args.max_deferred_items}.",
            file=sys.stderr,
        )
        return 2

    # Resolve repo root
    repo_root = _resolve_repo_root(args.repo_root)
    err = _validate_repo_root(repo_root)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    # Validate --output path
    output_path: pathlib.Path | None = None
    if args.output:
        output_path, err = _validate_output_path(args.output, repo_root)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 2

    # Validate --check-stale path
    check_stale_path: pathlib.Path | None = None
    if args.check_stale:
        check_stale_path, err = _validate_check_stale_path(args.check_stale, repo_root)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 2

    # Get current git metadata
    current_commit, current_branch = _read_git_head(repo_root)

    # Handle --check-stale mode
    if check_stale_path is not None:
        is_stale, reasons = _check_stale(check_stale_path, current_commit, current_branch)
        if is_stale:
            print("STALE SNAPSHOT DETECTED:")
            for r in reasons:
                print(f"  - {r}")
            print(
                f"Current commit: {current_commit}  branch: {current_branch}"
            )
            if args.fail_on_stale:
                return 1
        else:
            print(
                f"Snapshot appears current. "
                f"commit={current_commit[:12]} branch={current_branch}"
            )
        print(ADVISORY_ONLY_NOTE)
        return 0

    # Build snapshot
    snapshot, warnings, sensitive_detected, redaction_applied = _build_snapshot(repo_root, args)

    # Render output
    if args.format == "json":
        rendered = json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    else:
        rendered = _render_text(snapshot)

    # Write output file if requested
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered if args.format == "json" else
                                json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                                encoding="utf-8")
        print(f"Snapshot written to: {output_path}", file=sys.stderr)

    print(rendered, end="")

    if sensitive_detected and args.fail_on_sensitive_hit:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
