# Hermes Research-Brain Execution Plan

## Status And Authority

- Plan status: ACCEPTED_REPO_TRUTH_PLAN
- Package that locked this plan: WP95
- Authority: planning and repo-truth guidance only
- Runtime authority: NONE
- Paper authority: NONE
- Execution authority: NONE
- Live authority: NONE

PR #94 was merged before this plan was locked into repo truth. WP95 records the
accepted plan after that merge. Live trading remains disabled. Hermes is not
installed, is not connected, and has no runtime authority. Those facts may
change only through a future explicitly approved work package that updates repo
truth.

This plan does not install or connect Hermes and does not create schemas,
validators, prompt packs, runbooks, exporters, provider configuration, model
calls, memory, scheduler behavior, paper behavior, live behavior, credentials,
or order paths.

## Accepted Philosophy

Hermes should be powerful from the beginning as an adaptive research brain.
Guardrails must prevent execution and control risk without reducing legitimate
research usefulness. The repository should use structured Hermes inputs and
outputs so the research layer can gain capability later without requiring an
architectural redesign.

Hermes remains advisory. Its research can inform a human decision or a future
approved work package, but it cannot promote its own output into runtime or
trading authority.

Superseded by V2.1 as future target architecture (historical context only): WP95's
permanent Hermes-advisory-only / never-final-decision-maker assumption is
superseded. Under the accepted V2.1 architecture (`docs/architecture_decision_record.md` (V2.1 Strategy Lifecycle + Portfolio Authority Architecture)), humans define the
outer blast radius through a global PortfolioAuthorityPolicy, Hermes will later make
soft strategy/lifecycle judgments (continue / scale / reduce / adapt / quarantine)
inside it, and deterministic code enforces the outer envelope and account/execution
safety. Current runtime truth is unchanged: the existing controlled Hermes research
mode remains research-only and unchanged until S10-HERMES-STRAT-01, and Hermes still
cannot hold credentials, sign, place or cancel orders.

## Broad Research Freedoms

The architecture should support Hermes performing:

- market research and edge discovery;
- hypothesis generation and experiment design;
- strategy critique and future work-package recommendations;
- failure analysis and performance-improvement analysis;
- wallet and candidate review;
- regime monitoring;
- cross-market inconsistency analysis;
- resolution-rule ambiguity review;
- microstructure and slippage realism review;
- paper-strategy research after the relevant deterministic artifacts exist and
  a future work package authorizes that research surface.

These are broad research freedoms, not permission to create executable trade
instructions or bypass human review.

## Deterministic-Core Responsibilities

The deterministic core controls:

- execution and validation;
- risk and state;
- accounting and credentials;
- order lifecycle;
- live safety and the kill switch;
- audit logs;
- strategy-promotion gates.

Hermes output cannot override or replace these controls.

## Forbidden Hermes Authority

Hermes must not:

- access credentials or private endpoints;
- place, cancel, sign, or submit orders;
- control runtime, scheduler, or bot loop;
- mutate live configs or override risk;
- approve strategy promotion;
- approve pull requests or claim merge readiness;
- execute paper or live orders without deterministic validation and
  human-approved gates;
- act as the final decision-maker for trade, risk, or live actions.

## Execution Sequence

### Short Term

0. Post-WP94 repo-truth/status reconciliation and plan lock-in.
1. Hermes Advisory Foundation And Research-Brain Architecture V1.
2. Hermes input/output contracts and validator hardening, documented by WP97.
3. Hermes research prompt pack and operator runbooks.
4. Deterministic Hermes context-packet exporters.
5. Hermes local/offline simulation or manual run process.

### Medium Term

Hermes supports candidate-review workflow, wallet intelligence, market-edge
hypothesis generation, cross-market inconsistency detection, resolution-rule
ambiguity review, microstructure and slippage realism review, strategy proposal
critique, performance and failure analysis, and paper-strategy research.

