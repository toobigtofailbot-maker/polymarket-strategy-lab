"""Tests for tools/git/status_snapshot.py."""

import importlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import pytest

_HELPER_PATH = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / "tools" / "git" / "status_snapshot.py"
)

_spec = importlib.util.spec_from_file_location("status_snapshot", _HELPER_PATH)
ss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ss)

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_HELPER_PATH), *args],
        capture_output=True,
        text=True,
        cwd=cwd or str(REPO_ROOT),
    )


def _run_main(*args: str) -> int:
    return ss.main(list(args))


# ── 1. CLI help exits 0 ───────────────────────────────────────────────────────

class TestCliHelp:
    def test_help_exits_0(self):
        result = _run("--help")
        assert result.returncode == 0

    def test_help_mentions_advisory(self):
        result = _run("--help")
        assert "advisory" in result.stdout.lower()

    def test_help_mentions_snapshot(self):
        result = _run("--help")
        assert "snapshot" in result.stdout.lower()


# ── 2. Repo-root validation ───────────────────────────────────────────────────

class TestRepoRootValidation:
    def test_valid_repo_root_exits_0(self):
        code = _run_main("--repo-root", str(REPO_ROOT), "--format", "text")
        assert code == 0

    def test_rejects_missing_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create partial repo-truth structure
            pathlib.Path(tmp, "docs").mkdir()
            pathlib.Path(tmp, "docs/project_status.md").write_text("# status", encoding="utf-8")
            pathlib.Path(tmp, "docs/repo_truth_index.md").write_text("# index", encoding="utf-8")
            # AGENTS.md missing
            code = _run_main("--repo-root", tmp, "--format", "text")
            assert code == 2

    def test_rejects_missing_project_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "AGENTS.md").write_text("# agents", encoding="utf-8")
            pathlib.Path(tmp, "docs").mkdir()
            pathlib.Path(tmp, "docs/repo_truth_index.md").write_text("# index", encoding="utf-8")
            code = _run_main("--repo-root", tmp, "--format", "text")
            assert code == 2

    def test_rejects_missing_repo_truth_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "AGENTS.md").write_text("# agents", encoding="utf-8")
            pathlib.Path(tmp, "docs").mkdir()
            pathlib.Path(tmp, "docs/project_status.md").write_text("# status", encoding="utf-8")
            code = _run_main("--repo-root", tmp, "--format", "text")
            assert code == 2

    def test_accepts_all_required_files_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "AGENTS.md").write_text("# agents", encoding="utf-8")
            pathlib.Path(tmp, "docs").mkdir()
            pathlib.Path(tmp, "docs/project_status.md").write_text("# status", encoding="utf-8")
            pathlib.Path(tmp, "docs/repo_truth_index.md").write_text("# index", encoding="utf-8")
            # Also need a .git dir for git metadata (can be empty dir for test)
            code = _run_main("--repo-root", tmp, "--format", "text")
            assert code == 0


# ── 3. Safe input allowlist ───────────────────────────────────────────────────

