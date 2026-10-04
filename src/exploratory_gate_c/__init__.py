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

# Import-safe lazy facade: importing this package loads neither its submodules nor their
# consumed dependency chains (STRAT-LIFE, Hermes manager, EXEC-FEAS). A public name is
# resolved from its submodule only on first attribute access (PEP 562).
_EVALUATOR_NAMES = frozenset(
    {
        "EXPLORATORY_RISK_BAND",
        "PERMIT_COMPATIBLE_HERMES_ACTIONS",
        "build_exploratory_gate_c_permit",
        "evaluate_exploratory_gate_c",
    }
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


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if name in _EVALUATOR_NAMES:
        from . import evaluator as module
    else:
        from . import models as module
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
