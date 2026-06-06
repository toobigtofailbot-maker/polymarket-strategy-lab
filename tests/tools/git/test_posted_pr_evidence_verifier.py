"""Tests for tools/git/posted_pr_evidence_verifier.py — WP58.

No real network calls. All GitHub API calls are monkeypatched.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys

import pytest
from unittest.mock import patch

# ── Load module ───────────────────────────────────────────────────────────────

_HELPER_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "tools" / "git" / "posted_pr_evidence_verifier.py"
)

_spec = importlib.util.spec_from_file_location(
    "posted_pr_evidence_verifier", _HELPER_PATH
)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

verify = _mod.verify
VerifierArgs = _mod.VerifierArgs
_find_current_final_comments = _mod._find_current_final_comments
_latest_comment = _mod._latest_comment
_format_json = _mod._format_json
CURRENT_FINAL_MARKER = _mod.CURRENT_FINAL_MARKER

_MOD_NAME = "posted_pr_evidence_verifier"

# ── Test data ─────────────────────────────────────────────────────────────────

VALID_SHA = "abc123def456" * 3  # 36 chars
BASE_SHA = "fed654cba321" * 3

VALID_PR_BODY = f"""
## Summary

WP58 workflow hardening.

Head SHA: {VALID_SHA}
Base SHA: {BASE_SHA}
Changed files: 21
Full pytest: 87 passed
PR evidence consistency guard: PASS
Checked categories: A, B, C
exit 0
Guard input source: pr_body.txt
Ready for review: YES
Network was used only for Remote Main Sync Gate / git remote synchronization, PR push/publication, and the manual read-only GitHub PR evidence verifier.
"""

VALID_FINAL_COMMENT = f"""
CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments

WP: WP58
PR: #59
Head SHA: {VALID_SHA}
Base SHA: {BASE_SHA}
Changed files: 21
Full pytest: 87 passed
PR evidence consistency guard: PASS
Checked categories: A, B, C
exit 0
Guard input source: final_comment.txt
Ready for review: YES
Network was used only for Remote Main Sync Gate / git remote synchronization, PR push/publication, and the manual read-only GitHub PR evidence verifier.
"""


def make_pr(body: str, head_sha: str = VALID_SHA) -> dict:
    return {
        "html_url": "https://github.com/owner/repo/pull/59",
        "head": {"sha": head_sha},
        "body": body,
    }


def make_comment(
    body: str,
    url: str = "https://github.com/owner/repo/pull/59#issuecomment-1",
    created: str = "2026-06-06T12:00:00Z",
) -> dict:
    return {
        "html_url": url,
        "body": body,
        "created_at": created,
        "updated_at": created,
    }


def default_args(**kwargs) -> object:
    defaults = dict(
        repo="owner/repo",
        pr=59,
        expected_head=VALID_SHA,
        require_current_final_marker=True,
        require_guard_result=True,
        require_ready_yes=True,
        require_standard_network_wording=True,
        forbid_placeholder_evidence=True,
        forbid_inline_test_counts=False,
        require_guard_input_source=True,
        format="text",
        timeout_seconds=5,
        comment_page_size=100,
        max_comment_pages=5,
    )
    defaults.update(kwargs)
    return VerifierArgs(**defaults)


# ── Helper to patch at module level ──────────────────────────────────────────

def _patch_pr(pr_data):
    return patch.object(_mod, "_fetch_pr", return_value=pr_data)


def _patch_comments(comments):
    return patch.object(_mod, "_fetch_all_comments", return_value=comments)


def _patch_pr_error(exc):
    return patch.object(_mod, "_fetch_pr", side_effect=exc)


# ── Test 1: PASS when PR body and latest current-final comment are valid ──────

def test_pass_when_valid():
    args = default_args()
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([make_comment(VALID_FINAL_COMMENT)]):
            result = verify(args)
    assert result.status == "PASS"
    assert result.exit_code == 0
    assert "D:current_final_marker" in result.checked_categories


# ── Test 2: FAIL when no comments exist ──────────────────────────────────────

def test_fail_no_comments():
    args = default_args()
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([]):
            result = verify(args)
    assert result.status == "FAIL"
    assert result.exit_code == 1
    assert any("No comments" in e or "No current-final" in e or "current-final" in e.lower() for e in result.errors)


# ── Test 3: FAIL when comments exist but none contain CURRENT FINAL WP EVIDENCE

def test_fail_no_current_final_marker():
    args = default_args()
    plain_comment = make_comment("Just a regular comment without the marker.")
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([plain_comment]):
            result = verify(args)
    assert result.status == "FAIL"
    assert any("CURRENT FINAL WP EVIDENCE" in e or "current-final" in e.lower() for e in result.errors)


# ── Test 4: FAIL when latest current-final comment has stale head SHA ─────────

def test_fail_stale_head_sha_in_final_comment():
    stale_sha = "0000000000000000000000000000000000000000"
    stale_comment = VALID_FINAL_COMMENT.replace(VALID_SHA, stale_sha)
    args = default_args()
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([make_comment(stale_comment)]):
            result = verify(args)
    assert result.status == "FAIL"
    assert any("[E]" in e for e in result.errors)


# ── Test 5: PASS — newer current-final comment supersedes older stale one ─────

def test_pass_newest_comment_supersedes_older_stale():
    stale_sha = "0000000000000000000000000000000000000000"
    old_comment = make_comment(
        VALID_FINAL_COMMENT.replace(VALID_SHA, stale_sha),
        created="2026-06-06T10:00:00Z",
    )
    new_comment = make_comment(VALID_FINAL_COMMENT, created="2026-06-06T12:00:00Z")
    args = default_args()
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([old_comment, new_comment]):
            result = verify(args)
    assert result.status == "PASS"


# ── Test 6: FAIL when PR body lacks expected head SHA ─────────────────────────

def test_fail_pr_body_lacks_head_sha():
    bad_body = VALID_PR_BODY.replace(VALID_SHA, "MISSING")
    args = default_args()
    with _patch_pr(make_pr(bad_body, head_sha=VALID_SHA)):
        with _patch_comments([make_comment(VALID_FINAL_COMMENT)]):
            result = verify(args)
    assert result.status == "FAIL"
    assert any("[B]" in e for e in result.errors)


# ── Test 7: FAIL when final comment lacks guard result ────────────────────────

def test_fail_final_comment_lacks_guard_result():
    bad_comment = VALID_FINAL_COMMENT.replace(
        "PR evidence consistency guard: PASS\nChecked categories: A, B, C\nexit 0", ""
    )
    args = default_args(require_guard_result=True)
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([make_comment(bad_comment)]):
            result = verify(args)
    assert result.status == "FAIL"
    assert any("[F]" in e for e in result.errors)


# ── Test 8: FAIL when PR body lacks guard result ──────────────────────────────

def test_fail_pr_body_lacks_guard_result():
    bad_body = VALID_PR_BODY.replace(
        "PR evidence consistency guard: PASS\nChecked categories: A, B, C\nexit 0", ""
    )
    args = default_args(require_guard_result=True)
    with _patch_pr(make_pr(bad_body)):
        with _patch_comments([make_comment(VALID_FINAL_COMMENT)]):
            result = verify(args)
    assert result.status == "FAIL"
    assert any("[B]" in e for e in result.errors)


# ── Test 9: FAIL when Ready for review: YES missing ───────────────────────────

def test_fail_ready_yes_missing():
    bad_comment = VALID_FINAL_COMMENT.replace("Ready for review: YES", "Ready for review: NO")
    args = default_args(require_ready_yes=True)
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([make_comment(bad_comment)]):
            result = verify(args)
    assert result.status == "FAIL"
    assert any("[G]" in e for e in result.errors)


# ── Test 10: FAIL when standard network wording missing ───────────────────────

def test_fail_standard_network_wording_missing():
    bad_comment = VALID_FINAL_COMMENT.replace("Remote Main Sync Gate", "some unrelated text")
    bad_comment = bad_comment.replace("git remote synchronization", "").replace(
        "git push", ""
    ).replace("PR publication", "").replace("git fetch", "")
    args = default_args(require_standard_network_wording=True)
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([make_comment(bad_comment)]):
            result = verify(args)
    assert result.status == "FAIL"
    assert any("[H]" in e for e in result.errors)


# ── Test 11: FAIL when placeholder token appears ──────────────────────────────

def test_fail_placeholder_token():
    bad_comment = VALID_FINAL_COMMENT + "\nHead SHA: <HEAD_SHA>"
    args = default_args(forbid_placeholder_evidence=True)
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([make_comment(bad_comment)]):
            result = verify(args)
    assert result.status == "FAIL"
    assert any("[I]" in e for e in result.errors)


# ── Test 12: FAIL when guard input source missing ─────────────────────────────

def test_fail_guard_input_source_missing():
    bad_comment = VALID_FINAL_COMMENT.replace("Guard input source: final_comment.txt", "")
    args = default_args(require_guard_input_source=True)
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([make_comment(bad_comment)]):
            result = verify(args)
    assert result.status == "FAIL"
    assert any("[J]" in e for e in result.errors)


# ── Test 13: JSON output includes status and checked categories ───────────────

def test_json_output_format():
    args = default_args(format="json")
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([make_comment(VALID_FINAL_COMMENT)]):
            result = verify(args)
    output = json.loads(_format_json(result, args))
    assert "status" in output
    assert "checked_categories" in output
    assert "errors" in output
    assert output["status"] == "PASS"


# ── Test 14: Exit code 1 for verification failure ─────────────────────────────

def test_exit_code_1_on_fail():
    args = default_args()
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([]):
            result = verify(args)
    assert result.exit_code == 1


# ── Test 15: Exit code 3 for fetch error ──────────────────────────────────────

def test_exit_code_3_on_fetch_error():
    args = default_args()
    with _patch_pr_error(RuntimeError("network error")):
        result = verify(args)
    assert result.exit_code == 3


# ── Test 16: Helper does not read env vars for tokens ─────────────────────────

def test_no_env_token_reading():
    source = _HELPER_PATH.read_text(encoding="utf-8")
    for token_var in ["GITHUB_TOKEN", "GH_TOKEN", "GITHUB_AUTH", "API_TOKEN"]:
        # The source must not access these env vars
        assert f'os.environ' not in source or token_var not in source, (
            f"Module must not read env var {token_var}"
        )


# ── Test 17: Helper does not import third-party packages ──────────────────────

def test_no_third_party_imports():
    source = _HELPER_PATH.read_text(encoding="utf-8")
    for forbidden in ["import requests", "from requests", "import PyGithub", "from github", "import httpx"]:
        assert forbidden not in source, f"Forbidden import found: {forbidden}"


# ── Test 18: GitHub pagination — current-final on second page is found ────────

def test_pagination_finds_current_final_on_second_page():
    page1 = [make_comment("Just a comment", created="2026-06-06T10:00:00Z")]
    page2 = [make_comment(VALID_FINAL_COMMENT, created="2026-06-06T12:00:00Z")]

    def fake_fetch_all(owner, repo, pr, page_size, max_pages, timeout):
        return page1 + page2

    args = default_args()
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with patch.object(_mod, "_fetch_all_comments", side_effect=fake_fetch_all):
            result = verify(args)
    assert result.status == "PASS"


# ── Test 19: Multiple current-final comments — latest by timestamp selected ───

def test_multiple_current_final_comments_latest_selected():
    old_cf = make_comment(
        VALID_FINAL_COMMENT.replace(VALID_SHA, "0" * 36),
        created="2026-06-06T10:00:00Z",
    )
    new_cf = make_comment(VALID_FINAL_COMMENT, created="2026-06-06T12:00:00Z")
    args = default_args()
    with _patch_pr(make_pr(VALID_PR_BODY)):
        with _patch_comments([old_cf, new_cf]):
            result = verify(args)
    assert result.status == "PASS"
    assert "E:head_sha" in result.checked_categories


# ── Test 20: PR body / final comment file-count mismatch detected ─────────────

def test_file_count_mismatch_detected():
    pr_body_with_count = VALID_PR_BODY  # Contains "Changed files: 21"
    final_with_diff_count = VALID_FINAL_COMMENT.replace("Changed files: 21", "Changed files: 99")
    args = default_args()
    with _patch_pr(make_pr(pr_body_with_count)):
        with _patch_comments([make_comment(final_with_diff_count)]):
            result = verify(args)
    assert result.status == "FAIL"
    assert any("mismatch" in e.lower() or "[K]" in e for e in result.errors)
