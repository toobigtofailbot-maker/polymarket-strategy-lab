# Validation Output Summary Helper

## 1. Status

- Helper status: LOCAL_OFFLINE_READ_ONLY_TOOLING_IMPLEMENTED
- Runtime impact: NO_RUNTIME_CHANGE
- Dependency impact: NO_DEPENDENCY_CHANGE
- Network impact: NO_NETWORK
- Command execution impact: NO_COMMAND_EXECUTION
- Validation impact: NO_VALIDATION_REPLACEMENT
- Protected-boundary impact: NO_PROTECTED_BOUNDARY_CHANGE

## 2. Purpose

The validation output summary helper summarises pre-captured validation command output
for Claude Code / Codex PR reports. It reduces final-report token usage by producing
compact, evidence-complete summaries of validation results without running validation
commands and without weakening any required validation.

The helper summarises evidence that already exists. It does not replace validation,
security checks, pytest, the generated artifact guard, the Remote Main Sync Gate,
or human review.

## 3. Commands

### Help

```
python tools/validation/validation_output_summary.py --help
```

### Basic metadata

```
python tools/validation/validation_output_summary.py \
  --command "python -m pytest" \
  --exit-code 0 \
  --check-type full-pytest \
  --stdout-text "878 passed, 1 warning"
```

### JSON output

```
python tools/validation/validation_output_summary.py \
  --command "python -m pytest" \
  --exit-code 0 \
  --check-type full-pytest \
  --stdout-text "878 passed, 1 warning" \
  --format json
```

### Stdin failure

```
python tools/validation/validation_output_summary.py \
  --from-stdin \
  --command "python -m pytest tests/example.py" \
  --exit-code 1 \
  --check-type focused-pytest
```

### Security tool availability

```
python tools/validation/validation_output_summary.py \
  --command "python tools/security/run_available_security_checks.py" \
  --exit-code 0 \
  --check-type security \
  --tool-availability gitleaks=unavailable \
  --tool-availability semgrep=unavailable \
  --tool-availability pip-audit=unavailable
```

### Optional output file (ignored path only)

```
python tools/validation/validation_output_summary.py \
  --command "python -m pytest" \
  --exit-code 0 \
  --check-type full-pytest \
  --stdout-text "878 passed, 1 warning" \
  --format json \
  --output local_data/validation_summaries/wp32_validation.local.json
```

## 4. CLI Flags

| Flag | Default | Description |
|---|---|---|
| `--command` | (none) | Exact command string (display/evidence only; never executed) |
| `--exit-code` | (none) | Integer exit code returned by the command |
| `--check-type` | `other` | Check classification: `full-pytest`, `focused-pytest`, `security`, `artifact-guard`, `sync-gate`, `smoke`, `diff-scope`, `git-check`, `other` |
| `--stdout-text` | (none) | Direct stdout text snippet |
| `--stderr-text` | (none) | Direct stderr text snippet |
| `--stdout-file` | (none) | File with captured stdout (must be under `local_data/validation_summaries/inputs/`) |
| `--stderr-file` | (none) | File with captured stderr (must be under `local_data/validation_summaries/inputs/`) |
| `--from-stdin` | off | Read command output from stdin |
| `--format` | `text` | Output format: `text` or `json` |
| `--max-failure-lines` | `30` | Max failure lines in snippet |
| `--tool-availability` | (repeatable) | Declare tool availability as `name=status` |
| `--output` | (none) | Write output to file (must be under `local_data/validation_summaries/`) |
| `--fail-on-missing-required-evidence` | off | Exit 1 if no exit code or output is provided |
| `--fail-on-secret` | off | Exit 1 if secret-like output is detected |

## 5. Exit Codes

| Code | Meaning |
|---|---|
| 0 | Summary generated successfully (even if summarised status is FAIL) |
| 1 | Strict condition triggered: `--fail-on-missing-required-evidence` or `--fail-on-secret` |
| 2 | Usage or configuration error (invalid output path, invalid tool status, etc.) |

**The helper exit code never replaces actual validation command exit codes.**
A `0` exit from this helper does not mean validation passed.
The validation reminder always appears in the output.

## 6. Output Interpretation

The summary includes:

