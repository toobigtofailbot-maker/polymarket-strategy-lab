# Testing Requirements

## WP36 Memory / Status Snapshot Helper Implementation Tests

- `tools/git/status_snapshot.py` must exist and be stdlib-only.
- CLI help exits 0 and mentions advisory/snapshot behavior.
- Repo-root validation: all required files present → exit 0; missing AGENTS.md, docs/project_status.md, or docs/repo_truth_index.md → exit 2.
- Safe input allowlist enforced: `source_files_used` contains only allowlisted files; no `--input-file` or arbitrary-file flag exists.
- Prohibited input paths rejected: `.env`, `.env.*`, credential files, private-key files, `local_data/`, `src/`, arbitrary paths flagged by `_is_prohibited_input`.
- Output path validation: `local_data/status_snapshots/<file>.json` → accepted; absolute path → exit 2; traversal → exit 2; outside dir → exit 2.
- Text output: contains current phase, advisory-only note, repo-truth verification reminder, validation/human-review reminder, source files section, header.
- JSON output: parseable, contains all required schema fields including `summary_schema_version`, `generated_timestamp_utc`, `repo_commit_sha`, `repo_branch`, `source_files_used`, `missing_source_files`, `current_phase`, `latest_merged_wp`, `protected_boundary_status`, `helper_inventory`, `open_deferred_item_digest`, `next_wp_candidates`, `advisory_only_note`, `repo_truth_verification_reminder`, `validation_human_review_reminder`, `sensitive_content_detected`, `redaction_applied`, `warnings`.
- JSON output: sorted keys, trailing newline.
- `--format markdown` exits 2 with error message.
- Project status parsing: extracts current phase, current branch, merged WPs, latest merged WP, live trading status, hermes status, next intended WP line.
- `--include-deferred`: returns OPEN deferred items with id/item/status/priority fields; `--max-deferred-items` cap enforced; values < 1 → exit 2.
- `--include-helper-inventory`: reports diff_scope_summary, validation_output_summary, code_blast_radius, and status_snapshot helpers with path/status/exists fields.
- `--include-protected-boundaries`: includes boundary status block with advisory note that does not authorize protected work.
- Staleness metadata: commit SHA is 40-char hex or "unknown"; branch is non-empty; timestamp includes T and timezone; schema version is "1.0"; source file list is non-empty list.
- `--check-stale`: detects current, stale commit, stale branch, missing timestamp, unsupported schema; rejects absolute path, traversal, outside-dir path (exit 2).
- `--fail-on-stale` exits 1 when stale snapshot detected.
- Secret redaction: API_KEY, PRIVATE_KEY, CLOB_SECRET, CLOB_PASS_PHRASE, MNEMONIC, TOKEN, long Bearer tokens, PEM blocks detected and redacted; raw values absent from output; `sensitive_content_detected` set.
- `--fail-on-sensitive-hit` exits 1 when sensitive content detected.
- Default writes no file; JSON default writes no file.
- Optional output: `--output local_data/status_snapshots/test.local.json` → file created, parseable JSON with `summary_schema_version`.
- No forbidden imports: `import subprocess`, `from subprocess`, `import requests`, `import httpx`, `import aiohttp`, `import websockets`, `import socket`, `import openai`, `import anthropic`, `import langchain`, `import hermes`, `from hermes`, `import py_clob_client`, `import chromadb`, `import llama_index`, `import mem0` must not appear.
- No forbidden calls: `os.system(`, `subprocess.run(`, `subprocess.Popen(`, `check_output(`, `eval(`, `exec(`, `post_order(`, `submit_order(`, `sign_order(`, `execute_trade(`, `create_trade_proposal(`, `generate_signal(` must not appear.
- CLI smoke: basic text, JSON, all optional flags, output+check-stale round-trip.
- Windows path handling: backslash normalized, prohibited Windows paths detected, Windows absolute output path rejected.
- `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md` must exist.
- `docs/repo_truth_index.md` must include both helper and design doc; numbering unique and sequential.
- WP35-D001 resolved; WP28-D001, WP30-D001, WP32-D001, WP34-D001 remain OPEN; WP36-D001 and WP36-D002 added.

## WP35 Memory / Status Snapshot Helper Design Tests

