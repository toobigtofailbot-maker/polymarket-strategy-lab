# WP175 Restricted Live Canary Contract

WP175 is a protected, manual-foreground canary, not mature live trading. The
implementation is limited to one strategy, one binary market, one LIMIT order,
one create attempt, and one active operator session. A3 is entered only after
an exact-head, short-lived, single-use manual arm receipt. Process restart
always returns the gateway to `A0_DISABLED` and requires authoritative
reconciliation before a new arm. The runtime derives the actual clean Git root
and HEAD itself and requires the single canonical per-wallet ledger path;
caller-supplied head or alternate-store strings cannot establish authority.

The Gate-C boundary consumes an already authenticated WP174B `GateBSession`.
The raw SDK client and ephemeral credentials remain private to Gate-B. The
only new venue mutation is a separately built and signed LIMIT order followed
by exactly one `post_order` call. A durable `GATE_C_CREATE_STARTED` event is
committed before that call. Accepted or possibly transmitted attempts are
never retried. Accepted and possibly transmitted outcomes automatically enter
the fixed three-probe official-read reconciliation sequence in the same
foreground workflow; unresolved identity/fill/position state remains blocked.
Resting accepted orders use the existing durable Gate-B cancellation path.

Hard maxima are fixed in code: wallet 50.00 pUSD, gross exposure 20.00 pUSD,
per-market exposure 15.00 pUSD, per-order committed 10.00 pUSD, one market,
one open order, one create attempt, a 30-minute session, daily realized loss
5.00 pUSD, drawdown 7.50 pUSD, and cumulative loss 10.00 pUSD. No config,
environment, browser, strategy, Hermes input, or venue response can widen
these values. Only fresh official `blocked=false` geoblock evidence permits
new exposure; cancellation remains available when new exposure is blocked.
The requested order's worst-case loss must fit inside every remaining loss
budget before signing. Caller-supplied account snapshots are never accepted.

The only operator entry point is
`python -m src.execution_gateway.gate_c_operator canary ...`. It requires a
foreground TTY, an exact human confirmation phrase, ephemeral no-echo Gate-B
authentication, a pre-existing canonical ledger and prepared order, official
market/geoblock/account reads, qualification, arm, one CREATE, classification,
bounded reconciliation, cancellation of a uniquely identified resting order,
and terminal sanitized evidence. It is never a scheduler or service.

An accepted POST response proves venue acceptance only. It does not prove
economic finality, a completed position lifecycle, or absence of residual
exposure. Accepted and ambiguous attempts remain halted and reconciliation-
required until bounded official authenticated reads converge. Any observed
fill is retained as residual-position evidence and remains blocked; a cancel
response alone never clears the live order or position ledger.

`GateCStrategyQualification` binds exact repository head, a fully validated
WP172 assessment/cost model and WP173 paper-store terminal head, selected
strategy evidence, and an interactive `OPERATOR-PRODUCTION-EVIDENCE` nonce.
Qualification and arm receipts contain IDs and timestamps only; local artifact
paths, secrets, signatures, raw SDK responses, exceptions, IP, country, and
region are never persisted or emitted. The qualification prerequisite is
currently unavailable, so Gate-C activation remains pending and no real
create or capital action is authorized by this package.

WP176 remains separately gated and owns unattended/service operation, broader
recovery, multiple markets/strategies, and capital scaling.

Merge versus live activation. This package separates four states and never
conflates them: code-complete; merged dormant capability; first live activation
canary; and mature live. The inert, fully disabled Gate-C implementation is
mergeable as dormant capability with `FINAL_MERGE_SMOKE_CREATE_ATTEMPTS=0`, so no
real economic CREATE, real secret, capital, or strategy qualification is required
before merging dormant code; dormant merge still needs a separate exact-head human
merge authorization. The single real CREATE is
`FIRST_LIVE_ACTIVATION_CANARY_CREATE_ATTEMPTS=1`, reserved for the post-merge first
live activation canary, and `MAX_CREATE_ATTEMPTS_PER_SESSION` stays 1. Merging
dormant capability grants no live authority, keeps live trading disabled and
startup A0_DISABLED, and does not weaken any live-runtime safeguard. The strategy
qualification prerequisite remains a hard Gate-C/live-activation blocker only; it
is not a dormant-merge blocker. Producing genuine qualification evidence depends on
a separately gated external historical research bridge (S10-DATA-02) that WP175
neither implements nor depends on.
