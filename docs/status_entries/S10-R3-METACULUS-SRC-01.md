# S10-R3-METACULUS-SRC-01

RUNTIME/Risk3/L, exactly 12 paths. Branch `codex/s10-r3-metaculus-src-01` cut from clean synchronized main
`439dcfb49884e477b3bb9a48e588ca9dc833e137`.

- PR #278 is merged: head `4ea498407b8faa78da3373cab485e521b96c0886`, merge `439dcfb49884e477b3bb9a48e588ca9dc833e137`.
- PR #268 is open, separate and untouched.
- Karl's first-person bootstrap authorizes copying four pinned MIT files from
  `Metaculus/forecasting-tools@a54dd6443d19745b267e99a3b0b7627e74b9a57a` after the license, import-closure,
  security and source-hash audit, plus the eight native files.
- Merge: NO (Karl only).

## Readiness

- Prompt SHA-256 `c13d2636fa92e24bcda377acf6907cda2594f7e57a3952ef72e45b2bdfbc9233`, spec SHA-256
  `541f2562e8a43ff050dac640089bdcd4bdd2b2461a4287fef7fae04c731526ff` (package `SHA256SUMS.txt` verified).
- Native gate on those exact bytes on clean detached main, before the branch and any source change: exit 0,
  `IMPLEMENTATION_READY`, RUNTIME, certificate_required=false, scope 12, 8 evidence items, 8 normative rules.
  No wording repair was needed; the committed prompt and spec are byte-identical.
- Startup reads first; Ponytail LITE was the first actually invoked skill.

## Implementation

Contract: `docs/metaculus_source_archive_quality_contract.md`.

- **Source reuse:** the four upstream files were fetched at the pinned commit and checked against the upstream
  tree (Git blobs match the pins), MIT LICENSE reviewed, import closure stdlib + pydantic 2 + sibling modules
  only. Copied verbatim; nothing installed; no dependency change.
- **Loader:** six fixed module names (three empty package stubs, three verified leaf modules); the heavy upstream
  package initializer is never vendored or loaded; foreign modules are never overwritten.
- **Call path:** frozen copy of an SRC-01 scratch -> unchanged native `run_source_grounding.verify` (VERIFIED) ->
  native visible text -> genuine upstream `CaptureResult` + `quality.evaluate`, `url_hash`
  (`canonicalize_url`), `content_hash` -> per-source comparison with native status controlling ->
  content-addressed receipt -> cold verify with sockets blocked.
- **Authority:** RESEARCH_ONLY; `promoted_by_upstream` 0; `authenticated_web_evidence` 0; native SRC-01, PIT and
  Alpha modules byte-identical (SRC-01 code identity unchanged).

## Outcome (SANITIZED_SYNTHETIC SRC-01 world, 21 sources)

- 13 upstream-evaluated, 8 abstained (every reason counted).
- Agreement: 5 both-pass, 5 both-fail, 3 divergent (302 and 100 statuses and a login wall pass upstream but fail
  native). 0 upstream-fail/native-pass.
- URL identity: 11 distinct upstream `url_hash` over 13 rows; 2 aliases collapsed; 1 URL key spans two markets;
  1 dedup disagreement (upstream URL+content duplicate across markets that native keeps per market).
- Adoption: R3-01 / R3-01-SOURCE_ARCHIVE `SELECTIVE_UPSTREAM_CODE_REUSE_OFFLINE`,
  `OPERATIONAL_USEFULNESS_NOT_VERIFIED`, owner acceptance pending. The other 34 of 36 ids are unchanged. The
  R3-23 public GET stays unconsumed.

## Validation state

VALIDATED on implementation commit `99f8e81824c50b423f66b97f8a6fac7b1f136ca2` (after `6b2643b`); the next commit
changes only this status record. Exact-head hosted checks, evidence mode and the Ready decision belong in the PR body.

- **Native gates on `99f8e81`:** diff gate (`--check-diff --base origin/main --head HEAD`) exit 0, `IMPLEMENTATION_READY`,
  scope 12; exact-scope helper exit 0, 0 warnings; generated-artifact guard passed; ruff clean on the new code.
- **Named tests (Windows host, Python 3.14):** all 8 R001-R008 evidence-plan nodes pass. Native neighbours
  (source grounding, Oracle3 parity, related-market, architecture boundaries) 97 passed.
- **Full suite (Linux):** docker image `s10-canary-siwc-validation:20261024` (`/usr/local/bin/python`, Python 3.12.14,
  pydantic 2.13.5), `--network none --read-only`, tmpfs `/tmp` and HOME, disposable LF clone at `99f8e81` with
  `origin/main` = `439dcfb`: 14744 passed, 15 skipped, 0 failed. A first attempt reported 38 environment-only failures
  (git `safe.directory` ownership, missing `origin/main` ref, read-only repo mount); fixed in the harness, no code change.
- **Security:** independent security sub-review found nothing at confidence >= 8; boundary review BOUNDARY_INTACT;
  upstream blobs verified in the committed tree; no `.gitleaksignore`, scanner, CI, dependency or lockfile change.
