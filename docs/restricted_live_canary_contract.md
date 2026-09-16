# WP175 Restricted Live Canary Contract

WP175 is a protected, manual-foreground canary, not mature live trading. The
implementation is limited to one strategy, one binary market, one LIMIT order,
one create attempt, and one active operator session. A3 is entered only after
an exact-head, short-lived, single-use manual arm receipt. Process restart
always returns the gateway to `A0_DISABLED` and requires authoritative
reconciliation before a new arm.

The Gate-C boundary consumes an already authenticated WP174B `GateBSession`.
The raw SDK client and ephemeral credentials remain private to Gate-B. The
only new venue mutation is a separately built and signed LIMIT order followed
by exactly one `post_order` call. A durable `GATE_C_CREATE_STARTED` event is
committed before that call. Accepted or possibly transmitted attempts are
never retried; ambiguous outcomes halt the canary and require reconciliation.
Resting accepted orders use the existing durable Gate-B cancellation path.

Hard maxima are fixed in code: wallet 50.00 pUSD, gross exposure 20.00 pUSD,
per-market exposure 15.00 pUSD, per-order committed 10.00 pUSD, one market,
one open order, one create attempt, a 30-minute session, daily realized loss
5.00 pUSD, drawdown 7.50 pUSD, and cumulative loss 10.00 pUSD. No config,
environment, browser, strategy, Hermes input, or venue response can widen
these values. Only fresh official `blocked=false` geoblock evidence permits
new exposure; cancellation remains available when new exposure is blocked.

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
