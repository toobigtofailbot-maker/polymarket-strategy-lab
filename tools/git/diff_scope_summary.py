"""
Local offline read-only diff scope summary helper.

Reads only local git diff metadata. Makes no network calls. Modifies no files.
Does not replace pytest, security checks, preflight tools, or human review.
"""

import argparse
import functools
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

# ── Schema version ──────────────────────────────────────────────────────────
SUMMARY_SCHEMA_VERSION = "1.0"
SPEC_SUMMARY_SCHEMA_VERSION = "2.0"

# ── Built-in pattern tables ──────────────────────────────────────────────────

DEPENDENCY_LOCK_PATTERNS = [
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "uv.lock",
    "package.json",
    "package-lock.json",
    "Cargo.toml",
    "Cargo.lock",
]

DEPENDENCY_LOCK_SUFFIXES = [".lock"]

GENERATED_ARTIFACT_PREFIXES = [
    "local_data/",
    ".venv-security/",
    ".venv-official-client/",
    "tools/.bin/",
    "tools/security/.cache/",
    "security-scan-output/",
    "official-client-sandbox-output/",
    ".pytest_cache/",
    "__pycache__/",
]

GENERATED_ARTIFACT_EXACT = [".coverage"]
GENERATED_ARTIFACT_SUFFIXES = [".sarif"]

PROTECTED_PREFIXES_BUILTIN = [
    "tools/hermes/",
    "agent_runtime/",
    "agent_memory/",
]

PROTECTED_EXACT_BUILTIN = [".env"]
PROTECTED_STARTSWITH_BUILTIN = [".env."]

CREDENTIAL_LIKE_PATTERNS = [
    r"private.?key",
    r"wallet.?key",
    r"mnemonic",
    r"passphrase",
    r"api.?key",
    r"secret.?key",
    r"\.pem$",
    r"\.p12$",
    r"\.pfx$",
    r"id_rsa",
    r"id_ed25519",
    r"credentials\.json",
    r"keystore",
    r"\.keystore",
]

VALIDATION_REMINDER = (
    "REMINDER: This summary does not replace pytest, security checks, "
    "preflight_generated_artifact_guard.py, preflight_sync_main.py (Remote Main Sync Gate), "
    "or human review. Run all required validation steps before requesting merge."
)


# ── Path normalisation ───────────────────────────────────────────────────────

def _norm(path: str) -> str:
    """Normalise separators to forward slash and strip leading ./"""
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


# ── Classification helpers ───────────────────────────────────────────────────

def is_dependency_or_lock(path: str) -> bool:
    p = _norm(path)
    basename = p.rsplit("/", 1)[-1]
    if basename in DEPENDENCY_LOCK_PATTERNS:
        return True
    for suf in DEPENDENCY_LOCK_SUFFIXES:
        if basename.endswith(suf):
            return True
    return False


def is_generated_artifact(path: str) -> bool:
    p = _norm(path)
    for prefix in GENERATED_ARTIFACT_PREFIXES:
        if p.startswith(prefix) or p == prefix.rstrip("/"):
            return True
    basename = p.rsplit("/", 1)[-1]
    if basename in GENERATED_ARTIFACT_EXACT:
        return True
    for suf in GENERATED_ARTIFACT_SUFFIXES:
        if basename.endswith(suf):
            return True
    return False


def is_protected_builtin(path: str) -> bool:
    p = _norm(path)
    basename = p.rsplit("/", 1)[-1]
    for prefix in PROTECTED_PREFIXES_BUILTIN:
        if p.startswith(prefix):
            return True
    if basename in PROTECTED_EXACT_BUILTIN:
        return True
    for sw in PROTECTED_STARTSWITH_BUILTIN:
        if p.startswith(sw) or basename.startswith(sw.lstrip(".")):
            return True
    for pattern in CREDENTIAL_LIKE_PATTERNS:
        if re.search(pattern, p, re.IGNORECASE):
            return True
    return False


def is_protected_explicit(path: str, forbidden_prefixes: list[str]) -> bool:
    p = _norm(path)
    for fp in forbidden_prefixes:
        nfp = _norm(fp)
        if p.startswith(nfp):
            return True
    return False


