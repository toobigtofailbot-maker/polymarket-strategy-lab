"""
Local offline read-only validation output summary helper.

Accepts pre-captured command output via stdin, text snippets, or restricted
local files. Makes no network calls. Executes no commands. Modifies no files.
Does not replace pytest, security checks, preflight tools, or human review.
"""

import argparse
import json
import os
import pathlib
import re
import sys

# ── Schema version ──────────────────────────────────────────────────────────
SUMMARY_SCHEMA_VERSION = "1.0"

# ── Allowed statuses for --tool-availability ────────────────────────────────
VALID_TOOL_STATUSES = {
    "available",
    "passed",
    "failed",
    "unavailable",
    "skipped",
    "skipped_not_available",
    "skipped_not_applicable",
}

# ── Valid check types ────────────────────────────────────────────────────────
VALID_CHECK_TYPES = {
    "full-pytest",
    "focused-pytest",
    "security",
    "artifact-guard",
    "sync-gate",
    "smoke",
    "diff-scope",
    "git-check",
    "other",
}

# ── Validation reminder ──────────────────────────────────────────────────────
VALIDATION_REMINDER = (
    "REMINDER: This summary does not replace pytest, security checks, "
    "preflight_generated_artifact_guard.py, preflight_sync_main.py (Remote Main Sync Gate), "
    "or human review. Run all required validation steps before requesting merge."
)

RAW_LOG_RETENTION_NOTE = (
    "Raw validation logs may remain local and uncommitted. "
    "Full logs must be inspected locally; do not paste raw output into PR comments."
)

# ── Path restrictions ────────────────────────────────────────────────────────
_ALLOWED_OUTPUT_PREFIX = "local_data/validation_summaries/"
_ALLOWED_INPUT_PREFIX = "local_data/validation_summaries/inputs/"

# ── Secret-like patterns ─────────────────────────────────────────────────────
# Multi-line PEM block patterns: match entire block from BEGIN to END (including body lines).
# Applied before single-line patterns to prevent body lines leaking into snippets.
_SECRET_PEM_PATTERNS = [
    re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
        r".*?"
        r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.DOTALL | re.IGNORECASE,
    ),
]