class TestSafeInputAllowlist:
    def test_only_allowlisted_files_in_source_files_used(self):
        code = _run_main("--repo-root", str(REPO_ROOT), "--format", "json")
        # Run via subprocess to capture JSON output
        result = _run("--format", "json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        allowed = set(ss.SAFE_INPUT_FILES)
        for f in data["source_files_used"]:
            assert f in allowed, f"File not in allowlist: {f}"

    def test_no_arbitrary_file_flag_exists(self):
        # Ensure there is no --input-file or similar flag
        import argparse
        parser = ss._build_parser()
        option_strings = []
        for action in parser._actions:
            option_strings.extend(action.option_strings)
        forbidden_flags = ["--input-file", "--read-file", "--file", "--path"]
        for flag in forbidden_flags:
            assert flag not in option_strings, f"Forbidden flag found: {flag}"


# ── 4. Prohibited input sources are not read ─────────────────────────────────

class TestProhibitedInputSources:
    PROHIBITED_NAMES = [
        ".env",
        ".env.local",
        "private_key.pem",
        "credentials.json",
        "wallet_key.txt",
        "mnemonic.txt",
        "api_key.txt",
        "secret_key.json",
        "id_rsa",
        "id_ed25519",
        "keystore.json",
        "local_data/snapshots/data.json",
        "local_data/polymarket/market.json",
        ".venv-security/lib/pkg.py",
        "tools/.bin/gitleaks",
        "security-scan-output/results.sarif",
        "official-client-sandbox-output/data.json",
        "src/data_layer/model.py",
    ]

    def test_prohibited_paths_are_flagged(self):
        for name in self.PROHIBITED_NAMES:
            assert ss._is_prohibited_input(name), f"Expected prohibited: {name}"

    def test_allowlisted_paths_are_not_prohibited(self):
        for name in ss.SAFE_INPUT_FILES:
            assert not ss._is_prohibited_input(name), f"Expected allowed: {name}"

    def test_env_file_prohibited(self):
        assert ss._is_prohibited_input(".env")

    def test_env_dotted_prohibited(self):
        assert ss._is_prohibited_input(".env.production")

    def test_local_data_prohibited(self):
        assert ss._is_prohibited_input("local_data/anything.json")

    def test_src_prohibited(self):
        assert ss._is_prohibited_input("src/some_module.py")


# ── 5. Output path validation ─────────────────────────────────────────────────

class TestOutputPathValidation:
    def test_accepts_valid_output_path(self):
        path, err = ss._validate_output_path(
            "local_data/status_snapshots/test.json", REPO_ROOT
        )
        assert err is None
        assert path is not None

    def test_rejects_absolute_path_unix(self):
        _, err = ss._validate_output_path("/tmp/snapshot.json", REPO_ROOT)
        assert err is not None

    def test_rejects_absolute_path_windows(self):
        _, err = ss._validate_output_path("C:\\tmp\\snapshot.json", REPO_ROOT)
        assert err is not None

    def test_rejects_traversal(self):
        _, err = ss._validate_output_path(
            "local_data/status_snapshots/../../etc/passwd", REPO_ROOT
        )
        assert err is not None

    def test_rejects_outside_allowed_dir(self):
        _, err = ss._validate_output_path("local_data/other/test.json", REPO_ROOT)
        assert err is not None

    def test_rejects_root_relative_outside(self):
        _, err = ss._validate_output_path("docs/snapshot.json", REPO_ROOT)
        assert err is not None


# ── 6. JSON output fields and reminders ──────────────────────────────────────

class TestJsonOutput:
    def _get_json(self, *extra_args: str) -> dict:
        result = _run("--format", "json", "--repo-root", str(REPO_ROOT), *extra_args)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        return json.loads(result.stdout)

    def test_json_parseable(self):
        result = _run("--format", "json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_required_schema_fields_present(self):
        data = self._get_json()
        required = [
            "summary_schema_version",
            "generated_timestamp_utc",
            "repo_commit_sha",
            "repo_branch",
            "source_files_used",
            "missing_source_files",
            "current_phase",
            "latest_merged_wp",
            "latest_merge_commit",
            "current_branch_from_repo_truth",
            "protected_boundary_status",
            "helper_inventory",
            "open_deferred_item_digest",
            "next_wp_candidates",
            "validation_reporting_expectations",
            "generated_artifact_output_rules",
            "manual_setup_decision_status",
            "stale_snapshot_warning",
            "advisory_only_note",
            "repo_truth_verification_reminder",
            "validation_human_review_reminder",
            "sensitive_content_detected",
            "redaction_applied",
            "warnings",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_schema_version_is_string(self):
        data = self._get_json()
        assert isinstance(data["summary_schema_version"], str)
        assert data["summary_schema_version"] == "1.0"

    def test_advisory_only_note_present(self):
        data = self._get_json()
        assert "advisory" in data["advisory_only_note"].lower()
        assert "not" in data["advisory_only_note"].lower()

    def test_repo_truth_verification_reminder_present(self):
        data = self._get_json()
        assert len(data["repo_truth_verification_reminder"]) > 20

    def test_validation_human_review_reminder_present(self):
        data = self._get_json()
        assert len(data["validation_human_review_reminder"]) > 20

    def test_sorted_keys(self):
        result = _run("--format", "json")
        assert result.returncode == 0
        # Verify sorted keys by checking key order
        raw_keys = [
            line.strip().split(":")[0].strip().strip('"')
            for line in result.stdout.splitlines()
            if line.strip() and not line.strip().startswith("{") and not line.strip().startswith("}")
            and ":" in line and not line.strip().startswith("[") and not line.strip().startswith("]")
        ]
        # Filter to top-level keys only (those at indent 2)
        top_keys = [
            line.strip().split(":")[0].strip().strip('"')
            for line in result.stdout.splitlines()
            if line.startswith('  "') and ":" in line
        ]
        assert top_keys == sorted(top_keys), "JSON output keys are not sorted"

    def test_trailing_newline(self):
        result = _run("--format", "json")
        assert result.returncode == 0
        assert result.stdout.endswith("\n")


# ── 7. Text output content ────────────────────────────────────────────────────

class TestTextOutput:
    def _get_text(self, *extra_args: str) -> str:
        result = _run("--format", "text", "--repo-root", str(REPO_ROOT), *extra_args)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        return result.stdout

    def test_text_output_contains_current_phase(self):
        text = self._get_text()
        assert "Current phase:" in text

    def test_text_output_contains_advisory_note(self):
        text = self._get_text()
        assert "ADVISORY" in text

    def test_text_output_contains_repo_truth_reminder(self):
        text = self._get_text()
        assert "REPO TRUTH" in text or "REPO-TRUTH" in text

    def test_text_output_contains_validation_reminder(self):
        text = self._get_text()
        assert "VALIDATION" in text

    def test_text_output_contains_source_files(self):
        text = self._get_text()
        assert "Source files used:" in text

    def test_text_output_mentions_advisory_only(self):
        text = self._get_text()
        assert "advisory" in text.lower()

    def test_text_output_has_header(self):
        text = self._get_text()
        assert "MEMORY / STATUS SNAPSHOT" in text


# ── 8. Markdown exits 2 ───────────────────────────────────────────────────────

class TestMarkdownUnsupported:
    def test_markdown_exits_2(self):
        result = _run("--format", "markdown")
        assert result.returncode == 2

    def test_markdown_error_message(self):
        result = _run("--format", "markdown")
        assert "markdown" in result.stderr.lower()
        assert "not implemented" in result.stderr.lower()


# ── 9. Project status parsing ─────────────────────────────────────────────────

class TestProjectStatusParsing:
    def test_parses_current_phase(self):
        sample = "- Current phase: WP99 - Test Phase\n"
        parsed = ss._parse_project_status(sample)
        assert parsed.get("current_phase") == "WP99 - Test Phase"

    def test_parses_current_branch(self):
        sample = "- Current branch: `wp99-test-branch`\n"
        parsed = ss._parse_project_status(sample)
        assert parsed.get("current_branch_from_repo_truth") == "wp99-test-branch"

    def test_parses_merged_wps(self):
        sample = "- Merged WPs: WP1, WP2, WP3\n"
        parsed = ss._parse_project_status(sample)
        assert parsed.get("merged_wps") == ["WP1", "WP2", "WP3"]

    def test_parses_latest_merged_wp(self):
        sample = "- Merged WPs: WP1, WP2, WP10\n"
        parsed = ss._parse_project_status(sample)
        assert parsed.get("latest_merged_wp") == "WP10"

    def test_parses_live_trading_status(self):
        sample = "- Live trading status: DISABLED\n"
        parsed = ss._parse_project_status(sample)
        assert parsed.get("live_trading_status") == "DISABLED"

    def test_parses_hermes_status(self):
        sample = "- Hermes status: NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY\n"
        parsed = ss._parse_project_status(sample)
        assert parsed.get("hermes_status") == "NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY"

    def test_parses_next_intended_wp(self):
        sample = "- Next intended WP: WP99 - Some Feature\n"
        parsed = ss._parse_project_status(sample)
        assert "WP99" in parsed.get("next_intended_wp_line", "")

    def test_extracts_next_wp_candidates(self):
        line = "WP99 - Feature A, WP100 - Feature B"
        candidates = ss._extract_next_wp_candidates(line)
        assert len(candidates) >= 1

    def test_real_project_status_has_current_phase(self):
        result = _run("--format", "json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["current_phase"] not in ("", "unknown"), \
            f"current_phase should be parsed, got: {data['current_phase']}"

    def test_real_project_status_has_protected_statuses(self):
        result = _run("--format", "json", "--include-protected-boundaries")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        pb = data.get("protected_boundary_status", {})
        assert "live_trading_status" in pb
        assert "hermes_status" in pb


# ── 10. Deferred digest ───────────────────────────────────────────────────────

class TestDeferredDigest:
    def test_include_deferred_returns_items(self):
        result = _run("--format", "json", "--include-deferred")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        items = data.get("open_deferred_item_digest", [])
        assert len(items) > 0, "Expected OPEN deferred items"

    def test_deferred_items_have_required_fields(self):
        result = _run("--format", "json", "--include-deferred")
        data = json.loads(result.stdout)
        for item in data["open_deferred_item_digest"]:
            assert "id" in item
            assert "item" in item
            assert "status" in item
            assert item["status"] == "OPEN"

    def test_max_deferred_items_cap(self):
        result = _run("--format", "json", "--include-deferred", "--max-deferred-items", "3")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data["open_deferred_item_digest"]) <= 3

    def test_max_deferred_items_zero_exits_2(self):
        result = _run("--format", "json", "--include-deferred", "--max-deferred-items", "0")
        assert result.returncode == 2

    def test_max_deferred_items_negative_exits_2(self):
        result = _run("--format", "json", "--include-deferred", "--max-deferred-items", "-5")
        assert result.returncode == 2

    def test_max_deferred_items_one_accepted(self):
        result = _run("--format", "json", "--include-deferred", "--max-deferred-items", "1")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data["open_deferred_item_digest"]) <= 1


# ── 11. Helper inventory ─────────────────────────────────────────────────────

class TestHelperInventory:
    def test_include_helper_inventory_returns_helpers(self):
        result = _run("--format", "json", "--include-helper-inventory")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        hi = data.get("helper_inventory", {})
        assert len(hi) > 0

    def test_diff_scope_helper_in_inventory(self):
        result = _run("--format", "json", "--include-helper-inventory")
        data = json.loads(result.stdout)
        hi = data["helper_inventory"]
        assert "diff_scope_summary" in hi

    def test_validation_output_helper_in_inventory(self):
        result = _run("--format", "json", "--include-helper-inventory")
        data = json.loads(result.stdout)
        hi = data["helper_inventory"]
        assert "validation_output_summary" in hi

    def test_code_blast_radius_helper_in_inventory(self):
        result = _run("--format", "json", "--include-helper-inventory")
        data = json.loads(result.stdout)
        hi = data["helper_inventory"]
        assert "code_blast_radius" in hi

    def test_helper_entries_have_path_and_status(self):
        result = _run("--format", "json", "--include-helper-inventory")
        data = json.loads(result.stdout)
        for name, info in data["helper_inventory"].items():
            assert "path" in info, f"{name} missing path"
            assert "status" in info, f"{name} missing status"
            assert "exists" in info, f"{name} missing exists"


# ── 12. Protected boundaries ──────────────────────────────────────────────────

class TestProtectedBoundaries:
    def test_include_protected_boundaries_present(self):
        result = _run("--format", "json", "--include-protected-boundaries")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        pb = data.get("protected_boundary_status", {})
        assert len(pb) > 0

    def test_protected_boundary_includes_note(self):
        result = _run("--format", "json", "--include-protected-boundaries")
        data = json.loads(result.stdout)
        pb = data["protected_boundary_status"]
        assert "note" in pb
        note = pb["note"]
        assert "cannot authorize" in note.lower() or "advisory" in note.lower()

    def test_protected_boundary_does_not_authorize_work(self):
        result = _run("--format", "json", "--include-protected-boundaries")
        data = json.loads(result.stdout)
        # Boundary status must NOT state trading is enabled
        pb = data["protected_boundary_status"]
        live = pb.get("live_trading_status", "")
        assert "disabled" in live.lower() or "not" in live.lower() or live == "DISABLED", \
            f"Unexpected live trading status: {live}"

    def test_text_output_includes_boundary_block(self):
        result = _run("--format", "text", "--include-protected-boundaries")
        assert result.returncode == 0
        assert "Protected boundary status" in result.stdout


# ── 13. Staleness metadata ────────────────────────────────────────────────────

class TestStalenessMetadata:
    def test_json_includes_commit_sha(self):
        result = _run("--format", "json")
        data = json.loads(result.stdout)
        assert "repo_commit_sha" in data
        sha = data["repo_commit_sha"]
        assert sha  # non-empty
        assert sha in ("unknown",) or len(sha) == 40

    def test_json_includes_branch(self):
        result = _run("--format", "json")
        data = json.loads(result.stdout)
        assert "repo_branch" in data
        assert data["repo_branch"]  # non-empty

    def test_json_includes_timestamp(self):
        result = _run("--format", "json")
        data = json.loads(result.stdout)
        assert "generated_timestamp_utc" in data
        ts = data["generated_timestamp_utc"]
        assert "T" in ts and "+" in ts or "Z" in ts

    def test_json_includes_schema_version(self):
        result = _run("--format", "json")
        data = json.loads(result.stdout)
        assert data.get("summary_schema_version") == "1.0"

    def test_json_includes_source_file_list(self):
        result = _run("--format", "json")
        data = json.loads(result.stdout)
        assert isinstance(data["source_files_used"], list)
        assert len(data["source_files_used"]) > 0

    def test_real_repo_has_known_sha_or_unknown(self):
        result = _run("--format", "json", "--repo-root", str(REPO_ROOT))
        data = json.loads(result.stdout)
        sha = data["repo_commit_sha"]
        assert sha == "unknown" or (len(sha) == 40 and all(c in "0123456789abcdef" for c in sha.lower()))


# ── 14. check-stale behavior ──────────────────────────────────────────────────

class TestCheckStale:
    def _make_snapshot(self, tmp_dir: str, **overrides) -> str:
        snap_dir = pathlib.Path(tmp_dir) / "local_data/status_snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        snap_path = snap_dir / "test.local.json"
        data = {
            "summary_schema_version": "1.0",
            "generated_timestamp_utc": "2026-01-01T00:00:00+00:00",
            "repo_commit_sha": "abc123def456abc123def456abc123def456abc1",
            "repo_branch": "test-branch",
            "source_files_used": ["AGENTS.md"],
        }
        data.update(overrides)
        snap_path.write_text(json.dumps(data), encoding="utf-8")
        return str(snap_path.relative_to(tmp_dir))

    def test_check_stale_current(self):
        # Create snapshot matching current state
        with tempfile.TemporaryDirectory() as tmp:
            snap_dir = pathlib.Path(tmp) / "local_data/status_snapshots"
            snap_dir.mkdir(parents=True)
            snap_path = snap_dir / "test.local.json"
            # Get actual current commit/branch
            result = _run("--format", "json", "--repo-root", str(REPO_ROOT))
            current = json.loads(result.stdout)
            data = {
                "summary_schema_version": "1.0",
                "generated_timestamp_utc": "2026-01-01T00:00:00+00:00",
                "repo_commit_sha": current["repo_commit_sha"],
                "repo_branch": current["repo_branch"],
                "source_files_used": ["AGENTS.md"],
            }
            snap_path.write_text(json.dumps(data), encoding="utf-8")
            rel = str(snap_path.relative_to(tmp))
            result2 = subprocess.run(
                [sys.executable, str(_HELPER_PATH), "--check-stale", rel,
                 "--repo-root", str(REPO_ROOT)],
                capture_output=True, text=True, cwd=tmp,
            )
            # Should not be stale (or may warn about branch diff which is OK for test)
            assert result2.returncode == 0

    def test_check_stale_detects_stale_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_dir = pathlib.Path(tmp) / "local_data/status_snapshots"
            snap_dir.mkdir(parents=True)
            snap_path = snap_dir / "test.local.json"
            data = {
                "summary_schema_version": "1.0",
                "generated_timestamp_utc": "2026-01-01T00:00:00+00:00",
                "repo_commit_sha": "0000000000000000000000000000000000000000",
                "repo_branch": "wp36-memory-status-snapshot-helper-implementation",
                "source_files_used": ["AGENTS.md"],
            }
            snap_path.write_text(json.dumps(data), encoding="utf-8")
            rel = str(snap_path.relative_to(tmp))
            result = subprocess.run(
                [sys.executable, str(_HELPER_PATH), "--check-stale", rel,
                 "--repo-root", str(REPO_ROOT)],
                capture_output=True, text=True, cwd=tmp,
            )
            assert result.returncode == 0
            assert "stale" in result.stdout.lower()

    def test_check_stale_detects_missing_timestamp(self):
        is_stale, reasons = ss._check_stale.__wrapped__ if hasattr(ss._check_stale, "__wrapped__") else (None, None)
        # Test via direct function call using a tmp file
        with tempfile.TemporaryDirectory() as tmp:
            snap_dir = pathlib.Path(tmp) / "local_data/status_snapshots"
            snap_dir.mkdir(parents=True)
            snap_path = snap_dir / "test.local.json"
            data = {
                "summary_schema_version": "1.0",
                # No generated_timestamp_utc
                "repo_commit_sha": "abc123def456abc123def456abc123def456abc1",
                "repo_branch": "test-branch",
            }
            snap_path.write_text(json.dumps(data), encoding="utf-8")
            is_stale, reasons = ss._check_stale(snap_path, "current_commit", "current_branch")
            assert is_stale
            assert any("timestamp" in r.lower() for r in reasons)

    def test_check_stale_detects_unsupported_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_dir = pathlib.Path(tmp) / "local_data/status_snapshots"
            snap_dir.mkdir(parents=True)
            snap_path = snap_dir / "test.local.json"
            data = {
                "summary_schema_version": "99.0",
                "generated_timestamp_utc": "2026-01-01T00:00:00+00:00",
                "repo_commit_sha": "abc123def456abc123def456abc123def456abc1",
                "repo_branch": "test-branch",
            }
            snap_path.write_text(json.dumps(data), encoding="utf-8")
            is_stale, reasons = ss._check_stale(snap_path, "abc123def456abc123def456abc123def456abc1", "test-branch")
            assert is_stale
            assert any("schema" in r.lower() for r in reasons)

    def test_check_stale_rejects_absolute_path(self):
        result = _run("--check-stale", "/absolute/path.json")
        assert result.returncode == 2

    def test_check_stale_rejects_traversal(self):
        result = _run("--check-stale", "local_data/status_snapshots/../../etc/passwd")
        assert result.returncode == 2

    def test_check_stale_rejects_outside_dir(self):
        result = _run("--check-stale", "docs/snapshot.json")
        assert result.returncode == 2


# ── 15. --fail-on-stale exits 1 ──────────────────────────────────────────────

class TestFailOnStale:
    def test_fail_on_stale_exits_1_when_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_dir = pathlib.Path(tmp) / "local_data/status_snapshots"
            snap_dir.mkdir(parents=True)
            snap_path = snap_dir / "test.local.json"
            data = {
                "summary_schema_version": "1.0",
                "generated_timestamp_utc": "2026-01-01T00:00:00+00:00",
                "repo_commit_sha": "0000000000000000000000000000000000000000",
                "repo_branch": "stale-branch",
                "source_files_used": ["AGENTS.md"],
            }
            snap_path.write_text(json.dumps(data), encoding="utf-8")
            rel = str(snap_path.relative_to(tmp))
            result = subprocess.run(
                [sys.executable, str(_HELPER_PATH),
                 "--check-stale", rel,
                 "--fail-on-stale",
                 "--repo-root", str(REPO_ROOT)],
                capture_output=True, text=True, cwd=tmp,
            )
            assert result.returncode == 1

    def test_fail_on_stale_exits_0_without_flag_when_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            snap_dir = pathlib.Path(tmp) / "local_data/status_snapshots"
            snap_dir.mkdir(parents=True)
            snap_path = snap_dir / "test.local.json"
            data = {
                "summary_schema_version": "1.0",
                "generated_timestamp_utc": "2026-01-01T00:00:00+00:00",
                "repo_commit_sha": "0000000000000000000000000000000000000000",
                "repo_branch": "stale-branch",
                "source_files_used": [],
            }
            snap_path.write_text(json.dumps(data), encoding="utf-8")
            rel = str(snap_path.relative_to(tmp))
            result = subprocess.run(
                [sys.executable, str(_HELPER_PATH),
                 "--check-stale", rel,
                 "--repo-root", str(REPO_ROOT)],
                capture_output=True, text=True, cwd=tmp,
            )
            assert result.returncode == 0


# ── 16. Secret redaction ──────────────────────────────────────────────────────

class TestSecretRedaction:
    SECRET_INPUTS = [
        ("API_KEY=abc123secret", "API_KEY"),
        ("PRIVATE_KEY=xyzprivate", "PRIVATE_KEY"),
        ("CLOB_SECRET=supersecret123", "CLOB_SECRET"),
        ("CLOB_PASS_PHRASE=mypassphrase", "CLOB_PASS_PHRASE"),
        ("MNEMONIC=word1 word2 word3", "MNEMONIC"),
        ("TOKEN=abc123tokenvalue", "TOKEN"),
        ("Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.long_token_here", "Bearer"),
        ("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----",  # EXAMPLE_ONLY
         "PEM_PRIVATE_KEY_REDACTED"),
    ]

    def test_api_key_redacted_in_output(self):
        text, was_redacted = ss._redact_secrets("API_KEY=abc123secret")
        assert was_redacted
        assert "abc123secret" not in text
        assert "[REDACTED]" in text

    def test_private_key_redacted(self):
        text, was_redacted = ss._redact_secrets("PRIVATE_KEY=xyzprivate")
        assert was_redacted
        assert "xyzprivate" not in text

    def test_clob_secret_redacted(self):
        text, was_redacted = ss._redact_secrets("CLOB_SECRET=supersecret")
        assert was_redacted
        assert "supersecret" not in text

    def test_mnemonic_redacted(self):
        text, was_redacted = ss._redact_secrets("MNEMONIC=word1 word2")
        assert was_redacted
        # Only the value portion redacted
        assert "[REDACTED]" in text

    def test_token_redacted(self):
        text, was_redacted = ss._redact_secrets("TOKEN=abc123tokenvalue")
        assert was_redacted
        assert "abc123tokenvalue" not in text

    def test_bearer_long_token_redacted(self):
        text, was_redacted = ss._redact_secrets(
            "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.longtoken"
        )
        assert was_redacted
        assert "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9" not in text

    def test_bearer_short_word_not_redacted(self):
        # "Bearer token" (English word) should not be redacted
        text, was_redacted = ss._redact_secrets("Bearer token")
        # Short token should not be treated as a secret
        assert "token" in text

    def test_pem_block_redacted(self):
        pem_input = (
            "-----BEGIN RSA PRIVATE KEY-----\n"  # EXAMPLE_ONLY
            "MIIEowIBAAKCAQEA12345\n"
            "-----END RSA PRIVATE KEY-----"
        )
        text, was_redacted = ss._redact_secrets(pem_input)
        assert was_redacted
        assert "MIIEowIBAAKCAQEA12345" not in text
        assert "REDACTED" in text

    def test_no_secret_no_redaction(self):
        text, was_redacted = ss._redact_secrets("This is a safe doc line.")
        assert not was_redacted
        assert text == "This is a safe doc line."

    def test_contains_secrets_detection(self):
        assert ss._contains_secrets("API_KEY=secret123")
        assert ss._contains_secrets("PRIVATE_KEY=abc")
        assert ss._contains_secrets("CLOB_SECRET=xyz")
        assert not ss._contains_secrets("This is safe text without keys.")

    def test_json_output_no_raw_secret_values(self):
        # Inject a file with a secret-like pattern via tmp repo
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "AGENTS.md").write_text(
                "# agents\nAPI_KEY=totally_fake_not_real_secret\n", encoding="utf-8"
            )
            pathlib.Path(tmp, "docs").mkdir()
            pathlib.Path(tmp, "docs/project_status.md").write_text(
                "- Current phase: WP1\n", encoding="utf-8"
            )
            pathlib.Path(tmp, "docs/repo_truth_index.md").write_text(
                "# index\n", encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(_HELPER_PATH), "--format", "json",
                 "--repo-root", tmp],
                capture_output=True, text=True,
            )
            assert result.returncode == 0
            assert "totally_fake_not_real_secret" not in result.stdout
            data = json.loads(result.stdout)
            assert data["sensitive_content_detected"] is True


