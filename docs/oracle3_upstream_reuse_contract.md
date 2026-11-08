# Oracle3 Upstream Selective Code Reuse Contract (S10-R3-ORACLE-UPSTREAM-01)

Status: RUNTIME / Risk 3, offline research tooling. Adoption class `SELECTIVE_UPSTREAM_CODE_REUSE` for `R3-03`
and `R3-03-FEES` only. Posture `RESEARCH_ONLY`. Every result is conditional and never tradable.

- Vendored upstream files: `src/data_layer/analytical_research/oracle3/`.
- Bridge: `src/data_layer/analytical_research/oracle3_upstream_bridge.py`.
- Operator CLI: `tools/alpha/run_oracle3_upstream_parity.py`.
- Tests: `tests/tools/alpha/test_oracle3_upstream_parity.py`.

There is no product, provider or account network. The package needs no credentials and makes no LLM or Hermes call. It
has no strategy, paper, order, capital, executable-edge or live authority, writes to no store and adds no dependency.

## Upstream-first decision

This WP takes upstream code, not just upstream ideas. The pure-math core of Oracle3 is copied verbatim and called directly.

The full upstream Poetry project is **not** installed. It pulls in `py-clob-client`, `kalshi-python`, `openai-agents`,
`mcp` and auth/trading clients that this offline scope does not need. `pyproject.toml` and the lockfile are unchanged.

The native S10-R3-REL-01 implementation (`docs/related_market_alpha_contract.md`) stays the only economic authority,
and none of its modules change. Oracle3 is an independent comparison that runs on the evidence REL-01 already verified.

## Source pins (all five files byte-identical, Git blob verified before execution)

Upstream is `YichengYang-Ethan/oracle3-prediction-market-agent` at commit `267fb7c48dae7c4ff8922c02a3a223443e51bf0b`
(package version `1.2.2`).

| Vendored file | Upstream path | Git blob SHA-1 |
|---|---|---|
| `oracle3/__init__.py` | `oracle3/__init__.py` | `7975dfeb618a1b84f4351adea496aef9aa9b843b` |
| `oracle3/arbitrage.py` | `oracle3/arbitrage.py` | `4805d572b55ce6547c9c46ab92a2aa4ce90de808` |
| `oracle3/fees.py` | `oracle3/fees.py` | `24624f84d40a43610302f7b8c3d17c347fa62e0c` |
| `oracle3/LICENSE` | `LICENSE` | `0a1f3263b67e7fbc96d62f30563f2ef61bb57661` |
| `oracle3/NOTICE` | `NOTICE` | `39dd4d41d44d48f6f62163578909c407cd08a78d` |

Upstream `tests/test_arbitrage.py` (blob `09a80229170cf1a345632e5850d30b3a6e8c6b45`) and `tests/test_fees.py` (blob
`ca8b7100f7129d982ff3e6f86f19dca2d9b25b8a`) are references only. Their vectors are re-derived in the native test
file; the files themselves are not vendored.

**License review.**

- `LICENSE` is the Apache License 2.0. It has minor wording differences from the apache.org text and no APPENDIX; the
  terms are unchanged.
- `NOTICE` (Copyright 2026 Yicheng Yang) declares MIT-licensed ancestry from `ulab-uiuc/oracle3` and from the bundled
  `coinjure` (Copyright (c) 2024 Haofei Yu), and reproduces the MIT text. Changes after 2026-02-28 are under Apache-2.0.
- Both files are kept verbatim next to the code, which satisfies Apache §4(a)/(d) and the MIT notice condition.

**Import closure.**

- `fees.py` imports only the stdlib: `collections.abc`, `dataclasses`, `decimal`, `typing`.
- `arbitrage.py` imports the stdlib (`math`, `dataclasses`, `decimal`, `typing`) plus `oracle3.fees`.
- `__init__.py` only declares `__version__`.
- No file opens files, sockets, subprocesses or dynamic imports.

## Package alias (the only loader)

The upstream `arbitrage.py` line `from oracle3.fees import FeeSchedule, default_schedule` stays unmodified.
`oracle3_upstream_bridge.load_upstream()` does the following:

1. It reads all five files from the fixed directory next to the bridge. Each must be a regular, single-link,
   non-symlink, non-reparse file whose Git blob equals its pin. Otherwise it stops with `UPSTREAM_FILE_MISSING`,
   `UPSTREAM_FILE_UNSAFE`, `UPSTREAM_BLOB_MISMATCH` or `UPSTREAM_VENDOR_DIR_UNSAFE`.