def is_in_scope(path: str, allowed_files: list[str], allowed_prefixes: list[str]) -> bool:
    """Return True if path matches any explicit allow rule; None if no rules given."""
    if not allowed_files and not allowed_prefixes:
        return None  # no scope declared — no out-of-scope warning
    p = _norm(path)
    for af in allowed_files:
        if p == _norm(af):
            return True
    for ap in allowed_prefixes:
        nap = _norm(ap)
        if p.startswith(nap):
            return True
    return False


# ── Package-class warning logic ──────────────────────────────────────────────

def package_class_warnings(package_class: str, changed_files: list[str],
                           allowed_files: list[str], allowed_prefixes: list[str]) -> list[str]:
    pc = package_class.lower()
    warnings = []

    # docs-only or policy WP touching src/
    if any(kw in pc for kw in ("docs-only", "docs only", "policy", "design")):
        src_hits = [f for f in changed_files if _norm(f).startswith("src/")]
        # Only warn if src/ is NOT explicitly allowed
        src_explicitly_allowed = any(
            _norm(ap).startswith("src/") or _norm(ap) == "src"
            for ap in allowed_prefixes
        ) or any(_norm(af).startswith("src/") for af in allowed_files)
        if src_hits and not src_explicitly_allowed:
            warnings.append(
                f"Package class '{package_class}' is docs/design but {len(src_hits)} "
                f"file(s) under src/ are changed: {src_hits[:5]}"
            )

    # design WP touching tools/ (unless implementation/tooling class)
    if "design" in pc and not any(kw in pc for kw in ("implementation", "tooling")):
        tools_hits = [f for f in changed_files if _norm(f).startswith("tools/")]
        tools_explicitly_allowed = any(
            _norm(ap).startswith("tools/")
            for ap in allowed_prefixes
        ) or any(_norm(af).startswith("tools/") for af in allowed_files)
        if tools_hits and not tools_explicitly_allowed:
            warnings.append(
                f"Package class '{package_class}' is design-only but {len(tools_hits)} "
                f"file(s) under tools/ are changed (add --allowed-prefix tools/... or "
                f"include 'tooling' in package class to suppress): {tools_hits[:5]}"
            )

    # local report/export touching credentials/network/trading
    if any(kw in pc for kw in ("local-report", "local report", "export")):
        sensitive_patterns = [
            r"credentials?",
            r"auth",
            r"trading",
            r"network",
            r"wallet",
            r"private",
        ]
        for f in changed_files:
            fp = _norm(f).lower()
            for pat in sensitive_patterns:
                if re.search(pat, fp):
                    warnings.append(
                        f"Package class '{package_class}' (local report/export) "
                        f"touches sensitive path: {f}"
                    )
                    break

    # read-only public-data touching private/auth/official-client files
    if any(kw in pc for kw in ("read-only", "public-data", "public data")):
        private_patterns = [r"private", r"auth", r"official.?client", r"credential", r"wallet"]
        for f in changed_files:
            fp = _norm(f).lower()
            for pat in private_patterns:
                if re.search(pat, fp):
                    warnings.append(
                        f"Package class '{package_class}' (read-only/public-data) "
                        f"touches private/auth path: {f}"
                    )
                    break

    # runtime-dependency warning unless class explicitly says so
    if "runtime-dependency" in pc or "runtime dependency" in pc:
        dep_hits = [f for f in changed_files if is_dependency_or_lock(f)]
        if not dep_hits:
            warnings.append(
                f"Package class '{package_class}' is runtime-dependency but no "
                "dependency/lock-file changes detected — verify this is intentional."
            )

    # live-trading package without docs/live_trading_authorization.md change
    if "live-trading" in pc or "live trading" in pc:
        auth_changed = any(
            "live_trading_authorization" in _norm(f)
            for f in changed_files
        )
        if not auth_changed:
            warnings.append(
                f"Package class '{package_class}' is live-trading but "
                "docs/live_trading_authorization.md was not changed — live trading "
                "requires explicit authorization update."
            )

    return warnings


# ── Git command helpers ──────────────────────────────────────────────────────

def _run_git(args: list[str], cwd: str | None = None) -> tuple[str, str, int]:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", "git not found", 2