_SECRET_PATTERNS = [
    re.compile(r"PRIVATE_KEY\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"API_KEY\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"CLOB_SECRET\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"CLOB_PASS_PHRASE\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"MNEMONIC\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"\bTOKEN\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    # Single-line fallback for orphan BEGIN header (no matching END present).
    re.compile(r"-----BEGIN\s+(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]

_CREDENTIAL_FILENAME_PATTERNS = [
    re.compile(r"\.env$", re.IGNORECASE),
    re.compile(r"private[_.]?key", re.IGNORECASE),
    re.compile(r"wallet[_.]?key", re.IGNORECASE),
    re.compile(r"mnemonic", re.IGNORECASE),
    re.compile(r"passphrase", re.IGNORECASE),
    re.compile(r"api[_.]?key", re.IGNORECASE),
    re.compile(r"secret[_.]?key", re.IGNORECASE),
    re.compile(r"credentials?\.json", re.IGNORECASE),
    re.compile(r"keystore", re.IGNORECASE),
    re.compile(r"token[_.]?file", re.IGNORECASE),
    re.compile(r"\.pem$", re.IGNORECASE),
    re.compile(r"\.p12$", re.IGNORECASE),
    re.compile(r"id_rsa", re.IGNORECASE),
    re.compile(r"id_ed25519", re.IGNORECASE),
]

# ── Meaningful failure line patterns ─────────────────────────────────────────
_FAILURE_LINE_PATTERNS = [
    re.compile(r"\bFAILED\b"),
    re.compile(r"\bERROR\b"),
    re.compile(r"Traceback"),
    re.compile(r"AssertionError"),
    re.compile(r"\bfailed\b", re.IGNORECASE),
    re.compile(r"\berror\b", re.IGNORECASE),
    re.compile(r"\bblocked\b", re.IGNORECASE),
    re.compile(r"Permission denied"),
]

# ── Generated output path patterns ───────────────────────────────────────────
_OUTPUT_PATH_PATTERNS = [
    re.compile(r"local_data/[\w./\-]+"),
    re.compile(r"[\w./\-]+\.(?:json|md|txt|sarif)"),
]


# ── Path utilities ───────────────────────────────────────────────────────────

def _norm(path: str) -> str:
    """Normalise separators to forward slash and strip leading ./"""
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def _is_absolute_path(path: str) -> bool:
    if os.path.isabs(path):
        return True
    norm = _norm(path)
    if norm.startswith("/"):
        return True
    if len(norm) >= 3 and norm[1] == ":" and norm[2] in ("/", "\\"):
        return True
    return False


def validate_output_path(output: str) -> str | None:
    """Return error string if output path is not acceptable, else None."""
    if not output:
        return None
    if _is_absolute_path(output):
        return (
            f"--output must be a repo-relative path under {_ALLOWED_OUTPUT_PREFIX!r}, "
            f"got absolute path: {output!r}"
        )
    norm = _norm(output)
    if ".." in norm.split("/"):
        return f"--output must not use path traversal: {output!r}"
    if not norm.startswith(_ALLOWED_OUTPUT_PREFIX):
        return f"--output must be under {_ALLOWED_OUTPUT_PREFIX!r}, got: {output!r}"
    return None


def validate_input_path(path: str, flag: str) -> str | None:
    """Return error string if input file path is not acceptable, else None."""
    if not path:
        return None
    if _is_absolute_path(path):
        return (
            f"{flag} must be a repo-relative path under {_ALLOWED_INPUT_PREFIX!r}, "
            f"got absolute path: {path!r}"
        )
    norm = _norm(path)
    if ".." in norm.split("/"):
        return f"{flag} must not use path traversal: {path!r}"
    if not norm.startswith(_ALLOWED_INPUT_PREFIX):
        return f"{flag} must be under {_ALLOWED_INPUT_PREFIX!r}, got: {path!r}"
    basename = norm.rsplit("/", 1)[-1]
    for pat in _CREDENTIAL_FILENAME_PATTERNS:
        if pat.search(basename):
            return (
                f"{flag} filename looks like a credential file: {path!r}. "
                "Credential files must not be passed to this helper."
            )
    return None


# ── Secret detection ─────────────────────────────────────────────────────────

def detect_and_redact_secrets(text: str) -> tuple[str, bool]:
    """
    Scan text for secret-like patterns. Return (redacted_text, was_detected).
    Replaces matched secret values with [REDACTED].

    Multi-line PEM block patterns are applied first so that body lines (base64
    key material) are replaced before single-line patterns or snippet extraction
    can observe them.
    """
    detected = False
    # Apply multi-line PEM block patterns first — replaces entire BEGIN…END block.
    for pat in _SECRET_PEM_PATTERNS:
        if pat.search(text):
            detected = True
            text = pat.sub("[REDACTED PEM PRIVATE KEY BLOCK]", text)
    # Apply remaining single-line patterns.
    for pat in _SECRET_PATTERNS:
        if pat.search(text):
            detected = True
            text = pat.sub(lambda m: _redact_secret_match(m.group(0)), text)
    return text, detected


def _redact_secret_match(match: str) -> str:
    """Redact the value portion of a single-line secret-like match."""
    if "=" in match:
        key, _ = match.split("=", 1)
        return f"{key}=[REDACTED]"
    if match.startswith("Bearer "):
        return "Bearer [REDACTED]"
    if "BEGIN" in match and "KEY" in match:
        # Orphan header with no matching END — replace the header only.
        return "[REDACTED PEM HEADER]"
    return "[REDACTED]"


# ── Parsers ──────────────────────────────────────────────────────────────────

def parse_pytest_output(text: str) -> dict:
    """
    Parse pytest result lines from text.
    Returns dict with pass_count, fail_count, error_count, warning_count, has_result.
    """
    result = {
        "pass_count": 0,
        "fail_count": 0,
        "error_count": 0,
        "warning_count": 0,
        "has_result": False,
    }
    # Match lines like: "878 passed, 1 warning" or "5 failed, 2 error, 10 passed, 3 warnings"
    # Also: "no tests ran" or standalone counts
    combined = re.compile(
        r"(?:(\d+)\s+passed)?[,\s]*(?:(\d+)\s+failed)?[,\s]*"
        r"(?:(\d+)\s+errors?)?[,\s]*(?:(\d+)\s+warnings?)?",
        re.IGNORECASE,
    )
    # Process line by line looking for pytest summary lines
    for line in text.splitlines():
        # Pytest short-test-summary lines like "FAILED tests/foo.py::test_bar"
        # Pytest result line: "N passed" / "N failed" / combined
        passed = re.search(r"(\d+)\s+passed", line, re.IGNORECASE)
        failed = re.search(r"(\d+)\s+failed", line, re.IGNORECASE)
        errored = re.search(r"(\d+)\s+error", line, re.IGNORECASE)
        warned = re.search(r"(\d+)\s+warning", line, re.IGNORECASE)
        if passed or failed or errored or warned:
            result["has_result"] = True
            if passed:
                result["pass_count"] = max(result["pass_count"], int(passed.group(1)))
            if failed:
                result["fail_count"] = max(result["fail_count"], int(failed.group(1)))
            if errored:
                result["error_count"] = max(result["error_count"], int(errored.group(1)))
            if warned:
                result["warning_count"] = max(result["warning_count"], int(warned.group(1)))
    return result


def parse_artifact_guard_output(text: str) -> str | None:
    """
    Parse artifact guard output. Returns 'pass', 'fail', or None if unknown.
    """
    lower = text.lower()
    if "generated artifact guard passed" in lower:
        return "pass"
    if any(kw in lower for kw in ("failed", "blocked", "generated artifacts visible")):
        return "fail"
    return None


def parse_sync_gate_output(text: str) -> str | None:
    """
    Parse Remote Main Sync Gate output. Returns 'pass', 'fail', or None.
    """
    lower = text.lower()
    if "remote main sync gate passed" in lower or "sync gate passed" in lower:
        return "pass"
    if any(kw in lower for kw in ("failed", "stale", "dirty", "missing required")):
        return "fail"
    return None


def parse_diff_scope_output(text: str) -> dict:
    """
    Parse diff/scope helper output. Returns dict with warning_count and has_result.
    """
    result = {"warning_count": 0, "has_result": False}
    m = re.search(r"Total warnings:\s*(\d+)", text, re.IGNORECASE)
    if m:
        result["warning_count"] = int(m.group(1))
        result["has_result"] = True
    elif "0 warnings" in text.lower():
        result["warning_count"] = 0
        result["has_result"] = True
    return result


def extract_generated_output_paths(text: str) -> list[str]:
    """Extract mention of generated output paths from log text."""
    paths = []
    seen = set()
    for pat in _OUTPUT_PATH_PATTERNS:
        for m in pat.finditer(text):
            p = m.group(0).strip().rstrip(".,;)")
            if p and p not in seen:
                # Filter out obvious non-paths
                if len(p) > 3 and ("/" in p or "." in p):
                    paths.append(p)
                    seen.add(p)
    return paths


# ── Failure snippet extraction ───────────────────────────────────────────────

def extract_failure_snippet(text: str, max_lines: int) -> tuple[list[str], bool]:
    """
    Extract meaningful failure lines from text.
    Returns (snippet_lines, truncated).
    """
    lines = text.splitlines()
    meaningful = []
    for line in lines:
        for pat in _FAILURE_LINE_PATTERNS:
            if pat.search(line):
                meaningful.append(line)
                break

    # Also include last few summary lines if not already captured
    if lines:
        tail = lines[-min(5, len(lines)):]
        for line in tail:
            if line.strip() and line not in meaningful:
                meaningful.append(line)

    truncated = False
    if len(meaningful) > max_lines:
        meaningful = meaningful[:max_lines]
        truncated = True

    return meaningful, truncated


# ── Security subtool status classification ───────────────────────────────────

def classify_security_status(tool_availability: dict[str, str]) -> str:
    """
    Classify overall security status from tool availability dict.
    tool_availability: {tool_name: status_string}
    """
    if not tool_availability:
        return "UNAVAILABLE"

    failed = [n for n, s in tool_availability.items() if s == "failed"]
    passed = [n for n, s in tool_availability.items()
              if s in ("passed", "available")]
    unavailable_or_skipped = [
        n for n, s in tool_availability.items()
        if s in ("unavailable", "skipped", "skipped_not_available", "skipped_not_applicable")
    ]

    if failed:
        return "FAIL"
    if passed and unavailable_or_skipped:
        return "PARTIAL"
    if unavailable_or_skipped and not passed and not failed:
        return "UNAVAILABLE"
    if passed and not unavailable_or_skipped and not failed:
        return "PASS"
    return "UNAVAILABLE"


# ── Overall status classification ────────────────────────────────────────────

def classify_status(
    exit_code: int | None,
    check_type: str,
    tool_availability: dict[str, str],
    parsed_pytest: dict,
    artifact_guard_result: str | None,
    sync_gate_result: str | None,
    secret_detected: bool,
    fail_on_secret: bool,
    fail_on_missing_evidence: bool,
    has_any_input: bool,
) -> str:
    """Classify the overall status."""
    # Secret forcing ERROR/FAIL
    if secret_detected and fail_on_secret:
        return "ERROR"
    if secret_detected:
        return "ERROR"

    # Check mandatory evidence
    if not has_any_input and exit_code is None:
        if fail_on_missing_evidence:
            return "ERROR"
        return "ERROR"  # Missing mandatory evidence is always ERROR per spec

    # Security check type uses subtool matrix
    if check_type == "security" and tool_availability:
        sec_status = classify_security_status(tool_availability)
        if sec_status == "FAIL":
            return "FAIL"
        if sec_status == "UNAVAILABLE":
            return "UNAVAILABLE"
        if sec_status == "PARTIAL":
            return "PARTIAL"
        # PASS from security subtools — verify exit code too
        if exit_code is not None and exit_code != 0:
            return "FAIL"
        return "PASS"

    # Artifact guard
    if check_type == "artifact-guard":
        if artifact_guard_result == "fail":
            return "FAIL"
        if artifact_guard_result == "pass":
            if exit_code is not None and exit_code != 0:
                return "FAIL"
            return "PASS"

    # Sync gate
    if check_type == "sync-gate":
        if sync_gate_result == "fail":
            return "FAIL"
        if sync_gate_result == "pass":
            if exit_code is not None and exit_code != 0:
                return "FAIL"
            return "PASS"

    # Pytest checks
    if check_type in ("full-pytest", "focused-pytest"):
        if parsed_pytest["has_result"]:
            if parsed_pytest["fail_count"] > 0 or parsed_pytest["error_count"] > 0:
                return "FAIL"
            if exit_code is not None and exit_code != 0:
                return "FAIL"
            return "PASS"

    # Generic: use exit code
    if exit_code is not None:
        if exit_code == 0:
            return "PASS"
        return "FAIL"

    # Fallback: if we have tool availability for security
    if tool_availability:
        return classify_security_status(tool_availability)

    # No usable evidence
    if fail_on_missing_evidence:
        return "ERROR"
    return "ERROR"


# ── Summary builder ──────────────────────────────────────────────────────────

def build_summary(
    command: str | None,
    check_type: str,
    exit_code: int | None,
    combined_text: str,
    tool_availability: dict[str, str],
    max_failure_lines: int,
    fail_on_missing_evidence: bool,
    fail_on_secret: bool,
    secret_detected_in_input: bool,
) -> dict:
    """Build the full validation output summary dict."""
    # Redact secrets in combined text
    combined_text, secret_in_text = detect_and_redact_secrets(combined_text)
    secret_detected = secret_detected_in_input or secret_in_text

    has_any_input = bool(combined_text.strip()) or exit_code is not None

    # Parse outputs
    parsed_pytest = parse_pytest_output(combined_text)
    artifact_guard_result = parse_artifact_guard_output(combined_text)
    sync_gate_result = parse_sync_gate_output(combined_text)
    generated_paths = extract_generated_output_paths(combined_text)

    # Extract failure snippet
    failure_snippet, truncated = ([], False)
    if combined_text.strip():
        failure_snippet, truncated = extract_failure_snippet(combined_text, max_failure_lines)

    # Classify tools
    passed_tools = [n for n, s in tool_availability.items() if s in ("passed", "available")]
    failed_tools = [n for n, s in tool_availability.items() if s == "failed"]
    unavailable_tools = [n for n, s in tool_availability.items()
                         if s in ("unavailable", "skipped_not_available")]
    skipped_tools = [n for n, s in tool_availability.items()
                     if s in ("skipped", "skipped_not_applicable")]

    # Determine status
    status = classify_status(
        exit_code=exit_code,
        check_type=check_type,
        tool_availability=tool_availability,
        parsed_pytest=parsed_pytest,
        artifact_guard_result=artifact_guard_result,
        sync_gate_result=sync_gate_result,
        secret_detected=secret_detected,
        fail_on_secret=fail_on_secret,
        fail_on_missing_evidence=fail_on_missing_evidence,
        has_any_input=has_any_input,
    )

    # Mandatory evidence check
    mandatory_evidence_present = has_any_input

    return {
        "summary_schema_version": SUMMARY_SCHEMA_VERSION,
        "command": command or "(not provided)",
        "check_type": check_type,
        "exit_code": exit_code if exit_code is not None else "unknown",
        "status": status,
        "pass_count": parsed_pytest["pass_count"],
        "fail_count": parsed_pytest["fail_count"],
        "error_count": parsed_pytest["error_count"],
        "warning_count": parsed_pytest["warning_count"],
        "unavailable_tools": unavailable_tools,
        "skipped_tools": skipped_tools,
        "failed_tools": failed_tools,
        "passed_tools": passed_tools,
        "generated_output_paths": generated_paths,
        "failure_snippet": failure_snippet,
        "truncated": truncated,
        "mandatory_evidence_present": mandatory_evidence_present,
        "secret_like_output_detected": secret_detected,
        "validation_reminder": VALIDATION_REMINDER,
        "raw_log_retention_note": RAW_LOG_RETENTION_NOTE,
    }


# ── Renderers ────────────────────────────────────────────────────────────────

def render_text(summary: dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("VALIDATION OUTPUT SUMMARY")
    lines.append("=" * 70)
    lines.append(f"Command:        {summary['command']}")
    lines.append(f"Check type:     {summary['check_type']}")
    lines.append(f"Exit code:      {summary['exit_code']}")
    lines.append(f"Status:         {summary['status']}")
    lines.append(f"Schema version: {summary['summary_schema_version']}")
    lines.append("")

    lines.append("Counts:")
    lines.append(f"  passed:   {summary['pass_count']}")
    lines.append(f"  failed:   {summary['fail_count']}")
    lines.append(f"  errors:   {summary['error_count']}")
    lines.append(f"  warnings: {summary['warning_count']}")
    lines.append("")

    if summary["passed_tools"]:
        lines.append(f"Passed tools: {', '.join(summary['passed_tools'])}")
    if summary["failed_tools"]:
        lines.append(f"Failed tools [WARNING]: {', '.join(summary['failed_tools'])}")
    if summary["unavailable_tools"]:
        lines.append(f"Unavailable tools: {', '.join(summary['unavailable_tools'])}")
    if summary["skipped_tools"]:
        lines.append(f"Skipped tools: {', '.join(summary['skipped_tools'])}")
    if summary["passed_tools"] or summary["failed_tools"] or \
       summary["unavailable_tools"] or summary["skipped_tools"]:
        lines.append("")

    if summary["generated_output_paths"]:
        lines.append("Generated output paths:")
        for p in summary["generated_output_paths"]:
            lines.append(f"  {p}")
        lines.append("")

    if summary["secret_like_output_detected"]:
        lines.append("[WARNING] Secret-like output detected and redacted.")
        lines.append("  Raw logs must be inspected locally. Do not paste raw output into PR comments.")
        lines.append("")

    if summary["failure_snippet"]:
        lines.append("Failure snippet:")
        for fl in summary["failure_snippet"]:
            lines.append(f"  {fl}")
        if summary["truncated"]:
            lines.append("  ... (output truncated; full log retained locally)")
        lines.append("")

    lines.append(f"Mandatory evidence present: {summary['mandatory_evidence_present']}")
    lines.append("")
    lines.append("-" * 70)
    lines.append(summary["validation_reminder"])
    lines.append("-" * 70)
    lines.append(summary["raw_log_retention_note"])

    return "\n".join(lines)


def render_json(summary: dict) -> str:
    return json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Local offline read-only validation output summary helper. "
            "Summarises pre-captured validation command output for Claude Code / Codex PR reports. "
            "Does not execute commands, replace validation, or modify files."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--command", default=None, help="Command string (display/evidence only; not executed)")
    p.add_argument("--exit-code", type=int, default=None, metavar="INT", help="Exit code returned by the command")
    p.add_argument(
        "--check-type",
        default="other",
        choices=sorted(VALID_CHECK_TYPES),
        help="Check classification (default: other)",
    )
    p.add_argument("--stdout-text", default=None, help="Direct stdout text snippet")
    p.add_argument("--stderr-text", default=None, help="Direct stderr text snippet")
    p.add_argument(
        "--stdout-file",
        default=None,
        metavar="PATH",
        help=f"File with captured stdout (must be under {_ALLOWED_INPUT_PREFIX!r})",
    )
    p.add_argument(
        "--stderr-file",
        default=None,
        metavar="PATH",
        help=f"File with captured stderr (must be under {_ALLOWED_INPUT_PREFIX!r})",
    )
    p.add_argument("--from-stdin", action="store_true", help="Read command output from stdin")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")
    p.add_argument("--max-failure-lines", type=int, default=30, metavar="N", help="Max failure lines in snippet (default: 30)")
    p.add_argument(
        "--tool-availability",
        action="append",
        default=[],
        dest="tool_availability",
        metavar="name=status",
        help="Declare tool availability as name=status (repeatable). "
             f"Valid statuses: {', '.join(sorted(VALID_TOOL_STATUSES))}",
    )
    p.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help=f"Write output to file (must be under {_ALLOWED_OUTPUT_PREFIX!r}). No file written by default.",
    )
    p.add_argument(
        "--fail-on-missing-required-evidence",
        action="store_true",
        help="Exit 1 if no exit code or output is provided for a mandatory check type",
    )
    p.add_argument(
        "--fail-on-secret",
        action="store_true",
        help="Exit 1 if secret-like output is detected (even if command exit code is 0)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate output path
    if args.output:
        err = validate_output_path(args.output)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 2

    # Validate input file paths
    if args.stdout_file:
        err = validate_input_path(args.stdout_file, "--stdout-file")
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 2

    if args.stderr_file:
        err = validate_input_path(args.stderr_file, "--stderr-file")
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 2

    # Parse tool availability
    tool_availability: dict[str, str] = {}
    for item in args.tool_availability:
        if "=" not in item:
            print(f"ERROR: --tool-availability must be name=status, got: {item!r}", file=sys.stderr)
            return 2
        name, status = item.split("=", 1)
        name = name.strip()
        status = status.strip()
        if not name:
            print(f"ERROR: --tool-availability tool name is empty: {item!r}", file=sys.stderr)
            return 2
        if status not in VALID_TOOL_STATUSES:
            print(
                f"ERROR: --tool-availability status {status!r} is not valid. "
                f"Valid values: {', '.join(sorted(VALID_TOOL_STATUSES))}",
                file=sys.stderr,
            )
            return 2
        tool_availability[name] = status

    # Collect input text
    parts = []
    secret_detected_in_input = False

    if args.stdout_text:
        text, sd = detect_and_redact_secrets(args.stdout_text)
        if sd:
            secret_detected_in_input = True
        parts.append(text)

    if args.stderr_text:
        text, sd = detect_and_redact_secrets(args.stderr_text)
        if sd:
            secret_detected_in_input = True
        parts.append(text)

    if args.stdout_file:
        try:
            file_text = pathlib.Path(args.stdout_file).read_text(encoding="utf-8", errors="replace")
            text, sd = detect_and_redact_secrets(file_text)
            if sd:
                secret_detected_in_input = True
            parts.append(text)
        except OSError as e:
            print(f"ERROR: Cannot read --stdout-file {args.stdout_file!r}: {e}", file=sys.stderr)
            return 2

    if args.stderr_file:
        try:
            file_text = pathlib.Path(args.stderr_file).read_text(encoding="utf-8", errors="replace")
            text, sd = detect_and_redact_secrets(file_text)
            if sd:
                secret_detected_in_input = True
            parts.append(text)
        except OSError as e:
            print(f"ERROR: Cannot read --stderr-file {args.stderr_file!r}: {e}", file=sys.stderr)
            return 2

    if args.from_stdin:
        try:
            stdin_text = sys.stdin.read()
            text, sd = detect_and_redact_secrets(stdin_text)
            if sd:
                secret_detected_in_input = True
            parts.append(text)
        except OSError as e:
            print(f"ERROR: Cannot read stdin: {e}", file=sys.stderr)
            return 2

    combined_text = "\n".join(parts)

    summary = build_summary(
        command=args.command,
        check_type=args.check_type,
        exit_code=args.exit_code,
        combined_text=combined_text,
        tool_availability=tool_availability,
        max_failure_lines=args.max_failure_lines,
        fail_on_missing_evidence=args.fail_on_missing_required_evidence,
        fail_on_secret=args.fail_on_secret,
        secret_detected_in_input=secret_detected_in_input,
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

    # Determine exit code
    if summary["secret_like_output_detected"] and args.fail_on_secret:
        return 1
    if not summary["mandatory_evidence_present"] and args.fail_on_missing_required_evidence:
        return 1
    if summary["status"] == "ERROR" and args.fail_on_missing_required_evidence:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
