# Metaculus Source-Archive Quality Reuse Contract (S10-R3-METACULUS-SRC-01)

Status: RUNTIME / Risk 3, offline research tooling. Adoption class `SELECTIVE_UPSTREAM_CODE_REUSE_OFFLINE` for
`R3-01` and `R3-01-SOURCE_ARCHIVE` only; owner acceptance: PENDING. Posture `RESEARCH_ONLY`.

- Vendored upstream files: `src/data_layer/analytical_research/metaculus_source_archive/`.
- Bridge: `src/data_layer/analytical_research/metaculus_source_archive_bridge.py`.
- Operator CLI: `tools/alpha/run_metaculus_source_archive_quality.py`.
- Tests: `tests/tools/alpha/test_metaculus_source_archive_quality.py`.

There is no product, provider or account network, no credential, no LLM or Hermes call, no fetcher, no store
write and no dependency change. Nothing here has source-admission, canonical-promotion, forecast, strategy,
paper, order, capital or live authority.

## Upstream-first decision

S10-R3-SRC-01 (`docs/source_grounding_contract.md`) adapted Metaculus source-archive quality ideas but never ran
Metaculus code. This WP runs the pinned upstream functions themselves on the bytes SRC-01 already froze:

- `quality.evaluate(models.CaptureResult(...))` (HTTP status, `MIN_TEXT_LEN` 200, `BLOCK_SIGNATURES`);
- `models.url_hash`, which calls `canonicalize.canonicalize_url`, plus `canonicalize_url` directly;
- `models.content_hash` and the `CaptureResult.content_hash` property.

The full `forecasting-tools` distribution is **not** installed. Its `source_archive/__init__.py` imports
cloud storage, browser fetchers and pipeline modules; that file is never vendored or loaded. `pydantic` 2.x is
already present as a transitive dependency of the pinned `polymarket-client==0.10.0` (`pydantic>=2,<3`);
`pyproject.toml` and the lockfile are unchanged.

## Source pins (byte-identical; Git blob verified before every execution)

Upstream is `Metaculus/forecasting-tools` at commit `a54dd6443d19745b267e99a3b0b7627e74b9a57a`, license MIT
(`Copyright (c) 2024 CodexVeritas`; the LICENSE file is vendored unmodified).

| Vendored file | Upstream path | Git blob SHA-1 |
|---|---|---|
| `LICENSE` | `LICENSE` | `95ca3360578732e0f3287fad707e029303427eec` |
| `canonicalize.py` | `forecasting_tools/agents_and_tools/source_archive/canonicalize.py` | `7d722c69940f736b2921629de2eb8da191d3f920` |
| `models.py` | `forecasting_tools/agents_and_tools/source_archive/models.py` | `08c63cd62764ae9f1b4dad7f1d40a8cd295ab2c1` |
| `quality.py` | `forecasting_tools/agents_and_tools/source_archive/quality.py` | `0bed34975731ae24c1a2e7222e29859ad08b5fb4` |

Import closure (checked statically from the AST before any byte executes):
`canonicalize.py` imports `urllib.parse`; `models.py` imports `hashlib`, `datetime`, `typing`, `pydantic` and the
vendored `canonicalize`; `quality.py` imports `pydantic` and the vendored `models`. Any drift, dynamic import or
extra file in the vendor directory (for example a planted `__init__.py`) stops the run.

## Loader

`load_upstream` registers exactly six module names: the package stubs `forecasting_tools`,
`forecasting_tools.agents_and_tools` and `forecasting_tools.agents_and_tools.source_archive` (each with an empty
`__path__`, so no other upstream file can be imported), and the three leaf modules executed from the verified
bytes. There is no `sys.path` change, import hook, environment read or bytecode write. A foreign module already
registered under any of the six names is never overwritten (`UPSTREAM_ALIAS_COLLISION`), and a failed load
unregisters everything it added.

## Call path

`run --src-scratch DIR --scratch-dir DIR`:

