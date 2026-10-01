# S10-QUAL-PLAN-01 Status

- WP: `S10-QUAL-PLAN-01` — Weather Qualification Prospective Plan Freeze
- Base: `e2edb21e25e7841376c3cb51c27a622fbc0cbc83` (execution base equals the frozen base)
- Predecessor: PR #204 / `S10-QUAL-B0X-01`, head `debcfdf723505b67a1280ac9f303d5abd293c998`, MERGED at the base SHA
  (`isDraft=false`)
- Package class: `WEATHER_QUALIFICATION_PROSPECTIVE_PLAN_FREEZE`; size L; governance FAST, risk 2, capital at risk
  USD 0; no draftability certificate required
- Exact changed-file scope: 13 (docs/tests only); src/tools/workflows/dependencies unchanged
- Branch: `claude/great-clarke-fkezb8` (the session-designated branch; suggested name
  `codex/s10-qual-plan-01-weather-plan-freeze`)
- Readiness: `IMPLEMENTATION_READY` (governance track FAST, minimum FAST, 13 files, 34 evidence items,
  27 normative rules)
- Authorization: Karl's sending of the exact package is the implementation authorization; merge separately gated
- Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`
- PR: see GitHub PR metadata and PR body.
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and
  non-self-referential; it does not encode dynamic PR metadata or the SHA of the commit containing itself.
- Merge authorized: NO

Current S10-QUAL-PLAN-01 state: IMPLEMENTED_READY_FOR_REVIEW

## Frozen Plan

- Plan: `docs/qualification_plans/S10-QUAL-PLAN-01/weather_plan_v1.json` (35583 bytes)
- Plan canonical: YES (UTF-8, sorted keys, compact separators, no binary float/NaN/Infinity, no trailing newline)
- Plan SHA-256: `3b2a99abea8bbd18794c8117d6c1ab696ac817217cd5713367b2ee9a76aa9463` (sha256 of exact file bytes; not in its own preimage)
- Power analysis: `docs/qualification_plans/S10-QUAL-PLAN-01/power_analysis_v1.md`, LF-normalized SHA-256
  `f20f24a26444c93389b10a34ed1a88530aca0f64bc7efb694dccce826c6ee884` (bound inside the plan)
- OOS start: 2026-10-15T00:00:00Z
- Freeze deadline: 2026-10-14T00:00:00Z (GitHub server merge timestamp on main plus merge SHA; a later merge is
  `OOS_START_FREEZE_WINDOW_MISSED`)
- 120-day cap: 2027-02-12T00:00:00Z
- DATA-02 dates: permanently `HISTORICAL_NON_OOS`
- Hypothesis frozen: YES (`nws-public-weather-incrementality` / `v1`, REVIEWED; Alpha lineage and AF1 receipt bound;
  research question and falsifiable theme preserved; registry not mutated)
- B0 frozen: YES (`EXTERNAL_PIT_MARKET_PROBABILITY_V1`, spread `0.1`, trade age `86400`, unclipped scoring)
- B1/B2 features frozen: YES (B1 `wx.ndfd_pop12_max_climate_day_v1` + `time.ndfd_lead_hours_v1`; B2 adds
  `mkt.ext_b0_probability_v1`; B2 = B1 ∪ added)
- Label frozen: YES (`label.polymarket_nws_cli_rain_yes_v1`, CLI >= 0.01 inch, trace excluded)
- Forecast model frozen: YES (Firth logistic B1/B2, all-zero init, tolerance 1e-10, max 100 iterations,
  `FIT_FAILED` without fallback)
- Hyperparameter search: NONE; post-hoc calibration NONE; randomness NONE; search space `{}`
- Random seeds frozen: `[]`
- Formation floor: >= 385 structurally eligible rows and >= 20 effective dates (Riley criterion iii; EPV10 unused)
- Selection floor: last 7 eligible historical dates, >= 5 effective after purge/embargo; 100 rows per role
- OOS target: 50 effective prospective target dates (power 0.8, one-sided alpha 0.025, dz 0.5, rho1 0.25, VIF 1.5)
- Brier/test family frozen: YES (Brier primary, log-loss diagnostic, B2 LTE 0.25; fixed sequence B2-B0, B2-B1, B1-B0 at
  one-sided FWER 0.025; FAMILY_TRIAL_COUNT, family size 3)
- Execution-evidence meaning frozen: YES (never backdated; DATA-02 CURRENT_ONLY stays CURRENT_ONLY)
- DATA-03 seal/exposure rules frozen: YES (`oosmembership:sha256:` preimage exact; `QUAL_OOS_INSUFFICIENT_AT_CAP`)
- WP170 handoff frozen: YES; WP170 remains sole preregistration/OOS authority: YES
- Label finality: prospective markets without terminal agreeing final-label evidence are `PENDING_LABEL_FINALITY`
  (no elapsed-time label deadline); D1..D50 sealed only on a stable chronological prefix; the cap is not a
  label-resolution timeout
- Mechanical resolution: MR01-MR15 closed rules; no operator discretion; WP170 samples are exactly the surviving
  FORMATION/SELECTION rows plus the sealed OOS rows (MR15)
- Independent exact-head review of `611e91e`: CHANGES_REQUIRED (1 blocking: WP170 sample set undefined); re-review
  of `8a13415`: CHANGES_REQUIRED (1 blocking: formation shortfall wording said "effective" instead of "structurally
  eligible" rows); both repaired in
  this WP by MR15, the `QUAL_OOS_ROWS_INSUFFICIENT` terminal, explicit shortfall rules, the historical exclusion code
  and the log-loss clip scope; the plan was re-hashed. Re-review of `9a1cfc4` (superseded plan hash
  `1124ecfb528e5055e4193a885e89a5d9bde74df501b48a0ca4ebded8df89c46e`): APPROVE. Side14 same-WP correction v2 then
  removed the unauthorized 7-day label deadline, froze `PENDING_LABEL_FINALITY` and the stable-prefix rule, and set
  S10-QUAL-DATA-02-D005 to `FROZEN_FOR_S10_QUAL_PLAN_01`; the earlier approvals and CI are historical and superseded
  by the corrected head's own review and CI (see the PR body). Review of `8e10491` (superseded plan hash
  `519f2b010b7523a02ea08ad451ff9f322fa2b6ea0557ed1aef815525a66f1316`): APPROVE with one non-blocking finding (the
  outcome rule still said "absence excludes"), repaired by aligning `outcome_source_rule` with the pending state;
  the governed prompt records correction v2 in section 17.6
- Synthetic qualification-plan compatibility: YES (synthetic mechanical values resolve the static decisions into plan
  bodies accepted unchanged by the existing `build_qualification_candidate`, synthetic S10-QUAL-01 Alpha fixture only)

## Validation

- Focused tests: `python -m pytest -q tests/data_layer/analytical_research/test_qualification_weather_plan_freeze.py tests/test_project_status_docs.py tests/test_repo_truth_docs.py` -> 295 passed
- Full suite: `python -m pytest -q -p no:cacheprovider` -> 12632 passed, 1 skipped (authoritative run on corrected candidate commit
  `ea09a2f`; the only later change is this evidence section; superseded candidates `ac3cb25`, `d7beadc` and `d42cdd2` each passed 12631 / 1 skipped)
- Readiness: `python tools/wp/wp_readiness_gate.py --wp docs/wp_specs/S10-QUAL-PLAN-01/wp_prompt.txt --spec docs/wp_specs/S10-QUAL-PLAN-01/wp_spec.json --repo-root .` -> IMPLEMENTATION_READY (FAST)
- Readiness --check-diff: `python tools/wp/wp_readiness_gate.py --wp docs/wp_specs/S10-QUAL-PLAN-01/wp_prompt.txt --spec docs/wp_specs/S10-QUAL-PLAN-01/wp_spec.json --repo-root . --check-diff --base e2edb21e25e7841376c3cb51c27a622fbc0cbc83 --head HEAD` -> IMPLEMENTATION_READY (FAST), error_codes [], exact 13 / 13 changed paths
- Generated artifact guard: passed; `git diff --check e2edb21e25e7841376c3cb51c27a622fbc0cbc83`: clean
- Local security checks (`tools/security/run_available_security_checks.py`): gitleaks, semgrep and pip-audit
  SKIPPED_NOT_AVAILABLE in this environment (existing WP3-D001/WP3-D002 posture); npm/cargo not applicable. Not
  claimed as passed.
- Local environment: CPython 3.12 virtualenv outside the repository with the unchanged pinned dependencies
  (including the pinned cockpit extra used by hosted CI).

## Authority

- PreregisteredExperiment created: NO
- QualificationCandidate created: NO
- Qualification gate run: NO
- Data accessed: NO
- Product/source network: NONE (workflow network only: git fetch/push, PR publication and installing the existing
  pinned dependencies into a local virtualenv outside the repository)
- qualification.py / qualification_gate.py / experiment_os.py / DATA-02 source-operator changed: NO
- WP170/WP172/WP173: NOT STARTED
- Gate C/live/capital/orders: NO / DISABLED / USD 0 / 0
- Merge authorized: NO

## Successor

If this WP merges at or before 2026-10-14T00:00:00Z, return to Side14. Next expected package: S10-QUAL-DATA-03 —
Prospective Weather Qualification OOS Accrual + Execution-Terms Capture (separately gated; not authorized by this WP).
S10-QUAL-REAL-01 only after 50 effective prospective dates and a valid membership seal. Deferred:
S10-QUAL-PLAN-01-D001..D005.
