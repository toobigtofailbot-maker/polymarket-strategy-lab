"""Current public execution-feasibility core (S10-EXEC-FEAS-01).

Answers one narrow question: can this exact proposed execution intent be mechanically
supported by currently observable public Polymarket venue state, and which execution
frictions or unknowns are visible? It binds one exact StrategyVersion read-only, reads
two fixed public GET endpoints only on an explicit foreground call, and produces three
immutable content-addressed records. It persists nothing and has no account, Gate-C,
order, execution or live authority. It is not WP172 executable-edge evidence and makes
no profitability claim.
"""

from .evaluator import assess_execution_feasibility, validate_execution_feasibility_assessment
from .models import (
    DIAGNOSTIC_CODES,
    EXECUTION_DIMENSION_STATES,
    EXECUTION_FEASIBILITY_STATUSES,
    EXECUTION_STYLES,
    FEE_EXACTNESS,
    ORDER_TYPES,
    RECORD_KINDS,
    SIDES,
    SOURCE_STATES,
    ExecutionFeasibilityAssessment,
    ExecutionFeasibilityError,
    ExecutionIntent,
    PublicExecutionVenueSnapshot,
    build_execution_intent,
    record_from_mapping,
    validate_execution_intent,
    validate_public_venue_snapshot,
)
from .public_market import fetch_public_venue_snapshot

__all__ = [
    "DIAGNOSTIC_CODES",
    "EXECUTION_DIMENSION_STATES",
    "EXECUTION_FEASIBILITY_STATUSES",
    "EXECUTION_STYLES",
    "FEE_EXACTNESS",
    "ORDER_TYPES",
    "RECORD_KINDS",
    "SIDES",
    "SOURCE_STATES",
    "ExecutionFeasibilityAssessment",
    "ExecutionFeasibilityError",
    "ExecutionIntent",
    "PublicExecutionVenueSnapshot",
    "assess_execution_feasibility",
    "build_execution_intent",
    "fetch_public_venue_snapshot",
    "record_from_mapping",
    "validate_execution_feasibility_assessment",
    "validate_execution_intent",
    "validate_public_venue_snapshot",
]