1. Copy the caller's SRC-01 scratch (regular single-link files only; size/count bounded) into the empty
   absolute scratch outside the repository.
2. Unchanged native `run_source_grounding.verify` on the copy must return `VERIFIED`.
3. Read `frozen_case.json`, `receipt.json` and `inputs/sources/NNN.bin` read-only. File names come only from the
   native frozen-case regex; every read is re-hashed against the native receipt.
4. Per source, the bridge builds the upstream `CaptureResult` with `url = final_url =` the frozen URL,
   `status_code =` the frozen HTTP status, `markdown =` native `source_grounding._visible_text`, and
   `fetched_at =` the native ingestion clock (never wall time). Upstream `evaluate` is then called.
5. One content-addressed receipt (`mcsrcqual:sha256:`) is written once.

`verify --scratch-dir DIR` re-verifies the native SRC copy, re-invokes the real upstream code with every socket
entry point blocked, and compares every core field. Identical replay returns `IDEMPOTENT_VERIFIED`; changed SRC
bytes or a partially written scratch refuse with `SCRATCH_NOT_EMPTY`.

## Decision table

Only sources the native gate evaluated for quality (`ACCEPTED`, `QUALITY_FAILED`, `DEDUPED`) reach upstream.

| Native outcome | Upstream verdict |
|---|---|
| Rejected before quality (fields, duplicate label, market, URL safety, empty, bytes changed, clocks, admissibility) | `ABSTAINED`, reason `NATIVE_PRE_QUALITY_REFUSED:<native reason>` |
| `QUALITY_FAILED` / `INVALID_BYTES` (invalid UTF-8 or NUL) | `ABSTAINED`, `INVALID_UTF8_OR_NUL` |
| Secret-shaped text in the source bytes | `ABSTAINED`, `SECRET_SHAPED_CONTENT` |
| Otherwise | `UPSTREAM_EVALUATED`, with `agreement` one of `AGREE_PASS`, `AGREE_FAIL`, `UPSTREAM_PASS_NATIVE_FAIL`, `UPSTREAM_FAIL_NATIVE_PASS` |

The native status and reason are copied verbatim into every row and remain controlling. An upstream pass never
makes a source `ACCEPTED` (`promoted_by_upstream` is always 0). Known, visible differences:

- upstream fails only `status_code >= 400`, so 1xx, 3xx and absent statuses pass upstream; native passes 2xx only;
- upstream has no login or paywall rule; native fails `LOGIN_WALL`;
- native rejects URLs carrying a `#fragment` or credential-shaped query keys before quality; upstream would
  canonicalize them.

## URL and content identity

Upstream `url_hash` (canonical URL: lowercase scheme and host, default port dropped, fragment dropped,
tracking parameters dropped, remaining query sorted, trailing slash removed) is reported separately from native
URL safety and native per-market content dedup. Receipt counters include `distinct_url_hash`,
`url_alias_collapsed`, `url_hash_spans_markets`, `upstream_url_content_duplicates`, `native_deduped` and
`dedup_disagreements`. Upstream `content_hash` over the raw bytes must equal the native SHA-256.

## Output hygiene

Receipts and CLI output carry hashes, labels, market ids, statuses and counts only: never a source URL, body
text, local path or credential. Refusals are stable codes; exception text is never echoed.

## Program commitments

All 36 program capability ids (R3-01 to R3-29 plus R3-01-SOURCE_ARCHIVE, R3-03-FEES, R3-05-CITATIONS,
R3-07-ROUTER, R3-09-BOOK_GAPS, R3-10-WANG, R3-12-SAMPLER) stay tracked; only R3-01 and R3-01-SOURCE_ARCHIVE
change class. The pinned PR #277 public GET (R3-23) stays UNCONSUMED and needs a separate owner instruction.
PR #268 stays separate and untouched. Operational usefulness is NOT_VERIFIED; owner acceptance: PENDING.
