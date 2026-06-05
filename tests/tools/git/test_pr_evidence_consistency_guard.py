"""Tests for tools/git/pr_evidence_consistency_guard.py."""

from __future__ import annotations

import importlib
import importlib.util
import json
import pathlib
import sys

import pytest

# ── Load module ───────────────────────────────────────────────────────────────

_HELPER_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "tools" / "git" / "pr_evidence_consistency_guard.py"
)

_spec = importlib.util.spec_from_file_location(
    "pr_evidence_consistency_guard", _HELPER_PATH
)
guard = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(guard)  # type: ignore[union-attr]


# ── Shared fixtures and helpers ───────────────────────────────────────────────

STANDARD_NETWORK_WORDING = guard.STANDARD_NETWORK_WORDING

_HEAD_SHA = "a" * 40
_OTHER_SHA = "b" * 40

_GOOD_COUNTS = "68 passed, 0 failed, 0 errors"
_GOOD_COUNTS_BIG = "1583 passed, 0 failed, 0 errors, 1 warning"

_REQUIRED_CMD = (
    "python tools/git/status_snapshot.py --format text "
    "--include-deferred --include-helper-inventory "
    "--include-next-wp-candidates --include-protected-boundaries"
)


def _make_good_body(
    *,
    sha: str = _HEAD_SHA,
    counts: str = _GOOD_COUNTS,
    cmd: str = _REQUIRED_CMD,
    network: str = STANDARD_NETWORK_WORDING,
    ready: str = "Ready for review: YES",
) -> str:
    return (
        f"# PR Body\n\n"
        f"Head commit: {sha}\n\n"
        f"```\n{cmd}\n→ {counts}\n```\n\n"
        f"{network}\n\n"
        f"{ready}\n"
    )


def _make_good_comment(
    *,
    sha: str = _HEAD_SHA,
    counts: str = _GOOD_COUNTS,
    cmd: str = _REQUIRED_CMD,
    network: str = STANDARD_NETWORK_WORDING,
    ready: str = "Ready for review: YES",
) -> str:
    return (
        f"# Final Comment\n\n"
        f"Head commit: {sha}\n\n"
        f"```\n{cmd}\n→ {counts}\n```\n\n"
        f"{network}\n\n"
        f"{ready}\n"
    )


def _run(
    tmp_path: pathlib.Path,
    body: str,
    comment: str,
    *,
    expected_head: str | None = None,
    required_commands: list[str] | None = None,
    require_network: bool = True,
    require_ready: bool = True,
    fmt: str = "text",
    forbid_inline_test_counts: bool = False,
    forbid_placeholder_evidence: bool = False,
    require_current_final_marker: bool = False,
    stale_count_tokens: list[str] | None = None,
    require_posted_evidence_note: bool = False,
    require_guard_result: bool = False,
) -> tuple[bool, list[str], list[str], list[str]]:
    body_file = tmp_path / "pr_body.md"
    comment_file = tmp_path / "final_comment.md"
    body_file.write_text(body, encoding="utf-8")
    comment_file.write_text(comment, encoding="utf-8")
    return guard.run_guard(
        pr_body_path=body_file,
        final_comment_path=comment_file,
        expected_head=expected_head,
        required_commands=required_commands or [],
        require_standard_network_wording=require_network,
        require_ready_yes=require_ready,
        forbid_inline_test_counts=forbid_inline_test_counts,
        forbid_placeholder_evidence=forbid_placeholder_evidence,
        require_current_final_marker=require_current_final_marker,
        stale_count_tokens=stale_count_tokens or [],
        require_posted_evidence_note=require_posted_evidence_note,
        require_guard_result=require_guard_result,
    )


# ── Pass cases ────────────────────────────────────────────────────────────────


def test_pass_matching_evidence(tmp_path: pathlib.Path) -> None:
    body = _make_good_body()
    comment = _make_good_comment()
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        expected_head=_HEAD_SHA,
        required_commands=[_REQUIRED_CMD],
        require_network=True,
        require_ready=True,
    )
    assert passed, f"Expected PASS but got errors: {errors}"