def get_name_status(base: str, head: str) -> tuple[list[dict], str | None]:
    """
    Run git diff --name-status and parse results.
    Returns (file_entries, error_message_or_None).
    Each entry: {status, path, old_path (for renames)}.
    """
    stdout, stderr, rc = _run_git(["diff", "--name-status", f"{base}...{head}"])
    if rc != 0:
        return [], f"git diff --name-status failed (rc={rc}): {stderr.strip()}"
    entries = parse_name_status(stdout)
    return entries, None


def _get_name_status_spec(base: str, head: str) -> tuple[list[dict], str | None]:
    stdout, stderr, rc = _run_git([
        "diff", "--name-status", "-z", "--find-renames=50%",
        "--find-copies=50%", "--find-copies-harder", f"{base}...{head}",
    ])
    if rc != 0:
        return [], "git operation failed"
    return parse_name_status(stdout), None


def _get_untracked_spec() -> tuple[list[str], str | None]:
    stdout, stderr, rc = _run_git(
        ["ls-files", "--others", "--exclude-standard", "-z"]
    )
    if rc != 0:
        return [], "git operation failed"
    return sorted({_norm(path) for path in stdout.split("\0") if path}), None


def parse_name_status(raw: str) -> list[dict]:
    """Parse git diff --name-status output into structured records."""
    entries = []
    if "\0" in raw:
        fields = raw.split("\0")
        if fields and fields[-1] == "":
            fields.pop()
        index = 0
        while index < len(fields):
            status_raw = fields[index]
            index += 1
            if status_raw.startswith(("R", "C")) and index + 1 < len(fields):
                entries.append({
                    "status": status_raw[0],
                    "status_detail": status_raw,
                    "old_path": _norm(fields[index]),
                    "path": _norm(fields[index + 1]),
                })
                index += 2
            elif index < len(fields):
                entries.append({
                    "status": status_raw[0] if status_raw else "?",
                    "status_detail": status_raw,
                    "path": _norm(fields[index]),
                })
                index += 1
        return entries
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if not parts:
            continue
        status_raw = parts[0].strip()
        # Rename/copy: R100\told_path\tnew_path or R\told\tnew
        if status_raw.startswith(("R", "C")) and len(parts) >= 3:
            entries.append({
                "status": status_raw[0],
                "status_detail": status_raw,
                "old_path": _norm(parts[1]),
                "path": _norm(parts[2]),
            })
        elif len(parts) >= 2:
            entries.append({
                "status": status_raw[0] if status_raw else "?",
                "status_detail": status_raw,
                "path": _norm(parts[1]),
            })
    return entries


def get_diff_stat(base: str, head: str) -> tuple[str, str | None]:
    stdout, stderr, rc = _run_git(["diff", "--stat", f"{base}...{head}"])
    if rc != 0:
        return "", f"git diff --stat failed (rc={rc}): {stderr.strip()}"
    return stdout.strip(), None


def get_diff_check(base: str, head: str) -> tuple[list[str], str | None]:
    """Run git diff --check; returns (whitespace_errors, error_or_None)."""
    stdout, stderr, rc = _run_git(["diff", "--check", f"{base}...{head}"])
    if rc == 0:
        return [], None
    if rc == 1:
        # rc=1 means whitespace errors found — that is the normal output
        errors = [l for l in stdout.splitlines() if l.strip()]
        return errors, None
    # rc=2+ is a real git error
    return [], f"git diff --check error (rc={rc}): {stderr.strip()}"


# ── Output path validation ───────────────────────────────────────────────────

_ALLOWED_OUTPUT_PREFIX = "local_data/diff_scope_summaries/"


def _is_absolute_path(path: str) -> bool:
    """Return True if path is absolute on any supported platform.

    os.path.isabs('/foo') returns False on Windows (no drive letter), so we
    also check for Unix-style leading slash and Windows drive-letter patterns.
    """
    if os.path.isabs(path):
        return True
    norm = _norm(path)
    # Unix-style absolute: starts with /
    if norm.startswith("/"):
        return True
    # Windows drive-letter absolute: C:/ or C:\
    if len(norm) >= 3 and norm[1] == ":" and norm[2] in ("/", "\\"):
        return True
    return False


