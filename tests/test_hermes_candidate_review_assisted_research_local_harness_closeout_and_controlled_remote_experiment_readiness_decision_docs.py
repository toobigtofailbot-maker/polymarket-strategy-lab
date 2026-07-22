"""Markdown-only tests for the WP146 local closeout and remote-readiness decision."""

from pathlib import Path
import ast
import re


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "hermes_candidate_review_assisted_research_local_harness_closeout_and_controlled_remote_experiment_readiness_decision.md"
TEXT = DOC.read_text(encoding="utf-8")

TITLE = "# Hermes Candidate-Review Assisted Research Local Harness Closeout And Controlled Remote Experiment Readiness Decision"
HEADINGS = (
    "## Purpose",
    "## Position After WP145",
    "## Authority And Non-Authority",
    "## Repository Inputs Reviewed",
    "## WP145 Evidence Reviewed",
    "## WP145 Follow-Up Reconciliation",
    "## WP145 Acceptance Decision",
    "## Local Harness Completeness Matrix",
    "## Remote Experiment Readiness Matrix",
    "## Current External Research Requirement",
    "## Remote Readiness Decision",
    "## Next Phase Decision",
    "## Promotion Gates",
    "## Explicit Deferred Capabilities",
    "## Output Surface Inventory",
    "## Forbidden Interpretations",
    "## Future WP147 Boundary",
    "## Decision",
    "## Non-Authority Statement",
)

LOCKED = (
    "Local harness phase status: CLOSED_COMPLETE_ENOUGH_FOR_BOUNDED_LOCAL_DRY_RUN",
    "WP145 corrected evidence accepted: YES",
    "Local one-case dry-run status: ACCEPTED_AS_TEST_ONLY_CONTROL_EVIDENCE",
    "WP145 implementation classification: BOUNDED_LOCAL_CONTROL_SKELETON",
    "WP145 phase-completion decision: ACCEPT",
    "Remote controlled experiment readiness: NOT_READY",
    "Primary remote-readiness blocker: CURRENT_PROVIDER_MODEL_PRIVACY_RETENTION_COST_AND_ENDPOINT_EVIDENCE_MISSING",
    "Provider/model candidate naming: DEFERRED_CURRENT_EXTERNAL_RESEARCH_REQUIRED",
    "Current external provider/model research: REQUIRED_BEFORE_REMOTE_EXPERIMENT_IMPLEMENTATION",
    "Remote experiment implementation authorization: DENIED_PENDING_RESEARCH_AND_CONTROL_GATES",
    "Remote adapter implementation: NOT AUTHORIZED",
    "Hermes installation/invocation: NOT AUTHORIZED",
    "Provider/model call: NOT AUTHORIZED",
    "Credential creation/use: NOT AUTHORIZED",
    "Network endpoint activation: NOT AUTHORIZED",
    "Experiment spending: NOT AUTHORIZED",
    "Raw input/output persistence: NOT AUTHORIZED",
    "Paper/live/execution authority: FORBIDDEN",
    "Next phase: CURRENT_PROVIDER_MODEL_PRIVACY_RETENTION_COST_RESEARCH_AND_CANDIDATE_SHORTLIST",
    "WP147 requires separate approval",
)

LOCAL_ROWS = (
    ("One-case local controller skeleton", "COMPLETE", "ACCEPT"),
    ("Exact state machine", "COMPLETE", "ACCEPT"),
    ("Input/permission/budget validation", "COMPLETE", "ACCEPT"),
    ("Precomputed synthetic response boundary", "COMPLETE", "ACCEPT"),
    ("Existing WP133 validation reuse", "COMPLETE", "ACCEPT"),
    ("Positive-case outcome enforcement", "COMPLETE", "ACCEPT"),
    ("Ten hard-gate evaluation", "COMPLETE", "ACCEPT"),
    ("Explicit human review", "COMPLETE", "ACCEPT"),
    ("Sanitized evidence", "COMPLETE", "ACCEPT"),
    ("Teardown/fail-closed behavior", "COMPLETE", "ACCEPT"),
    ("Test-only temp boundary", "COMPLETE", "ACCEPT"),
    ("No-network/no-credential proof", "COMPLETE FOR BOUNDED LOCAL TEST", "ACCEPT"),
    ("Multiple WP142 cases", "NOT IMPLEMENTED", "DEFER"),
    ("Hermes invocation", "NOT IMPLEMENTED", "DEFER"),
    ("Remote provider adapter", "NOT IMPLEMENTED", "DEFER"),
    ("Production sandbox", "NOT IMPLEMENTED", "DEFER"),
    ("Stable evidence storage", "NOT IMPLEMENTED", "DEFER"),
)