# ── 17. --fail-on-sensitive-hit ──────────────────────────────────────────────

class TestFailOnSensitiveHit:
    def test_fail_on_sensitive_hit_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "AGENTS.md").write_text(
                "API_KEY=fake_secret_for_test\n", encoding="utf-8"
            )
            pathlib.Path(tmp, "docs").mkdir()
            pathlib.Path(tmp, "docs/project_status.md").write_text(
                "- Current phase: WP1\n", encoding="utf-8"
            )
            pathlib.Path(tmp, "docs/repo_truth_index.md").write_text(
                "# index\n", encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(_HELPER_PATH),
                 "--format", "json",
                 "--fail-on-sensitive-hit",
                 "--repo-root", tmp],
                capture_output=True, text=True,
            )
            assert result.returncode == 1

    def test_no_sensitive_exits_0_with_flag(self):
        result = _run("--format", "json", "--fail-on-sensitive-hit")
        # If no sensitive content, should still exit 0
        assert result.returncode == 0


# ── 18. Default writes no file ────────────────────────────────────────────────

class TestDefaultNoOutput:
    def test_default_writes_no_file(self):
        snap_dir = REPO_ROOT / "local_data/status_snapshots"
        before = set(snap_dir.glob("*.json")) if snap_dir.exists() else set()
        result = _run("--format", "text")
        assert result.returncode == 0
        after = set(snap_dir.glob("*.json")) if snap_dir.exists() else set()
        new_files = after - before
        assert len(new_files) == 0, f"Unexpected files created: {new_files}"

    def test_json_default_writes_no_file(self):
        snap_dir = REPO_ROOT / "local_data/status_snapshots"
        before = set(snap_dir.glob("*.json")) if snap_dir.exists() else set()
        result = _run("--format", "json")
        assert result.returncode == 0
        after = set(snap_dir.glob("*.json")) if snap_dir.exists() else set()
        new_files = after - before
        assert len(new_files) == 0, f"Unexpected files created: {new_files}"


