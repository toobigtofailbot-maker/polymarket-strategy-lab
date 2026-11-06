# Hermes Cooperation and Grounded Citation Contract (S10-R3-HERMES-COOP-01)

Posture: `RESEARCH_ONLY`, `HUMAN_REVIEW_REQUIRED`. Receipt flags: `OFFLINE_RESEARCH_ONLY`,
`CITATION_INTEGRITY_NOT_FACT_TRUTH`, `ROLE_ORIGIN_NOT_VERIFIED`, `NO_PROVIDER_OR_TRADING_AUTHORITY`.

This operator checks two **caller-supplied** research submissions, one FORECASTER and one FALSIFIER, against one cold-verified S10-R3-SRC-01 grounding snapshot.

It never runs Hermes, `delegate_task`, a provider, a model, a web fetch or a socket. Two role submissions do not prove two real Hermes child runs or two independent models or humans. Every role row is `CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED` with `execution_provenance: ABSENT_NO_HERMES_INVOCATION`.

## Call path

```
python -B tools/alpha/run_source_grounding.py verify --scratch-dir <SRC01_SCRATCH>
python -B tools/alpha/run_hermes_cooperation.py run --grounding-scratch <SRC01_SCRATCH> --case <CASE.json> --scratch-dir <EMPTY_ABS_DIR>
python -B tools/alpha/run_hermes_cooperation.py verify --scratch-dir <EMPTY_ABS_DIR>
```

`run` performs these steps in order:

1. Copies the SRC-01 scratch into `inputs/grounding/` and the case bytes unchanged into `inputs/case.json`.
2. Calls the real `run_source_grounding.verify` on the frozen copy. The status must be `VERIFIED` and the receipt id must equal the case's `grounding_receipt_id`.
3. Rebuilds the admitted-source ledger through native `source_grounding.load_corpus`, `bind_rule_texts`, `evaluate_sources` and `join_alpha_candidates`.
4. Assesses every question and writes one write-once `receipt.json`.

`verify` reads only the frozen copies, re-runs the SRC-01 verify, recomputes the whole core and compares it.

The SRC-01 CLI is called, never edited. Its `code_identity()` hashes its own bytes, so editing it would break historical SRC-01 receipts. The test pins its git blob `49eb952984c50d5f38d1afd8e11ff90f14af2a33`.

Exit codes:

| Code | Statuses |
|---|---|
| 0 | `RUN_COMPLETE`, `VERIFIED`, `IDEMPOTENT_VERIFIED` (an identical repeat into the same scratch) |
| 1 | `STOPPED <reason_code>` (refusal) or `TAMPER_DETECTED` |
| 2 | `USAGE_ERROR` (sanitized, never echoes arguments) |

## Inputs and bounds

**Case file.** Schema `s10-r3-hermes-coop01-case-v1`, exact keys:

| Key | Constraint |
|---|---|
| `schema_id` | the schema above |
| `case_label` | label |
| `corpus_class` | equals the grounding's class |
| `grounding_receipt_id` | `srcground:sha256:<64hex>` |
| `as_of` | equals the grounding cutoff, canonical UTC |
| `benchmark_sha256` | see the freeze below |
| `questions` | 1 to 64 |

**Freeze.** `benchmark_sha256` is a self-commitment over the method ids, the 40-case minimum and every complete question (scope, labels, submissions, claims and quotes). It binds the case file to itself, and a mismatch stops the run with `BENCHMARK_FREEZE_MISMATCH`. It is not an external pre-registration: the external pre-method pin is the corpus SHA-256 asserted in the tests (below).

**Question.** Exact keys:

- `question_id`
- `market_id`: native SRC-01 corpus market.
- `candidate_id`: a native Alpha candidate joined to that market, or `null` (explicit absence).
- `source_cutoff`: at or before `as_of`.
- `rule_sha256`: must equal the native bound rule hash, or `null` when none is bound. A mismatch is `RULE_CONFLICT`.
- `source_allowlist`: at most 32 labels.
- `labels`: `{counterevidence_in_corpus, conflict_present}`, booleans.
- `submissions`: at most 4.

**Submission.** Exact keys:

- `role`: `FORECASTER` or `FALSIFIER`.
- `response_id`
- `declared_origin`: an opaque label or `null`. It is untrusted and never authenticated.
- `scope`: must equal the six question scope fields exactly.
- `native_draft`: `null` or a native Hermes draft.
- `claims`

**Claim.** `claim_id`, `proposition_id`, `stance` (`FOR`/`AGAINST`/`UNCERTAIN`), `text` (at most 1000 chars) and `citations`, each `{source_label, excerpt}` with excerpt length 12 to 500.

**Limits.**

| Bound | Value |
|---|---|
| Case file | 256 KiB |
| Claims per question | 64 |
| Citations per role | 16 |
| Grounding copy | 2000 files, 64 MiB |
| Source bytes | 2 MiB (SRC-01) |
| Run | 300 s |

The claim and citation limits are the prompt's per-case limits, applied to each question (one prompt "case" is one question). The 256 KiB bound covers the whole case file, which carries the 40+ question benchmark. At most 64 questions and 4 submissions per question are accepted.

