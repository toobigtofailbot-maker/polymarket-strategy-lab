# S10-QUAL-B0X-01 Status

- WP: `S10-QUAL-B0X-01` — External-Reconstruction B0 Qualification Contract Extension
- Base: `ebd6f84c95e30451fe1c9ad431e405c57c113074` (execution base equals the drafting-time main SHA)
- Predecessor: PR #203 / `S10-QUAL-DATA-02`, head `b9e2e6995ee232720d0516b1fa234dec8bdac5e3`, MERGED at the base
  SHA (`isDraft=false`)
- Package class: `EXTERNAL_RECONSTRUCTION_B0_QUALIFICATION_CONTRACT`; size L in the machine spec (drafted S; the
  `tools/wp/wp_spec_guard.py` budget is S<=5 / M<=10 / L<=20 files and the frozen scope is 14 paths; scope, track,
  risk and authority unchanged; recorded as S10-QUAL-B0X-01-D001)
- Governance: FAST, risk 2, capital at risk USD 0; no draftability certificate required
- Exact changed-file scope: 14; dependencies/workflows unchanged
- Branch: `claude/clever-cori-rfw5lb` (the session-designated branch; suggested name
  `codex/s10-qual-b0x-01-external-b0-contract`)
- Readiness: `IMPLEMENTATION_READY` (governance track FAST, minimum FAST, 14 files, 24 evidence items,
  17 normative rules)
