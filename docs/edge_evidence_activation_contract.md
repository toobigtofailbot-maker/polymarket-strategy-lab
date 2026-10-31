# Edge Evidence and Owner Activation Readiness

S10-EDGE-EVIDENCE-ACTIVATION-01 is one PROTECTED/Risk4 software WP based on
merged PR262 (`c2bbd18ef2f8a615226af959aac2e07273bd7f05`, predecessor head
`d968996a094a1d17d543c1104fab3cb5885e02a2`). Its exact21 paths and authority
are the independently certified prompt/spec under
`docs/wp_specs/S10-EDGE-EVIDENCE-ACTIVATION-01/`. This contract grants no live
authority. Karl alone merges.

## Concrete capability

`tools/alpha/run_edge_evidence_capture.py run --scratch-dir <new absolute external directory>`
performs one foreground unauthenticated public research capture through the existing
Hunter `run`/`acquire`/`analyze`/`verify` and research-only Alpha/PIT registry. No
new forecast method, financial acceptance framework, gateway, account store or
provider is introduced. The native rain family alone is queried: at most6 native
markets,40 attempted GETs,10seconds per bounded request,2,000,000bytes per response,
7200seconds per invocation, no proxy/redirect/retry/auth/cookie/provider budget.
The native acquisition normally finishes sooner. The configured limits are
ceilings, not promises of complete universe or enough observations.

The only endpoints are the native Gamma next-two-day rain-event slugs, NWS
station/points/gridpoint templates and CLOB token books. URLs are native derived;
the CLI accepts no URL. The single scratch root must be new, outside the repo
and secret directories, with symlink/reparse traversal rejected. Request start
is durably written before dispatch. Native source receipts and raw bytes remain
immutable; separate transport receipts retain closed status and numeric HTTP
status without raw errors. Secret-like content is refused before raw storage.
An interrupted/partial root is not resumed or repaired, and cannot reacquire.
Creating a new capture is a separate foreground operator action, never an
automatic scan-until-trade loop. No service is installed or started.

`verify --scratch-dir <same directory>` is offline, with no model, provider,
account or product request. It replays exact native source bytes and manifests,
requires one complete native operation and matching pinned native method/parser
code bytes, checks transport linkage and monotone capture clocks, and emits a
fixed-key JSON report. Code drift refuses replay; it does not backfill history.
An exact source snapshot must be preserved if later replay uses different bytes.

## What the receipts prove

`REPLAY_VERIFIED` means local byte integrity and deterministic native research
reproduction. It does not authenticate historical capture time, certify an
independent event resolution, prove forecast calibration or authorize a trade.
Locally self-hashed records, caller settlement flags and test fixtures cannot
promote a method. Native raw source receipts keep event/market/condition/token/
outcome/rule identity and method-bound forecast cutoffs. A source observation
made now cannot establish what the source predicted before an old event.

The report distinguishes observed Gamma rows, unique market ids, native markets,
pre-event forecasts, unresolved station/day/rule groups and per-host available
receipt counts. Station/day/rule identity does not establish statistical
independence: `independent_event_groups=0` until original events/settlements have
been independently qualified. `verified_settled_groups`, `n_train`, `n_holdout`
and `n_bucket` remain0 for forward research. No final settlement collector or
acceptor is invented without an authoritative verifiable source contract.
Unavailable/invalid capture reports unknown counts (`null`), never a false
successful zero. A verified capture with no supported rows may correctly report0;
it does not prove there are no opportunities outside the observed sources.

All production corpus/method allowlists remain empty. `evidence_diagnosis` returns
`NO_TRADE` even after valid replay. Hermes confidence and model prose cannot
provide a financial probability. The structural two-leg method remains
RESEARCH_ONLY: single-side FOK does not prove atomic all-leg payoff/execution.

## Historical diagnostics

The existing `historical_bound` remains TEST_ONLY. Its chronological70/30 split
now also requires every training label to have resolved before the earliest
holdout forecast cutoff. Duplicate/conflicting event groups, tied split
resolution, late/future source times and an unfrozen method fail closed. Decimal
one-sided95% floored Wilson, fixed deciles, minimum50 holdout groups and the
training-prevalence Brier comparison remain unchanged. Passing arithmetic never
fills an empty production allowlist.

## Owner checkpoint

`autonomous_cycle.evidence_activation_report` only combines offline evidence with
explicitly unobserved account/funding/custody/provider/host/canary fields. It does
not call authenticated `account()`. The original `activation_report` API is
unchanged. Software verification comes from real external validation receipts,
not a boolean asserted by the report itself.

The existing first live canary remains fee-inclusive USD5 and owner-specific:
eligible host/access/clock, exact signer/Deposit Wallet/custody, verified complete
account truth, qualified method/current fee and book, Stage A, witnessed OAuth,
attended Stage B and actual order/ledger reconciliation. No secret is requested
in chat. The dormant USD100 allocation/USD10 order/USD10 lifetime loss/USD90
reserve profile does not replace that first-canary procedure. Provider budget
remains0 absent distinct protected owner consent; later ceilingUSD2/rolling24h.
No funding, withdrawal, account read, economic mutation or unattended activation
is performed by implementation/CI or caused by merge. Windows research capture
does not qualify Windows as a production host.

## Source access and current fee facts

On2026-10-30, official NWS API documentation states its developer forecast/
observation interface; its disclaimer permits public-domain use unless otherwise
noted. A User-Agent is sent. ESPN is not queried: Disney's published automated
extraction restriction has no supplied separate permission. This is an access
limitation, not an invented ESPN dataset.

- https://www.weather.gov/documentation/services-web-api
- https://www.weather.gov/disclaimer
- https://disneytermsofuse.com/english/
- https://docs.polymarket.com/trading/fees

The current official fee table was inspected, including Weather0.05 and the
share-based taker formula. This is not current account/order evidence and does
not extend the native frozen policy beyond2026-11-04T00:00:00Z. Real market fee,
minimum, executable size and positive stress edge still require current native
proof. Fee-inclusive minimum exceedingUSD5 remains NO_TRADE.

## Output and test policy

Every public report field is enumerated by field-coverage tests. Schema/status/
reason/evidence labels and hash strings are closed/scanned; nonnegative counts,
null unknowns and false financial eligibility are type-exempt. Invalid outputs
are recursively checked for the same untrusted sentinel as valid outputs.
No raw caller mapping, source body, exception, header or path is projected into
the checkpoint. Native raw receipts are kept externally, not in repo/PR logs.

Negative matrix: missing/null/type/empty/malformed inputs, raw/receipt/manifest
tampering, code drift, source-time overlap, duplicate/conflicting groups, fake
finality, timeout/redirect/HTTP failure/oversize, endpoint/cap/clock/restart,
symlink/no-echo/secret-like bodies, unknown denominators and preserved native
wallet lock/risk/attended-canary denial. Natural-language trade-word spelling
filters are not introduced; their typo/case categories are inapplicable.

Actual process events (merge, certification, pre-source readiness, real capture,
independent source/security reviews, full suite, hosted CI and posted evidence)
are separate receipts in the stable status fragment/current PRbody. A pytest
test cannot prove those events happened. Current live PR head belongs in GitHub
metadata and PRbody; this document is not a dynamic activation receipt.