def test_pass_big_count_matching(tmp_path: pathlib.Path) -> None:
    body = _make_good_body(counts=_GOOD_COUNTS_BIG)
    comment = _make_good_comment(counts=_GOOD_COUNTS_BIG)
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        expected_head=_HEAD_SHA,
        required_commands=[_REQUIRED_CMD],
    )
    assert passed, f"Expected PASS but got errors: {errors}"


def test_pass_json_output(tmp_path: pathlib.Path) -> None:
    body = _make_good_body()
    comment = _make_good_comment()
    body_file = tmp_path / "pr_body.md"
    comment_file = tmp_path / "final_comment.md"
    body_file.write_text(body, encoding="utf-8")
    comment_file.write_text(comment, encoding="utf-8")

    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = guard.main([
            "--pr-body", str(body_file),
            "--final-comment", str(comment_file),
            "--expected-head", _HEAD_SHA,
            "--required-command", _REQUIRED_CMD,
            "--require-standard-network-wording",
            "--require-ready-yes",
            "--format", "json",
        ])

    assert rc == 0
    data = json.loads(buf.getvalue())
    assert data["status"] == "PASS"
    assert data["errors"] == []
    assert isinstance(data["checked_categories"], list)


# ── Fail cases: files ─────────────────────────────────────────────────────────


def test_fail_missing_pr_body(tmp_path: pathlib.Path) -> None:
    comment_file = tmp_path / "final_comment.md"
    comment_file.write_text("some content", encoding="utf-8")
    missing_body = tmp_path / "nonexistent_body.md"

    passed, errors, _, _ = guard.run_guard(
        pr_body_path=missing_body,
        final_comment_path=comment_file,
        expected_head=None,
        required_commands=[],
        require_standard_network_wording=False,
        require_ready_yes=False,
    )
    assert not passed
    assert any("[A]" in e and "PR body" in e for e in errors)


def test_fail_missing_final_comment(tmp_path: pathlib.Path) -> None:
    body_file = tmp_path / "pr_body.md"
    body_file.write_text("some content", encoding="utf-8")
    missing_comment = tmp_path / "nonexistent_comment.md"

    passed, errors, _, _ = guard.run_guard(
        pr_body_path=body_file,
        final_comment_path=missing_comment,
        expected_head=None,
        required_commands=[],
        require_standard_network_wording=False,
        require_ready_yes=False,
    )
    assert not passed
    assert any("[A]" in e and "Final comment" in e for e in errors)


def test_fail_empty_pr_body(tmp_path: pathlib.Path) -> None:
    passed, errors, _, _ = _run(tmp_path, "", "some content", require_network=False, require_ready=False)
    assert not passed
    assert any("[B]" in e and "PR body" in e for e in errors)


def test_fail_empty_final_comment(tmp_path: pathlib.Path) -> None:
    passed, errors, _, _ = _run(tmp_path, "some content", "", require_network=False, require_ready=False)
    assert not passed
    assert any("[B]" in e and "Final comment" in e for e in errors)


# ── Fail cases: required commands ────────────────────────────────────────────