**Whole-case refusals:**

- `SECRET_MATERIAL_REJECTED` (secret-shaped text anywhere).
- `FORBIDDEN_FIELD`: a credential, trade or control key (`prompt`, `tool`, `permission`, `stderr`, `command`, `delegat*`, `toolset`, `hermes_home`) anywhere outside a native draft.
- Unsafe paths: relative, symlink/reparse, hardlink, alias, secret directory, inside the repository or inside the scratch.
- An unverified or mismatched grounding.

Per-item defects are counted rows, never silent drops.

## Citation ledger and claim status

Only SRC-01 `ACCEPTED` sources enter the ledger. They are sorted by `source_label` and given `citation_index` 1..n. Each entry records:

- `citation_index` and `market_id`
- `raw_evidence_reference_id`, the native `RawEvidenceReference` id
- `content_sha256` and `byte_length`
- `capture_mode` (SRC-01 `PROSPECTIVE` or `LATER_IMPORT`)
- `evidence_bytes` (`AVAILABLE` or `EVIDENCE_BYTES_UNAVAILABLE`)
- `url_sha256`
- `source_origin: SOURCE_ORIGIN_UNVERIFIED`

SRC-01 sources that were not accepted are listed as unavailable with their native reason.

**Citation checks**, applied in this order. The first that fails decides the citation:

1. Fields invalid.
2. URL or path in the excerpt.
3. Not in the allowlist.
4. SRC-01 not accepted: `SOURCE_UNAVAILABLE`.
5. Unknown label.
6. Bytes unavailable: `SOURCE_UNAVAILABLE`.
7. Source bound to another market.
8. Not admissible at the question cutoff: `POST_CUTOFF`. `cutoff_refusal` re-applies SRC-01's own clock rules and the native `evaluate_replay_admissibility` at `source_cutoff`: `AVAILABLE_AFTER_CUTOFF` (published or public after it), `INGESTED_AFTER_CUTOFF` (a prospective capture ingested after it) or `NOT_ADMISSIBLE_AT_CUTOFF:<native basis>` (for example a later import without public availability, or a correction after the cutoff).
9. Excerpt not an exact UTF-8 substring of the frozen admitted bytes: `QUOTE_NOT_FOUND`.
10. Otherwise `SUPPORTED_QUOTE_PRESENT` with `quote_verified: true`.

**Claim status**, applied in this order:

1. Fields invalid, duplicate claim id, URL/path in the text: `UNSUPPORTED_OR_UNCITED`.
2. Instruction-shaped text or excerpt: `UNKNOWN`, `INSTRUCTION_SHAPED_CONTENT_NOT_EVIDENCE`. It is never acted on.
3. No citations: `UNCITED`.
4. Duplicate `(source, excerpt)` inside the claim: `DUPLICATE_CITATION`.
5. Otherwise the worst citation status, in the order `SOURCE_UNAVAILABLE` > `POST_CUTOFF` > `UNSUPPORTED_OR_UNCITED`.

A supported claim becomes `CONTRADICTED_BY_OTHER_ROLE` when the other role has a supported claim on the same `proposition_id` with the opposite stance.

**Separate fields:**

- syntax validity
- quote integrity (`quote_verified`)
- source origin (`SOURCE_ORIGIN_UNVERIFIED`)
- semantic fact verification (`NOT_AUTOMATICALLY_VERIFIED`)
- reviewer action (`HUMAN_REVIEW_REQUIRED`)

A matched quote proves byte correspondence with caller-local bytes only. It does not prove the document's public origin or the truth of the claimed implication. A source reused by both roles counts once in `distinct_quoted_sources`.

## Roles, native Hermes drafts and outcomes

**Native Hermes drafts.** A `native_draft` is passed unchanged to the native `models.validate_research_draft` with `expected_request_id = response_id`. Every draft source URL must be the frozen URL of an allowlisted admitted source.

- A rejection gives `NATIVE_DRAFT_REJECTED:<native code>`.
- An unsanctioned URL gives `NATIVE_DRAFT_SOURCE_NOT_SANCTIONED`.
- A scored claim citing a source the validated draft does not reference gives `NATIVE_DRAFT_CLAIM_SOURCE_UNBOUND`.

No Hermes policy, model, controller, runner or config is changed or executed. A validated draft is still caller-supplied.

**`baseline_single_role_v0`** is a construction for this benchmark, not a pre-existing production baseline. It is the FORECASTER submission alone, through the same citation checker.

**`two_role_cooperation_v1`** needs exactly one admitted FORECASTER and one admitted FALSIFIER. Otherwise it abstains:

- `ABSTAINED_MISSING_ROLE`, including a role with no claims (`ROLE_EMPTY`), which is never treated as silent agreement.
- `ABSTAINED_ROLE_INVALID`: an invalid submission, `SCOPE_MISMATCH`, `DUPLICATE_ROLE`, `SAME_RESPONSE_ID_BOTH_ROLES` or `SAME_DECLARED_EXECUTION_ORIGIN_BOTH_ROLES`.

**Outcome precedence:**

