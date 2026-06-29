# Hermes Candidate-Review Local Manual Export Smoke Exercise

## 1. Purpose

This document defines a temp-only pytest smoke exercise for the existing
WP106 -> WP108 -> WP109 manual export path.

The exercise proves that the WP110 operator runbook path is mechanically
coherent under a controlled local pytest run. It is a safety and operability
proof only. It does not create a real report pipeline.

## 2. Scope

The smoke exercise builds synthetic safe fixture data, creates a valid WP106
handoff result, builds a valid WP108 manual export artifact result, and writes
that artifact through the existing WP109 writer to `pytest` `tmp_path`.

The test writes only to the temporary path supplied by pytest. It does not
create, commit, preserve, or stage generated artifact files.

## 3. Non-Authority

WP111 is docs/status/tests-only. It does not add or authorize:

- CLI.
- Report or export pipeline.
- Automation.
- Background writer.
- Scheduler.
- Daemon.
- Hermes runtime.
- Prompt runner.
- Model or provider integration.
- Dashboard.
- Network, API, product, or account behavior.
- Credentials or private state.
- Paper or live behavior.
- Execution, risk, or order behavior.
- Dependency, workflow, or lock-file changes.
- Committed generated artifacts.

## 4. Fixture Safety

The smoke exercise uses synthetic safe fixture data only.

The fixture data must not include real market data, wallet identifiers, account
identifiers, private state, credentials, order text, paper or live state, raw
model output, prompt-runner output, raw metadata, or free-form metadata.

## 5. Output Boundary

The only output path is `tmp_path / "candidate_review_manual_export.md"` inside
the pytest-controlled temporary directory.

The test must not write under `docs/`, `src/`, `tests/`, tracked local output
folders, `local_data/`, or any committed artifact path.

Invalid artifact inputs must fail closed and must not create an output file.

## 6. Interpretation Boundary

The written artifact is a manual review artifact only. It is not a trade
signal, strategy recommendation, paper or live readiness statement, PR approval,
merge-readiness statement, expected-return estimate, position-sizing
instruction, runtime instruction, execution authority, or strategy promotion.

Any next research step cited by the artifact remains a manual research
suggestion only.

## 7. Relationship To WP110

WP110 documents the manual operator runbook for using the existing WP109 writer
with valid WP108 artifacts. WP111 adds a temp-only smoke exercise that verifies
the documented path can produce deterministic Markdown in a controlled pytest
temporary directory without widening WP110 authority.