def test_fail_required_command_missing_from_pr_body(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\nsome content without the command\n"
    comment = f"# Comment\n{_REQUIRED_CMD}\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        required_commands=[_REQUIRED_CMD],
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("[D]" in e and "PR body" in e for e in errors)


def test_fail_required_command_missing_from_final_comment(tmp_path: pathlib.Path) -> None:
    body = f"# PR Body\n{_REQUIRED_CMD}\n"
    comment = "# Comment\nsome content without the command\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        required_commands=[_REQUIRED_CMD],
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("[D]" in e and "final comment" in e for e in errors)


def test_fail_status_snapshot_in_comment_not_body(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\nNo helper references here.\n"
    comment = "# Comment\npython tools/git/status_snapshot.py --format text\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("status_snapshot.py" in e and "PR body" in e for e in errors)


# ── Fail cases: ellipsis ─────────────────────────────────────────────────────


def test_fail_ellipsis_in_command_line_in_body(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\npython tools/git/status_snapshot.py ...\n"
    comment = "# Comment\npython tools/git/status_snapshot.py --format text\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("[C]" in e for e in errors)


def test_fail_ellipsis_in_command_line_in_comment(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\npython tools/git/status_snapshot.py --format text\n"
    comment = "# Comment\npython -m pytest tests/ ...\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("[C]" in e for e in errors)


# ── Fail cases: head SHA ─────────────────────────────────────────────────────


def test_fail_expected_sha_missing_from_pr_body(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\nHead commit: some_other_ref\n"
    comment = f"# Comment\nHead commit: {_HEAD_SHA}\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        expected_head=_HEAD_SHA,
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("[E]" in e and "PR body" in e for e in errors)


def test_fail_expected_sha_missing_from_comment(tmp_path: pathlib.Path) -> None:
    body = f"# PR Body\nHead commit: {_HEAD_SHA}\n"
    comment = "# Comment\nHead commit: some_other_ref\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        expected_head=_HEAD_SHA,
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("[E]" in e and "final comment" in e for e in errors)


def test_fail_sha_mismatch_between_surfaces(tmp_path: pathlib.Path) -> None:
    body = f"# PR Body\nHead commit: {_HEAD_SHA}\n"
    comment = f"# Comment\nHead commit: {_OTHER_SHA}\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("[E]" in e for e in errors)


# ── Fail cases: test counts ──────────────────────────────────────────────────


def test_fail_focused_count_mismatch_68_vs_66(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\n68 passed, 0 failed, 0 errors\n"
    comment = "# Comment\n66 passed, 0 failed, 0 errors\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("[F]" in e for e in errors)


def test_fail_full_suite_count_mismatch_1583_vs_1581(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\n1583 passed, 0 failed, 0 errors, 1 warning\n"
    comment = "# Comment\n1581 passed, 0 failed, 0 errors, 1 warning\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("[F]" in e for e in errors)


def test_fail_warning_count_mismatch(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\n1583 passed, 0 failed, 0 errors, 1 warning\n"
    comment = "# Comment\n1583 passed, 0 failed, 0 errors, 2 warnings\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False,
        require_ready=False,
    )
    assert not passed
    assert any("[F]" in e for e in errors)


# ── Fail cases: network wording ──────────────────────────────────────────────


def test_fail_network_wording_missing_from_body(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\nNo network wording here.\n"
    comment = f"# Comment\n{STANDARD_NETWORK_WORDING}\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=True,
        require_ready=False,
    )
    assert not passed
    assert any("[G]" in e and "PR body" in e for e in errors)


def test_fail_no_network_wording_when_standard_required(tmp_path: pathlib.Path) -> None:
    body = f"# PR Body\nNo network was used.\n"
    comment = f"# Comment\nNo network was used.\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=True,
        require_ready=False,
    )
    assert not passed
    # Should flag missing standard wording and/or presence of "no network"
    assert any("[G]" in e for e in errors)


# ── Fail cases: ready status ─────────────────────────────────────────────────


def test_fail_ready_mismatch_yes_vs_no(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\nReady for review: YES\n"
    comment = "# Comment\nReady for review: NO\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False,
        require_ready=True,
    )
    assert not passed
    assert any("[H]" in e for e in errors)


def test_fail_ready_missing_from_comment(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\nReady for review: YES\n"
    comment = "# Comment\nNo ready status here.\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False,
        require_ready=True,
    )
    assert not passed
    assert any("[H]" in e and "final comment" in e for e in errors)


# ── Fail cases: security honesty ─────────────────────────────────────────────


def test_fail_security_tool_passed_and_unavailable(tmp_path: pathlib.Path) -> None:
    body = (
        "# PR Body\ngitleaks passed\ngitleaks: NOT_AVAILABLE\n"
        f"{STANDARD_NETWORK_WORDING}\nReady for review: YES\n"
    )
    comment = (
        "# Comment\ngitleaks passed\ngitleaks: NOT_AVAILABLE\n"
        f"{STANDARD_NETWORK_WORDING}\nReady for review: YES\n"
    )
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=True,
        require_ready=True,
    )
    assert not passed
    assert any("[J]" in e for e in errors)


# ── Fail cases: JSON output mode ─────────────────────────────────────────────


def test_fail_json_output_structured(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\n68 passed, 0 failed, 0 errors\n"
    comment = "# Comment\n66 passed, 0 failed, 0 errors\n"
    body_file = tmp_path / "pr_body.md"
    comment_file = tmp_path / "final_comment.md"
    body_file.write_text(body, encoding="utf-8")
    comment_file.write_text(comment, encoding="utf-8")

    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = guard.main([
            "--pr-body", str(body_file),
            "--final-comment", str(comment_file),
            "--format", "json",
        ])

    assert rc == 1
    data = json.loads(buf.getvalue())
    assert data["status"] == "FAIL"
    assert isinstance(data["errors"], list)
    assert len(data["errors"]) > 0
    assert isinstance(data["checked_categories"], list)


# ── CLI-level exit code 2 tests ───────────────────────────────────────────────


def test_cli_exit2_missing_pr_body(tmp_path: pathlib.Path) -> None:
    comment_file = tmp_path / "final_comment.md"
    comment_file.write_text("some content", encoding="utf-8")
    missing = tmp_path / "nonexistent_body.md"

    rc = guard.main([
        "--pr-body", str(missing),
        "--final-comment", str(comment_file),
    ])
    assert rc == 2, f"Expected exit 2 for missing PR body file, got {rc}"


def test_cli_exit2_missing_final_comment(tmp_path: pathlib.Path) -> None:
    body_file = tmp_path / "pr_body.md"
    body_file.write_text("some content", encoding="utf-8")
    missing = tmp_path / "nonexistent_comment.md"

    rc = guard.main([
        "--pr-body", str(body_file),
        "--final-comment", str(missing),
    ])
    assert rc == 2, f"Expected exit 2 for missing final comment file, got {rc}"


def test_cli_exit2_pr_body_is_directory(tmp_path: pathlib.Path) -> None:
    dir_path = tmp_path / "a_directory"
    dir_path.mkdir()
    comment_file = tmp_path / "final_comment.md"
    comment_file.write_text("some content", encoding="utf-8")

    rc = guard.main([
        "--pr-body", str(dir_path),
        "--final-comment", str(comment_file),
    ])
    assert rc == 2, f"Expected exit 2 for directory as PR body path, got {rc}"


def test_cli_exit2_final_comment_is_directory(tmp_path: pathlib.Path) -> None:
    body_file = tmp_path / "pr_body.md"
    body_file.write_text("some content", encoding="utf-8")
    dir_path = tmp_path / "a_directory"
    dir_path.mkdir()

    rc = guard.main([
        "--pr-body", str(body_file),
        "--final-comment", str(dir_path),
    ])
    assert rc == 2, f"Expected exit 2 for directory as final comment path, got {rc}"


# ── Unit tests for extraction helpers ────────────────────────────────────────


def test_extract_test_counts_basic() -> None:
    text = "68 passed, 0 failed, 0 errors"
    counts = guard._extract_test_counts(text)
    assert counts == ["68 passed, 0 failed, 0 errors"]


def test_extract_test_counts_with_warning() -> None:
    text = "1583 passed, 0 failed, 0 errors, 1 warning"
    counts = guard._extract_test_counts(text)
    assert counts == ["1583 passed, 0 failed, 0 errors, 1 warning(s)"]


def test_extract_labeled_shas() -> None:
    sha = "a" * 40
    text = f"Head commit: {sha}\n"
    shas = guard._extract_labeled_shas(text)
    assert sha in shas


def test_extract_labeled_shas_does_not_match_merge_commit() -> None:
    """Required previous merge commit lines must NOT be treated as head SHA labels."""
    sha = "b" * 40
    text = f"- Required previous merge commit: `{sha}` (WP45)\n"
    shas = guard._extract_labeled_shas(text)
    assert sha not in shas, (
        "merge commit lines must not match the head SHA label pattern"
    )


def test_extract_all_shas() -> None:
    sha = "deadbeef" * 5
    text = f"some text {sha} more text"
    shas = guard._extract_all_shas(text)
    assert sha in shas


def test_standard_network_wording_constant() -> None:
    assert "Remote Main Sync Gate" in STANDARD_NETWORK_WORDING
    assert "no runtime network behavior" in STANDARD_NETWORK_WORDING
    assert "no API polling" in STANDARD_NETWORK_WORDING
    assert "no account access" in STANDARD_NETWORK_WORDING
    assert "no product network behavior" in STANDARD_NETWORK_WORDING


# ── WP47 new flag tests: K — inline test counts ───────────────────────────────


def test_fail_forbid_inline_test_counts_focused_tests_phrase(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\nfocused tests (33 tests)\n"
    comment = "# Comment\nsome text\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        forbid_inline_test_counts=True,
    )
    assert not passed
    assert any("[K]" in e and "PR body" in e for e in errors)


def test_fail_forbid_inline_test_counts_tests_paren(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\nfoo tests (34 tests) bar\n"
    comment = "# Comment\n34 passed, 0 failed, 0 errors\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        forbid_inline_test_counts=True,
    )
    assert not passed
    assert any("[K]" in e for e in errors)


def test_pass_forbid_inline_test_counts_only_in_validation(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\n34 passed, 0 failed, 0 errors\n"
    comment = "# Comment\n34 passed, 0 failed, 0 errors\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        forbid_inline_test_counts=True,
    )
    assert passed, f"Expected PASS but got errors: {errors}"


# ── WP47 new flag tests: L — placeholder evidence ─────────────────────────────


def test_fail_forbid_placeholder_evidence_head_sha(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\nHead commit: <HEAD_SHA>\n"
    comment = "# Comment\nsome text\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        forbid_placeholder_evidence=True,
    )
    assert not passed
    assert any("[L]" in e and "<HEAD_SHA>" in e for e in errors)


def test_fail_forbid_placeholder_evidence_placeholder_token(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\nplaceholder\n"
    comment = "# Comment\nsome text\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        forbid_placeholder_evidence=True,
    )
    assert not passed
    assert any("[L]" in e for e in errors)


def test_fail_forbid_placeholder_evidence_actual_colon(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\nsome text\n"
    comment = "# Comment\nactual: something\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        forbid_placeholder_evidence=True,
    )
    assert not passed
    assert any("[L]" in e and "final comment" in e for e in errors)


def test_fail_forbid_placeholder_evidence_fake_sha_filler(
    tmp_path: pathlib.Path,
) -> None:
    fake_sha = "a" * 40
    body = "# PR Body\nsome text\n"
    comment = f"# Comment\nHead commit: {fake_sha}\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        forbid_placeholder_evidence=True,
    )
    assert not passed
    assert any("[L]" in e and "final comment" in e for e in errors)


# ── WP47 new flag tests: M — current final marker ────────────────────────────


def test_fail_require_current_final_marker_missing(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\nsome text\n"
    comment = "# Comment\nsome text without the marker\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        require_current_final_marker=True,
    )
    assert not passed
    assert any("[M]" in e for e in errors)


def test_pass_require_current_final_marker_present(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\nsome text\n"
    comment = (
        "CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments\n\n"
        "some evidence text\n"
    )
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        require_current_final_marker=True,
    )
    assert passed, f"Expected PASS but got errors: {errors}"


# ── WP47 new flag tests: N — stale count tokens ───────────────────────────────


def test_fail_forbid_stale_count_tokens_in_pr_body(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\n1612 passed, 0 failed, 0 errors\n"
    comment = "# Comment\nsome text\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        stale_count_tokens=["1612 passed"],
    )
    assert not passed
    assert any("[N]" in e and "PR body" in e for e in errors)


def test_fail_forbid_stale_count_tokens_in_final_comment(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\nsome text\n"
    comment = "# Comment\n28 passed, 0 failed, 0 errors\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        stale_count_tokens=["28 passed"],
    )
    assert not passed
    assert any("[N]" in e and "final comment" in e for e in errors)


# ── WP47 new flag tests: O — posted evidence note ────────────────────────────


def test_fail_require_posted_evidence_note_missing(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\nsome text\n"
    comment = "# Comment\nsome text\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        require_posted_evidence_note=True,
    )
    assert not passed
    assert any("[O]" in e for e in errors)


def test_pass_require_posted_evidence_note_present(
    tmp_path: pathlib.Path,
) -> None:
    note = "Guard input source: exact local drafts intended for posting"
    body = f"# PR Body\n{note}\n"
    comment = f"# Comment\n{note}\n"
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_network=False, require_ready=False,
        require_posted_evidence_note=True,
    )
    assert passed, f"Expected PASS but got errors: {errors}"


# ── WP47: JSON output includes new categories ─────────────────────────────────


def test_json_output_includes_new_categories(tmp_path: pathlib.Path) -> None:
    body = "# PR Body\nsome text\n"
    comment = "# Comment\nsome text\n"
    body_file = tmp_path / "pr_body.md"
    comment_file = tmp_path / "final_comment.md"
    body_file.write_text(body, encoding="utf-8")
    comment_file.write_text(comment, encoding="utf-8")

    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        guard.main([
            "--pr-body", str(body_file),
            "--final-comment", str(comment_file),
            "--format", "json",
            "--forbid-inline-test-counts",
            "--forbid-placeholder-evidence",
            "--require-current-final-marker",
            "--forbid-stale-count-tokens", "stale token",
            "--require-posted-evidence-note",
        ])

    data = json.loads(buf.getvalue())
    categories = data["checked_categories"]
    assert "K:inline_test_counts" in categories
    assert "L:placeholder_evidence" in categories
    assert "M:current_final_marker" in categories
    assert "N:stale_count_tokens" in categories
    assert "O:posted_evidence_note" in categories


def test_json_output_errors_include_new_category_errors(
    tmp_path: pathlib.Path,
) -> None:
    body = "# PR Body\nfocused tests (33 tests)\nHead commit: <HEAD_SHA>\n"
    comment = "# Comment\nsome content without marker\nactual: foo\n"
    body_file = tmp_path / "pr_body.md"
    comment_file = tmp_path / "final_comment.md"
    body_file.write_text(body, encoding="utf-8")
    comment_file.write_text(comment, encoding="utf-8")

    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = guard.main([
            "--pr-body", str(body_file),
            "--final-comment", str(comment_file),
            "--format", "json",
            "--forbid-inline-test-counts",
            "--forbid-placeholder-evidence",
            "--require-current-final-marker",
            "--require-posted-evidence-note",
        ])

    assert rc == 1
    data = json.loads(buf.getvalue())
    assert data["status"] == "FAIL"
    error_text = " ".join(data["errors"])
    assert "[K]" in error_text
    assert "[L]" in error_text
    assert "[M]" in error_text
    assert "[O]" in error_text


# ── WP54: --require-guard-result tests (P) ───────────────────────────────────

_GUARD_RESULT_PASS = (
    "PR evidence consistency guard: PASS\n"
    "Checked categories: A:missing_files, B:empty_evidence\n"
    "exit 0\n"
)

_GUARD_RESULT_FAIL = (
    "PR evidence consistency guard: FAIL\n"
    "Checked categories: A:missing_files\n"
    "exit 1\n"
)

_GUARD_CMD_ONLY = (
    "python tools/git/pr_evidence_consistency_guard.py "
    "--pr-body local_pr_body.md --final-comment local_final_comment.md\n"
)

_GUARD_VAGUE = "The guard passes and everything looks good.\n"


def _make_body_with_guard_result(result_block: str) -> str:
    return (
        f"# PR Body\n\n"
        f"Head commit: {_HEAD_SHA}\n\n"
        f"```\n{_REQUIRED_CMD}\n→ {_GOOD_COUNTS}\n```\n\n"
        f"{STANDARD_NETWORK_WORDING}\n\n"
        f"Guard input source: exact local drafts intended for posting\n\n"
        f"```\n{result_block}```\n\n"
        f"Ready for review: YES\n"
    )


def _make_comment_with_guard_result(result_block: str) -> str:
    return (
        f"CURRENT FINAL WP EVIDENCE — supersedes previous evidence comments\n\n"
        f"Head commit: {_HEAD_SHA}\n\n"
        f"```\n{_REQUIRED_CMD}\n→ {_GOOD_COUNTS}\n```\n\n"
        f"{STANDARD_NETWORK_WORDING}\n\n"
        f"Guard input source: exact local drafts intended for posting\n\n"
        f"```\n{result_block}```\n\n"
        f"Ready for review: YES\n"
    )


def test_require_guard_result_passes_when_result_in_both(
    tmp_path: pathlib.Path,
) -> None:
    body = _make_body_with_guard_result(_GUARD_RESULT_PASS)
    comment = _make_comment_with_guard_result(_GUARD_RESULT_PASS)
    passed, errors, _, checked = _run(
        tmp_path, body, comment,
        expected_head=_HEAD_SHA,
        required_commands=[_REQUIRED_CMD],
        require_network=True,
        require_ready=True,
        require_posted_evidence_note=True,
        require_current_final_marker=True,
        require_guard_result=True,
    )
    assert passed, f"Expected PASS but got errors: {errors}"
    assert any("P:guard_result" in c for c in checked)


def test_require_guard_result_passes_with_fail_result(
    tmp_path: pathlib.Path,
) -> None:
    body = _make_body_with_guard_result(_GUARD_RESULT_FAIL)
    comment = _make_comment_with_guard_result(_GUARD_RESULT_FAIL)
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        expected_head=_HEAD_SHA,
        required_commands=[_REQUIRED_CMD],
        require_guard_result=True,
    )
    assert passed, f"Expected PASS with FAIL result block but got errors: {errors}"


def test_require_guard_result_fails_when_result_missing_from_both(
    tmp_path: pathlib.Path,
) -> None:
    body = _make_body_with_guard_result(_GUARD_CMD_ONLY)
    comment = _make_comment_with_guard_result(_GUARD_CMD_ONLY)
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_guard_result=True,
    )
    assert not passed
    p_errors = [e for e in errors if "[P]" in e]
    assert p_errors, f"Expected [P] errors but got: {errors}"


def test_require_guard_result_fails_when_result_missing_from_pr_body(
    tmp_path: pathlib.Path,
) -> None:
    body = _make_body_with_guard_result(_GUARD_CMD_ONLY)
    comment = _make_comment_with_guard_result(_GUARD_RESULT_PASS)
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_guard_result=True,
    )
    assert not passed
    p_errors = [e for e in errors if "[P]" in e]
    assert p_errors, f"Expected [P] errors for PR body but got: {errors}"
    assert any("PR body" in e for e in p_errors)


def test_require_guard_result_fails_when_result_missing_from_final_comment(
    tmp_path: pathlib.Path,
) -> None:
    body = _make_body_with_guard_result(_GUARD_RESULT_PASS)
    comment = _make_comment_with_guard_result(_GUARD_CMD_ONLY)
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_guard_result=True,
    )
    assert not passed
    p_errors = [e for e in errors if "[P]" in e]
    assert p_errors, f"Expected [P] errors for final comment but got: {errors}"
    assert any("final comment" in e for e in p_errors)


