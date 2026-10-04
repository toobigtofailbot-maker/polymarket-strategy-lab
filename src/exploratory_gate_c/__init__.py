"""Exploratory Gate-C policy-permit core (S10-GATE-C-EXPLORE-01).

The first V2.1 deterministic exploratory execution-eligibility Gate C. Given the current
verified STRAT-LIFE lifecycle/policy state, the latest canonical Hermes strategy judgment
and the exact current-public EXEC-FEAS evidence for one execution intent, it decides
whether that exact intent may proceed to later runtime/account/access/reconciliation
checks inside the current human-authorized exploratory envelope.

It produces an immutable content-addressed ``ExploratoryGateCDecision`` and, only when
eligible, an exact-intent ``ExploratoryGateCPermit``. This is eligibility authority only:
no network/account/access read, credential, signing, order, execution transport,
persistence, scheduler or live authority, and it is separate from the legacy WP175
manual restricted-live canary path. Capital/orders remain USD 0 / 0.
"""

from .evaluator import (
    EXPLORATORY_RISK_BAND,
    PERMIT_COMPATIBLE_HERMES_ACTIONS,
    build_exploratory_gate_c_permit,
    evaluate_exploratory_gate_c,
)
from .models import (
    DECISION_STATUSES,
    ERROR_CODES,
    PERMIT_COMPATIBLE_FEASIBILITY_STATUSES,
    PERMIT_ELIGIBLE,
    PERMIT_REJECTED,
    REASON_CODES,
    ExploratoryGateCDecision,
    ExploratoryGateCError,
    ExploratoryGateCPermit,
    record_from_mapping,
    validate_exploratory_gate_c_decision,
    validate_exploratory_gate_c_permit,
)

__all__ = [
    "DECISION_STATUSES",
    "ERROR_CODES",
    "EXPLORATORY_RISK_BAND",
    "PERMIT_COMPATIBLE_FEASIBILITY_STATUSES",
    "PERMIT_COMPATIBLE_HERMES_ACTIONS",
    "PERMIT_ELIGIBLE",
    "PERMIT_REJECTED",
    "REASON_CODES",
    "ExploratoryGateCDecision",
    "ExploratoryGateCError",
    "ExploratoryGateCPermit",
    "build_exploratory_gate_c_permit",
    "evaluate_exploratory_gate_c",
    "record_from_mapping",
    "validate_exploratory_gate_c_decision",
    "validate_exploratory_gate_c_permit",
]
