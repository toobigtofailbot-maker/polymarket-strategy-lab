# Discovery-learning foreground proof contract (S10-ALPHA-03A)

`tools/alpha/run_discovery_learning_proof.py` is a finite foreground operator. It joins
native components that already exist and verify themselves separately. It adds only
the cross-system record they lacked: the queue-to-menu derivation, a STARTED-first
occurrence ledger, and one cold-verifiable manifest. It has no research, trading,
provider or scheduling authority.

## Usage

```
python tools/alpha/run_discovery_learning_proof.py prepare --case CASE.json --scratch-dir DIR
python tools/alpha/run_discovery_learning_proof.py run --scratch-dir DIR
python tools/alpha/run_discovery_learning_proof.py verify --scratch-dir DIR
```

There are no defaults. `DIR` must be absolute, empty and outside the repository. Each
named source store must be an absolute regular file outside the repository. It cannot
have SQLite sidecars or sit under a credential-like path. `prepare` freezes byte copies
in `DIR/inputs/`. Later phases read only those copies, except that `run` writes Hermes
manager feedback into `DIR/work/`. `run` stops with `SOURCE_CHANGED_SINCE_PREPARE` if an
original store changed after `prepare`. It blocks with `SOURCE_MUTATED` if an original
changes during the run. A second `run` is a verification replay, not a second attempt.

The case (`s10-alpha03a-proof-case-v1`, strict keys) names five things:

- the five source roles (`paper_store` may be null);
- the discovery policy, `as_of`, an optional earlier `prior_as_of`, and the ALPHA-02
  temporal mode and memory posture;
- the recorded tool-surface report, model label and caller-supplied decision clocks;
- recorded public venue documents;
- one to three occurrences, each with a label, `issued_at_ns`, `completed_at_ns` and the
  offline injected choice. An optional research-paper section supplies the expected
  binding inputs, strategy version, manager cutoff, clock and FakeHermesBackend draft.

Absolute paths stay in `DIR/private/`. They never reach the manifest.

## Stages

| Stage | Native component | Record |
|---|---|---|
| Source | `build_alpha_universe_snapshot` (+ `compare_alpha_universes`) | universe id, `BOUNDED_OBSERVED_UNIVERSE`, `external_universe_completeness: UNPROVEN` |
| Queue | `build_pre_allocation_triage_bases` -> `allocate_and_finalize_research_queue` | queue id, lane partition; every observed market in exactly one lane |
| Menu | Alpha registry, lifecycle and Hermes manager stores | members (max 8, AUTO-01 shape) plus a status for every market and exclusion |
| Decisions | AUTO-02 `run_one_cycle`, offline injected Stage B | one ledger row per occurrence |
| Paper | `build_research_paper_performance_snapshot` | research-paper facts |
| Feedback | `run_one_cycle` -> `_linked_feedback` -> `run_paper_performance_update` | linked assessment / run-record ids |

Menu membership is exact. A selected market enters only through its native matched
candidate ids. The rules are:

- The gamma id comes from `market:polymarket:<digits>`. The condition id comes from the
  observed market.
- The token is the single intersection of the candidate's subject refs with the observed
  token ids.
- The strategy versions are those whose `evidence_refs` name the candidate.
- Each version needs a latest Hermes assessment.

Each market's menu status is one of `NOT_SELECTED`, `RESEARCH_NEEDED` or
`CANDIDATES_EVALUATED`. Each excluded candidate records one of these reasons:

- `DUPLICATE_CANDIDATE`
- `DUPLICATE_STRATEGY_VERSION`
- `CANDIDATE_NOT_IN_REGISTRY`
- `MARKET_IDENTITY_UNVERIFIED`
- `TOKEN_LINK_UNVERIFIED`
- `NO_ELIGIBLE_STRATEGY`
- `NO_HERMES_ASSESSMENT`
- `MENU_CAPACITY_OVERFLOW`

Overflow is counted, never truncated silently. An empty menu is `NO_ELIGIBLE_STRATEGY`,
and no decision is attempted.

## Denominators

Each occurrence writes `ledger/occ-N.started.json` before any native work. When the
native cycle returns, it writes exactly one `occ-N.terminal.json`. A STARTED record
without a terminal is classified once, on the next `run`, as `INTERRUPTED_OR_UNKNOWN`.
It is never redispatched. Each occurrence has its own journal, so the same choice on two
explicit occurrences counts as two attempts.

- `attempted = completed + interrupted_or_unknown`.
- `not_attempted` counts occurrences skipped because the menu was empty.
- Terminal classes: `COMPLETED_PREVIEW`, `ABSTAINED_NO_TRADE`, `ABSTAINED_PAUSE`,
  `ABSTAINED_REASSESS`, `REJECTED`, `INCONCLUSIVE` (no admissible decision returned) and
  `INTERRUPTED_OR_UNKNOWN`.
- Feedback classes:
  - `DECISION_LINKED_NONCAUSAL`: the native eligible preview, same candidate, strategy
    version, lifecycle head and manager store, assessed.
  - `NOT_APPLICABLE_FEEDBACK`: abstentions. These get no paper credit, not zero return.
  - `DEFERRED`.
  - `NO_PAPER_SESSION`.
  - `NO_TERMINAL_DECISION`.
  - `REJECTED_<native code>`, for example lineage mismatch, cutoff not advanced, or paper
    evidence after the cutoff.

## Manifest and conclusion

`DIR/manifest.json` is written once as canonical JSON (max 256 KiB). Its
`manifest_id = alpha03aproof:sha256:<sha256 of the body>`. It carries source digests
only, the stage records, every ledger row, the denominators, the paper facts and the
authority block (real provider not invoked, model origin unverified, zero network
attempts, no order, no live, no causal or alpha claim).

The conclusion is one of three:

- `VERIFIED_OUTCOME_FEEDBACK_OBSERVED`: at least one decision-linked assessment.
- `PLUMBING_ONLY`: the composition ran and verified, but no linked feedback exists.
- `BLOCKED`: a typed fail-closed code.

`verify` re-derives every unblocked record from the frozen copies:

- the discovery, queue and menu records;
- the bundle digests, with journal replay through `run_one_cycle` on a backend that
  fails if it is dispatched;
- the manager run record and assessment;
- the paper snapshot id;
- the denominators and the conclusion.

It reports `fresh_attempts: 0`.

## Caveats

- Clocks are caller-supplied. Fixture clocks (for example the 2027 AUTO-01 world) are
  synthetic, and the manifest never claims current venue freshness.
- Discovery `as_of` after the decision cutoff is blocked as lookahead.
- Paper P&L is the cumulative session from one snapshot (`window_delta:
  NOT_COMPUTED_SINGLE_SNAPSHOT`). Missing marks stay `UNKNOWN_MISSING_MARKS`. A simulated
  research paper is never a venue or a qualification claim.
- Native identities are recorded unchanged. Occurrence ids are local digests of the case
  digest, the ordinal and the label. They are not a registry.