2. It refuses if `oracle3`, `oracle3.fees` or `oracle3.arbitrage` is already loaded from anywhere else
   (`UPSTREAM_ALIAS_COLLISION`). A foreign module is never overwritten.
3. It registers exactly those three names and executes the **verified bytes** (`compile` + `exec`, no re-read and no
   bytecode cache). The `oracle3` package has an empty `__path__`, so no other file can be imported through it.
4. On any failure it removes only the names it registered and stops with `UPSTREAM_IMPORT_FAILED`.

It never touches `sys.path`, the environment, an import hook, a plugin finder or an arbitrary path.

A checkout that converts line endings (CRLF) fails closed on the blob check. CI pins `core.autocrlf false`.

## Call path

```
python -B tools/alpha/run_oracle3_upstream_parity.py run --rel-scratch ABS --scratch-dir ABS
python -B tools/alpha/run_oracle3_upstream_parity.py verify --scratch-dir ABS
```

1. The run byte-copies the caller's REL-01 scratch to `inputs/rel/**`, reusing the REL path guards. Paths must be
   absolute, contain no `..`, and must not be symlinks, reparse points, hard links, aliases, secret-shaped directories or
   locations inside the repository. They must not overlap the scratch. Limits are 200 MiB and 3000 files.
2. The unchanged native `run_related_market_alpha.verify` runs on the frozen copy and must return `VERIFIED`
   (`REL_RECEIPT_NOT_VERIFIED`). The SHA-256 of the frozen `request.json` must equal the value bound in the REL receipt.
3. For each REL result row, `oracle3_upstream_bridge.assess_rel_core` builds `oracle3.arbitrage.Quote` objects (venue
   `polymarket`) from native best asks. Each quote gets an explicit `oracle3.fees.PolymarketSchedule` and is passed to
   the genuine `oracle3.arbitrage.check_constraint(relation, quotes, contracts=basket_shares, maker=False)`.
4. The run writes one write-once receipt `s10-r3-oracle3-upstream-parity-receipt-v1`.
   - Its `receipt_id` is `oracle3parity:sha256:` + SHA-256 of canonical `{"core": core}`.
   - The core binds the REL receipt id and code identity, every frozen REL file hash, the upstream commit, blobs and
     SHA-256s, and the bridge/CLI/vendored code identity.
   - It also records per-case verdicts with abstention reasons, the parity rows, the denominators and the
     `check_constraint_invocations` count.
5. `verify` recomputes everything with every socket entry point blocked, including the native REL verify and the
   genuine upstream calls. Any difference is `TAMPER_DETECTED`. The possible failures are `OUTPUT_MISMATCH:<key>`,
   `RECEIPT_ID_MISMATCH` and `RECOMPUTE_REFUSED:<code>`.
6. Repeating a run over identical REL bytes returns `IDEMPOTENT_VERIFIED` and writes nothing. Changed bytes or a
   partial scratch return `SCRATCH_NOT_EMPTY`.

Exit 0 means `RUN_COMPLETE`, `VERIFIED` or `IDEMPOTENT_VERIFIED`. Exit 1 means `STOPPED` with one stable
`reason_code`, or `TAMPER_DETECTED`. Error output never contains paths, headers or exception text.

## Bounded semantics (first matching abstention wins)

| Gate | Abstention |
|---|---|
| Native row not `EVALUATED` (manual pair, invalid model, duplicate or missing market) | `NATIVE_NOT_EVALUATED:<status>` |
| No `FORMAL_BOUNDED_PAYOFF_PROOF` (counterexample, unmodelled tie/void/cancel/partial, nonbinary) | `NO_FORMAL_PROOF` |
| `LOCAL_REAL_PIT`: native REL-01 never emits a decision-time confirmed rule | `REAL_RULE_CONFIRMATION_ABSENT` |
| Real-world class other than `INCONCLUSIVE_RULE_SEMANTICS` (cross-venue claim, rule conflict or orientation contradiction, one-condition identity, unbound/ambiguous/stale rule, time-window mismatch) | `RELATION_NOT_ADMISSIBLE:<class>` |
| No native basket whose every leg is `COST_KNOWN` (missing quote, depth below size, stale book, neg-risk, tick, minimum order, unknown fee) | `NO_USABLE_QUOTE_OR_DEPTH` |
| Fee policy not `WINDOW_VALID` at decision time (absent, expired, not yet valid, extension of the 2026-11-04 native policy) | `FEE_POLICY_*` |
| Native near-term screener policy (a documented bound, not per-market data) | `FEE_CONFIG_UNKNOWN` |
| Gamma body has neither `feeSchedule` nor `feesEnabled: false`, so upstream would fall back to its conservative default | `FEE_SCHEDULE_NOT_EXPLICIT_NO_DEFAULT` |
| Upstream `UnsupportedFeeSchedule` (exponent other than 1, maker fees, missing rate); TEST_ONLY exponent other than 1 | `FEE_SCHEDULE_UNSUPPORTED_BY_UPSTREAM` / `FEE_EXPONENT_UNSUPPORTED_BY_UPSTREAM` |
| Two frozen Gamma bodies of one market disagree; leg not bound to a frozen Gamma body | `FEE_SCHEDULE_CONFLICT` / `FEE_SOURCE_UNBOUND` |
| Upstream itself rejects the input (NaN/Inf/out-of-range price, duplicate contract, invalid size) | verdict `UPSTREAM_REFUSED` |