def validate_output_path(output: str) -> str | None:
    """Return error string if output path is not acceptable, else None."""
    if not output:
        return None
    # Reject all absolute paths — only repo-relative paths are allowed.
    # An absolute path like /tmp/local_data/diff_scope_summaries/... would pass
    # a substring check but writes outside the repo; reject unconditionally.
    if _is_absolute_path(output):
        return (
            f"--output must be a repo-relative path under {_ALLOWED_OUTPUT_PREFIX!r}, "
            f"got absolute path: {output!r}"
        )
    norm = _norm(output)
    # Reject path traversal
    if ".." in norm.split("/"):
        return f"--output must not use path traversal: {output!r}"
    # Must start with the allowed prefix
    if not norm.startswith(_ALLOWED_OUTPUT_PREFIX):
        return (
            f"--output must be under {_ALLOWED_OUTPUT_PREFIX!r}, got: {output!r}"
        )
    return None


# ── Core summary builder ─────────────────────────────────────────────────────

def build_summary(
    base: str,
    head: str,
    package_class: str,
    allowed_files: list[str],
    allowed_prefixes: list[str],
    forbidden_prefixes: list[str],
    entries: list[dict],
    diff_stat: str,
    diff_check_errors: list[str],
    git_errors: list[str],
    *,
    wp_spec_path=None,
    wp_spec_schema_version=None,
    required_changed_files=(),
    untracked_files=(),
    max_changed_files=None,
    exact_scope_required=False,
    authority=None,
    git_operations_succeeded=True,
) -> dict:
    """
    Build a structured summary dict from parsed diff data.
    All classification and warning logic lives here for testability.
    """
    spec_mode = wp_spec_path is not None
    warnings = list(git_errors)

    # Count by status
    counts = {"A": 0, "M": 0, "D": 0, "R": 0, "C": 0, "other": 0}
    all_paths = []
    by_status: dict[str, list[str]] = {"A": [], "M": [], "D": [], "R": [], "C": [], "other": []}

    if spec_mode:
        seen_destinations = set()
        for e in entries:
            s = e["status"]
            p = e["path"]
            if p in seen_destinations:
                continue
            seen_destinations.add(p)
            all_paths.append(p)
            if s in counts:
                counts[s] += 1
                by_status[s].append(p)
            else:
                counts["other"] += 1
                by_status["other"].append(p)
        normalized_untracked = sorted({_norm(path) for path in untracked_files})
        for path in normalized_untracked:
            if path not in seen_destinations:
                seen_destinations.add(path)
                all_paths.append(path)
                counts["A"] += 1
                by_status["A"].append(path)
        all_paths = sorted(seen_destinations)
        for key in by_status:
            by_status[key] = sorted(set(by_status[key]))
        policy_paths = sorted(set(
            all_paths
            + [
                e["old_path"] for e in entries
                if e.get("status") in ("R", "C") and "old_path" in e
            ]
        ))
        # Copy origins are provenance, not additional changed paths. Retain all
        # origins in policy_paths for safety/authority; only rename origins also
        # participate in allowed scope. Independently changed copy origins are
        # already present in all_paths and therefore remain scope-checked.
        allowed_scope_paths = sorted(set(
            all_paths + [
                e["old_path"] for e in entries
                if e.get("status") == "R" and "old_path" in e
            ]
        ))
        total = len(all_paths)
    else:
        normalized_untracked = []
        policy_paths = all_paths
        for e in entries:
            s = e["status"]
            p = e["path"]
            all_paths.append(p)
            if s in counts:
                counts[s] += 1
                by_status[s].append(p)
            else:
                counts["other"] += 1
                by_status["other"].append(p)
        policy_paths = all_paths
        total = len(all_paths)
        allowed_scope_paths = all_paths

    # Scope classification
    out_of_scope = []
    scope_declared = bool(allowed_files or allowed_prefixes)
    if scope_declared:
        for p in allowed_scope_paths:
            in_scope = is_in_scope(p, allowed_files, allowed_prefixes)
            if in_scope is False:
                out_of_scope.append(p)
    if spec_mode:
        out_of_scope = sorted(set(out_of_scope))

    # Protected paths (builtin + explicit forbidden)
    protected_hits_builtin = [p for p in policy_paths if is_protected_builtin(p)]
    protected_hits_explicit = [
        p for p in policy_paths if is_protected_explicit(p, forbidden_prefixes)
    ]
    if spec_mode:
        protected_hits_builtin = sorted(set(protected_hits_builtin))
        protected_hits_explicit = sorted(set(protected_hits_explicit))
    all_protected = sorted(set(protected_hits_builtin + protected_hits_explicit))

    # Dependency/lock
    dep_lock_hits = [p for p in policy_paths if is_dependency_or_lock(p)]
    if spec_mode:
        dep_lock_hits = sorted(set(dep_lock_hits))

    # Generated artifacts
    generated_hits = [p for p in policy_paths if is_generated_artifact(p)]
    if spec_mode:
        generated_hits = sorted(set(generated_hits))

    # Package-class warnings
    pc_warnings = package_class_warnings(package_class, policy_paths, allowed_files, allowed_prefixes)

    unauthorized_hits = []
    if spec_mode:
        effective_authority = authority or {}
        for path in policy_paths:
            needed = _authority_for_path(path)
            if needed is None or any(
                effective_authority.get(permission) is not True
                for permission in needed
            ):
                unauthorized_hits.append(path)
        unauthorized_hits = sorted(set(unauthorized_hits))

    # Accumulate warnings
    if out_of_scope:
        warnings.append(
            f"{len(out_of_scope)} file(s) outside declared allowed scope: {out_of_scope[:10]}"
        )
    if all_protected:
        warnings.append(
            f"{len(all_protected)} protected-path hit(s): {all_protected[:10]}"
        )
    if dep_lock_hits:
        warnings.append(
            f"{len(dep_lock_hits)} dependency/lock-file change(s): {dep_lock_hits}"
        )
    if generated_hits:
        warnings.append(
            f"{len(generated_hits)} generated-artifact/local-output path(s): {generated_hits[:10]}"
        )
    warnings.extend(pc_warnings)
    if diff_check_errors:
        warnings.append(
            f"{len(diff_check_errors)} whitespace error(s) from git diff --check: "
            f"{diff_check_errors[:5]}"
        )
    if spec_mode and max_changed_files is not None and total > max_changed_files:
        warnings.append(
            f"Changed-file count {total} exceeds the declared maximum "
            f"{max_changed_files}."
        )
    if unauthorized_hits:
        warnings.append(
            f"{len(unauthorized_hits)} path(s) contradict declared authority: "
            f"{unauthorized_hits[:10]}"
        )

    # Suggested review attention areas
    attention = []
    if out_of_scope:
        attention.append("Review out-of-scope files: confirm they belong in this WP.")
    if all_protected:
        attention.append("Review protected-path hits: confirm no boundary violations.")
    if dep_lock_hits:
        attention.append("Review dependency/lock changes: confirm this WP authorizes them.")
    if generated_hits:
        attention.append("Review generated-artifact paths: ensure they are not committed.")
    if pc_warnings:
        attention.append("Review package-class warnings: confirm WP class matches scope.")
    if diff_check_errors:
        attention.append("Fix whitespace errors detected by git diff --check.")
    if unauthorized_hits:
        attention.append("Review authority violations: the WP specification does not authorize these paths.")
    if not attention:
        attention.append("No specific attention areas flagged by this summary.")

    summary = {
        "summary_schema_version": (
            SPEC_SUMMARY_SCHEMA_VERSION if spec_mode else SUMMARY_SCHEMA_VERSION
        ),
        "base": base,
        "head": head,
        "package_class": package_class,
        "total_changed_files": total,
        "counts": {
            "added": counts["A"],
            "modified": counts["M"],
            "deleted": counts["D"],
            "renamed": counts["R"],
            "copied": counts["C"],
            "other": counts["other"],
        },
        "changed_files_by_status": {k: v for k, v in by_status.items() if v},
        "scope_declared": scope_declared,
        "out_of_scope_files": out_of_scope,
        "protected_path_hits": all_protected,
        "protected_path_hits_builtin": protected_hits_builtin,
        "protected_path_hits_explicit": protected_hits_explicit,
        "dependency_lock_changes": dep_lock_hits,
        "generated_artifact_hits": generated_hits,
        "package_class_warnings": pc_warnings,
        "diff_check_errors": diff_check_errors,
        "diff_stat_summary": diff_stat,
        "warnings": warnings,
        "warning_count": len(warnings),
        "suggested_review_attention": attention,
        "validation_reminder": VALIDATION_REMINDER,
        "exit_behavior": (
            "Exit 0 (summary generated). Use --fail-on-warning for exit 1 on any warning."
            if warnings else
            "Exit 0 (summary generated, no warnings)."
        ),
    }
    if spec_mode:
        required = list(required_changed_files)
        present = set(all_paths)
        missing = [path for path in required if path not in present]
        exact_pass = (
            not out_of_scope
            and not missing
            and max_changed_files is not None
            and total <= max_changed_files
            and not all_protected
            and not generated_hits
            and not unauthorized_hits
            and not diff_check_errors
            and git_operations_succeeded
        )
        if exact_scope_required and not exact_pass:
            # main() returns 1 in this case; never print a contradicting exit line.
            summary["exit_behavior"] = "Exit 1 (exact scope required but not satisfied)."
        summary.update({
            "wp_spec_path": _norm(wp_spec_path),
            "wp_spec_schema_version": wp_spec_schema_version,
            "required_changed_files": required,
            "allowed_changed_files": list(allowed_files),
            "missing_required_files": missing,
            "untracked_files": normalized_untracked,
            "exact_scope_required": bool(exact_scope_required),
            "exact_scope_pass": exact_pass,
        })
    return summary