- `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER_DESIGN.md` must exist.
- Design doc must contain required status fields: `DESIGN_ONLY`, `NOT_IMPLEMENTED`, `Claude Code and Codex`, `NO_RUNTIME_CHANGE`, `NO_TOOL_IMPLEMENTATION`, `NO_DEPENDENCY_CHANGE`, `NO_NETWORK`, `NO_VALIDATION_WEAKENING`, `NO_PROTECTED_BOUNDARY_CHANGE`, `ADVISORY_ONLY_NOT_REPO_TRUTH`.
- Design doc must contain authority model: repo truth wins, snapshot is advisory, stale until compared with main, cannot override `AGENTS.md` or `docs/project_status.md`, cannot approve work, cannot authorize merge-ready status.
- Design doc must contain intended future modes: Stdout orientation mode, Snapshot file mode, Compare/staleness mode, Design-only mode, and default mode writes no file.
- Design doc must contain intended future CLI shape: `tools/git/status_snapshot.py`, `--format text|json|markdown`, `--output`, `--repo-root`, `--include-deferred`, `--include-helper-inventory`, `--include-next-wp-candidates`, `--include-protected-boundaries`, `--max-deferred-items`, `--check-stale`, `--fail-on-stale`, `--fail-on-sensitive-hit`.
- Design doc must contain safe input sources: `AGENTS.md`, `CODEX_START_HERE.md`, `docs/project_status.md`, `docs/repo_truth_index.md`, `docs/deferred_items_log.md`, `docs/review_checklist.md`, `docs/testing_requirements.md`, `docs/security_and_secrets.md`, `docs/runtime_boundaries.md`, `docs/live_trading_authorization.md`.
- Design doc must contain prohibited input sources: `.env`, credential/private-key/wallet/mnemonic/token files, local account data, private endpoint responses, `local_data/` contents by default, generated reports/exports by default, arbitrary filesystem paths, network or GitHub API responses, chat history or user memory outside repo truth.
- Design doc must contain intended output fields: summary schema version, generated timestamp, repo commit SHA, branch, source repo-truth files used, current phase, latest merged WP, protected boundary status block, helper inventory, open deferred item digest, next WP candidate digest, stale snapshot warning, advisory-only note, repo-truth verification reminder, validation/human-review reminder.
- Design doc must contain sanitization model: `API_KEY`, `PRIVATE_KEY`, `CLOB_SECRET`, `CLOB_PASS_PHRASE`, `MNEMONIC`, `TOKEN`, `Bearer`, private-key blocks, redaction, not a replacement for gitleaks/semgrep.
- Design doc must contain staleness model: commit SHA, branch, generated timestamp, helper version/schema, input file list, current HEAD differs, required repo-truth files changed, schema unsupported.
- Design doc must contain snapshot lifecycle and storage policy: default no file generated, ignored `local_data/status_snapshots/`, never staged or committed, no tracked memory file, no durable project memory outside repo truth.
- Design doc must contain relationship to existing helpers: Diff/scope helper, Validation-output helper, Code blast-radius helper, none replace mandatory validation or review.
- Design doc must contain future implementation test plan sections for safe/prohibited input, output path restriction, status parsing, deferred item digest, helper inventory, next WP candidate extraction, stale snapshot metadata, sensitive-output redaction, no-network/no-command-execution/no-forbidden import, and Windows path handling.
- Design doc must contain open design questions and recommended next WP referencing WP36.
- `docs/repo_truth_index.md` must index the design doc; Authority Hierarchy must have no duplicate numeric prefixes and numbering must be sequential.
- `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` must reference the design doc.
- `docs/ai/codex/README.md` must reference the design doc.
- No implementation paths may exist: no `tools/git/status_snapshot.py`, no `tools/git/memory_snapshot.py`, no `tools/status_snapshot*`, no `tools/memory_snapshot*`, no tracked `local_data/status_snapshots/`, no `docs/ai/codex/MEMORY_STATUS_SNAPSHOT_HELPER.md`, no `src/agents/`, no `src/agent_layer/`, no `tools/hermes/`, no `agent_runtime/`, no `agent_memory/`.
- Dependency files must not add forbidden packages: OpenAI, Anthropic, LangChain, Hermes, token-savior, code-review-graph, tree-sitter, networkx, graphviz, chromadb, llama-index, mem0, rich, click, typer.

## WP34 Code Index / Blast-Radius Helper Implementation Tests

- `tools/git/code_blast_radius.py` must exist and be stdlib-only.
- CLI help exits 0 and mentions advisory/blast-radius behavior.
- Input validation: missing changed inputs → exit 2; absolute changed paths → exit 2; traversal → exit 2; invalid `--max-results` ≤ 0 → exit 2.
- Output path validation: `local_data/code_blast_radius/` → accepted; absolute path → exit 2; traversal → exit 2; outside dir → exit 2.
- Excluded paths (`.git/`, `local_data/`, `.venv-security/`, `.pytest_cache/`, `__pycache__/`, `.coverage`, `.claude/`) are skipped in filesystem scan.
- Sensitive files (`.env`, `.env.*`, `private_key`, `mnemonic`, `id_rsa`, `.pem`, etc.) are not read.
- Direct reference detection: path string and stem mentions in local text files detected correctly.
- Naming heuristic tests: `test_<module>.py` patterns suggested for changed files.
- Naming heuristic docs: docs files with matching stem suggested.
- Repo-truth relationship rules: `docs/repo_truth_index.md` → `docs/project_status.md`; `docs/project_status.md` → `docs/deferred_items_log.md`; `docs/ai/codex/` → README + TOKEN_EFFICIENCY_OPERATING_MODEL.md; `tools/git/` → `tests/tools/git/`; `tools/validation/` → `tests/tools/validation/`; `src/data_layer/` → tests + `docs/runtime_boundaries.md`.
- Protected/sensitive attention: `src/` flagged as protected-prefix; `tools/hermes/` flagged; `.env` flagged as sensitive; credential-like names flagged; `requirements.txt` flagged as dependency-lock.
- Generated output attention: `local_data/`, `.sarif`, `.coverage`, `security-scan-output/` flagged.
- Package-class warnings: docs-only touching `src/` → warning; local-tooling touching unrelated runtime → warning; dependency/lock change without dep class → warning; live-trading without auth file → warning.
- Text output: includes advisory-only note, validation reminder, human-review reminder, mode, schema version; no raw file dumps.
- JSON output: parseable, contains `summary_schema_version`, `mode`, `stale_index_status`, `changed_files`, `likely_tests`, `likely_docs`, `repo_truth_files_to_inspect`, `protected_boundary_attention`, `validation_reminder`, `human_review_reminder`, `advisory_only_note`.
- `--max-results` caps sections and records truncation notes.
- Exit 0: success (with or without protected hits unless `--fail-on-protected-hit`).
- Exit 1: protected hit + `--fail-on-protected-hit`.
- Exit 2: usage or config error.
- Optional output writes under `local_data/code_blast_radius/` only; JSON parseable after write.
- No `subprocess` import in helper source; no network library imports; no `os.system`.
- No network calls in tests.
- CLI smoke tests: basic text, JSON, prefix mode, strict protected-hit (exit 1), no output by default.
- AST import parsing: imports detected from .py files; syntax errors handled gracefully.
- `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER.md` must exist.
- `docs/repo_truth_index.md` must include both helper and design doc; numbering unique and sequential.
- WP30-D002 resolved; WP28-D001, WP30-D001, WP32-D001 remain OPEN; WP34-D001 added.

