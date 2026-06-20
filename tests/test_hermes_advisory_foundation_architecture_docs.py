"""Focused docs tests for WP96 Hermes advisory foundation architecture."""

from __future__ import annotations

import pathlib
import re
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ARCH_DOC = REPO_ROOT / "docs" / "hermes_advisory_foundation_research_brain_architecture.md"
PLAN_DOC = REPO_ROOT / "docs" / "hermes_research_brain_execution_plan.md"
STATUS_DOC = REPO_ROOT / "docs" / "project_status.md"
STATUS_ENTRY = REPO_ROOT / "docs" / "status_entries" / "WP96.md"
REPO_TRUTH_INDEX = REPO_ROOT / "docs" / "repo_truth_index.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _flat(path: pathlib.Path) -> str:
    return " ".join(_read(path).split())


def test_architecture_doc_exists_and_is_registered() -> None:
    assert ARCH_DOC.is_file()
    index_text = _read(REPO_TRUTH_INDEX)
    assert "docs/hermes_advisory_foundation_research_brain_architecture.md" in index_text
    assert "tests/test_hermes_advisory_foundation_architecture_docs.py" in index_text


def test_status_and_authority_forbid_runtime_artifacts() -> None:
    text = _flat(ARCH_DOC)
    required = (
        "WP96_REPO_TRUTH_ARCHITECTURE_FOUNDATION",
        "docs/status/tests-only architecture lock-in",
        "Runtime authority: NONE",
        "Execution authority: NONE",
        "Paper authority: NONE",
        "Live authority: NONE",
        "Credential authority: NONE",
        "Schema, validator, prompt-pack, runbook, exporter, and runtime artifact authority: NONE",
        "does not install Hermes",
        "does not connect Hermes",
        "does not create machine-readable contracts",
        "does not create validators",
        "does not create prompt packs",
        "does not create operator runbooks",
        "does not create exporters",
    )
    for phrase in required:
        assert phrase in text


def test_wp95_relationship_and_phase_one_are_explicit() -> None:
    text = _flat(ARCH_DOC)
    assert "WP95 locked the accepted Hermes research-brain execution plan" in text
    assert "WP96 is Phase 1" in text
    assert "does not override WP95" in text
    assert "docs/hermes_research_brain_execution_plan.md" in text


def test_hermes_is_powerful_research_brain_not_passive_summarizer() -> None:
    text = _flat(ARCH_DOC)
    required = (
        "powerful from the beginning as an adaptive research brain",
        "Guardrails prevent execution and control risk",
        "must not reduce legitimate research usefulness",
        "Research breadth is intentionally broad",
        "not by making Hermes a passive summarizer",
    )
    for phrase in required:
        assert phrase in text


def test_broad_research_freedoms_are_present() -> None:
    text = _read(ARCH_DOC)
    required = (
        "market research",
        "edge discovery",
        "hypothesis generation",
        "experiment design",
        "strategy critique",
        "future WP recommendations",
        "failure analysis",
        "performance-improvement ideas",
        "wallet and candidate review",
        "regime monitoring",
        "cross-market inconsistency analysis",
        "resolution-rule ambiguity review",
        "microstructure and slippage realism review",
        "paper-strategy research after future deterministic artifacts exist",
    )
    for phrase in required:
        assert phrase in text


def test_mode_map_contains_h0_through_h10() -> None:
    text = _read(ARCH_DOC)
    for mode in [f"H{i}" for i in range(11)]:
        assert f"| {mode} |" in text
    required = (
        "Repo-truth discovery and artifact inventory",
        "Advisory foundation / authority boundary",
        "Output contract and validator hardening",
        "Research prompt pack and operator runbooks",
        "Deterministic context-packet consumption",
        "Shadow analyst",
        "Paper assistant",
        "Manual-live review assistant",
        "Restricted-live monitoring/explanation assistant",
    )
    for phrase in required:
        assert phrase in text


def test_authority_matrix_covers_required_rows_and_columns() -> None:
    text = _read(ARCH_DOC)
    for column in (
        "Allowed now?",
        "Allowed later with separate WP?",
        "Forbidden?",
        "Required human gate?",
        "Deterministic owner",
        "Notes",
    ):
        assert column in text
    for row in (
        "Market research",
        "Edge hypothesis",
        "Experiment proposal",
        "Wallet/candidate review",
        "Cross-market inconsistency review",
        "Resolution ambiguity review",
        "Microstructure/slippage critique",
        "Strategy critique",
        "Failure analysis",
        "Performance review",
        "Future WP suggestion",
        "Context-packet reading",
        "Prompt/runbook use",
        "Config mutation",
        "Credentials",
        "Private endpoints",
        "Account data",
        "Order placement/cancel/signing/submission",
        "Risk override",
        "Scheduler/bot loop",
        "Paper/live execution",
        "PR approval / merge readiness",
    ):
        assert row in text