REMOTE_ROWS = (
    ("Current provider candidate evidence", "MISSING", "BLOCK"),
    ("Current model/version evidence", "MISSING", "BLOCK"),
    ("No-training/API data-use evidence", "MISSING", "BLOCK"),
    ("Retention/deletion evidence", "MISSING", "BLOCK"),
    ("Jurisdiction/subprocessor evidence", "MISSING", "BLOCK"),
    ("Current pricing/token-cost evidence", "MISSING", "BLOCK"),
    ("API stability/error/timeout evidence", "MISSING", "BLOCK"),
    ("Exact endpoint allowlist candidate", "MISSING", "BLOCK"),
    ("Provider/model shortlist", "MISSING", "BLOCK"),
    ("Remote adapter mapping", "NOT IMPLEMENTED", "BLOCK"),
    ("Enforced endpoint/network sandbox", "NOT IMPLEMENTED", "BLOCK"),
    ("Secret injection mechanism", "NOT IMPLEMENTED", "BLOCK"),
    ("Revocable experiment credential", "NOT CREATED", "BLOCK"),
    ("Hermes version/install evidence", "NOT CREATED", "BLOCK"),
    ("Remote raw-output evidence policy", "NOT APPROVED", "BLOCK"),
    ("Operator budget approval", "NOT RECORDED", "BLOCK"),
    ("Remote dry-run evidence", "NONE", "BLOCK"),
    ("Paper/live/trading authority", "FORBIDDEN", "PRESERVE"),
)

HARD_GATES = (
    "NO_FORBIDDEN_AUTHORITY",
    "NO_CREDENTIAL_OR_PRIVATE_DATA_LEAKAGE",
    "NO_UNSAFE_INPUT_ECHO",
    "NO_FABRICATED_CITATION",
    "NO_FABRICATED_SOURCE_ACCESS_CLAIM",
    "NO_AUTOMATIC_DOWNSTREAM_RECORD_CREATION",
    "NO_DETERMINISTIC_VALIDATOR_BYPASS",
    "NO_INPUT_MUTATION",
    "NO_UNAPPROVED_PERSISTENCE",
    "HUMAN_REVIEW_REQUIRED",
)


def _section(heading: str) -> str:
    start = TEXT.index(heading)
    later = [TEXT.find(candidate, start + 1) for candidate in HEADINGS if TEXT.find(candidate, start + 1) >= 0]
    end = min(later) if later else len(TEXT)
    return TEXT[start:end]


def test_exact_title_and_heading_order() -> None:
    lines = TEXT.splitlines()
    assert lines[0] == TITLE
    assert tuple(line for line in lines if line.startswith("## ")) == HEADINGS


def test_all_locked_decision_tokens_are_exact_and_repeated_in_decision() -> None:
    decision = _section("## Decision")
    for token in LOCKED:
        assert token in TEXT
        assert token in decision


def test_repository_and_wp145_final_evidence_inventory_is_complete() -> None:
    reviewed = _section("## Repository Inputs Reviewed") + _section("## WP145 Evidence Reviewed")
    for phrase in (
        "ca2669a4c21f57394a146a5e606bfda7cd1c648d",
        "797b5732eeaad22166d19377ff8e246104310af8",
        "c3a36601b6b747d1a35fde93ebd5dfb0c3bac7a4",
        "exactly 13 changed files",
        "exactly one\nsource module",
        "no fixture, tools,\nworkflow, dependency, lock, config, credential, prompt, or stable-output file\nchange",
        "complete WP141 contract/test/status",
        "complete WP142\ndocument/fixture/tests/status",
        "complete WP143 decision/test/status",
        "complete WP144 contract/test/status",
        "final merged WP145 source, focused\ntest, temp smoke, operator note, status fragment, final PR body, final head, and\nmerge metadata",
    ):
        assert phrase in reviewed


def test_corrected_precomputed_response_and_positive_outcome_are_explicit() -> None:
    evidence = _section("## WP145 Evidence Reviewed")
    for phrase in (
        "already-materialized plain synthetic response",
        "Arbitrary callable execution is absent",
        "adapter call count is zero",
        "external callable invocation is false",
        "GC-P01-COMPLETE-SUPPORTED",
        "SAFE_DRAFT_EXPECTED",
        "RESPONSE_COMPLETE_PENDING_HUMAN_REVIEW",
        "REQUIRED_SECTIONS_PRESENT",
        "HUMAN_REVIEW_PENDING",
        "existing\nWP133 validator is reused",
        "Human review is explicit and caller supplied",
    ):
        assert phrase in evidence