def test_require_guard_result_fails_on_vague_phrase(
    tmp_path: pathlib.Path,
) -> None:
    body = _make_body_with_guard_result(_GUARD_VAGUE)
    comment = _make_comment_with_guard_result(_GUARD_VAGUE)
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_guard_result=True,
    )
    assert not passed
    p_errors = [e for e in errors if "[P]" in e]
    assert p_errors, f"Expected [P] errors for vague phrase but got: {errors}"


def test_require_guard_result_fails_when_exit_code_missing(
    tmp_path: pathlib.Path,
) -> None:
    result_no_exit = (
        "PR evidence consistency guard: PASS\n"
        "Checked categories: A:missing_files, B:empty_evidence\n"
    )
    body = _make_body_with_guard_result(result_no_exit)
    comment = _make_comment_with_guard_result(result_no_exit)
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_guard_result=True,
    )
    assert not passed
    p_errors = [e for e in errors if "[P]" in e]
    assert p_errors, f"Expected [P] errors for missing exit code but got: {errors}"
    assert any("exit" in e.lower() for e in p_errors)


def test_require_guard_result_fails_when_checked_categories_missing(
    tmp_path: pathlib.Path,
) -> None:
    result_no_categories = (
        "PR evidence consistency guard: PASS\n"
        "exit 0\n"
    )
    body = _make_body_with_guard_result(result_no_categories)
    comment = _make_comment_with_guard_result(result_no_categories)
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_guard_result=True,
    )
    assert not passed
    p_errors = [e for e in errors if "[P]" in e]
    assert p_errors, f"Expected [P] errors for missing checked categories but got: {errors}"
    assert any("Checked categories" in e for e in p_errors)