1. `QUESTION_INVALID`
2. `INCONCLUSIVE`: `RULE_CONFLICT`, `NO_VALID_CITATIONS` or `CLAIM_EVIDENCE_DEFECT`. Any unsupported, unavailable, post-cutoff or unknown claim triggers it.
3. `DISAGREEMENT_REVIEW_REQUIRED`
4. `CITATIONS_VERIFIED_REVIEW_REQUIRED`

There is no vote, no agreement-to-truth step, and no probability, value, strategy or authority.

## Receipt

The receipt has three fields: `core`, `provenance_manifest` and `receipt_id`.

- `provenance_manifest` is a native `ResearchProvenanceManifest` over the ledger reference ids and hashes.
- `receipt_id` is `hermescoop:sha256:` + SHA-256 of `{core, provenance_manifest}`.
- `non_identity` holds local CPU timings only.

`core.inputs.file_sha256` hashes every frozen file. Altering a receipt, case byte, grounding source or grounding receipt fails `verify`. A socket attempt stops the run with `NETWORK_ATTEMPT_BLOCKED`.

`authority` is all false or 0 except `research_only`.

## Frozen benchmark (SANITIZED_SYNTHETIC)

The corpus is defined inline in `tests/tools/alpha/test_hermes_cooperation.py` (`KINDS` + `QUESTIONS`), with SHA-256 `9dc3ab67413c4abf33ba322dedb3738df1595f3d893186c000ec9aaf64feae12`:

- 54 questions over 10 SRC-01 markets with 22 accepted sources (plus 1 SRC-01 `THIN_CONTENT` rejection).
- 52 eligible; 2 invalid (unknown market, non-native candidate).
- 44 validly paired, 7 comparison-only, 1 where both methods abstain.

| Measure (52 eligible) | baseline_single_role_v0 | two_role_cooperation_v1 |
|---|---|---|
| Evaluated / abstained | 51 / 1 | 44 / 8 |
| Claims (cited / uncited) | 51 (51 / 0) | 88 (87 / 1) |
| Citations, quote verified / false | 52, 47 / 2 | 88, 80 / 4 |
| Quoted claim coverage | 45/51 | 77/88 |
| Labelled conflicts found / missed (of 10) | 0 / 10 | 10 / 0 |
| Counterevidence surfaced / missed (of 23) | 0 / 23 | 21 / 2 |
| Outcomes | 44 verified-review, 7 inconclusive | 22 verified-review, 10 disagreement, 12 inconclusive |

The labels were authored with the corpus. A single role cannot disagree with itself, so the conflict and counterevidence differences hold by construction. They measure the checker's accounting, not research quality, real-world lift, latency, Brier score or profit. No real Hermes agent, provider or model was invoked.

## Capability status (all 36 ids kept)

**Advanced offline only by this WP:**

- `R3-05`: `OFFLINE_RESEARCH_COOP_FUNCTIONAL_NOT_REAL_HERMES_DELEGATION_INTEGRATED`
- `R3-05-CITATIONS`: `OFFLINE_CITATION_LEDGER_FUNCTIONAL_NOT_VALUE_VERIFIED`

Real delegated Hermes execution, provider cost and citation origin stay separately gated. See S10-R3-HERMES-COOP-01-D001 to D003.

**Unchanged by this WP:**

| Group | Ids | Status |
|---|---|---|
| Earlier merged offline source/forecast/learning | `R3-01`, `R3-01-SOURCE_ARCHIVE`, `R3-02`, `R3-06`, `R3-10`, `R3-10-WANG`, `R3-12`, `R3-12-SAMPLER` | Callable offline, no real lift |
| PR272 related-market bundle | `R3-03`, `R3-03-FEES`, `R3-04`, `R3-11`, `R3-19` | Conditional, no value |
| Provider-gated (six named provider decisions) | `R3-07`, `R3-07-ROUTER`, `R3-08`, `R3-09`, `R3-09-BOOK_GAPS`, `R3-13`, `R3-14` | Not activated |
| Native protocol/parity candidates (12) | `R3-15`, `R3-18`, `R3-20`, `R3-21`, `R3-22`, `R3-23`, `R3-24`, `R3-25`, `R3-26`, `R3-27`, `R3-28`, `R3-29` | Open; `R3-29` parity is not self-closed |
| Lane B, separate owner | `R3-16`, `R3-17` | Unchanged |

## Upstream method pins (adapted, no code copied, no dependency)

| Repository @ commit | File | Git blob | Use here |
|---|---|---|---|
| `NousResearch/hermes-agent` @ `345cd2b057a452236de401d3534b8502a7465e8d` | `tools/delegate_tool.py` | `272ae0971881c154a624fdfe1d5e3f1269ce9b16` | Parent/child role-result separation concept only. The upstream tool spawns real child agents; this operator never invokes it. |
| same | `skills/research/grounded-citations/SKILL.md` (MIT) | `97c4bce66391e88129287aa0a8f7ed75236ff513` | Ledger index allocation and literal-quote verification. The upstream ledger is mutable profile state; here it is one immutable receipt, and no `HERMES_HOME` is touched. |