- Authorization: Karl's sending of the exact package is the implementation authorization; merge separately gated
- Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`
- PR: see GitHub PR metadata and PR body.
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and
  non-self-referential; it does not encode dynamic PR metadata or the SHA of the commit containing itself.
- Merge authorized: NO

Current S10-QUAL-B0X-01 state: IMPLEMENTED_READY_FOR_REVIEW

## Frozen Decision

- Qualification schema version: 1.0.0
- Canonical B0 rule unchanged: YES (`PIT_MARKET_PROBABILITY_V1`, canonical PIT, B2 additions `MARKET_PIT` only)
- External B0 rule: `EXTERNAL_PIT_MARKET_PROBABILITY_V1` (third-party reconstruction; B2 additions
  `MARKET_EXTERNAL_RECONSTRUCTION` only)
- External market feature class: `MARKET_EXTERNAL_RECONSTRUCTION` (appended after the unchanged canonical three)
- Both market classes reject in B1; mixed canonical/external B2 additions reject; B2 stays exact `B1 ∪ added`.
- Parameters: identical keys and bounds (`max_midpoint_spread` in [0, 1], nonnegative integer
  `max_last_trade_age_seconds`); identical midpoint / last-trade / unavailable fallback mechanics.
- Observability of the external rule: capture `timestamp_received <= decision_time`; the spread is recomputed from
  best bid/ask; `NOT_OBSERVED_IN_SEARCHED_HOURS` is never imputed; archive `Last-Modified` /
  `public_available_time` never backdates availability.
- No canonicalization/import bridge; external evidence is never `MARKET_PIT`, `SOURCE_KIND_CANONICAL_PIT`, a
  DatasetSnapshotReference or local-first-seen evidence.
- `__init__.py` unchanged: neither B0 rule constant is package-root exported; the already-exported
  `QUALIFICATION_FEATURE_SOURCE_CLASSES` exposes the additive class.

## Canonical Identity (bound before any source edit, R003)

- Canonical fixture candidate ID before: qualificationcandidate:sha256:6f94dec0c556d9a3574349e8696cee6fb128933cf393fb8da212f70adf075f21
- Canonical fixture candidate ID after: qualificationcandidate:sha256:6f94dec0c556d9a3574349e8696cee6fb128933cf393fb8da212f70adf075f21
- Canonical generic fixture candidate ID before/after:
  qualificationcandidate:sha256:cf99f3f902abd8e39278d026c83a0a770126f5fca3478068c6db979a1b4b0cd9
- Canonical serialized packet SHA-256 (sorted-key JSON) before/after:
  c6ba2d6d4a447f32d1eb42d2ac0de96c4734693e4e6b74fea5d07ef2fe177df5
- Canonical packet identity stable: YES (bound in `test_q31_canonical_identity_and_serialized_packet_unchanged`)

## Matrix Results

- External B0 + external B2: VALID (`test_q32`)
- External B0 + MARKET_PIT B2 rejection: FORECAST_PLAN_INVALID (`test_q33`)
- Canonical B0 + external B2 rejection: FORECAST_PLAN_INVALID (`test_q34`)
- Mixed B2 rejection: FORECAST_PLAN_INVALID under both rules (`test_q35`)
- External class in B1 rejection: FORECAST_PLAN_INVALID; MARKET_PIT in B1 still rejects (`test_q36`, `test_q18`)
- Unknown B0 literal rejection: FORECAST_PLAN_INVALID (`test_q37`)
- Parameter-bound parity: YES (every canonical invalid case rejects and both inclusive boundaries accept with
  identical normalized parameters under the external rule; `test_q38_*`)
- B2 != exact B1 ∪ added rejection: FORECAST_PLAN_INVALID (`test_q39`)
- No canonical backdating/relabeling: YES (`test_q40`, `test_q41_external_b0_is_additive_and_not_root_exported`)
- Gate admits an otherwise valid external-B0 candidate with dimensions identical to the canonical fixture and
  applies the existing evidence rules to shortfalls (`test_qualification_gate.py::test_q28`, `::test_q29`)
- Mutation check: relaxing the coupling to accept either market class fails `test_q33`, `test_q34` and both
  `test_q35` cases.
- Qualification gate source changed: NO
- WP170 source changed: NO
- DATA-02 source/operator changed: NO

## Validation

- Focused tests: `python -m pytest -q tests/data_layer/analytical_research/test_qualification.py tests/data_layer/analytical_research/test_qualification_boundaries.py tests/data_layer/analytical_research/test_qualification_gate.py tests/test_project_status_docs.py tests/test_repo_truth_docs.py` -> 541 passed
- Full suite: `python -m pytest -q` -> 12584 passed, 1 skipped (one authoritative run on candidate commit
  `f70ed91fd9755edac5b6cae19c26f08d8d68429d`; the only later change is this evidence line). An earlier attempt with the
  local virtualenv inside the worktree failed only `tests/test_no_secret_placeholders.py` on third-party
  `.venv/` test vectors; the virtualenv was moved outside the repository before the authoritative run.
- Readiness: `python tools/wp/wp_readiness_gate.py --wp docs/wp_specs/S10-QUAL-B0X-01/wp_prompt.txt --spec docs/wp_specs/S10-QUAL-B0X-01/wp_spec.json --repo-root .` -> IMPLEMENTATION_READY (FAST)
- Generated artifact guard: passed; `git diff --check ebd6f84c95e30451fe1c9ad431e405c57c113074`: clean
- Local security checks (`tools/security/run_available_security_checks.py`): gitleaks, semgrep and pip-audit
  SKIPPED_NOT_AVAILABLE in this environment (existing WP3-D001/WP3-D002 posture); npm/cargo not applicable. Not
  claimed as passed.
- Local environment: CPython 3.12 virtualenv outside the repository with the unchanged pinned dependencies
  (including the pinned cockpit extra used by hosted CI).

## Authority

- Network/data acquisition: NONE (workflow network only: git fetch/push, PR publication and installing the
  existing pinned dependencies into a local virtualenv outside the repository)
- QualificationCandidate real execution: NO
- Qualification gate real run: NO
- WP170/WP172/WP173: NOT STARTED
- Gate C/live/capital/orders: NO / DISABLED / USD 0 / 0
- Merge authorized: NO

## Successor

On a clean merge, return to Side14. Next expected package: S10-QUAL-REAL-01 (separately gated; not authorized by
this WP). Deferred: S10-QUAL-B0X-01-D002 (external B0 materialization belongs to S10-QUAL-REAL-01).