def test_deterministic_core_and_forbidden_hermes_authority_are_explicit() -> None:
    text = _read(ARCH_DOC)
    for phrase in (
        "execution",
        "validation",
        "risk",
        "state",
        "accounting",
        "credentials",
        "order lifecycle",
        "live safety",
        "kill switch",
        "audit logs",
        "strategy-promotion gates",
        "access credentials or private endpoints",
        "place, cancel, sign, or submit orders",
        "control runtime, scheduler, or bot loop",
        "mutate live configs",
        "override risk",
        "approve strategy promotion",
        "approve PRs or claim merge readiness",
        "act as the final decision-maker for trade, risk, or live actions",
    ):
        assert phrase in text


def test_input_and_output_families_are_architecture_only() -> None:
    text = _read(ARCH_DOC)
    for phrase in (
        "repo-truth summary packet",
        "market research candidate packet",
        "wallet/candidate review packet",
        "resolution ambiguity packet",
        "cross-market relationship packet",
        "microstructure/slippage realism packet",
        "paper-result/failure-review packet",
        "performance-review packet",
        "experiment-design packet",
        "research hypothesis",
        "experiment proposal",
        "market/candidate critique",
        "wallet-signal critique",
        "cross-market inconsistency note",
        "resolution ambiguity warning",
        "microstructure realism critique",
        "strategy critique",
        "failure-analysis note",
        "performance-improvement idea",
        "future-WP suggestion",
        "These are not schemas",
    ):
        assert phrase in text


def test_forbidden_output_matrix_contains_reviewer_traps() -> None:
    text = _read(ARCH_DOC)
    for phrase in (
        "Buy/sell/hold/enter/exit commands",
        "Position size",
        "Limit price as instruction",
        "Order instructions",
        "Live readiness claims",
        "Risk override",
        "Credential requests",
        "Private endpoint requests",
        "Merge-readiness claims",
        "Config mutation requests",
        "Scheduler/bot-loop instructions",
        "Strategy-promotion approval",
        "Paper/live execution decision",
    ):
        assert phrase in text


def test_no_actual_hermes_implementation_artifacts_added() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
        text=True,
        timeout=60,
    ).stdout.splitlines()
    forbidden_patterns = (
        re.compile(r"(^|/)hermes.*schema.*\.(json|yaml|yml|py)$", re.IGNORECASE),
        re.compile(r"(^|/)hermes.*validator.*\.py$", re.IGNORECASE),
        re.compile(r"(^|/)hermes.*prompt", re.IGNORECASE),
        re.compile(r"(^|/)hermes.*runbook", re.IGNORECASE),
        re.compile(r"(^|/)hermes.*exporter.*\.py$", re.IGNORECASE),
        re.compile(r"^tools/hermes/", re.IGNORECASE),
        re.compile(r"^src/.*/hermes", re.IGNORECASE),
    )
    allowed = {
        "docs/hermes_readonly_boundary.md",
        "docs/hermes_research_brain_execution_plan.md",
        "docs/hermes_advisory_foundation_research_brain_architecture.md",
        "tests/test_hermes_advisory_foundation_architecture_docs.py",
    }
    findings = []
    for path in tracked:
        normalized = path.replace("\\", "/")
        if normalized in allowed:
            continue
        if any(pattern.search(normalized) for pattern in forbidden_patterns):
            findings.append(normalized)
    assert findings == []


def test_project_status_records_wp96_stable_target_state() -> None:
    text = _read(STATUS_DOC)
    merged_line = next(line for line in text.splitlines() if line.startswith("- Merged WPs:"))
    assert "WP96" in merged_line
    assert "Hermes advisory foundation architecture status: REPO_TRUTH_ARCHITECTURE_LOCKED" in text
    assert "docs/hermes_advisory_foundation_research_brain_architecture.md" in text
    assert "Next intended WP: Hermes input/output contracts and validator hardening" in text


def test_status_docs_reject_wp96_stale_branch_placeholders() -> None:
    project_text = _read(STATUS_DOC)
    status_text = _read(STATUS_ENTRY)
    for text in (project_text, status_text):
        for phrase in (
            "WP96 on branch",
            "WP96 active branch",
            "Merge commit: TBD after merge",
            "PR: TBD",
            "Ready for review: YES paired with missing PR metadata",
        ):
            assert phrase not in text
        assert re.search(r"Current live PR head:\s*`?[0-9a-f]{40}`?", text, re.IGNORECASE) is None


def test_wp95_plan_marks_wp96_as_architecture_foundation_step() -> None:
    text = _read(PLAN_DOC)
    assert "1. Hermes Advisory Foundation And Research-Brain Architecture V1" in text
    assert "WP96 records this Phase 1 architecture foundation" in text
    assert "Hermes input/output contracts and validator hardening" in text


def test_status_entry_is_stable_and_boundary_complete() -> None:
    text = _read(STATUS_ENTRY)
    for phrase in (
        "PR: see GitHub PR metadata and PR body.",
        "Current live PR head: see GitHub PR metadata and PR body",
        "stable and non-self-referential",
        "Validated implementation commit:",
        "Evidence mode: PRIVATE_REPO_MANUAL_VERIFIED",
        "Ready for review: YES",
        "Hermes input/output contracts and validator hardening",
        "No Hermes runtime, install, provider/model config, credential, schema, validator, prompt pack, runbook, exporter",
    ):
        assert phrase in text
