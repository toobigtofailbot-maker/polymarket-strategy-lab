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

- Plan: `docs/qualification_plans/S10-QUAL-PLAN-01/weather_plan_v1.json` (32148 bytes)
- Plan canonical: YES (UTF-8, sorted keys, compact separators, no binary float/NaN/Infinity, no trailing newline)
- Plan SHA-256: `d24cdc8ac75068b3bf7dc62c4fcf585d7cd381dd9203fac889f028620c4e69da` (sha256 of exact file bytes; not in its own preimage)
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
- Mechanical resolution: MR01-MR14 closed rules; no operator discretion
- Synthetic qualification-plan compatibility: YES (synthetic mechanical values resolve the static decisions into plan
  bodies accepted unchanged by the existing `build_qualification_candidate`, synthetic S10-QUAL-01 Alpha fixture only)

## Validation

- Focused tests: pending the stable candidate
- Full suite: pending the stable candidate
- Readiness --check-diff: pending the stable candidate

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
