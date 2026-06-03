"""
Local offline stdlib PR evidence consistency guard.

Reads two local text files (PR body draft and final comment draft) and checks
them for consistency and evidence quality before Ready for review: YES.

Makes no network calls. Posts no GitHub comments. Modifies no files.
Does not prove commands actually ran. Validates consistency and evidence
structure only.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Known helper names that should not appear in abbreviated form ────────────

KNOWN_HELPER_NAMES = [
    "status_snapshot.py",
    "diff_scope_summary.py",
    "code_blast_radius.py",
    "preflight_sync_main.py",
    "preflight_generated_artifact_guard.py",
    "verify_project_gitleaks.py",
    "check_security_tools.py",
    "run_available_security_checks.py",
]

# ── Command-line starters that must not contain "..." ────────────────────────

COMMAND_STARTERS = [
    "python ",
    "python3 ",
    "git ",
    "uv ",
    "ruff ",
    "pytest",
    "python -m pytest",
]

# ── Standard network wording ─────────────────────────────────────────────────

STANDARD_NETWORK_WORDING = (
    "Network was used only for Remote Main Sync Gate / git remote synchronization "
    "and PR push/publication. This WP adds no runtime network behavior, no API "
    "polling, no account access, and no product network behavior."
)

_NO_NETWORK_PATTERN = re.compile(r"no network was used", re.IGNORECASE)

# ── Test count line pattern ───────────────────────────────────────────────────
# Matches lines like: 68 passed, 0 failed, 0 errors
#                     1583 passed, 0 failed, 0 errors, 1 warning
# Warning count is captured when present and included in the normalized output.
_TEST_COUNT_PATTERN = re.compile(
    r"(\d+)\s+passed[\s,].*?(\d+)\s+failed[\s,].*?(\d+)\s+errors?"
    r"(?:[,\s]+(\d+)\s+warnings?)?",
    re.IGNORECASE,
)

# ── Head SHA pattern (40 hex chars) ──────────────────────────────────────────
_SHA_FULL_PATTERN = re.compile(r"\b([0-9a-f]{40})\b", re.IGNORECASE)

# ── Head SHA label patterns ───────────────────────────────────────────────────
# Only match "Head commit", "Head SHA", or "head:" labels — not generic "commit:"
# which would incorrectly match "Required previous merge commit: SHA" lines.
# The :? allows both "Head commit SHA" and "Head commit: SHA" forms.
_SHA_LABEL_PATTERN = re.compile(
    r"(?:head\s+commit|head\s+sha|head:)\s*:?\s*[`\s]*([0-9a-f]{40})\b",
    re.IGNORECASE,
)

# ── Ready for review pattern ──────────────────────────────────────────────────
_READY_YES_PATTERN = re.compile(
    r"ready\s+for\s+review\s*:\s*yes", re.IGNORECASE
)
_READY_NO_PATTERN = re.compile(
    r"ready\s+for\s+review\s*:\s*no\b", re.IGNORECASE
)
_READY_ANY_PATTERN = re.compile(
    r"ready\s+for\s+review", re.IGNORECASE
)

# ── File-count patterns ───────────────────────────────────────────────────────
_FILE_COUNT_PATTERNS = [
    re.compile(r"(\d+)\s+changed\s+files?", re.IGNORECASE),
    re.compile(r"Added\s+\((\d+)\)", re.IGNORECASE),
    re.compile(r"Modified\s+\((\d+)\)", re.IGNORECASE),
]

# ── Inline test-count patterns (K) ────────────────────────────────────────────
# Matches parenthetical test-count phrases like "(33 tests)", "(34 focused tests)",
# "focused tests (34 tests)". These belong in validation sections, not file lists.
_INLINE_TEST_COUNT_PATTERN = re.compile(
    r"\(\s*\d+\s+(?:focused\s+)?tests?\s*\)", re.IGNORECASE
)

# ── Placeholder evidence patterns (L) ─────────────────────────────────────────
_PLACEHOLDER_LITERAL_TOKENS = [
    "<HEAD_SHA>",
    "placeholder",
    "actual:",
    "TBD",
    "TODO",
]
# Detect long runs of the same repeated character that signal fake SHA filler.
_FAKE_SHA_FILLER_PATTERN = re.compile(r"a{8,}", re.IGNORECASE)

# ── Current final evidence marker patterns (M) ────────────────────────────────
_CURRENT_FINAL_MARKER_PATTERN = re.compile(
    r"CURRENT\s+FINAL\s+WP\s+EVIDENCE", re.IGNORECASE
)

# ── Posted evidence note pattern (O) ──────────────────────────────────────────
_POSTED_EVIDENCE_NOTE_PATTERN = re.compile(
    r"Guard\s+input\s+source\s*:", re.IGNORECASE
)

# ── Security tool honesty patterns ───────────────────────────────────────────
_SECURITY_PASSED_PATTERNS = [
    re.compile(r"gitleaks\s+passed", re.IGNORECASE),
    re.compile(r"semgrep\s+passed", re.IGNORECASE),
    re.compile(r"pip.audit\s+passed", re.IGNORECASE),
]
_SECURITY_UNAVAILABLE_PATTERNS = [
    re.compile(
        r"gitleaks.*?(NOT_AVAILABLE|SKIPPED_NOT_AVAILABLE|UNAVAILABLE|SKIPPED)",
        re.IGNORECASE,
    ),
    re.compile(
        r"semgrep.*?(NOT_AVAILABLE|SKIPPED_NOT_AVAILABLE|UNAVAILABLE|SKIPPED)",
        re.IGNORECASE,
    ),
    re.compile(
        r"pip.?audit.*?(NOT_AVAILABLE|SKIPPED_NOT_AVAILABLE|UNAVAILABLE|SKIPPED)",
        re.IGNORECASE,
    ),
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_test_counts(text: str) -> list[str]:
    """Return normalized test count strings found in the text.

    Warning counts are included in the normalized string when present so that
    mismatched warning counts between PR body and final comment are detected.
    """
    results = []
    for m in _TEST_COUNT_PATTERN.finditer(text):
        passed = int(m.group(1))
        failed = int(m.group(2))
        errors = int(m.group(3))
        warning_count = int(m.group(4)) if m.group(4) is not None else 0
        base = f"{passed} passed, {failed} failed, {errors} errors"
        if warning_count > 0:
            base += f", {warning_count} warning(s)"
        results.append(base)
    return results


def _extract_labeled_shas(text: str) -> list[str]:
    """Return SHAs that appear next to head-commit/SHA labels."""
    return [m.group(1).lower() for m in _SHA_LABEL_PATTERN.finditer(text)]


def _extract_all_shas(text: str) -> list[str]:
    """Return all 40-character SHAs found in text."""
    return [m.group(1).lower() for m in _SHA_FULL_PATTERN.finditer(text)]


def _extract_file_counts(text: str) -> dict[str, list[str]]:
    """Return a dict mapping pattern label to matched count strings."""
    result: dict[str, list[str]] = {}
    for pat in _FILE_COUNT_PATTERNS:
        matches = [m.group(0) for m in pat.finditer(text)]
        if matches:
            result[pat.pattern] = matches
    return result


# ── Guard checks ─────────────────────────────────────────────────────────────

def check_missing_files(
    pr_body_path: pathlib.Path,
    final_comment_path: pathlib.Path,
) -> list[str]:
    errors = []
    if not pr_body_path.exists():
        errors.append(
            f"[A] PR body file not found: {pr_body_path}"
        )
    if not final_comment_path.exists():
        errors.append(
            f"[A] Final comment file not found: {final_comment_path}"
        )
    return errors


def check_empty_evidence(
    pr_body: str,
    final_comment: str,
) -> list[str]:
    errors = []
    if not pr_body.strip():
        errors.append("[B] PR body is empty.")
    if not final_comment.strip():
        errors.append("[B] Final comment is empty.")
    return errors


def check_ellipses_in_commands(
    pr_body: str,
    final_comment: str,
    required_commands: list[str],
) -> list[str]:
    errors = []
    for label, text in [("PR body", pr_body), ("final comment", final_comment)]:
        for line in text.splitlines():
            stripped = line.strip()
            # Check lines that look like commands
            is_command_line = any(
                stripped.startswith(starter) or stripped.startswith(f"$ {starter}")
                for starter in COMMAND_STARTERS
            )
            if is_command_line and "..." in stripped:
                errors.append(
                    f"[C] Ellipsis found in command line in {label}: {stripped!r}"
                )
            # Check known helper names
            for helper in KNOWN_HELPER_NAMES:
                if helper in stripped and "..." in stripped:
                    errors.append(
                        f"[C] Helper '{helper}' appears with '...' in {label}: "
                        f"{stripped!r}"
                    )
        # Check if any required command is present in abbreviated form
        for cmd in required_commands:
            if "..." in cmd:
                errors.append(
                    f"[C] Required command itself contains '...': {cmd!r}"
                )
    return errors


def check_required_commands(
    pr_body: str,
    final_comment: str,
    required_commands: list[str],
) -> list[str]:
    errors = []
    for cmd in required_commands:
        in_body = cmd in pr_body
        in_comment = cmd in final_comment
        if not in_body and not in_comment:
            errors.append(
                f"[D] Required command missing from both PR body and final comment: "
                f"{cmd!r}"
            )
        elif not in_body:
            errors.append(
                f"[D] Required command missing from PR body (present in final comment): "
                f"{cmd!r}"
            )
        elif not in_comment:
            errors.append(
                f"[D] Required command missing from final comment (present in PR body): "
                f"{cmd!r}"
            )
    return errors


def check_helper_symmetry(
    pr_body: str,
    final_comment: str,
) -> list[str]:
    """Detect known helpers present in one surface but not the other."""
    errors = []
    for helper in KNOWN_HELPER_NAMES:
        in_body = helper in pr_body
        in_comment = helper in final_comment
        if in_body and not in_comment:
            errors.append(
                f"[D] Helper '{helper}' appears in PR body but not in final comment."
            )
        elif in_comment and not in_body:
            errors.append(
                f"[D] Helper '{helper}' appears in final comment but not in PR body."
            )
    return errors


def check_head_sha(
    pr_body: str,
    final_comment: str,
    expected_head: str | None,
) -> list[str]:
    errors = []

    if expected_head:
        sha = expected_head.lower()
        in_body = sha in pr_body.lower()
        in_comment = sha in final_comment.lower()
        if not in_body and not in_comment:
            errors.append(
                f"[E] Expected head SHA {sha!r} missing from both PR body and "
                f"final comment."
            )
        elif not in_body:
            errors.append(
                f"[E] Expected head SHA {sha!r} missing from PR body "
                f"(present in final comment)."
            )
        elif not in_comment:
            errors.append(
                f"[E] Expected head SHA {sha!r} missing from final comment "
                f"(present in PR body)."
            )

    # Check for labeled SHA mismatch between the two surfaces
    body_shas = _extract_labeled_shas(pr_body)
    comment_shas = _extract_labeled_shas(final_comment)
    if body_shas and comment_shas:
        if set(body_shas) != set(comment_shas):
            errors.append(
                f"[E] Head SHA mismatch between PR body {body_shas} and "
                f"final comment {comment_shas}."
            )

    # Check for two different full SHAs labeled as head across surfaces
    body_labeled = set(body_shas)
    comment_labeled = set(comment_shas)
    all_labeled = body_labeled | comment_labeled
    if len(all_labeled) > 1:
        errors.append(
            f"[E] Multiple distinct head SHAs detected across surfaces: "
            f"{sorted(all_labeled)}. PR body and final comment must use the same SHA."
        )

    return errors


def check_test_counts(
    pr_body: str,
    final_comment: str,
) -> list[str]:
    errors = []
    body_counts = _extract_test_counts(pr_body)
    comment_counts = _extract_test_counts(final_comment)

    # Build multisets for comparison
    body_set = sorted(set(body_counts))
    comment_set = sorted(set(comment_counts))

    if body_counts and comment_counts and body_set != comment_set:
        errors.append(
            f"[F] Test count mismatch between PR body and final comment.\n"
            f"    PR body counts:      {body_counts}\n"
            f"    Final comment counts: {comment_counts}"
        )
    return errors


def check_network_wording(
    pr_body: str,
    final_comment: str,
    require_standard: bool,
) -> list[str]:
    if not require_standard:
        return []
    errors = []
    body_has_standard = STANDARD_NETWORK_WORDING in pr_body
    comment_has_standard = STANDARD_NETWORK_WORDING in final_comment

    if not body_has_standard:
        errors.append(
            "[G] Standard network wording missing from PR body.\n"
            f"    Expected: {STANDARD_NETWORK_WORDING!r}"
        )
    if not comment_has_standard:
        errors.append(
            "[G] Standard network wording missing from final comment.\n"
            f"    Expected: {STANDARD_NETWORK_WORDING!r}"
        )

    # Detect "no network was used" when standard wording is required
    for label, text in [("PR body", pr_body), ("final comment", final_comment)]:
        if _NO_NETWORK_PATTERN.search(text) and not STANDARD_NETWORK_WORDING in text:
            errors.append(
                f"[G] 'No network was used' wording found in {label} but standard "
                f"network workflow wording is required. Replace with the standard "
                f"wording that acknowledges git/PR network use."
            )

    return errors


def check_ready_status(
    pr_body: str,
    final_comment: str,
    require_ready_yes: bool,
) -> list[str]:
    if not require_ready_yes:
        return []
    errors = []
    body_yes = bool(_READY_YES_PATTERN.search(pr_body))
    body_no = bool(_READY_NO_PATTERN.search(pr_body))
    comment_yes = bool(_READY_YES_PATTERN.search(final_comment))
    comment_no = bool(_READY_NO_PATTERN.search(final_comment))
    body_any = bool(_READY_ANY_PATTERN.search(pr_body))
    comment_any = bool(_READY_ANY_PATTERN.search(final_comment))

    if not body_yes:
        errors.append("[H] 'Ready for review: YES' missing from PR body.")
    if not comment_yes:
        errors.append("[H] 'Ready for review: YES' missing from final comment.")

    # Mismatch: one says YES, other says NO
    if body_yes and comment_no:
        errors.append(
            "[H] PR body says 'Ready for review: YES' but final comment says NO."
        )
    if comment_yes and body_no:
        errors.append(
            "[H] Final comment says 'Ready for review: YES' but PR body says NO."
        )

    # Ready appears in one but not the other
    if body_any and not comment_any:
        errors.append(
            "[H] 'Ready for review' appears in PR body but not in final comment."
        )
    if comment_any and not body_any:
        errors.append(
            "[H] 'Ready for review' appears in final comment but not in PR body."
        )

    return errors


def check_file_counts(
    pr_body: str,
    final_comment: str,
) -> list[str]:
    errors = []
    body_counts = _extract_file_counts(pr_body)
    comment_counts = _extract_file_counts(final_comment)

    for pat_key in body_counts:
        if pat_key in comment_counts:
            bc = body_counts[pat_key]
            cc = comment_counts[pat_key]
            if bc != cc:
                errors.append(
                    f"[I] File count mismatch for pattern '{pat_key}':\n"
                    f"    PR body:       {bc}\n"
                    f"    Final comment: {cc}"
                )
    return errors


def check_security_honesty(
    pr_body: str,
    final_comment: str,
) -> list[str]:
    errors = []
    for label, text in [("PR body", pr_body), ("final comment", final_comment)]:
        for i, passed_pat in enumerate(_SECURITY_PASSED_PATTERNS):
            if passed_pat.search(text):
                unavail_pat = _SECURITY_UNAVAILABLE_PATTERNS[i]
                if unavail_pat.search(text):
                    tool_name = ["gitleaks", "semgrep", "pip-audit"][i]
                    errors.append(
                        f"[J] Security honesty conflict in {label}: "
                        f"'{tool_name} passed' appears alongside "
                        f"NOT_AVAILABLE/SKIPPED wording."
                    )
    return errors


# ── New guard checks (WP47) ───────────────────────────────────────────────────

def check_inline_test_counts(
    pr_body: str,
    final_comment: str,
) -> list[str]:
    """K — Fail if parenthetical test-count phrases appear in either file."""
    errors = []
    for label, text in [("PR body", pr_body), ("final comment", final_comment)]:
        for m in _INLINE_TEST_COUNT_PATTERN.finditer(text):
            errors.append(
                f"[K] Inline test count found in {label}: {m.group(0)!r}. "
                "Move test counts to validation evidence only; remove parenthetical "
                "count from file list / summary."
            )
    return errors


def check_placeholder_evidence(
    pr_body: str,
    final_comment: str,
) -> list[str]:
    """L — Fail if obvious placeholder evidence tokens appear in either file."""
    errors = []
    for label, text in [("PR body", pr_body), ("final comment", final_comment)]:
        for token in _PLACEHOLDER_LITERAL_TOKENS:
            if token in text:
                errors.append(
                    f"[L] Placeholder evidence token {token!r} found in {label}. "
                    "Replace with actual evidence before marking Ready for review: YES."
                )
        if _FAKE_SHA_FILLER_PATTERN.search(text):
            m = _FAKE_SHA_FILLER_PATTERN.search(text)
            assert m is not None
            errors.append(
                f"[L] Fake SHA filler (repeated 'a' characters: {m.group(0)!r}) "
                f"found in {label}. Replace with the actual head commit SHA."
            )
    return errors


def check_current_final_marker(
    final_comment: str,
) -> list[str]:
    """M — Fail if final comment lacks the CURRENT FINAL WP EVIDENCE marker."""
    if _CURRENT_FINAL_MARKER_PATTERN.search(final_comment):
        return []
    return [
        "[M] Final comment is missing the required current-final evidence marker. "
        "The final comment must start with or contain: "
        "'CURRENT FINAL WP EVIDENCE' or "
        "'CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments'. "
        "This marker tells reviewers which evidence comment is current."
    ]


def check_stale_count_tokens(
    pr_body: str,
    final_comment: str,
    stale_tokens: list[str],
) -> list[str]:
    """N — Fail if any supplied stale token appears in either file."""
    errors = []
    for token in stale_tokens:
        for label, text in [("PR body", pr_body), ("final comment", final_comment)]:
            if token in text:
                errors.append(
                    f"[N] Stale count token {token!r} found in {label}. "
                    "Remove or replace with the current accurate count."
                )
    return errors


def check_posted_evidence_note(
    pr_body: str,
    final_comment: str,
) -> list[str]:
    """O — Fail unless both files contain a 'Guard input source:' note."""
    errors = []
    if not _POSTED_EVIDENCE_NOTE_PATTERN.search(pr_body):
        errors.append(
            "[O] PR body is missing the required 'Guard input source:' note. "
            "Add a line such as: "
            "'Guard input source: exact local drafts intended for posting' or "
            "'Guard input source: copied posted PR body and current final evidence comment'."
        )
    if not _POSTED_EVIDENCE_NOTE_PATTERN.search(final_comment):
        errors.append(
            "[O] Final comment is missing the required 'Guard input source:' note. "
            "Add a line such as: "
            "'Guard input source: exact local drafts intended for posting' or "
            "'Guard input source: copied posted PR body and current final evidence comment'."
        )
    return errors


# ── Main guard ────────────────────────────────────────────────────────────────

def run_guard(
    pr_body_path: pathlib.Path,
    final_comment_path: pathlib.Path,
    expected_head: str | None,
    required_commands: list[str],
    require_standard_network_wording: bool,
    require_ready_yes: bool,
    forbid_inline_test_counts: bool = False,
    forbid_placeholder_evidence: bool = False,
    require_current_final_marker: bool = False,
    stale_count_tokens: list[str] | None = None,
    require_posted_evidence_note: bool = False,
) -> tuple[bool, list[str], list[str], list[str]]:
    """
    Returns (passed, errors, warnings, checked_categories).
    passed = True if no errors.
    """
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []

    # A — Missing files
    checked.append("A:missing_files")
    missing = check_missing_files(pr_body_path, final_comment_path)
    errors.extend(missing)
    if missing:
        # Cannot proceed without files
        return False, errors, warnings, checked

    pr_body = pr_body_path.read_text(encoding="utf-8", errors="replace")
    final_comment = final_comment_path.read_text(encoding="utf-8", errors="replace")

    # B — Empty evidence
    checked.append("B:empty_evidence")
    errors.extend(check_empty_evidence(pr_body, final_comment))

    # C — Ellipses in commands
    checked.append("C:ellipses_in_commands")
    errors.extend(
        check_ellipses_in_commands(pr_body, final_comment, required_commands)
    )

    # D — Required command presence + helper symmetry
    checked.append("D:required_commands")
    if required_commands:
        errors.extend(
            check_required_commands(pr_body, final_comment, required_commands)
        )
    checked.append("D:helper_symmetry")
    errors.extend(check_helper_symmetry(pr_body, final_comment))

    # E — Head SHA
    checked.append("E:head_sha")
    errors.extend(check_head_sha(pr_body, final_comment, expected_head))

    # F — Test counts
    checked.append("F:test_counts")
    errors.extend(check_test_counts(pr_body, final_comment))

    # G — Network wording
    checked.append("G:network_wording")
    errors.extend(
        check_network_wording(
            pr_body, final_comment, require_standard_network_wording
        )
    )

    # H — Ready status
    checked.append("H:ready_status")
    errors.extend(
        check_ready_status(pr_body, final_comment, require_ready_yes)
    )

    # I — File counts
    checked.append("I:file_counts")
    errors.extend(check_file_counts(pr_body, final_comment))

    # J — Security honesty
    checked.append("J:security_honesty")
    errors.extend(check_security_honesty(pr_body, final_comment))

    # K — Inline test counts (optional)
    checked.append("K:inline_test_counts")
    if forbid_inline_test_counts:
        errors.extend(check_inline_test_counts(pr_body, final_comment))

    # L — Placeholder evidence (optional)
    checked.append("L:placeholder_evidence")
    if forbid_placeholder_evidence:
        errors.extend(check_placeholder_evidence(pr_body, final_comment))

    # M — Current final marker (optional, final comment only)
    checked.append("M:current_final_marker")
    if require_current_final_marker:
        errors.extend(check_current_final_marker(final_comment))

    # N — Stale count tokens (optional)
    checked.append("N:stale_count_tokens")
    if stale_count_tokens:
        errors.extend(check_stale_count_tokens(pr_body, final_comment, stale_count_tokens))

    # O — Posted evidence note (optional)
    checked.append("O:posted_evidence_note")
    if require_posted_evidence_note:
        errors.extend(check_posted_evidence_note(pr_body, final_comment))

    passed = len(errors) == 0
    return passed, errors, warnings, checked


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pr_evidence_consistency_guard",
        description=(
            "Local offline stdlib PR evidence consistency guard. "
            "Reads local PR body and final comment drafts and checks them "
            "for consistency before Ready for review: YES."
        ),
    )
    p.add_argument(
        "--pr-body",
        required=True,
        metavar="PATH",
        help="Path to local PR body draft file.",
    )
    p.add_argument(
        "--final-comment",
        required=True,
        metavar="PATH",
        help="Path to local final comment draft file.",
    )
    p.add_argument(
        "--expected-head",
        metavar="SHA",
        default=None,
        help="Expected 40-character head commit SHA. Must appear in both files.",
    )
    p.add_argument(
        "--required-command",
        metavar="TEXT",
        action="append",
        default=[],
        dest="required_commands",
        help=(
            "Exact command text that must appear in both PR body and final comment. "
            "Repeatable."
        ),
    )
    p.add_argument(
        "--require-standard-network-wording",
        action="store_true",
        default=False,
        help=(
            "Require the standard network wording to appear in both files: "
            f"{STANDARD_NETWORK_WORDING!r}"
        ),
    )
    p.add_argument(
        "--require-ready-yes",
        action="store_true",
        default=False,
        help="Require 'Ready for review: YES' to appear in both files.",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: text (default) or json.",
    )
    p.add_argument(
        "--forbid-inline-test-counts",
        action="store_true",
        default=False,
        help=(
            "Fail if PR body or final comment contains parenthetical test-count "
            "phrases such as '(33 tests)' or 'focused tests (34 tests)' outside "
            "validation evidence. Move test counts to validation sections only."
        ),
    )
    p.add_argument(
        "--forbid-placeholder-evidence",
        action="store_true",
        default=False,
        help=(
            "Fail if either file contains obvious placeholder evidence tokens: "
            "'<HEAD_SHA>', 'placeholder', 'actual:', 'TBD', 'TODO', or fake SHA "
            "filler (long repeated 'a' characters)."
        ),
    )
    p.add_argument(
        "--require-current-final-marker",
        action="store_true",
        default=False,
        help=(
            "Fail unless the final comment contains the required current-final "
            "evidence marker: 'CURRENT FINAL WP EVIDENCE' or "
            "'CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments'."
        ),
    )
    p.add_argument(
        "--forbid-stale-count-tokens",
        metavar="TEXT",
        action="append",
        default=[],
        dest="stale_count_tokens",
        help=(
            "Fail if the supplied stale token appears in either PR body or final "
            "comment. Repeatable. Example: --forbid-stale-count-tokens '1612 passed'."
        ),
    )
    p.add_argument(
        "--require-posted-evidence-note",
        action="store_true",
        default=False,
        help=(
            "Fail unless both PR body and final comment contain a 'Guard input "
            "source:' line identifying whether the guard was run on exact local "
            "drafts intended for posting or on copied posted GitHub content."
        ),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    pr_body_path = pathlib.Path(args.pr_body)
    final_comment_path = pathlib.Path(args.final_comment)

    # Exit 2 for missing files, non-file paths, or unreadable input.
    usage_errors: list[str] = []
    if not pr_body_path.exists():
        usage_errors.append(f"PR body file not found: {pr_body_path}")
    elif not pr_body_path.is_file():
        usage_errors.append(f"PR body path is not a regular file: {pr_body_path}")

    if not final_comment_path.exists():
        usage_errors.append(f"Final comment file not found: {final_comment_path}")
    elif not final_comment_path.is_file():
        usage_errors.append(
            f"Final comment path is not a regular file: {final_comment_path}"
        )

    if usage_errors:
        for msg in usage_errors:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 2

    try:
        pr_body_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"ERROR: Cannot read PR body file: {exc}", file=sys.stderr)
        return 2

    try:
        final_comment_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"ERROR: Cannot read final comment file: {exc}", file=sys.stderr)
        return 2

    passed, errors, warnings, checked = run_guard(
        pr_body_path=pr_body_path,
        final_comment_path=final_comment_path,
        expected_head=args.expected_head,
        required_commands=args.required_commands,
        require_standard_network_wording=args.require_standard_network_wording,
        require_ready_yes=args.require_ready_yes,
        forbid_inline_test_counts=args.forbid_inline_test_counts,
        forbid_placeholder_evidence=args.forbid_placeholder_evidence,
        require_current_final_marker=args.require_current_final_marker,
        stale_count_tokens=args.stale_count_tokens,
        require_posted_evidence_note=args.require_posted_evidence_note,
    )

    if args.format == "json":
        result: dict[str, Any] = {
            "status": "PASS" if passed else "FAIL",
            "errors": errors,
            "warnings": warnings,
            "checked_categories": checked,
        }
        print(json.dumps(result, indent=2))
        return 0 if passed else 1

    # Text output
    if passed:
        print("PR evidence consistency guard: PASS")
        print(f"Checked categories: {', '.join(checked)}")
    else:
        print("PR evidence consistency guard: FAIL")
        print(f"Checked categories: {', '.join(checked)}")
        print(f"\n{len(errors)} error(s) found:\n")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        print(
            "\nFix the above issues in the PR body and/or final comment "
            "before setting Ready for review: YES."
        )

    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