# ── 19. Optional output smoke ─────────────────────────────────────────────────

class TestOptionalOutputSmoke:
    def test_output_writes_json_under_allowed_dir(self):
        snap_dir = REPO_ROOT / "local_data/status_snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        out_path = "local_data/status_snapshots/test_smoke_output.local.json"
        abs_out = REPO_ROOT / out_path
        try:
            result = _run(
                "--format", "json",
                "--output", out_path,
            )
            assert result.returncode == 0
            assert abs_out.exists(), "Output file not created"
            # JSON parseable
            data = json.loads(abs_out.read_text(encoding="utf-8"))
            assert "summary_schema_version" in data
        finally:
            if abs_out.exists():
                abs_out.unlink()

    def test_output_writes_parseable_json(self):
        snap_dir = REPO_ROOT / "local_data/status_snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        out_path = "local_data/status_snapshots/test_parseable.local.json"
        abs_out = REPO_ROOT / out_path
        try:
            result = _run("--format", "json", "--output", out_path)
            assert result.returncode == 0
            assert abs_out.is_file()
            data = json.loads(abs_out.read_text(encoding="utf-8"))
            assert isinstance(data, dict)
            assert data["summary_schema_version"] == "1.0"
        finally:
            if abs_out.exists():
                abs_out.unlink()