def test_all_ten_hard_gates_are_derived_and_false_blocks_success() -> None:
    evidence = _section("## WP145 Evidence Reviewed")
    assert all(gate in evidence for gate in HARD_GATES)
    assert "All ten WP142 hard gates are explicitly derived by a named evaluator" in evidence
    assert "One false gate blocks success" in evidence
    assert "not blanket-initialized true" in evidence
    assert "validated scalar\nand sequence text surfaces" in evidence
    assert "Citation references are restricted to supplied\nsynthetic references" in evidence
    assert "Original case, fixture, and caller inputs remain\nunchanged" in evidence


def test_sanitized_evidence_human_review_and_teardown_proof_are_complete() -> None:
    evidence = _section("## WP145 Evidence Reviewed")
    for phrase in (
        "exact 17 WP144 states",
        "both perform teardown before `COMPLETED` or\n`STOPPED_FAILED_CLOSED`",
        "no retry or background continuation",
        "`tmp_path` remains empty",
        "sanitized\nevidence and neutral no-echo diagnostics only",
        "no raw input/output or\ndownstream record",
    ):
        assert phrase in evidence


def test_follow_up_reconciliation_and_acceptance_are_bounded() -> None:
    follow_up = _section("## WP145 Follow-Up Reconciliation")
    acceptance = _section("## WP145 Acceptance Decision")
    for phrase in (
        "arbitrary caller-supplied callable",
        "precomputed plain synthetic response",
        "invokes no external\ncallable",
        "blanket initialization of nine\ngates",
        "exact positive label and\ncompletion posture",
        "derives all ten gates explicitly",
        "recursively scans all\nconfigured validated response text surfaces",
        "merged source, focused tests, temp smoke,\noperator note, stable WP145 status fragment, and final PR #145 body",
    ):
        assert phrase in follow_up
    for phrase in (
        "WP145 implementation classification: BOUNDED_LOCAL_CONTROL_SKELETON",
        "WP145 phase-completion decision: ACCEPT",
        "does not establish production readiness, remote readiness, Hermes\nintegration, provider suitability, factual correctness, source verification,\nor trading readiness",
    ):
        assert phrase in acceptance


def test_local_completeness_matrix_has_every_exact_row() -> None:
    section = _section("## Local Harness Completeness Matrix")
    for name, status, decision in LOCAL_ROWS:
        assert f"| {name} | {status} | {decision} |" in section
    assert section.count("| COMPLETE | ACCEPT |") == 11
    assert "| COMPLETE FOR BOUNDED LOCAL TEST | ACCEPT |" in section
    assert section.count("| NOT IMPLEMENTED | DEFER |") == 5


def test_remote_readiness_matrix_has_every_exact_blocking_row() -> None:
    section = _section("## Remote Experiment Readiness Matrix")
    for name, status, decision in REMOTE_ROWS:
        assert f"| {name} | {status} | {decision} |" in section
    assert section.count("| MISSING | BLOCK |") == 9
    assert section.count("| NOT IMPLEMENTED | BLOCK |") == 3
    assert section.count("| NOT CREATED | BLOCK |") == 2
    assert section.count("| NOT APPROVED | BLOCK |") == 1
    assert section.count("| NOT RECORDED | BLOCK |") == 1
    assert section.count("| NONE | BLOCK |") == 1
    assert "Every `MISSING`, `NOT IMPLEMENTED`, `NOT CREATED`, `NOT APPROVED`, `NOT\nRECORDED`, and `NONE` entry above remains blocking" in section


def test_external_research_and_remote_denial_are_complete() -> None:
    research = _section("## Current External Research Requirement")
    readiness = _section("## Remote Readiness Decision")
    for phrase in (
        "Current external provider/model research: REQUIRED_BEFORE_REMOTE_EXPERIMENT_IMPLEMENTATION",
        "Provider/model candidate naming: DEFERRED_CURRENT_EXTERNAL_RESEARCH_REQUIRED",
        "current authoritative provider documentation",
        "training/data-use posture",
        "retention/deletion",
        "jurisdiction/subprocessors",
        "endpoint/domain requirements",
        "hosted tools and memory defaults",
        "current\npricing",
        "key lifecycle",
        "expected WP142 experiment cost",
        "local-model baseline feasibility",
        "WP146 performs none of this research and\nnames no candidate",
    ):
        assert phrase in research
    for phrase in (
        "Remote experiment implementation authorization: DENIED_PENDING_RESEARCH_AND_CONTROL_GATES",
        "no more than two remote candidates",
        "WP143\neligibility",
        "privacy, retention, jurisdiction, and\nsubprocessor evidence",
        "remote evidence/storage policy is approved",
        "separate implementation WP\nis explicitly authorized",
    ):
        assert phrase in readiness


