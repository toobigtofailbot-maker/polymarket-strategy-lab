# WALLET-03 PIT wallet observability and conditional cost research

S10-WALLET-03 adds a bounded advisory assessment in
`src/data_layer/wallet_intelligence/copyability.py`. It is research evidence only.
WALLET-04 owns incrementality against non-wallet controls. The historical WP81
fixture evaluator is a comparator, not authoritative market evidence, and its
promotional statuses are not reused.

## Authority / Non-Authority

The Centralized Boundary Group Reference table in
`docs/ai/codex/PROTECTED_PATHS.md` remains controlling. The only source-access
exception approved by Karl in REV3 is reading an existing WALLET-01 SQLite ledger
through the unchanged verified loader and WALLET-02 profile builder. There is no
new database, persistence, source module beyond `copyability.py`, provider client,
dependency, scheduler, strategy, qualification, paper, execution or live behavior.
No order, credential, private account or capital authority is created. Normal
authenticated GitHub repository operations are separate workflow authority;
hosted Actions require later authorization and any PR remains draft.

## Public interface and source verification

The package exports `WalletCopyabilityCostScenario`,
`WalletCopyabilityQuoteWitness`, `WalletCopyabilityResearchAssessment`,
`WalletCopyabilityError`, `build_wallet_copyability_research_assessment`,
`wallet_copyability_research_assessment_to_mapping`, and
`wallet_copyability_research_assessment_from_mapping`.

The keyword-only builder takes `profile`, `wallet_ledger_path`,
`expected_ledger_head`, `cohort_snapshot`, `target_wallet`, `as_of`,
`market_contexts`, optional `identity_observability`, `quote_witnesses`,
`delay_seconds` and `cost_scenarios`.

It validates the profile, cohort, contexts and provenance with existing public
WALLET-02 validators, loads the existing ledger read-only, requires its exact
expected head, canonically rederives the complete profile with
`build_wallet_profile_snapshot(wallet_ledger_path=...)`, and compares both the
entire dataclass and canonical mapping. A second explicit verified load after
rederivation rejects intervening drift. Original source verification involves
three native ledger reads including the builder's internal read. All assessment
calculations thereafter operate in memory. WALLET-01/02 sources are unchanged.

An internally consistent profile ID is insufficient source proof. Wrong, missing,
foreign, unreadable, corrupt or changed source, wrong head, cutoff, cohort,
context or target, and self-rehashed fabricated derived evidence fail closed.
No caller verification flag, monkeypatch of native globals, copied derivation
algorithm or in-memory snapshot passed as a pathname is used.

## Quote witnesses and provenance

Each frozen input witness declares context-typed condition/token identifiers,
`price_direction_sign` (+1 for acquisition-side price comparison, -1 for
disposition-side comparison), price, optional top-level depth in outcome shares,
`ObservabilityEvidence`, DQ and replay fidelity. It can also carry an existing
`RawEvidenceReference`, `ResearchProvenanceManifest` and retained raw bytes.
These are input witnesses, not a new canonical registry or acquisition service.

`OBSERVED` requires all of the following:

- Exact raw-reference and manifest records in the verified backing ledger;
  rebuilding their native content identities yields full equality.
- Retained bytes with the declared SHA-256 and byte length, plus manifest binding
  to both the reference ID and content hash.
- The narrow public CLOB `/book` JSON witness contract: source system
  `POLYMARKET_CLOB`, retrieval method `GET`, media type `application/json`, request
  `token_id`, and document `market`/`asset_id` matching the declared condition/token.
- No duplicate JSON keys; price and size levels are canonical decimal text.
  The declared price matches the minimum ask or maximum bid, and declared depth
  matches the sum of size at that top price. Missing depth remains missing.
- Raw and witness availability clocks agree, all applicable DQ states are OK,
  replay is EXACT/FAITHFUL, and timestamps are admissible. The manifest information
  cutoff cannot exceed quote availability; raw ingestion cannot exceed analysis.
  Raw revision time cannot exceed the claimed quote availability. A book witness
  carrying resolution metadata is inadmissible, including future resolution.

Missing/unregistered source binding or a different source adapter is
`SCENARIO_ONLY`, never observed. A present native source binding that contradicts
its bytes, identifiers, clock or book fields is rejected. Future, corrected,
backfilled, unavailable, unpersisted or uncertain quotes cannot establish observed
evidence. Neither content hashes nor these offline checks independently attest
physical provider origin. The caller's verified retained evidence is the trust
boundary; this WP acquires no real market data. Tests use synthetic retained
source records and do not establish real-world wallet feasibility.

## PIT selection and denominators

The existing profile's canonical reconciliation decision and selected observation
are used. Wallet event time is never substituted for action availability. Only
strong-identity, unambiguous, standard binary trade-fill evidence with a usable
PIT context and reference price is eligible. Unsupported activities, ambiguous
identity, missing/future context and actions observed after outcome availability
are excluded. Native profile exclusion reasons preserve disagreement, reorg,
duplicate, evidence-window, DQ and replay distinctions. Related-account evidence
uses native clustering and reconciliation; an equivalent economic event does not
increase the eligible denominator.

For each declared delay, select the earliest matching quote captured at or after
action availability plus that delay, available by the analysis cutoff and before
outcome availability. Delay means a minimum observation offset, not an exact fill
latency. Simultaneous contradictory prices/depth produce explicit insufficiency;
they are not resolved by choosing a favorable quote. Equal semantically matching
witnesses use deterministic source-quality/ID tie-breaking. Duplicate witness
or raw-reference rows reject. Independent fills remain distinct; related account
membership alone is not proof that different fills are the same event.

