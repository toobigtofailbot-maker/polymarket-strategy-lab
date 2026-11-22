# S10-HERMES-DELEGATED-SPECIALISTS-01

RUNTIME/Risk3/L, exactly 18 paths (approved 15 -> 17 -> 18 amendments). Branch `codex/s10-hermes-delegated-specialists-01`
cut from clean synchronized main `1c98183` (merge of PR #280, head `92e71a3`).

- PR #281 (docs-only) was open at implementation and merged on 2026-11-21 as main `743a3b1`. PR #268 (open) is separate and untouched; nothing is stacked on either.
- Stage C (2026-11-21, Side26 scope-limited grant under Karl's standing software-development delegation): merged `origin/main` `743a3b1` into this branch with a normal merge, corrected stale prompt/spec/doc wording within the same 18 paths, and changed no source or test code.
- The 2026-11-17 planning note alone was not the implementation grant. The distinct `S10_HERMES_DELEGATED_SPECIALISTS_01_CC_BOOTSTRAP.md` owner authorization covered the bounded offline 15-path implementation, conditional on native RUNTIME readiness. Karl then approved the 17-path
  amendment in chat ("Yes, I approve 17"). He also approved one extra exact allowlist entry in the second guard for the
  in-scope test file `tests/research_runtime/hermes_controlled_runtime/test_delegated_specialists.py`, with its hostile
  `_shadow` negative ("Yes, add it"). The Linux full suite then showed the historical meta-guard
  `tests/research_runtime/hermes_controlled_runtime/test_autonomous_feedback.py` pins both guard files to base text plus
  enumerated additions; Karl approved it as the eighteenth path ("Yes, approve 18") to enumerate this WP's exact guard
  additions. Merge: NO (Karl only).

## Identity

- WP ID: S10-HERMES-DELEGATED-SPECIALISTS-01
- Title: Pinned upstream Hermes specialist delegation to grounded native Alpha evidence
- Branch: codex/s10-hermes-delegated-specialists-01
- PR: see GitHub PR metadata and PR body.
- Base commit: 1c981838c2cc3ff2fcd5991aa97cf78194a10a2f (original cut); Stage C sync base: 743a3b1d2478737a81eb6691e6cf2ec15ee5fd5a
- Validated implementation commit: recorded in the PR body (this fragment is stable and non-self-referential).
- Current live PR head: see GitHub PR metadata and PR body. This status fragment is stable and non-self-referential.
- Merge commit: (fill after merge)
- Evidence mode: PUBLIC_VERIFIER_PASS (public repo; from the posted-body verifier run recorded in the PR body; it covers posted reporting only and does not show that pinned Hermes tests ran in hosted CI, see D002)

## Readiness

- Prompt SHA-256 (evidence-mode correction, current): `2ae7470bbf52f80f312441c576fbdf05e665a89b8167b36a7bbfb00c22213e32` (Stage C prompt `6847bc4004f2f8ec714f4c4303d5006e942434f4a8bad6ddd670d9da6cf0d5cb` is historical); spec `a1e8b4d913b4862a08cb3460b5bd96a4d22876bfa74351c6dd5d4bdaac90f69b`. Native gate on these bytes (the pre-edit run on the previous 18-path bytes also passed): exit 0, `IMPLEMENTATION_READY`, RUNTIME, certificate_required=false, scope 18, 12 evidence items, 12 rules, error_codes [].
- Prompt SHA-256 (18-path amendment, historical): `1b7c132fff0ee67480d46084d07c603264e0a065e1c89d88d978bc350a1721ac`; 17-path prompt `776077b6c852c1aea6a39103941fda4f43f16b863b596285e4b73625cb10d207` is historical.
- Spec SHA-256 (18-path amendment, historical): `cd048af5cebb7ffa78793bde32f552c2f6e9439bab4044205c491deae8b01cf8`; 17-path spec `160f1ad84ddea73bcdf2cdcebe67a76003ce22e6bc05e6aa79c617ba8d258970` is historical.
- The 17-path copies were byte-identical to the continuation package. The committed copies add only the eighteenth path
  to both scope lists and an "OWNER SCOPE AMENDMENT 02" paragraph in the prompt.
- The native gate ran on the 17-path package bytes in an isolated `git archive` copy of `origin/main`, before any source edit:
  - exit 0, `IMPLEMENTATION_READY`, RUNTIME, certificate_required=false;
  - scope 17, 12 evidence items, 12 normative rules, error_codes [].
- 18-path amendment, before re-running tests: `wp_readiness_gate.py` (no `--check-diff`) exit 0, `IMPLEMENTATION_READY`, RUNTIME,
  certificate_required=false, scope 18, 12 evidence items, 12 rules, error_codes []. The final diff gate is in the PR body.
- The earlier 15-path readiness and probe receipts are historical feasibility evidence only.
- Ponytail LITE was the first actually invoked skill after startup.

## Pin

- Local exact checkout of NousResearch/hermes-agent at `345cd2b057a452236de401d3534b8502a7465e8d` (tag `v2026.9.14`, version 0.21.3). Tree clean, MIT, no `.env`.
- Venv: CPython 3.11.9.
- Bound by `.git/HEAD` plus LF-normalized SHA-256 of nine seam files.
- The AUTO-02 runtime profile does not describe this venv (deferred D001).

## Implementation

Contract: `docs/hermes_delegated_specialists_contract.md`.

- **Policy.** `DelegatedSpecialistsPolicy` is separate, frozen, content-addressed and narrowing-only. The H1 `HermesInvocationPolicy` is unchanged; R001 pins its golden policy id and managed-config digest.
- **Runner.** `run_pinned_python_worker` makes one bounded `python -I -B` launch in its own process group:
  - the caller supplies the full env and an empty cwd;
  - a timeout kill-tree runs on expiry;
  - it returns digests only, never raw output.
- **Witness.** In the pinned venv, the worker observes the original upstream `_build_child_agent` and `_run_single_child`, restores them, and calls `delegate_task(tasks=[A3, A4], background=False)` once.
  - The provider is scripted only at `agent.process_bootstrap.OpenAI`.
  - Sockets and subprocesses are denied by an audit hook.
  - The only network attempts observed were denied `127.0.0.1:9` sentinel probes.
  - Upstream's `cmd.exe` launch attempts were denied and never executed; they are recorded as evidence.
- **Host.** The host validates the witness into closed codes and seals it as a one-shot `DelegationWitness`. Roles come from the task index only.
- **Consumer.** The operator runs this chain:
  1. native SRC-01 `verify` and `grounding_context`;
  2. `assess_question`;
  3. a lineage check against the frozen registry chain;
  4. `build_research_episode` (`DATA_INSUFFICIENT`, `OTHER_VALIDATED_ADVISORY`, human review);
  5. `append_alpha_factory_records`;
  6. cold `load_and_verify_alpha_factory_registry`.

  The same inputs give an idempotent append, and `verify` is a cold re-derivation.
- **Unchanged.** Not modified: `research_cooperation.py`, Alpha Factory core and registry, `run_hermes_cooperation.py`, upstream source, dependencies, workflows.

## Outcome

- Evidence class: `OFFLINE_NATIVE_DELEGATION_TEST_ONLY`.
- Acceptance: `OFFLINE_IMPLEMENTATION_COMPLETE_REAL_PROVIDER_ACCEPTANCE_PENDING`.
- In isolated test registries, real pinned children produced a grounded `CITATIONS_VERIFIED_REVIEW_REQUIRED` outcome. One advisory episode was appended and cold-verified, and a second run was idempotent.
- No real provider, market GET, credential, Alpha discovery, qualification, paper, order, deployment or production registry write took place.
- No claim is made about research quality, forecast quality or Alpha.

## Limitations

See `docs/deferred_items_log.md`, section "S10-HERMES-DELEGATED-SPECIALISTS-01 deferred items", D001–D006:

- the profile mismatch;
- hosted CI has no pin, so the native tests skip there;
- real-provider acceptance is pending;
- upstream's denied shell probes;
- the guard-allowlist recurrence;
- the external npm advisory that failed hosted `cockpit-frontend` (resolved 2026-11-21: advisory withdrawn; 4 moderate advisories remain).

## Validation state

Validation commands and results, exact-head hosted checks, the evidence mode and the Ready decision belong in the PR body.