The fee schedule always comes from one of two explicit sources:

- `TEST_ONLY_HYPOTHETICAL`: the rate is the declared test rate, and the receipt labels it
  `TEST_ONLY_HYPOTHETICAL:<policy_id>`.
- `GAMMA_BODY_PER_MARKET`: the schedule comes from the upstream `PolymarketSchedule.from_gamma_market`, applied to the
  frozen Gamma body. That body is unauthenticated.

`default_schedule` and `for_category` are never called, and every `Quote` carries a schedule. Synthetic labels are
never relabelled.

## Parity and honest differences

An upstream basket is compared with the native basket that has the same sides. The comparison reports the deltas in
payout, top-of-book cost, fee and net edge, plus `edge_sign_agrees`. Each basket gets one parity label:

- `EXACT`: every delta is zero.
- `SIGN_AGREES_VALUE_DELTA`: the sign of the edge agrees but the values differ.
- `SIGN_MISMATCH`: the signs differ.
- `NATIVE_COST_UNKNOWN`: the native cost is unknown.

The differences are systematic and are reported, never tuned away:

- Upstream uses float math at the top-of-book price with a full fill assumed. Native uses an exact Decimal best-first
  depth sweep.
- Upstream fees use 5 dp ROUND_HALF_UP with a 0.00001 minimum. Native fees use a 5 dp ROUND_CEILING per leg.
- Upstream pays the reference minimum. Native pays the re-derived certified minimum.

Results on the frozen SANITIZED_SYNTHETIC REL-01 corpus (49 models, GAMMA_BODY_PER_MARKET rate 0.02):

- 3 models evaluated by upstream (`v01`, `v07`, `v08`) and 46 abstained. Abstention reasons are listed in the receipt
  denominators.
- 5 baskets compared, all `EXACT`, because each book has one price level and the fees align.
- With a two-level book the native sweep makes the upstream full-fill edge disappear (`SIGN_MISMATCH`). With a shallow
  second level and a TEST_ONLY rate of 0.03 the sign agrees but the values differ (`SIGN_AGREES_VALUE_DELTA`).
- `real_world_verified` is 0 and `tradable` is 0.

## Adoption truth (36 capability ids preserved)

`R3-03` and `R3-03-FEES` move to `SELECTIVE_UPSTREAM_CODE_REUSE` with value status `CONDITIONAL_NOT_VALUE_VERIFIED`
and owner acceptance `PENDING`. `R3-04`, `R3-11` and `R3-19` stay reference only, unchanged.

All other ids keep their program status, and none is closed by this WP. The full set is:

- `R3-01`, `R3-02`, `R3-03`, `R3-04`, `R3-05`, `R3-06`, `R3-07`, `R3-08`, `R3-09`, `R3-10`
- `R3-11`, `R3-12`, `R3-13`, `R3-14`, `R3-15`, `R3-16`, `R3-17`, `R3-18`, `R3-19`, `R3-20`
- `R3-21`, `R3-22`, `R3-23`, `R3-24`, `R3-25`, `R3-26`, `R3-27`, `R3-28`, `R3-29`
- `R3-01-SOURCE_ARCHIVE`, `R3-03-FEES`, `R3-05-CITATIONS`, `R3-07-ROUTER`, `R3-09-BOOK_GAPS`, `R3-10-WANG`,
  `R3-12-SAMPLER`

The `R3-23` one-shot public GET activation stays pinned and unconsumed, and needs a separate deliberate owner
instruction. PR #268 stays separate.

Limitations are tracked as S10-R3-ORACLE-UPSTREAM-01-D001..D003 in `docs/deferred_items_log.md`.
