#!/usr/bin/env python3
"""
Posted PR evidence verifier — WP58 workflow-governance helper.

Read-only. Manual CLI. Public GitHub REST API only. No authentication.
No token loading. No third-party dependencies. No posting or editing.

Usage:
  python tools/git/posted_pr_evidence_verifier.py \
    --repo owner/repo --pr 58 --expected-head <SHA> \
    --require-current-final-marker --require-guard-result \
    --require-ready-yes --require-standard-network-wording \
    --forbid-placeholder-evidence --forbid-inline-test-counts \
    --require-posted-verifier-pass --require-follow-up-classification \
    --require-file-count --expected-file-count 29 \
    --format text

Exit codes:
  0 — pass
  1 — verification failed
  2 — usage error
  3 — GitHub fetch / network error
  4 — JSON parse error
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


GITHUB_API = "https://api.github.com"
CURRENT_FINAL_MARKER = "CURRENT FINAL WP EVIDENCE"
PLACEHOLDER_TOKENS = ["<HEAD_SHA>", "TBD", "TODO", "placeholder", "actual:", "<SHA>", "<BASE_SHA>"]
GUARD_RESULT_PHRASES = ["PR evidence consistency guard: PASS", "Checked categories:", "exit 0"]
STALE_POSTED_VERIFIER_PHRASES = [
    "Posted GitHub evidence verifier: PENDING",
    "PR number not yet assigned",
    "Will be run after PR is created",
]
INLINE_TEST_COUNT_PATTERN = re.compile(
    r'\.py\b[^\n]*\(\s*\d+\s+(?:tests?|passed|failing|failed)\s*\)',
    re.IGNORECASE,
)


@dataclass
class VerifierArgs:
    repo: str
    pr: int
    expected_head: str
    require_current_final_marker: bool = False
    require_guard_result: bool = False
    require_ready_yes: bool = False
    require_standard_network_wording: bool = False
    forbid_placeholder_evidence: bool = False
    forbid_inline_test_counts: bool = False
    require_follow_up_classification: bool = False
    require_guard_input_source: bool = False
    require_file_count: bool = False
    expected_file_count: Optional[int] = None
    require_posted_verifier_pass: bool = False
    format: str = "text"
    timeout_seconds: int = 10
    comment_page_size: int = 100
    max_comment_pages: int = 5


@dataclass
class VerifierResult:
    status: str  # "PASS" or "FAIL"
    errors: List[str] = field(default_factory=list)
    checked_categories: List[str] = field(default_factory=list)
    pr_url: str = ""
    pr_head_sha: str = ""
    latest_current_final_url: str = ""
    exit_code: int = 0


def _fetch_json(url: str, timeout: int) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "posted-pr-evidence-verifier/wp58",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise RuntimeError(f"GitHub API rate limited or forbidden: {e.code} {e.reason}")
        if e.code == 404:
            raise RuntimeError(f"GitHub resource not found: {url}")
        raise RuntimeError(f"GitHub API HTTP error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"GitHub API network error: {e.reason}")
    except json.JSONDecodeError as e:
        raise ValueError(f"GitHub API JSON parse error: {e}")


def _contains_guard_result(text: str) -> bool:
    return all(phrase in text for phrase in GUARD_RESULT_PHRASES)


def _contains_ready_yes(text: str) -> bool:
    return "Ready for review: YES" in text


def _contains_standard_network_wording(text: str) -> bool:
    network_indicators = [
        "Remote Main Sync Gate",
        "git remote synchronization",
        "workflow network",
        "PR publication",
        "git fetch",
        "git push",
    ]
    return any(indicator in text for indicator in network_indicators)


def _contains_placeholder(text: str) -> bool:
    return any(tok in text for tok in PLACEHOLDER_TOKENS)


def _contains_guard_input_source(text: str) -> bool:
    return "Guard input source:" in text


def _contains_stale_posted_verifier(text: str) -> Optional[str]:
    """Return the first stale posted-verifier phrase found, or None."""
    for phrase in STALE_POSTED_VERIFIER_PHRASES:
        if phrase in text:
            return phrase
    return None


def _contains_posted_verifier_pass(text: str) -> bool:
    return "Posted GitHub evidence verifier: PASS" in text and "exit 0" in text


def _contains_follow_up_classification(text: str) -> bool:
    return "Follow-up correction required:" in text


def _contains_inline_test_counts(text: str) -> bool:
    return bool(INLINE_TEST_COUNT_PATTERN.search(text))


def _parse_file_count(text: str) -> Optional[int]:
    match = re.search(r"Changed files:\s*(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def _fetch_pr(owner: str, repo: str, pr: int, timeout: int) -> Dict[str, Any]:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr}"
    return _fetch_json(url, timeout)


def _fetch_all_comments(
    owner: str, repo: str, pr: int, page_size: int, max_pages: int, timeout: int
) -> List[Dict[str, Any]]:
    all_comments: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        url = (
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr}/comments"
            f"?per_page={page_size}&page={page}"
        )
        page_data = _fetch_json(url, timeout)
        if not page_data:
            break
        all_comments.extend(page_data)
        if len(page_data) < page_size:
            break
    return all_comments


def _find_current_final_comments(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [c for c in comments if CURRENT_FINAL_MARKER in c.get("body", "")]


def _latest_comment(comments: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not comments:
        return None
    return max(comments, key=lambda c: c.get("updated_at", c.get("created_at", "")))


def verify(args: VerifierArgs) -> VerifierResult:
    if "/" not in args.repo:
        return VerifierResult(
            status="FAIL",
            errors=["[2] Invalid --repo format. Use owner/repo."],
            exit_code=2,
        )

    owner, repo_name = args.repo.split("/", 1)
    result = VerifierResult(status="PASS")
    errors: List[str] = []
    checked: List[str] = []

    # A: Fetch PR
    try:
        pr_data = _fetch_pr(owner, repo_name, args.pr, args.timeout_seconds)
        checked.append("A:pr_fetch")
    except ValueError as e:
        return VerifierResult(status="FAIL", errors=[f"[4] {e}"], exit_code=4)
    except RuntimeError as e:
        return VerifierResult(status="FAIL", errors=[f"[3] {e}"], exit_code=3)

    result.pr_url = pr_data.get("html_url", "")
    result.pr_head_sha = pr_data.get("head", {}).get("sha", "")
    pr_body = pr_data.get("body") or ""

    # B: PR body checks
    pr_body_errors: List[str] = []
    if not pr_body:
        pr_body_errors.append("[B] PR body is empty.")
    else:
        if args.expected_head and args.expected_head not in pr_body:
            pr_body_errors.append(
                f"[B] PR body does not contain expected head SHA: {args.expected_head}"
            )
        if args.require_ready_yes and not _contains_ready_yes(pr_body):
            pr_body_errors.append("[B] PR body does not contain 'Ready for review: YES'.")
        if args.require_guard_result and not _contains_guard_result(pr_body):
            pr_body_errors.append(
                "[B] PR body does not contain required guard result "
                "(PASS + Checked categories + exit 0)."
            )
        if args.require_standard_network_wording and not _contains_standard_network_wording(pr_body):
            pr_body_errors.append("[B] PR body does not contain standard network wording.")
        if args.forbid_placeholder_evidence and _contains_placeholder(pr_body):
            pr_body_errors.append("[B] PR body contains forbidden placeholder token.")
        if args.require_guard_input_source and not _contains_guard_input_source(pr_body):
            pr_body_errors.append("[B] PR body does not contain 'Guard input source:'.")

    if not pr_body_errors:
        checked.append("B:pr_body")
    else:
        errors.extend(pr_body_errors)

    # C: Fetch comments
    try:
        all_comments = _fetch_all_comments(
            owner, repo_name, args.pr,
            args.comment_page_size, args.max_comment_pages, args.timeout_seconds,
        )
        checked.append("C:comments_fetch")
    except ValueError as e:
        return VerifierResult(
            status="FAIL", errors=errors + [f"[4] {e}"],
            checked_categories=checked, exit_code=4,
        )
    except RuntimeError as e:
        return VerifierResult(
            status="FAIL", errors=errors + [f"[3] {e}"],
            checked_categories=checked, exit_code=3,
        )

    if not all_comments:
        errors.append("[C] No comments found on this PR.")

    # D: Current-final marker
    cf_comments = _find_current_final_comments(all_comments)
    if args.require_current_final_marker and not cf_comments:
        errors.append(f"[D] No comment containing '{CURRENT_FINAL_MARKER}' found.")
    elif cf_comments:
        checked.append("D:current_final_marker")

    latest_cf = _latest_comment(cf_comments)
    latest_cf_body = (latest_cf.get("body") or "") if latest_cf else ""
    result.latest_current_final_url = (latest_cf.get("html_url") or "") if latest_cf else ""

    # E: Head SHA in latest current-final comment
    if latest_cf:
        if args.expected_head and args.expected_head not in latest_cf_body:
            errors.append(
                f"[E] Latest current-final comment does not contain expected head SHA: "
                f"{args.expected_head}"
            )
        else:
            checked.append("E:head_sha")
    elif args.require_current_final_marker:
        errors.append("[E] No current-final comment found to check head SHA.")

    # F: Guard result in latest current-final comment
    if args.require_guard_result:
        if latest_cf and _contains_guard_result(latest_cf_body):
            checked.append("F:guard_result")
        elif latest_cf:
            errors.append(
                "[F] Latest current-final comment does not contain required guard result "
                "(PASS + Checked categories + exit 0)."
            )
        else:
            errors.append("[F] No current-final comment found to check guard result.")

    # G: Ready YES in latest current-final comment
    if args.require_ready_yes:
        if latest_cf and _contains_ready_yes(latest_cf_body):
            checked.append("G:ready_status")
        elif latest_cf:
            errors.append(
                "[G] Latest current-final comment does not contain 'Ready for review: YES'."
            )
        else:
            errors.append("[G] No current-final comment found to check ready status.")

    # H: Standard network wording
    if args.require_standard_network_wording:
        if latest_cf and _contains_standard_network_wording(latest_cf_body):
            checked.append("H:network_wording")
        elif latest_cf:
            errors.append(
                "[H] Latest current-final comment does not contain standard network wording."
            )
        else:
            errors.append("[H] No current-final comment found to check network wording.")

    # I: Placeholder tokens
    if args.forbid_placeholder_evidence:
        has_placeholder_in_comment = latest_cf and _contains_placeholder(latest_cf_body)
        if not has_placeholder_in_comment:
            checked.append("I:placeholder_tokens")
        else:
            errors.append("[I] Latest current-final comment contains forbidden placeholder token.")

    # J: Guard input source
    if args.require_guard_input_source:
        cf_has_source = latest_cf and _contains_guard_input_source(latest_cf_body)
        pr_has_source = _contains_guard_input_source(pr_body)
        if cf_has_source and pr_has_source:
            checked.append("J:guard_input_source")
        elif not cf_has_source and latest_cf:
            errors.append(
                "[J] Latest current-final comment does not contain 'Guard input source:'."
            )
        elif not pr_has_source:
            errors.append("[J] PR body does not contain 'Guard input source:'.")

    # K: Cross-surface consistency
    cross_errors: List[str] = []
    if latest_cf and pr_body:
        if args.expected_head:
            pr_has_sha = args.expected_head in pr_body
            cf_has_sha = args.expected_head in latest_cf_body
            if pr_has_sha != cf_has_sha:
                cross_errors.append(
                    "[K] Head SHA present in one surface but missing from the other."
                )
        if args.require_guard_result:
            pr_has_guard = _contains_guard_result(pr_body)
            cf_has_guard = _contains_guard_result(latest_cf_body)
            if pr_has_guard != cf_has_guard:
                cross_errors.append(
                    "[K] Guard result present in one surface but missing from the other."
                )
        pr_file_count = _parse_file_count(pr_body)
        cf_file_count = _parse_file_count(latest_cf_body)
        if (
            pr_file_count is not None
            and cf_file_count is not None
            and pr_file_count != cf_file_count
        ):
            cross_errors.append(
                f"[K] File count mismatch: PR body says {pr_file_count}, "
                f"final comment says {cf_file_count}."
            )

    if not cross_errors:
        checked.append("K:cross_surface_consistency")
    else:
        errors.extend(cross_errors)

    # L: Stale posted-verifier wording (always active)
    l_errors: List[str] = []
    stale_in_body = _contains_stale_posted_verifier(pr_body)
    if stale_in_body:
        l_errors.append(
            f"[L] PR body contains stale posted-verifier wording: '{stale_in_body}'. "
            "Update the PR body with the actual verifier result before requesting review."
        )
    if latest_cf:
        stale_in_cf = _contains_stale_posted_verifier(latest_cf_body)
        if stale_in_cf:
            l_errors.append(
                f"[L] Latest current-final comment contains stale posted-verifier wording: "
                f"'{stale_in_cf}'."
            )
    if not l_errors:
        checked.append("L:posted_verifier_stale")
    else:
        errors.extend(l_errors)

    # M: Posted verifier PASS in both surfaces (when --require-posted-verifier-pass)
    if args.require_posted_verifier_pass:
        m_errors: List[str] = []
        if not _contains_posted_verifier_pass(pr_body):
            m_errors.append(
                "[M] PR body does not contain "
                "'Posted GitHub evidence verifier: PASS' and 'exit 0'."
            )
        if latest_cf:
            if not _contains_posted_verifier_pass(latest_cf_body):
                m_errors.append(
                    "[M] Latest current-final comment does not contain "
                    "'Posted GitHub evidence verifier: PASS' and 'exit 0'."
                )
        else:
            m_errors.append(
                "[M] No current-final comment found to check posted verifier result."
            )
        if not m_errors:
            checked.append("M:posted_verifier_pass")
        else:
            errors.extend(m_errors)

    # N: Follow-up classification (when --require-follow-up-classification)
    if args.require_follow_up_classification:
        n_errors: List[str] = []
        if not _contains_follow_up_classification(pr_body):
            n_errors.append(
                "[N] PR body does not contain 'Follow-up correction required:'."
            )
        if latest_cf:
            if not _contains_follow_up_classification(latest_cf_body):
                n_errors.append(
                    "[N] Latest current-final comment does not contain "
                    "'Follow-up correction required:'."
                )
        else:
            n_errors.append(
                "[N] No current-final comment found to check follow-up classification."
            )
        if not n_errors:
            checked.append("N:follow_up_classification")
        else:
            errors.extend(n_errors)

    # O: File count presence and expected value
    if args.require_file_count or args.expected_file_count is not None:
        o_errors: List[str] = []
        pr_fc = _parse_file_count(pr_body)
        cf_fc = _parse_file_count(latest_cf_body) if latest_cf else None

        if args.require_file_count:
            if pr_fc is None:
                o_errors.append(
                    "[O] PR body does not contain a parseable 'Changed files: N' count."
                )
            if latest_cf:
                if cf_fc is None:
                    o_errors.append(
                        "[O] Latest current-final comment does not contain a parseable "
                        "'Changed files: N' count."
                    )
            else:
                o_errors.append(
                    "[O] No current-final comment found to check file count."
                )

        if args.expected_file_count is not None:
            exp = args.expected_file_count
            if pr_fc is not None and pr_fc != exp:
                o_errors.append(
                    f"[O] PR body file count {pr_fc} does not match expected {exp}."
                )
            elif pr_fc is None:
                o_errors.append(
                    f"[O] PR body does not contain a parseable file count "
                    f"(expected {exp})."
                )
            if latest_cf:
                if cf_fc is not None and cf_fc != exp:
                    o_errors.append(
                        f"[O] Latest current-final comment file count {cf_fc} does not "
                        f"match expected {exp}."
                    )
                elif cf_fc is None:
                    o_errors.append(
                        f"[O] Latest current-final comment does not contain a parseable "
                        f"file count (expected {exp})."
                    )

        if not o_errors:
            checked.append("O:file_count")
        else:
            errors.extend(o_errors)

    # P: Forbid inline test counts
    if args.forbid_inline_test_counts:
        p_errors: List[str] = []
        if _contains_inline_test_counts(pr_body):
            p_errors.append(
                "[P] PR body contains inline test-count annotation "
                "(e.g. file.py (33 tests)). Remove test counts from file listings."
            )
        if latest_cf and _contains_inline_test_counts(latest_cf_body):
            p_errors.append(
                "[P] Latest current-final comment contains inline test-count annotation."
            )
        if not p_errors:
            checked.append("P:inline_test_counts")
        else:
            errors.extend(p_errors)

    result.checked_categories = checked
    result.errors = errors
    result.status = "FAIL" if errors else "PASS"
    result.exit_code = 1 if errors else 0
    return result


def _format_text(result: VerifierResult, args: VerifierArgs) -> str:
    lines = []
    lines.append(f"Posted PR evidence verifier: {result.status}")
    lines.append(f"Repository: {args.repo}")
    lines.append(f"PR: #{args.pr}")
    if args.expected_head:
        lines.append(f"Expected head SHA: {args.expected_head}")
    if result.status == "PASS":
        lines.append("PR body head SHA: present")
        lines.append(
            f"Latest current-final comment: "
            f"{'found' if result.latest_current_final_url else 'not required'}"
        )
        if result.latest_current_final_url:
            lines.append(f"Latest current-final comment URL: {result.latest_current_final_url}")
        lines.append(f"Checked categories: {', '.join(result.checked_categories)}")
    else:
        lines.append(f"{len(result.errors)} error(s) found:")
        for i, err in enumerate(result.errors, 1):
            lines.append(f"  {i}. {err}")
    lines.append(f"exit {result.exit_code}")
    return "\n".join(lines)


def _format_json(result: VerifierResult, args: VerifierArgs) -> str:
    return json.dumps(
        {
            "status": result.status,
            "repository": args.repo,
            "pr": args.pr,
            "expected_head_sha": args.expected_head,
            "pr_url": result.pr_url,
            "latest_current_final_url": result.latest_current_final_url,
            "checked_categories": result.checked_categories,
            "errors": result.errors,
            "exit_code": result.exit_code,
        },
        indent=2,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only GitHub posted PR evidence verifier (WP58 workflow-governance helper)."
    )
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr", type=int, required=True, help="PR number")
    parser.add_argument("--expected-head", default="", help="Expected head commit SHA")
    parser.add_argument("--require-current-final-marker", action="store_true")
    parser.add_argument("--require-guard-result", action="store_true")
    parser.add_argument("--require-ready-yes", action="store_true")
    parser.add_argument("--require-standard-network-wording", action="store_true")
    parser.add_argument("--forbid-placeholder-evidence", action="store_true")
    parser.add_argument("--forbid-inline-test-counts", action="store_true")
    parser.add_argument("--require-follow-up-classification", action="store_true")
    parser.add_argument("--require-guard-input-source", action="store_true")
    parser.add_argument("--require-file-count", action="store_true")
    parser.add_argument("--expected-file-count", type=int, default=None)
    parser.add_argument("--require-posted-verifier-pass", action="store_true")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--timeout-seconds", type=int, default=10)
    parser.add_argument("--comment-page-size", type=int, default=100)
    parser.add_argument("--max-comment-pages", type=int, default=5)

    parsed = parser.parse_args(argv)

    if "/" not in parsed.repo or len(parsed.repo.split("/")) != 2:
        print("Error: --repo must be in owner/repo format.", file=sys.stderr)
        return 2

    args = VerifierArgs(
        repo=parsed.repo,
        pr=parsed.pr,
        expected_head=parsed.expected_head,
        require_current_final_marker=parsed.require_current_final_marker,
        require_guard_result=parsed.require_guard_result,
        require_ready_yes=parsed.require_ready_yes,
        require_standard_network_wording=parsed.require_standard_network_wording,
        forbid_placeholder_evidence=parsed.forbid_placeholder_evidence,
        forbid_inline_test_counts=parsed.forbid_inline_test_counts,
        require_follow_up_classification=parsed.require_follow_up_classification,
        require_guard_input_source=parsed.require_guard_input_source,
        require_file_count=parsed.require_file_count,
        expected_file_count=parsed.expected_file_count,
        require_posted_verifier_pass=parsed.require_posted_verifier_pass,
        format=parsed.format,
        timeout_seconds=parsed.timeout_seconds,
        comment_page_size=parsed.comment_page_size,
        max_comment_pages=parsed.max_comment_pages,
    )

    result = verify(args)

    if parsed.format == "json":
        print(_format_json(result, args))
    else:
        print(_format_text(result, args))

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