def _authority_for_path(path: str) -> list[str] | None:
    """Return the closed WP-spec authority requirements for one path."""
    p = _norm(path)
    basename = p.rsplit("/", 1)[-1]
    requirements = []
    if p.startswith("docs/"):
        requirements.append("docs")
    elif p.startswith("tests/"):
        requirements.append("tests")
    elif p.startswith("src/"):
        requirements.append("source_runtime")
    elif p.startswith(".github/workflows/"):
        requirements.append("workflow_files")
    elif p.startswith("tools/") or p in _security_scan_config_paths():
        requirements.append("local_offline_tooling")
    elif is_dependency_or_lock(p):
        requirements.append("dependencies")
    else:
        return None
    if is_dependency_or_lock(p):
        requirements.append("dependencies")
    if p.startswith("docs/wp_specs/"):
        requirements.append("canonical_evidence_policy")
    if p.startswith(("tools/hermes/", "agent_runtime/", "agent_memory/")):
        requirements.append("hermes_runtime")
    if is_protected_builtin(p) and not p.startswith(
        ("tools/hermes/", "agent_runtime/", "agent_memory/")
    ):
        requirements.append("credentials")
    return requirements


# ── Renderers ────────────────────────────────────────────────────────────────

def render_text(summary: dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("DIFF SCOPE SUMMARY")
    lines.append("=" * 70)
    lines.append(f"Base:           {summary['base']}")
    lines.append(f"Head:           {summary['head']}")
    lines.append(f"Package class:  {summary['package_class']}")
    lines.append(f"Schema version: {summary['summary_schema_version']}")
    if summary["summary_schema_version"] == SPEC_SUMMARY_SCHEMA_VERSION:
        lines.append(f"WP spec:        {summary['wp_spec_path']}")
        lines.append(
            f"WP spec schema: {summary['wp_spec_schema_version']}"
        )
    lines.append("")

    c = summary["counts"]
    lines.append(
        f"Changed files: {summary['total_changed_files']} total  "
        f"(+{c['added']} added, ~{c['modified']} modified, -{c['deleted']} deleted, "
        f"R{c['renamed']} renamed, C{c['copied']} copied"
        + (f", ?{c['other']} other" if c["other"] else "") + ")"
    )
    lines.append("")

    for status_key, label in [("A", "Added"), ("M", "Modified"), ("D", "Deleted"),
                               ("R", "Renamed"), ("C", "Copied"), ("other", "Other")]:
        files = summary["changed_files_by_status"].get(status_key, [])
        if files:
            lines.append(f"{label} ({len(files)}):")
            for f in files:
                lines.append(f"  {f}")
            lines.append("")

    if not summary["scope_declared"]:
        lines.append("Scope: no --allowed-file or --allowed-prefix declared; no out-of-scope check.")
    else:
        oos = summary["out_of_scope_files"]
        if oos:
            lines.append(f"Out-of-scope files ({len(oos)}) [WARNING]:")
            for f in oos:
                lines.append(f"  {f}")
        else:
            lines.append("Out-of-scope files: none (all changed files match declared scope).")
    lines.append("")

    ph = summary["protected_path_hits"]
    if ph:
        lines.append(f"Protected-path hits ({len(ph)}) [WARNING]:")
        for f in ph:
            lines.append(f"  {f}")
    else:
        lines.append("Protected-path hits: none.")
    lines.append("")

    dl = summary["dependency_lock_changes"]
    if dl:
        lines.append(f"Dependency/lock-file changes ({len(dl)}) [WARNING]:")
        for f in dl:
            lines.append(f"  {f}")
    else:
        lines.append("Dependency/lock-file changes: none.")
    lines.append("")

    ga = summary["generated_artifact_hits"]
    if ga:
        lines.append(f"Generated-artifact/local-output hits ({len(ga)}) [WARNING]:")
        for f in ga:
            lines.append(f"  {f}")
    else:
        lines.append("Generated-artifact/local-output hits: none.")
    lines.append("")

    pcw = summary["package_class_warnings"]
    if pcw:
        lines.append(f"Package-class warnings ({len(pcw)}) [WARNING]:")
        for w in pcw:
            lines.append(f"  {w}")
    else:
        lines.append("Package-class warnings: none.")
    lines.append("")

    dce = summary["diff_check_errors"]
    if dce:
        lines.append(f"git diff --check: {len(dce)} whitespace error(s) [WARNING]:")
        for e in dce[:10]:
            lines.append(f"  {e}")
    else:
        lines.append("git diff --check: no whitespace errors.")
    lines.append("")

    lines.append(f"Total warnings: {summary['warning_count']}")
    lines.append("")

    if summary["summary_schema_version"] == SPEC_SUMMARY_SCHEMA_VERSION:
        missing = summary["missing_required_files"]
        if missing:
            lines.append(f"Missing required files ({len(missing)}):")
            for path in missing:
                lines.append(f"  {path}")
        else:
            lines.append("Missing required files: none.")
        lines.append(
            f"Exact scope required: {str(summary['exact_scope_required']).lower()}"
        )
        lines.append(
            f"Exact scope pass: {str(summary['exact_scope_pass']).lower()}"
        )
        lines.append("")

    lines.append("Suggested review attention areas:")
    for a in summary["suggested_review_attention"]:
        lines.append(f"  - {a}")
    lines.append("")

    lines.append("-" * 70)
    lines.append(summary["validation_reminder"])
    lines.append("-" * 70)
    lines.append(summary["exit_behavior"])

    return "\n".join(lines)


def render_json(summary: dict) -> str:
    return json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False)


# ── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Local offline read-only diff scope summary helper. "
            "Summarises changed files between two git refs for Claude Code / Codex PR review. "
            "Does not replace pytest, security checks, preflight tools, or human review."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--base", default="main", help="Base ref (default: main)")
    p.add_argument("--head", default="HEAD", help="Head ref (default: HEAD)")
    p.add_argument(
        "--package-class",
        default=None,
        help="Active WP package class (e.g. docs-only, design, local-tooling)",
    )
    p.add_argument(
        "--wp-spec",
        default=None,
        metavar="PATH",
        help="Validated machine-readable WP specification (activates exact scope mode)",
    )
    p.add_argument(
        "--require-exact-scope",
        action="store_true",
        help="Require exact-scope pass (valid only with --wp-spec)",
    )
    p.add_argument(
        "--allowed-file",
        action="append",
        default=[],
        dest="allowed_files",
        metavar="PATH",
        help="Specific file allowed in this WP (repeatable)",
    )
    p.add_argument(
        "--allowed-prefix",
        action="append",
        default=[],
        dest="allowed_prefixes",
        metavar="PREFIX",
        help="Directory prefix allowed in this WP (repeatable)",
    )
    p.add_argument(
        "--forbidden-prefix",
        action="append",
        default=[],
        dest="forbidden_prefixes",
        metavar="PREFIX",
        help="Directory prefix forbidden in this WP (repeatable)",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: text (default) or json",
    )
    p.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help=(
            f"Write output to file (must be under {_ALLOWED_OUTPUT_PREFIX!r}). "
            "No file is written by default."
        ),
    )
    p.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit 1 if any warnings are present (default: exit 0 when summary succeeds)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.require_exact_scope and not args.wp_spec:
        print("ERROR: --require-exact-scope requires --wp-spec.", file=sys.stderr)
        return 2

    if args.wp_spec and (
        args.allowed_files
        or args.allowed_prefixes
        or args.forbidden_prefixes
        or args.package_class is not None
        or args.output is not None
    ):
        print("ERROR: WP-spec mode does not accept manual scope or output flags.", file=sys.stderr)
        return 2

    # Validate output path before doing any git work
    if args.output:
        err = validate_output_path(args.output)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 2

    git_errors: list[str] = []
    spec_mode = args.wp_spec is not None
    spec_scope = None
    if spec_mode:
        spec_scope, spec_errors = _read_wp_spec_scope(args.wp_spec)
        if spec_scope is None:
            print("ERROR: WP specification is invalid.", file=sys.stderr)
            return 2
        package_class = spec_scope["package_class"]
        allowed_files = list(spec_scope["allowed_changed_files"])
        allowed_prefixes = []
        forbidden_prefixes = list(spec_scope["forbidden_prefixes"])
    else:
        package_class = args.package_class or "unspecified"
        allowed_files = [_norm(f) for f in args.allowed_files]
        allowed_prefixes = [_norm(p) for p in args.allowed_prefixes]
        forbidden_prefixes = [_norm(p) for p in args.forbidden_prefixes]

    if spec_mode:
        entries, err = _get_name_status_spec(args.base, args.head)
    else:
        entries, err = get_name_status(args.base, args.head)
    if err:
        git_errors.append(f"git diff --name-status: {err}")

    diff_stat, err = get_diff_stat(args.base, args.head)
    if err:
        git_errors.append(f"git diff --stat: {err}")

    diff_check_errors, err = get_diff_check(args.base, args.head)
    if err:
        git_errors.append(f"git diff --check: {err}")

    if spec_mode:
        untracked_files, err = _get_untracked_spec()
        if err:
            git_errors.append("git ls-files operation failed")
    else:
        untracked_files = []

    if spec_mode and git_errors:
        print("ERROR: required git operation failed.", file=sys.stderr)
        return 2

    summary = build_summary(
        base=args.base,
        head=args.head,
        package_class=package_class,
        allowed_files=allowed_files,
        allowed_prefixes=allowed_prefixes,
        forbidden_prefixes=forbidden_prefixes,
        entries=entries,
        diff_stat=diff_stat,
        diff_check_errors=diff_check_errors,
        git_errors=git_errors,
        wp_spec_path=args.wp_spec if spec_mode else None,
        wp_spec_schema_version=(
            spec_scope["schema_version"] if spec_mode else None
        ),
        required_changed_files=(
            spec_scope["required_changed_files"] if spec_mode else ()
        ),
        untracked_files=untracked_files,
        max_changed_files=(
            spec_scope["max_changed_files"] if spec_mode else None
        ),
        exact_scope_required=(
            spec_scope["exact_scope_required"] or args.require_exact_scope
            if spec_mode else False
        ),
        authority=spec_scope["authority"] if spec_mode else None,
        git_operations_succeeded=not git_errors,
    )

    if args.format == "json":
        output_text = render_json(summary)
    else:
        output_text = render_text(summary)

    if args.output:
        out_path = pathlib.Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"Summary written to: {args.output}")
        if args.format == "text":
            print(output_text)
    else:
        print(output_text)

    if args.fail_on_warning and summary["warning_count"] > 0:
        return 1
    if (
        spec_mode
        and summary["exact_scope_required"]
        and not summary["exact_scope_pass"]
    ):
        return 1
    return 0


@functools.lru_cache(maxsize=1)
def _spec_guard_module():
    """Load the sibling canonical guard once, without changing this module's public imports."""
    guard_path = pathlib.Path(__file__).resolve().parents[1] / "wp" / "wp_spec_guard.py"
    module_spec = importlib.util.spec_from_file_location(
        "_wp159_wp_spec_guard", guard_path
    )
    if module_spec is None or module_spec.loader is None:
        return None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _security_scan_config_paths() -> tuple[str, ...]:
    """Exact root secret-scan config paths from the canonical guard (none if unavailable: fail closed)."""
    module = _spec_guard_module()
    return tuple(getattr(module, "SECURITY_SCAN_CONFIG_PATHS", ())) if module else ()


def _read_wp_spec_scope(path: str):
    module = _spec_guard_module()
    if module is None:
        return None, ()
    return module.read_and_validate_spec_scope(path)


if __name__ == "__main__":
    sys.exit(main())