### Long Term

Hermes evolves through explicitly approved stages as a read-only research
brain, shadow analyst, paper assistant, strategy critic, failure-review
assistant, manual-live review assistant, and restricted-live monitoring and
explanation assistant. It remains advisory unless future repo truth explicitly
changes an authority boundary.

The later phase sequence is:

6. Paper-strategy design with Hermes critique support.
7. Paper engine and dry-run order-intent layers with Hermes as reviewer only.
8. Manual live-approval design with Hermes as review assistant only.
9. Restricted-live or production-style bot with Hermes limited to research,
   monitoring, explanation, and failure review unless future repo truth changes.

## Manual-Step Checkpoints

When a manual step is required, Side 5 or the active planning chat must stop and
give Karl direct chat instructions instead of hiding the manual step inside a
work package.

Manual approval is required for runtime/provider choice, local or sandbox
installation, model provider and budget, API keys outside the repository,
memory permission, internet/browser permission, allowed and denied files or
folders, allowed commands, file-write permission, output location, paid
model/API use, scheduler or automation, and any paper/live/Hermes integration
escalation.

## Cost Controls

- Perform deterministic preprocessing before Hermes.
- Prefer structured context packets over raw dumps.
- Use batching and triggered runs instead of continuous loops.
- Route to local or lower-cost models when sufficient.
- Cache stable summaries.
- Require cost logging and budget caps before paid or remote use.
- Do not run long-lived autonomous loops without later explicit approval.

## Repo-Truth Update Rule

Future changes to the accepted Hermes/research-brain execution plan must update
repo-truth docs in the same work package or an approved follow-up.

- Chat memory alone is not authoritative.
- PR comments alone are not authoritative.
- Dynamic PR state belongs in GitHub metadata and the PR body.
- Committed repo docs must stay stable post-merge.

## Next Work Package

The next substantive work package after WP95 should be Hermes Advisory
Foundation And Research-Brain Architecture V1. Later work packages should cover
input/output contracts and validator hardening, the research prompt pack and
operator runbooks, deterministic context-packet exporters, and a local/offline
simulation or manual run process.

Each later phase requires its own approved scope. This plan describes sequencing
but grants no implementation authority.

## WP96 Phase 1 Architecture Foundation

WP96 records this Phase 1 architecture foundation at
`docs/hermes_advisory_foundation_research_brain_architecture.md`. That document
elaborates the advisory foundation, mode map, broad research freedoms,
authority matrix, deterministic-core responsibilities, future input/output
family names, and forbidden Hermes authority.

WP96 does not create actual schemas, validators, prompt packs, runbooks,
exporters, context packets, runtime artifacts, provider/model configuration,
credentials, network behavior, paper/live behavior, execution behavior, risk
behavior, scheduler behavior, dashboard behavior, or bot-loop behavior.

WP97 documents Phase 2 contract and validator requirements at
`docs/hermes_input_output_contracts_and_validator_requirements.md`. WP97 is
documentation-level only; it creates no machine-readable schemas, validators,
prompt packs, runbooks, exporters, context packets, runtime artifacts,
provider/model configuration, credentials, network behavior, paper/live
behavior, execution behavior, risk behavior, scheduler behavior, dashboard
behavior, or bot-loop behavior.

## V2.1 Status (S10-STRAT-LIFE-01)

V2.1 target architecture: ACCEPTED (see `docs/architecture_decision_record.md` (V2.1 Strategy Lifecycle + Portfolio Authority Architecture)). S10-STRAT-LIFE-01
implements only the deterministic strategy lifecycle and global portfolio-authority
substrate that a future Hermes strategy manager will consume; it implements no Hermes
strategy-manager runtime. The existing controlled Hermes research mode remains
research-only and unchanged until S10-HERMES-STRAT-01. The "Forbidden Hermes
Authority" list above remains current runtime truth until a separately authorized
successor changes it.