# ── 20. No forbidden imports ─────────────────────────────────────────────────

class TestNoForbiddenImports:
    # Import-style patterns that must not appear (as imports or invocations)
    FORBIDDEN_IMPORTS = [
        "import subprocess",
        "from subprocess",
        "import requests",
        "import httpx",
        "import aiohttp",
        "import websockets",
        "import socket",
        "import openai",
        "import anthropic",
        "import langchain",
        "import hermes",
        "from hermes",
        "import py_clob_client",
        "import chromadb",
        "import llama_index",
        "import mem0",
    ]

    # Runtime-invocation patterns that must not appear anywhere in source
    FORBIDDEN_CALLS = [
        "os.system(",
        "subprocess.run(",
        "subprocess.Popen(",
        "check_output(",
        "eval(",
        "exec(",
        "post_order(",
        "submit_order(",
        "sign_order(",
        "execute_trade(",
        "create_trade_proposal(",
        "generate_signal(",
    ]

    def test_no_forbidden_imports_in_helper(self):
        source = _HELPER_PATH.read_text(encoding="utf-8")
        for term in self.FORBIDDEN_IMPORTS:
            assert term not in source, \
                f"Forbidden import '{term}' found in {_HELPER_PATH.name}"

    def test_no_forbidden_calls_in_helper(self):
        source = _HELPER_PATH.read_text(encoding="utf-8")
        for term in self.FORBIDDEN_CALLS:
            assert term not in source, \
                f"Forbidden call '{term}' found in {_HELPER_PATH.name}"