## WP33 Code Index / Blast-Radius Helper Design Tests

- `docs/ai/codex/CODE_INDEX_BLAST_RADIUS_HELPER_DESIGN.md` must exist.
- Design doc must contain required status fields: `DESIGN_ONLY`, `NOT_IMPLEMENTED`, `Claude Code and Codex`, `NO_RUNTIME_CHANGE`, `NO_TOOL_IMPLEMENTATION`, `NO_DEPENDENCY_CHANGE`, `NO_NETWORK`, `NO_VALIDATION_WEAKENING`, `NO_PROTECTED_BOUNDARY_CHANGE`.
- Design doc must contain intended future modes: On-demand scan mode, Snapshot/index file mode, Query mode, Design-only mode, and first implementation should prefer on-demand scan.
- Design doc must contain intended future CLI shape: `tools/git/code_blast_radius.py`, `--changed-file`, `--changed-prefix`, `--package-class`, `--include-tests`, `--include-docs`, `--include-protected-boundaries`, `--format text|json`, `--output`, `--max-results`, `--fail-on-protected-hit`, `--repo-root`.
- Design doc must contain relationship model terms: Direct references, Naming heuristics, Repo-truth relationships, Protected/sensitive relationships, confidence high/medium/low.
- Design doc must contain package-class awareness warnings.
- Design doc must contain stale-index model.
- Design doc must contain excluded paths and sensitive-content model.
- Design doc must contain validation-preservation rules.
- Design doc must contain future implementation test plan.
- Design doc must contain open design questions and recommended next WP.
- `docs/repo_truth_index.md` must index the design doc; Authority Hierarchy must have no duplicate numeric prefixes and numbering must be sequential.
- No implementation paths may exist: no `tools/git/code_blast_radius.py`, no `tools/git/code_index.py`, no `tools/code_index*`, no `tools/blast_radius*`, no tracked `local_data/code_index/`.
- Dependency files must not add forbidden indexing/dependency packages: RTK, OpenAI, Anthropic, LangChain, Hermes, token-savior, code-review-graph, tree-sitter.

## WP32 Validation Output Summary Helper Implementation Tests

