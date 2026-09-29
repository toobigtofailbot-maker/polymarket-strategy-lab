# S10-NDFD-GRIB-01 Status

- WP: `S10-NDFD-GRIB-01` — NDFD GRIB2 Decoder Dependency Enablement
- Base: `3d3e3b673e53dae4d2e3b28a6816264b205bb015`
- Predecessor: PR #200 / `S10-ALPHA-REAL-01`, head `80faf1dcb32d760a15c5de3c008cd2aefa3a6f12`,
  MERGED at the base SHA (`isDraft=false`)
- Triggering blocker: S10-QUAL-DATA-01 source probe
  `SOURCE_COMPATIBILITY_BLOCKED:NDFD_DEPENDENCY_REQUIRED` (no GRIB2 template 5.3 decoder)
- Package class: `RUNTIME_DEPENDENCY_NDFD_GRIB2_ENABLEMENT`; size L
- Governance: RUNTIME, risk 3, capital at risk USD 0; no draftability certificate required
- Exact changed-file scope: 16; zero `src/` paths
- Branch: `codex/s10-ndfd-grib-01-eccodes`
- Readiness: `IMPLEMENTATION_READY` (governance track RUNTIME, minimum RUNTIME, 16 files,
  24 evidence items, 13 normative rules)
- Authorization: Karl's receipt of the exact package (no second go); merge separately gated
- Evidence mode: `PRIVATE_REPO_MANUAL_VERIFIED`
- PR: see GitHub PR metadata and PR body (created Ready for Review, never Draft).
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and
  non-self-referential; it does not encode dynamic PR metadata or the SHA of the commit
  containing itself.
- Merge authorized: NO

## Change

- `pyproject.toml`: one new optional extra `ndfd-grib` =
  `eccodes==2.48.0; python_version == "3.12"` and
  `eccodeslib==2.48.0.26; python_version == "3.12" and platform_system != "Windows"`.
  `requires-python`, the six base pins and the `test`/`cockpit` extras are unchanged; no lock file.
- `tests/fixtures/ndfd_grib/ndfd_pop12_reference.grib2`: first GRIB2 message (offset 80, length
  453433, SHA-256 `ecdac869039c2342f8a8ff8c57aa4fef602728e3257d0de7af5c091047c719ea`) of the official
  `noaa-ndfd-pds` object `wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046` (SHA-256
  `50ab9671f38381bb4799d8b7bb92fe82ab2af734506ca86925650a347852f5d4`, retrieved 2026-09-28 by one
  anonymous GET). Compatibility oracle only; not canonical research evidence.
- Focused test `tests/data_layer/analytical_research/test_ndfd_grib_dependency_compatibility.py`
  and contract-doc test `tests/test_ndfd_grib_decoder_dependency_contract_docs.py`; contract
  `docs/ndfd_grib_decoder_dependency_contract.md`.
- `.github/workflows/ci.yml`: new `ndfd-grib-compat` (ubuntu-24.04 and windows-2022, Python 3.12,
  strict, binary-only ecCodes family, pip check, exact versions, selfcheck, focused tests with zero
  skips) and `ndfd-grib-dependency-audit` (ubuntu-24.04 / Python 3.12 pip-audit over base closure plus
  the extra). Existing jobs unchanged.

## Decode Oracle

Templates 3.30 / 4.9 / 5.3 (spatial differencing order 2); discipline 0, category 1, number 8
(PoP12, probability above 0.254 mm); grid 2145 x 1377 (2953665 points); reference
2026-09-03T11:00Z; 12 h accumulation interval ending 2026-09-03T12:00Z; 1454641 missing /
1499024 valid; fixed point index 1846511 (nearest to KNYC) value 99; canonical decode fingerprint
`0b5e478b2fff21519adbe12a993f0f3106f449343640f0fb521e4e8f792653ec`.

## Local Pre-Push Evidence (non-authoritative; hosted CI is authoritative)

- Linux replica (Docker `python:3.12-slim`, eccodes 2.48.0 + eccodeslib 2.48.0.26 binary wheels,
  `NDFD_GRIB_STRICT=1`): focused test 27 passed, 0 skipped; `python -m eccodes selfcheck` reported
  ecCodes v2.48.0 and "Your system is ready."
- Windows sanity (local CPython 3.11 venv, eccodes 2.48.0 cp311 win_amd64 wheel; not a claimed
  target): header oracle and canonical fingerprint equal the Linux result; projected coordinates
  agree within 1e-14 degrees.
- Local Python 3.14 without the optional extra: focused test 13 passed, 0 skipped (decoder tests
  not collected by design).

## Capability Boundary

- `NDFD_GRIB_SUPPORTED`: ubuntu-24.04 / CPython 3.12; windows-2022 / CPython 3.12
- `NDFD_GRIB_NOT_CLAIMED`: Python 3.13, Python 3.14, macOS, ARM
- Global Python support remains 3.12–3.14 (unchanged).

## Authority Posture

- Implementation authority: YES (this exact RUNTIME dependency-enablement package)
- Dependency authority: exact `ndfd-grib` extra only; workflow authority: `.github/workflows/ci.yml` only
- Network: no product/runtime/API/account network; workflow network only for the Remote Main Sync
  Gate (git fetch), one bounded implementation-time official NOAA fixture GET, local PyPI installs
  for replica validation, branch push, Ready-for-Review PR publication and hosted-CI observation
- Credentials / scheduler / Hermes / strategy / paper / execution / live: NO
- S10-QUAL-DATA-01: NOT IMPLEMENTED by this WP (may be redrafted/resumed next, separately gated)
- QualificationCandidate created: NO; real qualification gate receipt: NONE
- WP170/WP172/WP173: NOT STARTED for this weather candidate
- Gate C: NOT AUTHORIZED; live: DISABLED; capital/orders: USD 0 / 0

## Deferred Items

- `S10-NDFD-GRIB-01-D001` — decoder capability claimed only for Python 3.12 on ubuntu-24.04 /
  windows-2022.
- `S10-NDFD-GRIB-01-D002` — the ecCodes message API is lenient about a missing end section; the
  successor adapter must keep the structural GRIB2 validation.
- The S10-QUAL-DATA-01 `NDFD_DEPENDENCY_REQUIRED` decoder blocker is recorded as
  `S10-NDFD-GRIB-01-D003`; it becomes resolved only after exact-head hosted decoder compatibility
  evidence is green.

## Scope Boundary

Changed files (exactly 16):
- `docs/ndfd_grib_decoder_dependency_contract.md`
- `docs/status_entries/S10-NDFD-GRIB-01.md`
- `docs/deferred_items_log.md`
- `docs/long_term_bot_completion_roadmap.md`
- `docs/project_status.md`
- `docs/repo_truth_index.md`
- `docs/security_tooling_status.md`
- `docs/wp_specs/S10-NDFD-GRIB-01/wp_prompt.txt`
- `docs/wp_specs/S10-NDFD-GRIB-01/wp_spec.json`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `tests/data_layer/analytical_research/test_ndfd_grib_dependency_compatibility.py`
- `tests/fixtures/ndfd_grib/ndfd_pop12_reference.grib2`
- `tests/test_ndfd_grib_decoder_dependency_contract_docs.py`
- `tests/test_project_status_docs.py`
- `tests/test_repo_truth_docs.py`