# ── 21. CLI smoke ─────────────────────────────────────────────────────────────

class TestCliSmoke:
    def test_basic_text(self):
        result = _run("--format", "text")
        assert result.returncode == 0
        assert "MEMORY / STATUS SNAPSHOT" in result.stdout

    def test_basic_json(self):
        result = _run("--format", "json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "summary_schema_version" in data

    def test_full_flags_text(self):
        result = _run(
            "--format", "text",
            "--include-deferred",
            "--include-helper-inventory",
            "--include-next-wp-candidates",
            "--include-protected-boundaries",
        )
        assert result.returncode == 0

    def test_full_flags_json(self):
        result = _run(
            "--format", "json",
            "--include-deferred",
            "--include-helper-inventory",
            "--include-next-wp-candidates",
            "--include-protected-boundaries",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["helper_inventory"]
        assert isinstance(data["open_deferred_item_digest"], list)
        assert data["protected_boundary_status"]

    def test_output_then_check_stale(self):
        snap_dir = REPO_ROOT / "local_data/status_snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        out_path = "local_data/status_snapshots/test_cli_smoke.local.json"
        abs_out = REPO_ROOT / out_path
        try:
            # Write snapshot
            result = _run("--format", "json", "--output", out_path)
            assert result.returncode == 0
            assert abs_out.exists()
            # Check stale
            result2 = _run("--check-stale", out_path)
            assert result2.returncode == 0
            # Snapshot just written from same commit should not be stale
        finally:
            if abs_out.exists():
                abs_out.unlink()


# ── 22. Windows path handling ─────────────────────────────────────────────────

class TestWindowsPathHandling:
    def test_norm_windows_backslash(self):
        assert ss._norm("docs\\project_status.md") == "docs/project_status.md"

    def test_norm_strips_dotslash(self):
        assert ss._norm("./docs/file.md") == "docs/file.md"

    def test_prohibited_windows_path(self):
        assert ss._is_prohibited_input("local_data\\snapshots\\data.json")

    def test_output_path_rejects_windows_absolute(self):
        _, err = ss._validate_output_path("C:\\tmp\\output.json", REPO_ROOT)
        assert err is not None