def test_next_phase_promotion_gates_and_wp147_boundary_are_exact() -> None:
    next_phase = _section("## Next Phase Decision")
    gates = _section("## Promotion Gates")
    future = _section("## Future WP147 Boundary")
    assert "Next phase: CURRENT_PROVIDER_MODEL_PRIVACY_RETENTION_COST_RESEARCH_AND_CANDIDATE_SHORTLIST" in next_phase
    assert "WP147 requires separate approval" in next_phase
    assert "not remote\nexperiment implementation" in next_phase
    assert "One failed or missing gate preserves `NOT_READY`" in gates
    assert "WP147 — Hermes Candidate-Review Assisted Research Current Provider/Model, Privacy, Retention, Cost, And Endpoint Research With Candidate Shortlist V1" in future
    for phrase in (
        "current authoritative provider documentation",
        "at most two\nremote candidates and one optional local baseline",
        "score candidates against WP143\neligibility",
        "update docs/status/tests\nonly",
        "must not install Hermes",
        "create a provider account or credential",
        "call a\nmodel",
        "implement an adapter",
        "activate an endpoint",
        "run cases",
        "persist model\noutput",
        "trade",
        "implement WP148",
        "WP147 requires separate approval",
    ):
        assert phrase in future


def test_all_deferred_capabilities_and_output_boundaries_are_explicit() -> None:
    deferred = _section("## Explicit Deferred Capabilities")
    inventory = _section("## Output Surface Inventory")
    for phrase in (
        "Hermes installation/version selection",
        "provider/model activation",
        "provider account",
        "credential creation",
        "secret store",
        "endpoint allowlist implementation",
        "remote adapter/sandbox",
        "provider SDK/API\nclient",
        "remote request",
        "prompt execution",
        "case execution",
        "provider comparison\nresults",
        "raw-output retention",
        "stable experiment evidence",
        "source retrieval",
        "spending",
        "paper/live/trading integration",
        "not WP146 defects",
    ):
        assert phrase in deferred
    for phrase in (
        "Markdown decision record",
        "Markdown-only focused\ntest",
        "stable WP146 status fragment",
        "creates no source, tool, fixture, workflow, dependency, lock, configuration",
        "prompt, provider/model selection, credential, endpoint, network call, runtime",
        "raw output, storage, report/export, experiment result, or trading artifact",
    ):
        assert phrase in inventory


def test_forbidden_interpretations_and_non_authority_reject_reviewer_traps() -> None:
    forbidden = _section("## Forbidden Interpretations")
    non_authority = _section("## Non-Authority Statement")
    for phrase in (
        "Local closeout does not mean production readiness",
        "Accepted test-only evidence does not mean a remote experiment is ready",
        "Required external research does not select or activate a provider/model",
        "future endpoint candidate does not authorize endpoint activation",
        "future credential lifecycle does not authorize credential creation or use",
        "WP143 budget caps do not authorize spending",
        "Remote evidence planning does not authorize raw persistence",
        "WP147 gating does not mean WP147 is implemented",
    ):
        assert phrase in forbidden
    for phrase in (
        "grants no source,\ntools, harness, adapter, Hermes, provider/model, account, credential, endpoint,\nnetwork",
        "network, source-retrieval, prompt-execution, case-execution, spend, raw-output,\nstorage",
        "storage, recommendation, probability, ranking, paper/live, execution, risk,\norder, trading, WP147 implementation, or promotion authority",
    ):
        assert phrase in non_authority

    reviewer_traps = (
        r"(?m)^(?:- )?WP145 is production-ready",
        r"(?m)^(?:- )?Remote experiment is ready",
        r"(?m)^(?:- )?Provider/model (?:is|has been) selected",
        r"(?m)^(?:- )?Provider/model (?:is|has been) activated",
        r"(?m)^(?:- )?Hermes may be installed",
        r"(?m)^(?:- )?Credentials? (?:are|is) authorized",
        r"(?m)^(?:- )?Endpoint activation is authorized",
        r"(?m)^(?:- )?Experiment spending is authorized",
        r"(?m)^(?:- )?Provider/model calls? (?:are|is) authorized",
        r"(?m)^(?:- )?Raw (?:input/output )?persistence is authorized",
        r"(?m)^(?:- )?Trading is authorized",
        r"(?m)^(?:- )?WP147 is implemented",
    )
    for trap in reviewer_traps:
        assert re.search(trap, TEXT, re.IGNORECASE) is None


def test_docs_test_reads_markdown_only_and_imports_no_product_module() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    assert "DOC.read_text" in source
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imported == {"ast", "pathlib", "re"}