Each result conserves `considered = eligible + excluded` and
`eligible = sum(outcome_reason_counts)`. It records context coverage, source-bound
observable unique quote witnesses, selected quote IDs and mutually exclusive missing quote,
conflicting quote, missing cost, missing depth and insufficient depth reasons.
No quote is synthesized from the leader's historical reference price.

## Explicit scenarios and numerical meaning

Each cost scenario requires all four fields, with explicit null allowed for
unknown: `taker_fee_per_share`, `slippage_per_share`,
`transaction_cost_per_share` (USD per outcome share), and
`required_depth_shares` (strictly positive outcome shares). These are declared
scenario assumptions, not observed venue fees or realized follower costs.
Explicit zero is a scenario assumption; unknown is null and is never replaced
with zero. No rates, basis points or absolute currency totals may be mixed into
these fields. No spread is inferred.

Conditional difference per event/scenario is
`(reference_price - delayed_quote_price) * price_direction_sign - fee - slippage - transaction_cost`.
Calculation uses a fixed 80-digit Decimal context. Prices are bounded to [0,1].
Input decimals are canonical nonnegative text, with at most 18 fractional places,
48 characters and magnitude 1e9. Floats, exponents, NaN, negative costs and
noncanonical zero/trailing-zero text reject. Delays are canonical decimal seconds
with microsecond resolution, [0,86400], at most eight distinct windows. There are
at most eight distinct scenarios, 512 profile events, 256 quote witnesses and
65536 retained bytes per quote. Inputs above bounds reject rather than truncate.

No differences are emitted for a selected quote if any scenario cost is unknown,
depth is missing or any required depth is unmet. Best/worst figures are extrema
over the emitted event/scenario differences, not an average or forecast. All
scenarios are retained; no favorable scenario is automatically promoted.

Per-delay statuses are `OBSERVABLE_CONDITIONAL` when all eligible events have
source-bound usable quotes and complete assumptions, `SCENARIO_ONLY` when usable
estimates include unbound quote assumptions, `UNOBSERVABLE` when no eligible
event has an admissible quote, and `INSUFFICIENT_CONTEXT` for no eligible events
or remaining mixed/missing evidence. Positive figures do not establish profit,
alpha, expected return, skill, executable improvement or a recommendation. True
follower fills, sizing, queue position, market impact, adverse selection,
causality and realized P&L are unknown.

## Closed assessment and mapping integrity

The frozen assessment's public fields are its own content ID, schema/policy,
profile ID, verified ledger head, subject cluster/cohort IDs, analysis cutoff,
context IDs, delays, complete cost scenarios, sanitized event/quote evidence,
derived delay results and four immutable true non-authority flags. Hash identity
uses native canonical wallet JSON over all fields except its own ID. Order of
semantically identical caller inputs does not change identity. The serializer
recursively enumerates dataclass fields; a field-coverage test verifies coverage.

Output contains hashes, canonical timestamps/decimals, closed reasons and counts;
it omits addresses, raw bytes, paths, account claims, free-text source metadata
and context labels. Errors contain only closed `COPYABILITY_*` codes.

Mapping roundtrip checks exact schemas, known ID namespaces, bounds, identity,
true flags, references, duplicate rows and deterministic recalculation of every
delay result, including boolean-versus-integer distinctions. A rehashed
contradictory result rejects. Standalone mapping integrity is not independent
source authenticity; a completely self-consistent source forgery can only be
tested against original source inputs through the builder. No mapped record has
execution or qualification authority.

## Requirement and negative evidence matrix

| Requirement | Focused evidence | Negative boundary |
|---|---|---|
| R001 source derivation | `test_wallet03_verified_profile_ledger` | self-rehashed derived fields, foreign/missing/corrupt ledger, cutoff/context/cohort/target/head mismatch and read drift |
| R002 PIT | `test_wallet03_pit_observability` | event-time substitution, future manifest/quote, after-outcome, foreign instrument, corrected/backfilled/uncertain clocks |
| R003 costs | `test_wallet03_explicit_delayed_costs` | float/negative/exponent/noncanonical text, unknown costs, absent/insufficient depth, conflicting earliest quotes |
| R004 denominators | `test_wallet03_reconciliation_denominators` | duplicate/equivalent, superseded, reorged, contradictory and ambiguous source flow |
| R005 integrity | `test_wallet03_stable_record_roundtrip` | rehashed incorrect counts/extrema, extra fields, malformed quote, false flags and raw metadata |
| R006 authority | `test_wallet03_read_only_no_authority` | write/network/subprocess/environment attempts, database mutations, unsafe output; original database/input unchanged |

Final evidence must include native exact-diff readiness, the exact eleven-file scope,
artifact/static/security checks, adjacent tests and one authoritative full local
suite on the stable committed candidate. Side19 acceptance and authorized hosted
exact-head CI remain separate gates. Status is not LOCAL_ACCEPTED merely because
local tests pass, and hosted checks remain pending before review readiness/merge.

The authorized historical WP81 source guard requires exactly its fixture evaluator
and the WALLET-03 module. Negative probes cover either module missing, a third
matching file and a third matching directory; unrelated tools/trading/report
guards are preserved. Full-suite validation uses an offline writable Linux-native
checkout from canonical Git objects after native/hash/shell/output preflight.