- **command** — exact command string provided.
- **check type** — classification from `--check-type`.
- **exit code** — integer exit code or `unknown` if not provided.
- **status** — one of PASS / FAIL / SKIPPED / UNAVAILABLE / PARTIAL / ERROR.
- **counts** — passed, failed, error, and warning counts (when parseable).
- **unavailable tools** — tools declared as unavailable or skipped-not-available.
- **skipped tools** — tools declared as skipped or skipped-not-applicable.
- **failed tools** — tools declared as failed.
- **passed tools** — tools declared as passed or available.
- **generated output paths** — paths mentioned in the output.
- **failure snippet** — concise failure lines for diagnosis.
- **truncation indicator** — explicit flag when output was truncated.
- **secret-like output warning** — warning if secret-like content was detected and redacted.
- **validation reminder** — explicit statement that this summary does not replace required validation.
- **raw log retention note** — statement that full logs remain local and uncommitted.

## 7. Status Classification

| Status | Meaning |
|---|---|
| PASS | Exit code 0, no failure marker, no missing evidence, no secret trigger |
| FAIL | Exit code nonzero and not an unavailable/skipped case; or failure marker present |
| UNAVAILABLE | All relevant tools unavailable/skipped, no failure |
| PARTIAL | Mixed: at least one tool passed/ran and at least one was unavailable/skipped |
| SKIPPED | Check explicitly optional or not applicable |
| ERROR | Invalid input, missing mandatory evidence with strict flag, secret with strict flag, or internal inconsistency |

**Critical:** unavailable gitleaks/semgrep/pip-audit are never summarised as PASS.
Missing evidence (no exit code, no output) is never summarised as PASS.

## 8. Safety

- **Local only** — reads only provided text, stdin, or restricted local files.
- **Offline** — makes no network calls of any kind.
- **Read-only** — does not edit, stage, delete, or modify any file.
- **No command execution** — `--command` is display/evidence only; it is never executed.
- **No subprocess** — does not import `subprocess` or use `os.system`.
- **No network** — no HTTP, no DNS, no subprocess network calls.
- **No dependency** — Python standard library only; no pip install, no requirements change.
- **No mutation** — flags and reports only; never edits or stages files.
- **No secrets scanning replacement** — gitleaks and semgrep remain fully separate tools.
- **No validation replacement** — does not replace pytest, preflight tools, security checks,
  the Remote Main Sync Gate, the generated artifact guard, or human review.
- **No automatic approval** — helper output does not constitute PR approval.

## 9. Input Path Restriction

Files may only be read from repo-relative paths under `local_data/validation_summaries/inputs/`.
Absolute paths, path traversal (`..`), paths outside the allowed directory, and credential-like
filenames are all rejected with exit code 2.

The helper must not read `.env`, credential files, private keys, wallet files, token files,
or arbitrary repo files.

## 10. Output Path Restriction

The optional `--output` flag writes only under the git-ignored path
`local_data/validation_summaries/`. Output outside this directory is rejected with exit code 2.
Path traversal (`..`) is rejected. Absolute paths are rejected.

Generated output under `local_data/validation_summaries/` must never be committed or staged.

## 11. Non-Goals

- No PR approval or approval recommendation.
- No security scan replacement (gitleaks, semgrep, pip-audit replacement).
- No pytest replacement.
- No command runner (runner mode remains forbidden and unimplemented).
- No trading, execution, strategy, signal, or order authority.
- No agent runtime, Hermes, or LLM behavior.
- No network calls.
- No file mutation.
- No dependency changes.
- No generated artifacts committed to repo.

## 12. Design Decisions (resolved in WP32)

See `docs/ai/codex/VALIDATION_OUTPUT_SUMMARY_HELPER_DESIGN.md` Section 17 (WP32
Implementation Decisions) for the full record of how open design questions were resolved.

Key decisions:
- Parser + metadata mode implemented; runner mode remains forbidden.
- JSON output implemented; `--format text|json` flag available.
- Optional output restricted to repo-relative `local_data/validation_summaries/`.
- Secret-like output is detected and redacted; `secret_like_output_detected` flag set.
- Security subtool matrix distinguishes PASS / FAIL / PARTIAL / UNAVAILABLE.
- `--fail-on-secret` and `--fail-on-missing-required-evidence` strict flags available.