- `tools/validation/validation_output_summary.py` must exist and be stdlib-only.
- CLI help test: `python tools/validation/validation_output_summary.py --help` exits 0.
- Metadata mode test: command + exit-code + check-type + stdout-text "878 passed, 1 warning" produces PASS with pass_count=878 and warning_count=1.
- Parser/stdin mode test: `--from-stdin` with pytest failure text produces FAIL summary and failure snippet.
- JSON output test: `--format json` produces parseable JSON containing `summary_schema_version`, status, counts, and validation reminder.
- Text output test: contains command, check type, status, counts, validation reminder, and raw log retention note; does not dump raw full logs.
- Pytest parser tests: parses passed/failed/error/warning counts from common lines; handles combined lines like "878 passed, 1 warning".
- Artifact guard parser tests: "Generated artifact guard passed" produces pass marker; failed/blocked output produces fail marker.
- Remote Main Sync Gate parser tests: passed output produces pass marker; stale/dirty/missing-required output produces fail marker.
- Security tool availability tests: all unavailable classifies as UNAVAILABLE; mixed passed + unavailable classifies as PARTIAL; any failed classifies as FAIL; all passed classifies as PASS; unavailable tools are never classified as PASS; invalid status exits 2.
- Missing evidence tests: no exit code and no output is ERROR; with `--fail-on-missing-required-evidence`, exit is nonzero.
- Failure snippet tests: includes meaningful failure lines; respects `--max-failure-lines`; sets truncated when truncated.
- Secret-like output tests: detects API_KEY, PRIVATE_KEY, Bearer token, PEM key; redacts matching values; does not echo raw secret; sets `secret_like_output_detected`; with `--fail-on-secret`, exits nonzero.
- Generated output path detection tests: detects `local_data/...`, `.json`, `.sarif` paths mentioned in output.
- Input path validation tests: accepts repo-relative `local_data/validation_summaries/inputs/<file>`; rejects absolute paths; rejects traversal; rejects paths outside allowed prefix; rejects `.env` and credential-like filenames.
- Output path validation tests: accepts repo-relative `local_data/validation_summaries/<file>.json`; rejects absolute paths; rejects traversal; rejects output outside `local_data/validation_summaries/`.
- No-network/no-command-execution/no-forbidden import tests: source must not import subprocess, requests, httpx, aiohttp, websockets, socket, openai, anthropic, langchain, hermes, py_clob_client; must not contain os.system, subprocess.run, eval(, exec(; must not contain trading execution terms.
- CLI smoke tests: metadata smoke exits 0; JSON smoke exits 0 and produces parseable JSON; stdin failure smoke exits 0 by default but status FAIL in summary; invalid output path exits 2; no output file written when `--output` not provided.
- All tests runnable locally with no live network.
- No test may write to real `local_data/` outside `tmp_path` fixtures.

## WP31 Validation Output Summary Helper Design Tests

- `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md` must exist.
- Design doc must contain required status fields: `DESIGN_ONLY`, `NOT_IMPLEMENTED`, `Claude Code and Codex`, `NO_RUNTIME_CHANGE`, `NO_TOOL_IMPLEMENTATION`, `NO_DEPENDENCY_CHANGE`, `NO_NETWORK`, `NO_VALIDATION_WEAKENING`, `NO_PROTECTED_BOUNDARY_CHANGE`.
- Design doc must contain intended future modes: parser mode, metadata mode, future runner mode, first implementation should prefer parser/metadata mode.
- Design doc must contain intended future CLI shape: `tools/validation/validation_output_summary.py`, `--command`, `--exit-code`, `--check-type`, `--stdout-file`, `--stderr-file`, `--from-stdin`, `--format text|json`, `--max-failure-lines`, `--tool-availability`, `--output`, `--fail-on-missing-required-evidence`.
- Design doc must contain intended input sources: explicit command string, exit code, stdout/stderr snippets or files, pytest result lines, generated artifact guard output, Remote Main Sync Gate output, security tool availability output, diff/scope helper output.
- Design doc must contain output fields: command, check type, exit code, status, pass count, warning count, unavailable tools list, generated output paths, failure snippet, truncation indicator, validation reminder, raw log retention note.
- Design doc must contain status classification rules: PASS, FAIL, SKIPPED, UNAVAILABLE, PARTIAL, ERROR; unavailable tools must not be summarized as passed; missing command result must not be summarized as passed.
- Design doc must contain validation preservation rules: focused tests, full pytest, generated artifact guard, Remote Main Sync Gate, security checks, git diff --check, human review, final PR comment; helper cannot authorize merge-ready status by itself.
- Design doc must contain future implementation test plan: pytest parser tests, artifact guard parser tests, sync gate parser tests, security tool state tests, status classification tests, truncation tests, secret-like output handling tests, JSON/text output tests, output path restriction tests, Windows path handling tests.
- Design doc must contain open design questions and a recommended next WP referencing WP32.
- `docs/repo_truth_index.md` must index the design doc; Authority Hierarchy must have no duplicate numeric prefixes.
- `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` must reference the design doc.
- `docs/ai/codex/CONCISE_REPORTING_RULES.md` must reference the design doc.
- `docs/ai/codex/VALIDATION_MATRIX.md` must reference the design doc.
- `docs/ai/codex/README.md` must reference the design doc.
- No implementation paths may exist: no `tools/validation/validation_output_summary.py`, no `tools/validation_output_summary.py`, no `tools/validation_summary*`, no `tools/command_output*`, no `tools/output_compression*`.
- No forbidden agent/runtime directories may exist: no `src/agents/`, no `src/agent_layer/`, no `tools/hermes/`, no `agent_runtime/`, no `agent_memory/`.
- Dependency files must not add forbidden dependencies: RTK, OpenAI, Anthropic, LangChain, Hermes, token-savior, code-review-graph, tree-sitter, rich, click, typer.

## WP30 Local Diff And Scope Summary Helper Implementation Tests

- Parser tests: added/modified/deleted/renamed files counted and grouped from `git diff --name-status` output.
- Scope classification tests: files matching `--allowed-file` and `--allowed-prefix` are in scope; files outside are warnings; no scope declared means no out-of-scope warning.
- Protected path tests: explicit `--forbidden-prefix` flags changed paths; built-in `tools/hermes/`, `.env`, credential/token-like names are flagged.
- Dependency/lock tests: `pyproject.toml`, `requirements.txt`, `uv.lock`, `package-lock.json`, `Cargo.lock`, and `*.lock` files are flagged.
- Generated artifact tests: `local_data/...`, `.venv-security/...`, `tools/.bin/...`, `security-scan-output/...`, `.sarif`, `__pycache__/...` are flagged.
- Package-class warning tests: docs-only/design WP touching `src/` warns; design WP touching `tools/` warns unless implementation/tooling package class; live-trading without `docs/live_trading_authorization.md` warns.
- Text output tests: includes changed file count, warnings, validation reminder, suggested review attention areas; does not include raw diffs.
- JSON output tests: parseable JSON; contains stable schema/version, base/head refs, counts, changed files, warnings, validation reminder.
- Output path restriction tests: accepts `local_data/diff_scope_summaries/<file>.json`; rejects outside allowed directory; rejects path traversal; rejects absolute path outside allowed directory.
- Exit code tests: default exits 0 with warnings; `--fail-on-warning` exits 1 with warnings; invalid CLI usage/config exits 2.
- No-network/no-forbidden import tests: source must not import requests, httpx, aiohttp, websockets, openai, anthropic, langchain, hermes, py_clob_client, socket; source must not contain trading execution terms.
- CLI help/smoke tests: `--help` exits 0; patched-git CLI test exits 0 and prints summary; JSON CLI smoke test produces parseable JSON with schema version.
- All tests runnable locally with no live network.
- No test may write to real `local_data/`.

## WP29 Diff Scope Summary Helper Design Tests

- `docs/ai/codex/DIFF_SCOPE_SUMMARY_HELPER_DESIGN.md` must exist.
- Design doc must contain required status fields: `DESIGN_ONLY`, `NOT_IMPLEMENTED`, `Claude Code and Codex`, `NO_RUNTIME_CHANGE`, `NO_DEPENDENCY_CHANGE`, `NO_NETWORK`, `NO_VALIDATION_WEAKENING`, `NO_PROTECTED_BOUNDARY_CHANGE`.
- Design doc must contain future helper constraints: standard-library only, local/offline/read-only, no dependency/lock-file changes, no network calls, no repo mutation, stdout summary by default.
- Design doc must contain intended future CLI shape: `tools/git/diff_scope_summary.py`, `--base`, `--head`, `--package-class`, `--allowed-file`, `--allowed-prefix`, `--forbidden-prefix`.
- Design doc must contain intended input sources: `git diff --name-status`, `git diff --stat`, `git diff --check`, allowed/forbidden path lists, repo-truth protected-path docs.
- Design doc must contain output fields: changed file count, files outside allowed scope, protected-path hits, dependency/lock-file changes, generated-artifact/local_data hits, package-class warnings, validation reminder.
- Design doc must contain package-class warnings: docs-only policy WP touching runtime source, design WP adding tools/source files, read-only public-data WP touching private/auth/client files, future live-trading package without live authorization update.
- Design doc must contain exit status design: `0`, `1`, `2`, and an explicit statement that exit status cannot bypass required validation.
- Design doc must contain future implementation test plan: fixture-based tests, protected path detection, dependency/lock-file detection, generated artifact detection, Windows path handling.
- Design doc must contain open design questions and a recommended next WP referencing WP30.
- `docs/repo_truth_index.md` must index the design doc; Authority Hierarchy must have no duplicate numeric prefixes.
- `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` must reference the design doc.
- `docs/ai/codex/README.md` must reference the design doc.
- No implementation paths may exist: no `tools/git/diff_scope_summary.py`, no `tools/diff_scope_summary.py`, no `tools/diff_summary*`, no `tools/scope_summary*`.
- No forbidden agent/runtime directories may exist: no `src/agents/`, no `src/agent_layer/`, no `tools/hermes/`, no `agent_runtime/`, no `agent_memory/`.
- Dependency files must not add forbidden dependencies: RTK, OpenAI, Anthropic, LangChain, Hermes, token-savior, code-review-graph, tree-sitter, rich, click, typer.

## WP28 Token Efficiency Operating Model Lock Tests

- `docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md` must exist.
- `docs/ai/codex/CONCISE_REPORTING_RULES.md` must exist.
- `docs/ai/codex/REUSABLE_WP_PROMPT_BLOCKS.md` must exist.
- Token-efficiency doc must contain: `ACTIVE_REPO_TRUTH_GUIDANCE`, `Codex and Claude Code`, `NO_VALIDATION_WEAKENING`, `NO_RUNTIME_CHANGE`, `NO_DEPENDENCY_CHANGE`, `NO_PROTECTED_BOUNDARY_CHANGE`, `context hygiene`, `validation-output summarization`, `reusable prompt blocks`, `future helper-tool design gates`.
- Concise-reporting doc must contain: `final PR comment remains mandatory`, `PR body does not replace final report`, `validation summary`, `Boundary check`, `Deferred items`, `Ready for review: YES/NO`, `unavailable tools`.
- Reusable prompt-blocks doc must contain: `Standard Preflight Block`, `Standard Security Check Block`, `Standard Validation Block`, `Standard Final Report Block`, `Standard Safety Boundary Block`, `Standard Generated Artifact Block`, `Standard Stop/Escalation Block`, `previous merge commit`, `forbidden scope`, `acceptance`, `failure criteria`.
- `AGENTS.md` must reference the token-efficiency operating model.
- `CODEX_START_HERE.md` must reference the token-efficiency operating model.
- `docs/ai/codex/README.md` must reference the new docs.
- `docs/codex_execution_guidelines.md` must reference the token-efficiency operating model.
- `docs/work_package_template.md` must reference the reusable prompt blocks.
- PR template must include concise-reporting / validation-summary checks without removing existing required checks.
- `docs/repo_truth_index.md` must index all three new docs.
- No `tools/token*`, `tools/diff_summary*`, `tools/code_index*` paths may exist.
- No `src/agents/`, `src/agent_layer/`, `tools/hermes/`, `agent_runtime/`, `agent_memory/` directory may exist.
- Dependency files must not add RTK, OpenAI, Anthropic, LangChain, Hermes, or similar dependencies.

## WP27 Agent/Hermes Manual Setup Decision Record Tests

- Decision record `docs/agent_hermes_manual_setup_decision_record.md` must exist.
- Decision record must contain required status fields: MANUAL_SETUP_DECISION_RECORD, NOT_INSTALLED_NOT_RUNTIME_DEPENDENCY, NOT_STARTED, FORBIDDEN, DISABLED, NOT_USED, NOT_GRANTED_FOR_AGENT_RUNTIME, NOT_GRANTED, DECISION_DEFERRED_PENDING_USER_SELECTION.
- Decision record must list current local advisory assets (WP23–WP26).
- Decision record must list candidate future runtime choices including Hermes, alternative runtime, no runtime, and deferred.
- Decision record must list manual user decisions required before any runtime setup.
- Decision record must list what Codex can safely prepare automatically in later WPs.
- Decision record must list what Codex must not do automatically.
- Decision record must list required future approval gates.
- Decision record must state the live-trading gate is separate and not satisfied by agent setup.
- `docs/repo_truth_index.md` must index the decision record.
- `docs/ai_agent_integration_policy.md` must reference the decision record or WP27.
- `docs/hermes_readonly_boundary.md` must reference the decision record or WP27.
- No `src/agents/`, `src/agent_layer/`, `tools/agents/`, `tools/hermes/`, `agent_runtime/`, or `agent_memory/` directory may exist.
- No dependency file may add Hermes, OpenAI, Anthropic, LangChain, or other agent runtime dependencies.
- No runtime/source/dependency/lock changes are expected for WP27.

## WP26 Read-Only Analyst Report Operator Runbook Tests

- Runbook must exist.
- Runbook must contain required exporter/report-generator commands.
- Runbook must contain output validation and git hygiene guidance.
- Runbook must contain safety, non-goals, and stop conditions.
- Runbook docs must be indexed in `docs/repo_truth_index.md`.
- `docs/agent_context_report_generator.md` must reference the runbook.
- No runtime/source/dependency/lock changes are expected for WP26.
- Tests must enforce no new Hermes, OpenAI, Anthropic, or agent runtime dependency markers in dependency files.

## WP25 Local Read-Only Analyst Report Generator Tests

- Report output must contain required report schema fields.
- Report mode must be `local_offline_read_only_report`.
- Input path validation must accept only `local_data/agent_context_exports/`.
- Output path validation must accept only `local_data/agent_context_reports/`.
- Default CLI behavior must write no file.
- Explicit Markdown and JSON output must stay under ignored `local_data/agent_context_reports/`.
- Tests must prove no network/client/auth/trading/Hermes/LLM dependency is added.
- Tests must prove no secret, credential, account, private endpoint, or raw forbidden material is included in report JSON.
- Tests must prove no strategy signal, trade proposal, recommendation, historical strategy evaluation, paper trading, or execution behavior is produced.
- Generated output must not be committed.

## WP24 Agent Context Exporter Operator Runbook Tests

- Runbook must exist.
- Runbook must contain required exporter commands.
- Runbook must contain output validation guidance.
- Runbook must contain git hygiene guidance.
- Runbook must contain safety, non-goals, and stop conditions.
- Runbook docs must be indexed in `docs/repo_truth_index.md`.
- `docs/agent_context_exporter.md` must reference the runbook.
- No runtime source, dependency file, package manager file, or lock file changes are expected for WP24.
- Tests must enforce no new Hermes, OpenAI, Anthropic, or agent runtime dependency markers in dependency files.

## WP23 Local Read-Only Agent Context Exporter Tests

- Export dictionary must contain all WP21 top-level schema fields.
- Export mode must be `local_offline_read_only`.
- Safety boundaries must confirm no live trading, no credentials, no execution, no Hermes runtime dependency, and no autonomous trading agent.
- Default exporter must read only fixed allowlisted tracked docs.
- Optional local report metadata must be metadata-only by default and limited to allowlisted ignored local paths.
- Output writer must accept only `local_data/agent_context_exports/`.
- Output writer must reject path traversal, arbitrary repo-root output, and non-allowed directories.
- CLI default must exit cleanly, write no file, use no network, and print the safety summary.
- CLI explicit output must write parseable JSON only under ignored `local_data/agent_context_exports/`.
- Tests must prove no secret, credential, account, wallet, token, or `.env` content is read.
- Source-boundary tests must keep network clients, official clients, AI-provider SDKs, scheduler libraries, and trading/execution functions out of the exporter and CLI.
- Generated output must not be committed.

## WP22 Codex Workflow Hardening Tests

- Workflow docs must exist.
- Workflow docs must contain mandatory sections.
- PR template must contain mandatory final-report, validation, generated-artifact, and project-status checkboxes.
- Work package template must contain package identity, package class, authorization basis, expected repo truth, exact changed-file set, stop triggers, final PR comment, and Ready for review fields.
- Tests must enforce new workflow docs are indexed in `docs/repo_truth_index.md`.
- Tests must enforce no runtime source, agent implementation, exporter implementation, Hermes tools, or report output paths are added.
- Tests must enforce no dependency or lock files add Hermes, OpenAI, Anthropic, or agent runtime dependencies.

## WP21 Agent Context Export Schema Tests

- Schema doc `docs/agent_context_export_schema.md` must exist.
- Tests must enforce required top-level schema sections are documented.
- Tests must enforce forbidden-use statements exist for credentials, account connection, private endpoints, order placement, signing, execution, scheduler, bot loop, network scanning, and autonomous parameter application.
- Tests must enforce provenance, redaction, staleness, and human-review statements.
- Tests must enforce no runtime/source/exporter paths are added.
- Tests must enforce no dependency files add Hermes, OpenAI, Anthropic, or other agent runtime dependencies.
- Tests must enforce repo-truth index records the new schema doc.
- No test may call the Polymarket network, AI-provider network, or Hermes network.

## WP20 AI-Agent Boundary Policy Tests

- AI-agent policy docs must exist.
- Hermes boundary doc must exist.
- Agent model registry must exist if created.
- Tests must enforce no AI-agent or Hermes execution authority.
- Tests must enforce Hermes is not installed as a dependency.
- Tests must enforce the fully autonomous trading agent is excluded for now.
- Tests must enforce allowed advisory roles are documented: read-only analysis, performance review, market research, strategy suggestion, and Codex / WP support.
- Tests must enforce forbidden capabilities are documented: autonomous order placement, autonomous order cancellation, autonomous parameter application, agent-controlled credentials, agent-controlled execution, and scheduler or bot loop.
- Tests must enforce no runtime/source agent implementation files are added.
- Tests must enforce accepted agent suggestions require human review, approved config changes, or normal Codex work-package flow.

## WP19 Guard-Aware Snapshot Quality Report Tests

- Tests must use local fake manifests only.
- No test may call the Polymarket network.
- No test may require credentials, authentication, or the official-client package.
- Markdown and JSON report outputs must include guard provenance summaries.
- Default quality CLI behavior must remain offline and write no files unless explicit output paths are provided.
- Network-used manifests without guard provenance must produce WARNING, not ERROR.
- Complete WP18-style guarded manifests must avoid the new guard warning codes.
- Source-boundary tests must keep network/client/auth/trading terms out of quality/reporting code.

## WP18 Guarded Manual Snapshot Capture Tests

- Guarded snapshot capture tests must use fake clients and injected clocks or guards.
- Default snapshot capture CLI tests must prove no network calls are made.
- Tests must prove `RateLimitGuard` is consulted before Gamma and optional CLOB reads.
- Tests must prove guard denial prevents fake client calls.
- Tests must prove market and order-book request counts are bounded by WP16 policy.
- No test may call the Polymarket network.
- No test may require credentials, authentication, or the official-client package.
- Source-boundary tests must keep scheduler, bot-loop, trading, auth, private endpoint, and non-stdlib network client terms out of the guarded capture path.

## WP17 Manual Read-Only Polling Runner Tests

- Runner tests must be offline by default using fake clients.
- CLI tests must prove default command makes no network calls.
- Tests must prove `--allow-network` is required before any public request path.
- Tests must prove guard denial prevents client calls.
- Tests must prove finite bounds are enforced.
- Tests must prove source contains no scheduler, while-true loop, time.sleep, official-client import, credentials, or trading/order behavior.

- Governance tests must verify required repo-truth files exist.
- No-live-default tests must verify live trading remains disabled unless explicitly authorized.
- Secret placeholder tests must flag real-looking credentials, private keys, mnemonic labels, and committed `.env` files.
- Future unit tests must cover strategy, risk, data, and utility behavior.
- Future integration tests must cover venue clients only after audit and approval.
- Future paper/live mode tests must prove mode separation.
- Future audit tests must validate source-repo audit artifacts and reuse decisions.
- Deferred-items tests must verify `docs/deferred_items_log.md` exists, required statuses are documented, required unavailable security/dependency tools are tracked, and every item row has status, priority, reason, required-before, and resolution condition fields.
- Architecture-boundary tests must verify WP3 architecture docs exist, `src/` contains README-only scaffolding, strategies cannot place orders directly, live trading remains disabled, and security tooling gates are documented before runtime dependency integration.
- Security tooling tests must verify required documentation and scripts exist.
- Security tooling script tests must verify tooling wrappers do not install packages or alter system state.
- Security tooling script tests must verify tooling wrappers do not authorize live trading.
- Remote main sync gate tests must verify the gate script exists, contains fetch, fast-forward pull, clean-worktree, `HEAD` to `origin/main`, previous-WP commit, and previous-WP file checks, and that repo-truth docs require the gate before WP branch creation.
- Security tooling completion tests must verify project-local security setup and verification scripts exist, local security-tool paths are ignored, forbidden global/system/user install commands are absent, and WP5 status docs record actual outcomes.
- Generated artifact guard tests must verify cleanup scripts are allowlist-only and refuse tracked or staged generated files.
- Security setup tests must verify `.venv-security/` ignore protection is checked before environment creation.
- Gitleaks gate tests must verify: `setup_project_gitleaks.py` and `verify_project_gitleaks.py` exist; `docs/gitleaks_secret_scan_gate.md` exists; `.gitignore` protects `tools/.bin/` and `security-scan-output/`; setup script checks ignore protection before writing; setup script contains no forbidden install commands (winget, choco, brew, apt, npm install -g, cargo install, pip install --user); setup script contains no trading/API/secret terms; `verify_project_gitleaks.py` exits 0; `run_available_security_checks.py` detects gitleaks project-local binary; `docs/security_tooling_status.md` references WP7; `docs/deferred_items_log.md` contains WP7 Gitleaks Secret Scan Gate Update.
- Official-client sandbox tests must be offline by default.
- Official-client sandbox tests must not require live network or package installation.
- Official-client sandbox tests must assert official client imports are absent from `src/`.
- Official-client sandbox tests must allow official client import strings only under sandbox tools, docs, and tests.
- Official-client sandbox tests must assert no project dependency file adds `py-clob-client-v2`.
- Official-client sandbox tests must assert setup script does not perform global/system install.
- Official-client sandbox tests must assert the network probe requires `--allow-network`.
- WP3-D001 may only be marked READY_FOR_WP in tests if scan evidence exists in the deferred items log or security tooling status.
- Read-only adapter tests (WP8+) must mock network; no automated test may require live network access.
- Network smoke tests must require explicit `--allow-network` opt-in; they must not be collected or run by pytest.
- Adapter boundary tests must confirm: no POST/PUT/PATCH/DELETE methods, no credentials, no private-key fields, no disallowed method names (place_order, create_order, post_order, submit_order, cancel_order, sign_order, execute_trade, trade, buy, sell), and no signing imports.
- Approved executable source scope under `src/data_layer/polymarket/` must not weaken tests blocking trading/execution code in other src/ directories.
- All tests must be runnable locally.
- Contract probe tool tests must be offline; no pytest test may require live network. (WP9+)
- Network validation tools must require `--allow-network` before making any network call. (WP9+)
- Response-shape parser changes must include offline fixtures or mocks covering both JSON-encoded string inputs and plain Python list inputs. (WP9+)
- Endpoint verification metadata tests must confirm: only WP9-probed endpoints are marked verified; CLOB /health remains unverified; verified entries carry verified_in_wp and verified_at_utc fields. (WP9+)
- Snapshot persistence tests must use tmp_path or temporary directories; no test may write to real local_data/. (WP10+)
- Snapshot capture CLI tests must not make live network calls; --allow-network gate must be tested offline. (WP10+)
- Snapshot files must be git-ignored and absent from all commits; tests must verify .gitignore includes local_data/. (WP10+)
- Snapshot writer must reject output paths not under local_data/; path validation must be tested with forbidden paths. (WP10+)
- No test may require actual Polymarket network access; all snapshot capture tests must use mocked adapter clients. (WP10+)
- Snapshot record tests must confirm read_only_provenance field is present and correct. (WP10+)
- No large raw API payload may be written to snapshot files; tests must verify raw_field_names is a list of strings, not a full dict. (WP10+)
- Snapshot reader/catalog/replay tests must use tmp_path fixtures; no test may write to real local_data/. (WP11+)
- Replay tests must be finite and must not use sleep or time delays. (WP11+)
- CLI inspection tests must not require live network; CLI must run cleanly with missing/empty input dir. (WP11+)
- No test may require actual Polymarket network access for replay/catalog tests. (WP11+)
- Catalog code must not import execution, strategy, or authenticated client modules. (WP11+)
- Quality/report tests must use tmp_path fixtures. (WP12+)
- Report output tests must not write to real local_data/. (WP12+)
- CLI quality report tests must not require live network. (WP12+)
- No test may require actual Polymarket network access for quality/reporting tests. (WP12+)
- Quality/reporting code must not import execution, strategy, authenticated client, or network modules. (WP12+)
- Dedup/export tests must use tmp_path fixtures or synthetic local records. (WP13+)
- Export output tests must not write to real local_data/. (WP13+)
- CLI export tests must not require live network. (WP13+)
- No test may require actual Polymarket network access for dedup/export tests. (WP13+)
- Dedup/export code must not import execution, strategy, authenticated client, or network modules. (WP13+)
- Deduplication must retain and report conflicts rather than silently merging them. (WP13+)
- Tests must assert no official client dependency is added in WP14. (WP14+)
- Tests must assert no `py_clob_client_v2` imports exist in source/runtime files. (WP14+)
- Tests must assert no credential/private-key/auth/order method names are introduced. (WP14+)
- Future official-client evaluation tests must be explicit-network only and no-credential until a later approved WP. (WP14+)
- Rate-limit guard tests must use injected clocks. (WP16+)
- Polling policy tests must be offline. (WP16+)
- No test may call Polymarket network. (WP16+)
- No test may require official-client sandbox package installation. (WP16+)
- Polling CLI tests must not use network. (WP16+)
- Any future polling runner must be explicit-network and bounded. (WP16+)