def test_require_guard_result_not_active_by_default(
    tmp_path: pathlib.Path,
) -> None:
    body = _make_body_with_guard_result(_GUARD_CMD_ONLY)
    comment = _make_comment_with_guard_result(_GUARD_CMD_ONLY)
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        require_guard_result=False,
    )
    p_errors = [e for e in errors if "[P]" in e]
    assert not p_errors, f"[P] check should not run without --require-guard-result: {p_errors}"


def test_require_guard_result_preserves_wp47_behavior(
    tmp_path: pathlib.Path,
) -> None:
    body = (
        "focused tests (33 tests)\n"
        + _make_body_with_guard_result(_GUARD_RESULT_PASS)
    )
    comment = _make_comment_with_guard_result(_GUARD_RESULT_PASS)
    passed, errors, _, _ = _run(
        tmp_path, body, comment,
        forbid_inline_test_counts=True,
        require_guard_result=True,
    )
    assert not passed
    k_errors = [e for e in errors if "[K]" in e]
    assert k_errors, "WP47 --forbid-inline-test-counts must still trigger"
    p_errors = [e for e in errors if "[P]" in e]
    assert not p_errors, "Guard result is present so [P] must not trigger"


def test_require_guard_result_json_output_includes_category_p(
    tmp_path: pathlib.Path,
) -> None:
    import io
    from contextlib import redirect_stdout

    body = _make_body_with_guard_result(_GUARD_RESULT_PASS)
    comment = _make_comment_with_guard_result(_GUARD_RESULT_PASS)
    body_file = tmp_path / "pr_body.md"
    comment_file = tmp_path / "final_comment.md"
    body_file.write_text(body, encoding="utf-8")
    comment_file.write_text(comment, encoding="utf-8")

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = guard.main([
            "--pr-body", str(body_file),
            "--final-comment", str(comment_file),
            "--format", "json",
            "--require-guard-result",
        ])

    data = json.loads(buf.getvalue())
    assert "P:guard_result" in data["checked_categories"]
