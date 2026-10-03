"""Focused tests for the S10-STRAT-LIFE-01 strategy lifecycle core (R001-R057)."""

from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
import importlib
import json
import os
from pathlib import Path
import sqlite3

import pytest

from src.strategy_lifecycle import (
    PORTFOLIO_CAPACITY_REJECTED,
    PORTFOLIO_CAPACITY_VALID,
    STORE_APPLICATION_ID,
    PortfolioAuthorityPolicy,
    StrategyFamily,
    StrategyLifecycleError,
    StrategyLifecycleSnapshot,
    StrategyRiskAllocation,
    StrategyVersion,
    append_strategy_lifecycle_record,
    build_portfolio_authority_policy,
    build_portfolio_policy_receipt,
    build_strategy_family,
    build_strategy_health_receipt,
    build_strategy_restriction_receipt,
    build_strategy_risk_allocation,
    build_strategy_version,
    canonical_json_bytes,
    derive_adaptation_class,
    derive_inherited_risk_band_ceiling,
    evaluate_portfolio_capacity,
    initialize_strategy_lifecycle_store,
    load_strategy_lifecycle_store,
)
from src.strategy_lifecycle import models as M
from src.strategy_lifecycle import policy as P
from src.strategy_lifecycle import store as S


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "strategy_lifecycle"
SPEC = ROOT / "docs" / "wp_specs" / "S10-STRAT-LIFE-01" / "wp_spec.json"
HEX = "a" * 64

BASE_SPEC = {
    "thesis": {"claim": "mean reversion after overreaction"},
    "universe": {"category": "weather"},
    "entry_rule": {"signal": "zscore_above"},
    "exit_rule": {"horizon": "resolution"},
    "execution_rule": {"style": "PASSIVE_MAKER"},
    "parameters": {"lookback": 5, "edge": "0.5", "mode": "A", "fixed": 7},
}
BASE_BOUNDS = {
    "lookback": {"kind": "INTEGER_RANGE", "min": 0, "max": 10},
    "edge": {"kind": "DECIMAL_RANGE", "min": "0.1", "max": "0.9"},
    "mode": {"kind": "ENUM", "values": ["A", "B"]},
}
LIMITS = {
    "global_capital_at_risk_max_usd": "1000",
    "global_gross_exposure_max_usd": "1000",
    "global_daily_loss_max_usd": "100",
    "global_drawdown_max_usd": "200",
    "global_cumulative_loss_max_usd": "300",
    "exploratory_pool_max_usd": "300",
    "validated_pool_max_usd": "300",
    "mature_pool_max_usd": "300",
    "max_exploratory_per_strategy_usd": "100",
    "max_validated_per_strategy_usd": "200",
    "max_mature_per_strategy_usd": "300",
    "max_per_market_usd": "50",
    "max_order_notional_usd": "10",
    "max_active_strategies": 3,
    "max_active_markets": 10,
    "max_simultaneous_open_orders": 20,
    "max_mutations_per_minute": 60,
}


# ---------------------------------------------------------------------------
# Builders and helpers.
# ---------------------------------------------------------------------------


def code_of(fn, *args, **kwargs) -> str:
    with pytest.raises(StrategyLifecycleError) as excinfo:
        fn(*args, **kwargs)
    return excinfo.value.code


def family(key: str = "alpha.family", t: int = 1) -> StrategyFamily:
    return build_strategy_family(
        family_key=key, family_label="Alpha family", created_time_ns=t,
        creation_provenance="unit:fixture",
    )


def spec_with(**changes: object) -> dict:
    spec = json.loads(json.dumps(BASE_SPEC))
    for key, value in changes.items():
        spec[key] = value
    return spec


def params(**changes: object) -> dict:
    values = dict(BASE_SPEC["parameters"])
    values.update(changes)
    return spec_with(parameters=values)


def version(
    fam: StrategyFamily,
    *,
    parent: StrategyVersion | None = None,
    spec: dict | str | None = None,
    bounds: dict | str | None = None,
    posture: str = "REPEATABLE_STATISTICAL",
    code: str = "strategy_code:v1",
    label: str = "version",
    refs: tuple[str, ...] = (),
    t: int = 2,
) -> StrategyVersion:
    return build_strategy_version(
        strategy_family_id=fam.strategy_family_id,
        parent=parent,
        strategy_label=label,
        evidence_posture=posture,
        strategy_code_identity=code,
        strategy_spec=BASE_SPEC if spec is None else spec,
        adaptive_bounds=BASE_BOUNDS if bounds is None else bounds,
        evidence_refs=refs,
        created_time_ns=t,
        creation_provenance="unit:fixture",
    )


def child_class(parent: StrategyVersion, fam: StrategyFamily, **kwargs: object) -> str:
    return version(fam, parent=parent, t=3, **kwargs).adaptation_class  # type: ignore[arg-type]


def policy(
    *, label: str = "Global envelope", created: int = 10, effective: int = 10,
    expires: int | None = None, styles=("PASSIVE_MAKER", "AGGRESSIVE_TAKER"),
    account: str = "account:public-scope-1", predecessor: str | None = None, **limits: object,
) -> PortfolioAuthorityPolicy:
    values = dict(LIMITS)
    values.update(limits)
    return build_portfolio_authority_policy(
        predecessor_policy_id=predecessor, policy_label=label, account_scope_ref=account,
        effective_from_ns=effective, expires_at_ns=expires, allowed_order_styles=styles,
        created_time_ns=created, **values,
    )


def activate(pol: PortfolioAuthorityPolicy, previous: str | None = None, t: int = 20):
    return build_portfolio_policy_receipt(
        action="ACTIVATE", policy_id=pol.policy_id, previous_active_policy_id=previous,
        human_authorization_ref="human:karl-approval-1", created_time_ns=t,
    )


def revoke(pol: PortfolioAuthorityPolicy, t: int = 30):
    return build_portfolio_policy_receipt(
        action="REVOKE", policy_id=pol.policy_id, previous_active_policy_id=pol.policy_id,
        human_authorization_ref="human:karl-revoke-1", created_time_ns=t,
    )


def allocation(
    ver: StrategyVersion, pol: PortfolioAuthorityPolicy, *, band: str = "EXPLORATORY_LIVE",
    budget: str = "50", basis: str = "DIRECT_DECISION", start: int = 100,
    end: int | None = None, t: int = 100, refs: tuple[str, ...] = (),
) -> StrategyRiskAllocation:
    return build_strategy_risk_allocation(
        strategy_version_id=ver.strategy_version_id, policy_id=pol.policy_id, risk_band=band,
        active_budget_usd=budget, allocation_basis=basis, decision_ref="decision:unit-1",
        evidence_refs=refs, valid_from_ns=start, valid_until_ns=end, created_time_ns=t,
    )


def health(ver: StrategyVersion, previous: str, new: str, t: int = 50):
    return build_strategy_health_receipt(
        strategy_version_id=ver.strategy_version_id, previous_health_state=previous,
        new_health_state=new, decision_ref="decision:health-1", created_time_ns=t,
    )


def restriction(
    ver: StrategyVersion, *, key: str = "pause.1", action: str = "APPLY",
    kind: str = "PAUSE_NEW_EXPOSURE", cap: str | None = None, t: int = 60,
):
    return build_strategy_restriction_receipt(
        strategy_version_id=ver.strategy_version_id, restriction_key=key, action=action,
        restriction_kind=kind, max_active_budget_usd=cap, decision_ref="decision:restrict-1",
        created_time_ns=t,
    )


def rebuilt(record, **changes):
    """Recompute a record's content ID after a deliberate field change (test-only)."""

    return replace(record, **{record.ID_FIELD: M._PENDING_ID}, **changes)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    path = tmp_path / "lifecycle.sqlite3"
    assert initialize_strategy_lifecycle_store(path).status == "STORE_INITIALIZED"
    return path


def ok(path: Path, record):
    result = append_strategy_lifecycle_record(path, record)
    assert result.is_valid, result.error_codes
    return result


def err(path: Path, record) -> str:
    result = append_strategy_lifecycle_record(path, record)
    assert not result.is_valid and result.status == "STORE_REJECTED"
    assert result.snapshot is None
    return result.error_codes[0]


def snap(path: Path) -> StrategyLifecycleSnapshot:
    result = load_strategy_lifecycle_store(path)
    assert result.status == "STORE_LOADED_VERIFIED", result.error_codes
    return result.snapshot  # type: ignore[return-value]


def seeded(path: Path, **policy_limits: object):
    fam = family()
    root = version(fam)
    pol = policy(**policy_limits)
    for record in (fam, root, pol, activate(pol)):
        ok(path, record)
    return fam, root, pol


def extra_roots(path: Path, fam: StrategyFamily, count: int) -> list[StrategyVersion]:
    roots = []
    for index in range(count):
        ver = version(fam, code=f"strategy_code:extra{index}", label=f"extra {index}")
        ok(path, ver)
        roots.append(ver)
    return roots


def tamper(path: Path, sql: str, params_: tuple = ()) -> None:
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.execute("DROP TRIGGER lifecycle_records_no_update")
        connection.execute(sql, params_)
        connection.execute(S._EXPECTED_OBJECTS[("trigger", "lifecycle_records_no_update")])
    finally:
        connection.close()


def rows(path: Path) -> list[tuple]:
    connection = sqlite3.connect(path)
    try:
        return connection.execute(
            "SELECT sequence_number, record_kind, record_id, payload_json, payload_sha256,"
            " previous_entry_hash, entry_hash FROM lifecycle_records ORDER BY sequence_number"
        ).fetchall()
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Identity / canonicalization (R001-R006).
# ---------------------------------------------------------------------------


def test_family_identity_is_deterministic() -> None:
    first, second = family(), family()
    assert first == second
    assert first.strategy_family_id.startswith("strategyfamily:sha256:")
    preimage = {k: v for k, v in first.to_mapping().items() if k != "strategy_family_id"}
    expected = hashlib.sha256(
        json.dumps(preimage, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert first.strategy_family_id == "strategyfamily:sha256:" + expected
    assert family(key="other.family").strategy_family_id != first.strategy_family_id
    assert StrategyFamily.from_mapping(first.to_mapping()) == first


def test_family_forged_id_rejects() -> None:
    mapping = family().to_mapping()
    forged = dict(mapping, strategy_family_id="strategyfamily:sha256:" + HEX)
    assert code_of(StrategyFamily.from_mapping, forged) == "IDENTITY_CONFLICT"
    relabeled = dict(mapping, family_label="Different label")
    assert code_of(StrategyFamily.from_mapping, relabeled) == "IDENTITY_CONFLICT"
    for bad in ("strategyversion:sha256:" + HEX, "strategyfamily:sha256:XYZ", ""):
        assert code_of(StrategyFamily.from_mapping, dict(mapping, strategy_family_id=bad)) == "FIELD_VALUE_INVALID"
    assert code_of(StrategyFamily.from_mapping, dict(mapping, strategy_family_id=None)) == "FIELD_TYPE_INVALID"
    assert code_of(family, key="Bad Key") == "FIELD_VALUE_INVALID"
    assert code_of(family, key="x" * 129) == "FIELD_VALUE_INVALID"


def test_strategy_version_identity_is_deterministic() -> None:
    fam = family()
    reordered = dict(reversed(list(BASE_SPEC.items())))
    first = version(fam, refs=("ref:b", "ref:a"))
    second = version(fam, spec=reordered, refs=("ref:a", "ref:b"))
    assert first == second
    assert first.strategy_version_id.startswith("strategyversion:sha256:")
    assert first.evidence_refs == ("ref:a", "ref:b")
    assert StrategyVersion.from_mapping(first.to_mapping()) == first
    assert version(fam, label="other").strategy_version_id != first.strategy_version_id


def test_float_nan_and_unknown_fields_reject() -> None:
    fam = family()
    assert code_of(version, fam, spec=params(edge=0.5)) == "FIELD_TYPE_INVALID"
    float_text = M.canonical_json_text(BASE_SPEC).replace('"edge":"0.5"', '"edge":0.5')
    assert code_of(version, fam, spec=float_text) == "FIELD_TYPE_INVALID"
    nan_text = M.canonical_json_text(BASE_SPEC).replace('"fixed":7', '"fixed":NaN')
    assert code_of(version, fam, spec=nan_text) == "FIELD_TYPE_INVALID"
    duplicate = M.canonical_json_text(BASE_SPEC).replace('{"claim"', '{"claim":"x","claim"')
    assert code_of(version, fam, spec=duplicate) == "FIELD_VALUE_INVALID"
    assert code_of(M.canonical_json_text, {"x": float("nan")}) == "FIELD_TYPE_INVALID"
    mapping = version(fam).to_mapping()
    assert code_of(StrategyVersion.from_mapping, dict(mapping, human_approval_ref="human:x")) == "FIELD_VALUE_INVALID"
    missing = dict(mapping)
    del missing["strategy_label"]
    assert code_of(StrategyVersion.from_mapping, missing) == "FIELD_VALUE_INVALID"
    assert code_of(StrategyVersion.from_mapping, dict(mapping, created_time_ns=True)) == "FIELD_TYPE_INVALID"
    assert code_of(StrategyVersion.from_mapping, dict(mapping, created_time_ns=2.0)) == "FIELD_TYPE_INVALID"
    assert code_of(StrategyVersion.from_mapping, dict(mapping, strategy_label=None)) == "FIELD_TYPE_INVALID"
    assert code_of(StrategyVersion.from_mapping, dict(mapping, schema_id="other")) == "FIELD_VALUE_INVALID"
    assert code_of(StrategyVersion.from_mapping, dict(mapping, evidence_refs="ref:a")) == "FIELD_TYPE_INVALID"
    assert code_of(StrategyVersion.from_mapping, [mapping]) == "FIELD_TYPE_INVALID"
    pol = policy()
    alloc = allocation(version(fam), pol).to_mapping()
    assert code_of(StrategyRiskAllocation.from_mapping, dict(alloc, per_strategy_human_approval="yes")) == "FIELD_VALUE_INVALID"
    assert "human_approval" not in " ".join(alloc)
    assert code_of(M.record_from_mapping, "UNKNOWN_KIND", alloc) == "FIELD_VALUE_INVALID"


def test_strategy_spec_json_must_be_canonical() -> None:
    fam = family()
    canonical = M.canonical_json_text(BASE_SPEC)
    assert version(fam, spec=canonical).strategy_spec_json == canonical
    assert canonical == json.dumps(BASE_SPEC, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert code_of(version, fam, spec=json.dumps(BASE_SPEC)) == "FIELD_VALUE_INVALID"
    missing = {k: v for k, v in BASE_SPEC.items() if k != "exit_rule"}
    assert code_of(version, fam, spec=missing) == "FIELD_VALUE_INVALID"
    assert code_of(version, fam, spec=spec_with(extra={})) == "FIELD_VALUE_INVALID"
    assert code_of(version, fam, spec=spec_with(thesis="text")) == "FIELD_VALUE_INVALID"
    assert code_of(version, fam, spec=spec_with(parameters={"BadName": 1}), bounds={}) == "FIELD_VALUE_INVALID"
    assert code_of(version, fam, spec="[]") == "FIELD_VALUE_INVALID"
    assert code_of(version, fam, spec=spec_with(thesis={"blob": "x" * 70_000})) == "LIMIT_EXCEEDED"
    deep: dict = {}
    cursor = deep
    for _ in range(9):
        cursor["n"] = {}
        cursor = cursor["n"]
    assert code_of(version, fam, spec=spec_with(thesis=deep)) == "LIMIT_EXCEEDED"
    assert code_of(version, fam, spec=spec_with(thesis={"list": [0] * 4100})) == "LIMIT_EXCEEDED"
    many = {f"p{i}": i for i in range(257)}
    assert code_of(version, fam, spec=spec_with(parameters=many), bounds={}) == "LIMIT_EXCEEDED"
    assert code_of(version, fam, bounds={"unknown": BASE_BOUNDS["lookback"]}) == "FIELD_VALUE_INVALID"
    for bad_bound in (
        {"kind": "INTEGER_RANGE", "min": 5, "max": 1},
        {"kind": "INTEGER_RANGE", "min": True, "max": 3},
        {"kind": "DECIMAL_RANGE", "min": "0.10", "max": "0.9"},
        {"kind": "DECIMAL_RANGE", "min": "0.9", "max": "0.1"},
        {"kind": "ENUM", "values": ["A", "A"]},
        {"kind": "ENUM", "values": []},
        {"kind": "RANGE", "min": 0, "max": 1},
        {"kind": "INTEGER_RANGE", "min": 0, "max": 1, "step": 1},
    ):
        assert code_of(version, fam, bounds={"lookback": bad_bound}) in {"FIELD_VALUE_INVALID", "FIELD_TYPE_INVALID"}
    assert version(fam, bounds={}).adaptive_bounds_json == "{}"


def test_unsafe_refs_and_secret_like_refs_reject() -> None:
    fam = family()
    for bad in (
        "../escape", "dir/file", "dir\\file", "C:evidence", "~home", ".hidden", "", "x" * 300,
        "has space", "file://x", "ref..parent",
    ):
        assert code_of(M.opaque_ref, bad) == "FIELD_VALUE_INVALID", bad
        assert code_of(version, fam, refs=(bad,)) == "FIELD_VALUE_INVALID", bad
    for secret in (
        "my-secret-ref", "PASSWORD:1", "pass_word.ref", "Api-Key:abc", "APIKEY:abc",
        "wallet:0x" + "f" * 64, "Mnemonic:words", "private_key:1", "bearer:abc",
    ):
        assert code_of(M.opaque_ref, secret) == "FIELD_VALUE_INVALID", secret
    for safe in (
        "researchepisode:sha256:" + HEX, "wallet:0x" + "b" * 40, "git:abc123",
        "alphafactory:candidate:1", "decision:hermes-2026-10-02",
    ):
        assert M.opaque_ref(safe) == safe
    assert code_of(M.opaque_ref, 7) == "FIELD_TYPE_INVALID"
    assert code_of(version, fam, refs=("ref:a", "ref:a")) == "FIELD_VALUE_INVALID"
    assert code_of(version, fam, refs=tuple(f"ref:{i:04d}" for i in range(257))) == "LIMIT_EXCEEDED"
    assert code_of(version, fam, refs=(1,)) == "FIELD_TYPE_INVALID"
    assert code_of(version, fam, code="../code") == "FIELD_VALUE_INVALID"
    unsorted = dict(version(fam, refs=("ref:a", "ref:b")).to_mapping(), evidence_refs=["ref:b", "ref:a"])
    assert code_of(StrategyVersion.from_mapping, unsorted) == "FIELD_VALUE_INVALID"


# ---------------------------------------------------------------------------
# Adaptation classification (R007-R018).
# ---------------------------------------------------------------------------


def test_root_classification() -> None:
    fam = family()
    root = version(fam)
    assert root.adaptation_class == "ROOT"
    assert root.parent_strategy_version_id is None
    assert derive_adaptation_class(root, None) == "ROOT"
    mapping = root.to_mapping()
    assert code_of(StrategyVersion.from_mapping, dict(mapping, adaptation_class="MATERIAL_ADAPTATION")) == "ADAPTATION_INVALID"
    assert code_of(StrategyVersion.from_mapping, dict(mapping, adaptation_class="UNKNOWN")) == "FIELD_VALUE_INVALID"
    child = version(fam, parent=root, spec=params(lookback=6), t=3)
    assert code_of(StrategyVersion.from_mapping, dict(child.to_mapping(), adaptation_class="ROOT")) == "ADAPTATION_INVALID"
    assert code_of(
        build_strategy_version, strategy_family_id=fam.strategy_family_id, parent=None,
        strategy_label="x", evidence_posture="NOVEL_EXPLORATORY", strategy_code_identity="c:1",
        strategy_spec=BASE_SPEC, adaptive_bounds=BASE_BOUNDS, created_time_ns=1,
        creation_provenance="unit:x", adaptation_class="BOUNDED_ADAPTATION",
    ) == "ADAPTATION_INVALID"
    assert code_of(derive_adaptation_class, child, None) == "REFERENCE_INVALID"


def test_bounded_integer_change_is_bounded() -> None:
    fam = family()
    root = version(fam)
    for value in (6, 0, 10):
        assert child_class(root, fam, spec=params(lookback=value)) == "BOUNDED_ADAPTATION"
    child = version(fam, parent=root, spec=params(lookback=9), t=3)
    assert derive_adaptation_class(child, root) == "BOUNDED_ADAPTATION"


def test_bounded_decimal_change_is_bounded() -> None:
    fam = family()
    root = version(fam)
    for value in ("0.9", "0.1", "0.25"):
        assert child_class(root, fam, spec=params(edge=value)) == "BOUNDED_ADAPTATION"


def test_bounded_enum_change_is_bounded() -> None:
    fam = family()
    root = version(fam)
    assert child_class(root, fam, spec=params(mode="B")) == "BOUNDED_ADAPTATION"
    assert child_class(root, fam, spec=params(mode="B", lookback=1, edge="0.2")) == "BOUNDED_ADAPTATION"


def test_out_of_range_adaptive_change_is_material() -> None:
    fam = family()
    root = version(fam)
    for spec in (
        params(lookback=11), params(lookback=-1), params(lookback="5"), params(edge="0.95"),
        params(edge="0.09"), params(edge="0.50"), params(mode="C"), params(mode=1),
    ):
        assert child_class(root, fam, spec=spec) == "MATERIAL_ADAPTATION"


def test_non_adaptive_parameter_change_is_material() -> None:
    fam = family()
    root = version(fam)
    assert child_class(root, fam, spec=params(fixed=8)) == "MATERIAL_ADAPTATION"
    assert child_class(root, fam, spec=params(lookback=6, fixed=8)) == "MATERIAL_ADAPTATION"
    added = params(new_param=1)
    assert child_class(root, fam, spec=added) == "MATERIAL_ADAPTATION"
    removed = spec_with(parameters={k: v for k, v in BASE_SPEC["parameters"].items() if k != "fixed"})
    assert child_class(root, fam, spec=removed) == "MATERIAL_ADAPTATION"


def test_rule_posture_and_code_identity_changes_are_material() -> None:
    fam = family()
    root = version(fam)
    for key in ("thesis", "universe", "entry_rule", "exit_rule", "execution_rule"):
        assert child_class(root, fam, spec=spec_with(**{key: {"changed": True}})) == "MATERIAL_ADAPTATION", key
    assert child_class(root, fam, posture="EVENT_INFORMATION") == "MATERIAL_ADAPTATION"
    assert child_class(root, fam, code="strategy_code:v2") == "MATERIAL_ADAPTATION"
    assert child_class(root, fam, code="strategy_code:v2", spec=params(lookback=6)) == "MATERIAL_ADAPTATION"


def test_adaptive_bound_change_is_material() -> None:
    fam = family()
    root = version(fam)
    widened = dict(BASE_BOUNDS, lookback={"kind": "INTEGER_RANGE", "min": 0, "max": 20})
    assert child_class(root, fam, bounds=widened, spec=params(lookback=6)) == "MATERIAL_ADAPTATION"
    assert child_class(root, fam, bounds=widened) == "MATERIAL_ADAPTATION"
    added = dict(BASE_BOUNDS, fixed={"kind": "INTEGER_RANGE", "min": 0, "max": 9})
    assert child_class(root, fam, bounds=added, spec=params(fixed=8)) == "MATERIAL_ADAPTATION"
    removed = {k: v for k, v in BASE_BOUNDS.items() if k != "mode"}
    assert child_class(root, fam, bounds=removed) == "MATERIAL_ADAPTATION"
    reordered_enum = dict(BASE_BOUNDS, mode={"kind": "ENUM", "values": ["B", "A"]})
    assert child_class(root, fam, bounds=reordered_enum) == "MATERIAL_ADAPTATION"


def test_noop_child_rejects(store: Path) -> None:
    fam = family()
    root = version(fam)
    assert code_of(version, fam, parent=root, t=3) == "ADAPTATION_INVALID"
    assert code_of(version, fam, parent=root, t=3, label="relabeled", refs=("ref:new",)) == "ADAPTATION_INVALID"
    seed = version(fam, parent=root, spec=params(lookback=6), t=3)
    noop = rebuilt(seed, strategy_spec_json=root.strategy_spec_json)
    assert code_of(derive_adaptation_class, noop, root) == "ADAPTATION_INVALID"
    ok(store, fam)
    ok(store, root)
    assert err(store, noop) == "ADAPTATION_INVALID"
    lying = rebuilt(seed, adaptation_class="MATERIAL_ADAPTATION")
    assert err(store, lying) == "ADAPTATION_INVALID"


def test_missing_parent_and_cross_family_child_reject(store: Path) -> None:
    fam, other = family(), family(key="beta.family")
    root = version(fam)
    assert code_of(version, other, parent=root, spec=params(lookback=6), t=3) == "LINEAGE_INVALID"
    child = version(fam, parent=root, spec=params(lookback=6), t=3)
    ok(store, fam)
    ok(store, other)
    assert err(store, child) == "REFERENCE_INVALID"
    ok(store, root)
    cross = rebuilt(child, strategy_family_id=other.strategy_family_id)
    assert err(store, cross) == "LINEAGE_INVALID"
    assert code_of(derive_adaptation_class, cross, root) == "LINEAGE_INVALID"
    early = rebuilt(child, created_time_ns=1)
    assert err(store, early) == "LINEAGE_INVALID"
    orphan = version(family(key="gamma.family"))
    assert err(store, orphan) == "REFERENCE_INVALID"
    wrong_parent = rebuilt(child, parent_strategy_version_id="strategyversion:sha256:" + HEX)
    assert err(store, wrong_parent) == "REFERENCE_INVALID"
    assert code_of(derive_adaptation_class, wrong_parent, root) == "LINEAGE_INVALID"
    ok(store, child)


def test_bounded_child_inherits_parent_band_ceiling() -> None:
    for band in M.RISK_BANDS:
        assert derive_inherited_risk_band_ceiling(band, "BOUNDED_ADAPTATION") == band


def test_material_child_inheritance_capped_at_exploratory() -> None:
    expected = {
        "PAPER": "PAPER",
        "EXPLORATORY_LIVE": "EXPLORATORY_LIVE",
        "VALIDATED_LIVE": "EXPLORATORY_LIVE",
        "MATURE_LIVE": "EXPLORATORY_LIVE",
    }
    for band, ceiling in expected.items():
        assert derive_inherited_risk_band_ceiling(band, "MATERIAL_ADAPTATION") == ceiling
    assert derive_inherited_risk_band_ceiling(None, "ROOT") is None
    assert code_of(derive_inherited_risk_band_ceiling, "PAPER", "ROOT") == "LINEAGE_INVALID"
    assert code_of(derive_inherited_risk_band_ceiling, "LIVE", "MATERIAL_ADAPTATION") == "FIELD_VALUE_INVALID"
    assert code_of(derive_inherited_risk_band_ceiling, None, "BOUNDED_ADAPTATION") == "FIELD_VALUE_INVALID"
    assert code_of(derive_inherited_risk_band_ceiling, "PAPER", "OTHER") == "FIELD_VALUE_INVALID"


# ---------------------------------------------------------------------------
# Portfolio policy (R019-R024).
# ---------------------------------------------------------------------------


def test_policy_identity_is_deterministic() -> None:
    first = policy()
    second = policy(styles=("AGGRESSIVE_TAKER", "PASSIVE_MAKER"))
    assert first == second
    assert first.policy_id.startswith("portfolioauthoritypolicy:sha256:")
    assert first.allowed_order_styles == ("AGGRESSIVE_TAKER", "PASSIVE_MAKER")
    assert first.venue_scope == ("POLYMARKET",)
    assert PortfolioAuthorityPolicy.from_mapping(first.to_mapping()) == first
    assert policy(label="Other envelope").policy_id != first.policy_id
    assert policy(styles=("PASSIVE_MAKER",)).allowed_order_styles == ("PASSIVE_MAKER",)
    assert not any("approval" in name for name in first.to_mapping())


def test_policy_malformed_numbers_reject() -> None:
    for bad in ("01", "1.50", "-1", "1e3", " 1", "", "1.", ".5", "NaN", "1,000"):
        assert code_of(policy, global_daily_loss_max_usd=bad) == "FIELD_VALUE_INVALID", bad
    assert code_of(policy, global_daily_loss_max_usd=1.5) == "FIELD_TYPE_INVALID"
    assert code_of(policy, global_daily_loss_max_usd=100) == "FIELD_TYPE_INVALID"
    assert code_of(policy, max_active_strategies=True) == "FIELD_TYPE_INVALID"
    assert code_of(policy, max_active_strategies="3") == "FIELD_TYPE_INVALID"
    assert code_of(policy, max_active_strategies=-1) == "FIELD_VALUE_INVALID"
    assert code_of(policy, max_mutations_per_minute=None) == "FIELD_TYPE_INVALID"
    values = dict(LIMITS)
    del values["max_active_markets"]
    assert code_of(
        build_portfolio_authority_policy, policy_label="x", account_scope_ref="account:1",
        effective_from_ns=1, expires_at_ns=None, allowed_order_styles=("PASSIVE_MAKER",),
        created_time_ns=1, **values,
    ) == "FIELD_VALUE_INVALID"
    assert policy(global_daily_loss_max_usd="0").global_daily_loss_max_usd == "0"


def test_policy_pool_sum_over_global_rejects() -> None:
    assert code_of(policy, mature_pool_max_usd="401") == "POLICY_INVALID"
    assert code_of(policy, global_capital_at_risk_max_usd="899") == "POLICY_INVALID"
    assert policy(global_capital_at_risk_max_usd="900").global_capital_at_risk_max_usd == "900"


def test_policy_per_strategy_over_pool_rejects() -> None:
    assert code_of(policy, max_exploratory_per_strategy_usd="301") == "POLICY_INVALID"
    assert code_of(policy, max_validated_per_strategy_usd="300.01") == "POLICY_INVALID"
    assert code_of(policy, max_mature_per_strategy_usd="301") == "POLICY_INVALID"


def test_policy_order_over_market_rejects() -> None:
    assert code_of(policy, max_order_notional_usd="51") == "POLICY_INVALID"
    assert code_of(policy, max_per_market_usd="1001") == "POLICY_INVALID"
    assert policy(max_order_notional_usd="50").max_order_notional_usd == "50"


def test_policy_time_style_account_venue_reject() -> None:
    assert code_of(policy, created=11, effective=10) == "POLICY_INVALID"
    assert code_of(policy, expires=10) == "POLICY_INVALID"
    assert code_of(policy, expires=9) == "POLICY_INVALID"
    assert code_of(policy, effective=-1) == "FIELD_VALUE_INVALID"
    assert code_of(policy, expires=True) == "FIELD_TYPE_INVALID"
    assert code_of(policy, styles=()) == "FIELD_VALUE_INVALID"
    assert code_of(policy, styles=("MARKET_ORDER",)) == "FIELD_VALUE_INVALID"
    assert code_of(policy, styles=("PASSIVE_MAKER", "PASSIVE_MAKER")) == "FIELD_VALUE_INVALID"
    assert code_of(policy, styles="PASSIVE_MAKER") == "FIELD_TYPE_INVALID"
    reordered = dict(policy().to_mapping(), allowed_order_styles=["PASSIVE_MAKER", "AGGRESSIVE_TAKER"])
    assert code_of(PortfolioAuthorityPolicy.from_mapping, reordered) == "FIELD_VALUE_INVALID"
    for account in ("account:api_key=1", "../account", "wallet:0x" + "c" * 64, "Secret-Account"):
        assert code_of(policy, account=account) == "FIELD_VALUE_INVALID"
    assert policy(account="wallet:0x" + "c" * 40).account_scope_ref == "wallet:0x" + "c" * 40
    for venue in (("KALSHI",), ("POLYMARKET", "POLYMARKET"), ()):
        assert code_of(
            build_portfolio_authority_policy, policy_label="x", account_scope_ref="account:1",
            effective_from_ns=1, expires_at_ns=None, allowed_order_styles=("PASSIVE_MAKER",),
            created_time_ns=1, venue_scope=venue, **LIMITS,
        ) == "FIELD_VALUE_INVALID"
    assert code_of(policy, predecessor="not-a-policy") == "FIELD_VALUE_INVALID"
    assert policy(expires=11).expires_at_ns == 11


# ---------------------------------------------------------------------------
# Store (R025-R033).
# ---------------------------------------------------------------------------


def test_store_initialize_and_already_initialized(tmp_path: Path) -> None:
    path = tmp_path / "fresh.sqlite3"
    first = initialize_strategy_lifecycle_store(path)
    assert first.status == "STORE_INITIALIZED" and first.is_valid
    empty = first.snapshot
    assert empty.total_rows == 0 and empty.store_head_entry_hash is None
    assert empty.active_policy_id is None and empty.families == ()
    second = initialize_strategy_lifecycle_store(path)
    assert second.status == "STORE_ALREADY_INITIALIZED"
    assert load_strategy_lifecycle_store(path).status == "STORE_LOADED_VERIFIED"
    nested = tmp_path / "missing_dir" / "x.sqlite3"
    assert initialize_strategy_lifecycle_store(nested).error_codes == ("FIELD_VALUE_INVALID",)
    assert not nested.parent.exists()


def test_store_schema_identity_enforced(store: Path, tmp_path: Path) -> None:
    connection = sqlite3.connect(store)
    try:
        assert connection.execute("PRAGMA application_id").fetchone() == (STORE_APPLICATION_ID,)
        assert STORE_APPLICATION_ID == 1398033457
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "delete"
        assert connection.execute("SELECT * FROM lifecycle_meta").fetchall() == [
            (1, "s10-strategy-lifecycle-store", 1)
        ]
    finally:
        connection.close()

    def drifted(sql: str) -> tuple[str, ...]:
        path = tmp_path / f"drift{abs(hash(sql))}.sqlite3"
        path.write_bytes(store.read_bytes())
        connection = sqlite3.connect(path, isolation_level=None)
        try:
            connection.execute(sql)
        finally:
            connection.close()
        return load_strategy_lifecycle_store(path).error_codes

    assert drifted("PRAGMA application_id=1") == ("SCHEMA_CONFLICT",)
    assert drifted("PRAGMA user_version=2") == ("SCHEMA_CONFLICT",)
    assert drifted("CREATE TABLE current_state (x INTEGER)") == ("SCHEMA_CONFLICT",)
    assert drifted("DROP TRIGGER lifecycle_records_no_delete") == ("SCHEMA_CONFLICT",)
    assert drifted("CREATE INDEX extra_idx ON lifecycle_records (record_kind)") == ("SCHEMA_CONFLICT",)
    empty = tmp_path / "empty.sqlite3"
    empty.write_bytes(b"")
    assert initialize_strategy_lifecycle_store(empty).error_codes == ("SCHEMA_CONFLICT",)
    other = tmp_path / "other.sqlite3"
    connection = sqlite3.connect(other)
    connection.execute("CREATE TABLE t (x)")
    connection.commit()
    connection.close()
    assert load_strategy_lifecycle_store(other).error_codes == ("SCHEMA_CONFLICT",)
    garbage = tmp_path / "garbage.sqlite3"
    garbage.write_bytes(b"not a database" * 100)
    assert load_strategy_lifecycle_store(garbage).status == "STORE_REJECTED"


def test_store_update_delete_blocked(store: Path) -> None:
    seeded(store)
    connection = sqlite3.connect(store, isolation_level=None)
    try:
        for sql in (
            "UPDATE lifecycle_records SET record_kind = record_kind",
            "DELETE FROM lifecycle_records",
            "UPDATE lifecycle_meta SET schema_version = 1",
            "DELETE FROM lifecycle_meta",
        ):
            with pytest.raises(sqlite3.DatabaseError):
                connection.execute(sql)
    finally:
        connection.close()
    assert snap(store).total_rows == 4


def test_store_hash_chain_correct(store: Path) -> None:
    seeded(store)
    stored = rows(store)
    assert [row[0] for row in stored] == [0, 1, 2, 3]
    assert [row[1] for row in stored] == [
        "STRATEGY_FAMILY", "STRATEGY_VERSION", "PORTFOLIO_AUTHORITY_POLICY", "PORTFOLIO_POLICY_RECEIPT",
    ]
    previous = None
    for sequence, kind, record_id, payload, payload_sha, prior, entry in stored:
        assert hashlib.sha256(payload.encode("utf-8")).hexdigest() == payload_sha
        assert prior == previous
        preimage = {
            "sequence_number": sequence, "record_kind": kind, "record_id": record_id,
            "payload_sha256": payload_sha, "previous_entry_hash": prior,
        }
        expected = hashlib.sha256(
            json.dumps(preimage, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        assert entry == expected
        previous = entry
    current = snap(store)
    assert current.store_head_entry_hash == previous
    assert current.total_rows == 4
    assert current.total_payload_bytes == sum(len(row[3].encode("utf-8")) for row in stored)


def test_store_exact_retry_idempotent(store: Path) -> None:
    fam, root, pol = seeded(store)
    before = store.read_bytes()
    result = append_strategy_lifecycle_record(store, root)
    assert result.status == "STORE_APPEND_IDEMPOTENT" and result.record_id == root.strategy_version_id
    assert store.read_bytes() == before
    assert snap(store).total_rows == 4
    forged = family(key="forged.family")
    object.__setattr__(forged, "family_label", "Mutated after build")
    assert err(store, forged) == "IDENTITY_CONFLICT"
    assert err(store, {"not": "a record"}) == "FIELD_TYPE_INVALID"


def test_store_failed_append_leaves_bytes_unchanged(store: Path) -> None:
    fam, root, pol = seeded(store)
    before_bytes = store.read_bytes()
    before = snap(store)
    for bad in (
        health(root, "HEALTHY", "WATCH"),
        allocation(root, pol, budget="500"),
        restriction(root, action="CLEAR"),
        activate(pol, previous=None, t=21),
        version(fam, parent=version(fam, code="strategy_code:unstored"), spec=params(lookback=6), t=3),
    ):
        assert append_strategy_lifecycle_record(store, bad).status == "STORE_REJECTED"
        assert store.read_bytes() == before_bytes
    assert snap(store) == before


def test_store_payload_and_chain_tamper_rejects(store: Path, tmp_path: Path) -> None:
    fam, root, pol = seeded(store)
    original = store.read_bytes()
    stored = rows(store)

    def case(sql: str, params_: tuple) -> tuple[str, ...]:
        path = tmp_path / f"tamper{abs(hash((sql, params_)))}.sqlite3"
        path.write_bytes(original)
        tamper(path, sql, params_)
        return load_strategy_lifecycle_store(path).error_codes

    family_payload = stored[0][3]
    relabeled = family_payload.replace("Alpha family", "Alpha famil2")
    relabeled_sha = hashlib.sha256(relabeled.encode()).hexdigest()
    assert case("UPDATE lifecycle_records SET payload_json=? WHERE sequence_number=0", (relabeled,)) == ("INTEGRITY_TAMPER",)
    assert case(
        "UPDATE lifecycle_records SET payload_json=?, payload_sha256=? WHERE sequence_number=0",
        (relabeled, relabeled_sha),
    ) == ("INTEGRITY_TAMPER",)
    spaced = json.dumps(json.loads(family_payload))
    assert case(
        "UPDATE lifecycle_records SET payload_json=?, payload_sha256=? WHERE sequence_number=0",
        (spaced, hashlib.sha256(spaced.encode()).hexdigest()),
    ) == ("INTEGRITY_TAMPER",)
    duplicate = family_payload[:-1] + ',"family_key":"alpha.family"}'
    assert case(
        "UPDATE lifecycle_records SET payload_json=?, payload_sha256=? WHERE sequence_number=0",
        (duplicate, hashlib.sha256(duplicate.encode()).hexdigest()),
    ) == ("INTEGRITY_TAMPER",)
    assert case("UPDATE lifecycle_records SET previous_entry_hash=? WHERE sequence_number=2", (HEX,)) == ("INTEGRITY_TAMPER",)
    assert case("UPDATE lifecycle_records SET entry_hash=? WHERE sequence_number=3", (HEX,)) == ("INTEGRITY_TAMPER",)
    assert case("UPDATE lifecycle_records SET record_kind='STRATEGY_VERSION' WHERE sequence_number=0", ()) == ("INTEGRITY_TAMPER",)
    assert case("UPDATE lifecycle_records SET sequence_number=7 WHERE sequence_number=3", ()) == ("INTEGRITY_TAMPER",)
    assert load_strategy_lifecycle_store(store).is_valid


def test_store_unsafe_path_rejects(store: Path, tmp_path: Path) -> None:
    assert initialize_strategy_lifecycle_store(tmp_path / "wrong.db").error_codes == ("FIELD_VALUE_INVALID",)
    assert load_strategy_lifecycle_store(tmp_path / "absent.sqlite3").error_codes == ("FIELD_VALUE_INVALID",)
    directory = tmp_path / "dir.sqlite3"
    directory.mkdir()
    assert initialize_strategy_lifecycle_store(directory).error_codes == ("FIELD_VALUE_INVALID",)
    for bad in (None, b"x.sqlite3", 3, True):
        assert load_strategy_lifecycle_store(bad).error_codes == ("FIELD_TYPE_INVALID",)
    assert load_strategy_lifecycle_store("").error_codes == ("FIELD_VALUE_INVALID",)
    assert load_strategy_lifecycle_store("x\x00.sqlite3").error_codes == ("FIELD_VALUE_INVALID",)
    link = tmp_path / "hardlink.sqlite3"
    os.link(store, link)
    try:
        assert load_strategy_lifecycle_store(store).error_codes == ("FIELD_VALUE_INVALID",)
        assert append_strategy_lifecycle_record(link, family()).error_codes == ("FIELD_VALUE_INVALID",)
    finally:
        link.unlink()
    assert load_strategy_lifecycle_store(store).is_valid
    symlink = tmp_path / "symlink.sqlite3"
    try:
        symlink.symlink_to(store)
    except (OSError, NotImplementedError):
        return
    assert load_strategy_lifecycle_store(symlink).error_codes == ("FIELD_VALUE_INVALID",)
    linked_dir = tmp_path / "linked_dir"
    linked_dir.symlink_to(tmp_path, target_is_directory=True)
    assert load_strategy_lifecycle_store(linked_dir / store.name).error_codes == ("FIELD_VALUE_INVALID",)


def test_store_cross_record_reference_tamper_rejects(store: Path, tmp_path: Path) -> None:
    fam, root, pol = seeded(store)

    def insert_raw(path: Path, record) -> tuple[str, ...]:
        kind = M.record_kind_of(record)
        payload = canonical_json_bytes(record.to_mapping()).decode("utf-8")
        payload_sha = hashlib.sha256(payload.encode()).hexdigest()
        current = rows(path)
        sequence, previous = len(current), current[-1][6]
        entry = S.entry_hash(sequence, kind, record.record_id, payload_sha, previous)
        connection = sqlite3.connect(path, isolation_level=None)
        try:
            connection.execute(
                "INSERT INTO lifecycle_records VALUES (?, ?, ?, ?, ?, ?, ?)",
                (sequence, kind, record.record_id, payload, payload_sha, previous, entry),
            )
        finally:
            connection.close()
        return load_strategy_lifecycle_store(path).error_codes

    orphan_family = family(key="missing.family")
    for record in (
        version(orphan_family),
        version(fam, parent=version(fam, code="strategy_code:unstored"), spec=params(lookback=6), t=3),
        allocation(version(fam, code="strategy_code:unstored"), pol),
        health(version(fam, code="strategy_code:unstored"), "NEW", "HEALTHY"),
        activate(policy(label="Unstored envelope")),
        allocation(root, pol, budget="101"),
    ):
        path = tmp_path / f"ref{abs(hash(record.record_id))}.sqlite3"
        path.write_bytes(store.read_bytes())
        assert insert_raw(path, record) == ("INTEGRITY_TAMPER",)
    assert snap(store).total_rows == 4


# ---------------------------------------------------------------------------
# Lifecycle transitions (R034-R040).
# ---------------------------------------------------------------------------


def test_policy_activate_revoke_derives_single_active_policy(store: Path) -> None:
    first = policy()
    second = policy(label="Second envelope", predecessor=first.policy_id)
    assert err(store, second) == "REFERENCE_INVALID"
    ok(store, first)
    assert snap(store).active_policy_id is None
    assert err(store, activate(policy(label="Unknown"))) == "REFERENCE_INVALID"
    ok(store, activate(first))
    assert snap(store).active_policy_id == first.policy_id
    ok(store, second)
    ok(store, activate(second, previous=first.policy_id, t=25))
    assert snap(store).active_policy_id == second.policy_id
    ok(store, revoke(second))
    assert snap(store).active_policy_id is None
    assert code_of(activate, first, previous=first.policy_id) == "POLICY_TRANSITION_INVALID"
    assert code_of(
        build_portfolio_policy_receipt, action="ACTIVATE", policy_id=first.policy_id,
        previous_active_policy_id=None, human_authorization_ref="", created_time_ns=40,
    ) == "FIELD_VALUE_INVALID"
    assert code_of(
        build_portfolio_policy_receipt, action="ACTIVATE", policy_id=first.policy_id,
        previous_active_policy_id=None, human_authorization_ref="human:password=hunter2",
        created_time_ns=40,
    ) == "FIELD_VALUE_INVALID"
    assert code_of(
        build_portfolio_policy_receipt, action="REVOKE", policy_id=first.policy_id,
        previous_active_policy_id=None, human_authorization_ref="human:1", created_time_ns=40,
    ) == "POLICY_TRANSITION_INVALID"
    ok(store, activate(first, t=45))
    assert snap(store).active_policy_id == first.policy_id


def test_policy_activation_predecessor_mismatch_rejects(store: Path) -> None:
    first = policy(expires=1000)
    second = policy(label="Second envelope")
    ok(store, first)
    ok(store, second)
    ok(store, activate(first))
    assert err(store, activate(second, previous=None)) == "POLICY_TRANSITION_INVALID"
    assert err(store, revoke(second)) == "POLICY_TRANSITION_INVALID"
    assert err(store, activate(first, previous=second.policy_id)) == "POLICY_TRANSITION_INVALID"
    ok(store, revoke(first, t=40))
    assert err(store, activate(first, t=1000)) == "POLICY_TRANSITION_INVALID"
    assert err(store, activate(first, t=5)) == "POLICY_TRANSITION_INVALID"
    assert snap(store).active_policy_id is None


def test_new_version_health_is_new(store: Path) -> None:
    fam, root, _ = seeded(store)
    assert snap(store).health_of(root.strategy_version_id) == "NEW"
    child = version(fam, parent=root, spec=params(lookback=6), t=3)
    ok(store, child)
    assert snap(store).current_health_by_strategy_version == tuple(
        sorted({root.strategy_version_id: "NEW", child.strategy_version_id: "NEW"}.items())
    )


def test_valid_health_transitions(store: Path) -> None:
    fam, root, pol = seeded(store)
    path = ["NEW", "HEALTHY", "WATCH", "DEGRADED", "QUARANTINED", "HEALTHY", "DEGRADED", "WATCH", "RETIRED"]
    for index, (previous, new) in enumerate(zip(path, path[1:])):
        ok(store, health(root, previous, new, t=50 + index))
        assert snap(store).health_of(root.strategy_version_id) == new
    assert snap(store).allocation_of(root.strategy_version_id) is None


def test_invalid_health_transitions_reject(store: Path) -> None:
    fam, root, _ = seeded(store)
    assert code_of(health, root, "HEALTHY", "HEALTHY") == "HEALTH_TRANSITION_INVALID"
    assert code_of(health, root, "HEALTHY", "NEW") == "HEALTH_TRANSITION_INVALID"
    assert code_of(health, root, "RETIRED", "HEALTHY") == "HEALTH_TRANSITION_INVALID"
    assert code_of(health, root, "HEALTHY", "ALIVE") == "FIELD_VALUE_INVALID"
    assert err(store, health(root, "HEALTHY", "WATCH")) == "HEALTH_TRANSITION_INVALID"
    ok(store, health(root, "NEW", "RETIRED"))
    assert err(store, health(root, "HEALTHY", "WATCH", t=51)) == "HEALTH_TRANSITION_INVALID"
    unknown = version(fam, code="strategy_code:unstored")
    assert err(store, health(unknown, "NEW", "HEALTHY")) == "REFERENCE_INVALID"
    assert snap(store).health_of(root.strategy_version_id) == "RETIRED"


def test_restriction_apply_clear_exactness(store: Path) -> None:
    fam, root, _ = seeded(store)
    ok(store, restriction(root, key="pause.1"))
    assert err(store, restriction(root, key="pause.1", t=61)) == "RESTRICTION_TRANSITION_INVALID"
    assert err(store, restriction(root, key="pause.2", action="CLEAR")) == "RESTRICTION_TRANSITION_INVALID"
    assert err(store, restriction(root, key="pause.1", action="CLEAR", kind="PAPER_ONLY")) == "RESTRICTION_TRANSITION_INVALID"
    ok(store, restriction(root, key="cap.1", kind="ACTIVE_BUDGET_CAP", cap="30"))
    assert err(store, restriction(root, key="cap.1", action="CLEAR", kind="ACTIVE_BUDGET_CAP", cap="31")) == "RESTRICTION_TRANSITION_INVALID"
    assert len(snap(store).restrictions_of(root.strategy_version_id)) == 2
    ok(store, restriction(root, key="pause.1", action="CLEAR", t=70))
    ok(store, restriction(root, key="cap.1", action="CLEAR", kind="ACTIVE_BUDGET_CAP", cap="30", t=71))
    assert snap(store).restrictions_of(root.strategy_version_id) == ()
    assert snap(store).active_restrictions_by_strategy_version == ()
    ok(store, restriction(root, key="pause.1", t=72))
    assert code_of(restriction, root, kind="ACTIVE_BUDGET_CAP") == "FIELD_VALUE_INVALID"
    assert code_of(restriction, root, cap="10") == "FIELD_VALUE_INVALID"
    assert code_of(restriction, root, kind="ACTIVE_BUDGET_CAP", cap="1.0") == "FIELD_VALUE_INVALID"
    assert code_of(restriction, root, key="Global Pause") == "FIELD_VALUE_INVALID"
    assert code_of(restriction, root, kind="GLOBAL_KILL") == "FIELD_VALUE_INVALID"


def test_restriction_is_strategy_local(store: Path) -> None:
    fam, root, pol = seeded(store)
    (other,) = extra_roots(store, fam, 1)
    ok(store, allocation(other, pol, budget="40"))
    ok(store, restriction(root, key="pause.1"))
    current = snap(store)
    assert current.restrictions_of(other.strategy_version_id) == ()
    assert current.health_of(other.strategy_version_id) == "NEW"
    assert err(store, restriction(other, key="pause.1", action="CLEAR")) == "RESTRICTION_TRANSITION_INVALID"
    ok(store, restriction(other, key="pause.1", kind="PAPER_ONLY", t=61))
    ok(store, restriction(root, key="pause.1", action="CLEAR", t=62))
    current = snap(store)
    assert current.restrictions_of(root.strategy_version_id) == ()
    assert [r.restriction_kind for r in current.restrictions_of(other.strategy_version_id)] == ["PAPER_ONLY"]
    assert current.active_policy_id == pol.policy_id


# ---------------------------------------------------------------------------
# Risk allocations / capacity (R041-R053).
# ---------------------------------------------------------------------------


def test_allocation_requires_active_policy(store: Path) -> None:
    fam = family()
    root = version(fam)
    pol = policy()
    for record in (fam, root, pol):
        ok(store, record)
    assert err(store, allocation(root, pol)) == "ALLOCATION_INVALID"
    ok(store, activate(pol))
    assert err(store, allocation(root, policy(label="Unstored"))) == "REFERENCE_INVALID"
    assert err(store, allocation(version(fam, code="strategy_code:unstored"), pol)) == "REFERENCE_INVALID"
    assert err(store, allocation(root, pol, start=5)) == "ALLOCATION_INVALID"
    second = policy(label="Second envelope", expires=500)
    ok(store, second)
    ok(store, activate(second, previous=pol.policy_id, t=25))
    assert err(store, allocation(root, pol)) == "ALLOCATION_INVALID"
    assert err(store, allocation(root, second)) == "ALLOCATION_INVALID"
    assert err(store, allocation(root, second, end=501)) == "ALLOCATION_INVALID"
    ok(store, allocation(root, second, end=500))
    ok(store, revoke(second, t=40))
    assert err(store, allocation(root, second, end=400, budget="10")) == "ALLOCATION_INVALID"
    assert code_of(allocation, root, pol, start=100, end=100) == "ALLOCATION_INVALID"


def test_paper_allocation_nonzero_budget_rejects(store: Path) -> None:
    fam, root, pol = seeded(store)
    assert code_of(allocation, root, pol, band="PAPER", budget="5") == "ALLOCATION_INVALID"
    assert code_of(allocation, root, pol, band="PAPER", budget="0.0") == "FIELD_VALUE_INVALID"
    ok(store, allocation(root, pol, band="PAPER", budget="0"))
    assert snap(store).allocation_of(root.strategy_version_id).risk_band == "PAPER"
    assert code_of(allocation, root, pol, band="LIVE") == "FIELD_VALUE_INVALID"
    assert code_of(allocation, root, pol, basis="HUMAN_APPROVAL") == "FIELD_VALUE_INVALID"


def test_parent_inheritance_ceiling_enforced(store: Path) -> None:
    fam, root, pol = seeded(store)
    bounded = version(fam, parent=root, spec=params(lookback=6), t=3)
    material = version(fam, parent=root, spec=params(fixed=9), t=3)
    ok(store, bounded)
    ok(store, material)
    assert material.adaptation_class == "MATERIAL_ADAPTATION"
    assert err(store, allocation(bounded, pol, basis="PARENT_INHERITANCE")) == "ALLOCATION_INVALID"
    assert err(store, allocation(root, pol, basis="PARENT_INHERITANCE")) == "ALLOCATION_INVALID"
    ok(store, allocation(root, pol, band="VALIDATED_LIVE", budget="100"))
    ok(store, allocation(bounded, pol, band="VALIDATED_LIVE", budget="100", basis="PARENT_INHERITANCE"))
    assert err(store, allocation(material, pol, band="VALIDATED_LIVE", budget="10", basis="PARENT_INHERITANCE")) == "ALLOCATION_INVALID"
    assert err(store, allocation(material, pol, band="MATURE_LIVE", budget="10", basis="PARENT_INHERITANCE")) == "ALLOCATION_INVALID"
    ok(store, allocation(material, pol, band="EXPLORATORY_LIVE", budget="10", basis="PARENT_INHERITANCE"))
    ok(store, allocation(material, pol, band="VALIDATED_LIVE", budget="10", t=101))


def test_direct_decision_obeys_capacity_without_evidence_gate(store: Path) -> None:
    fam, root, pol = seeded(store)
    exploratory = version(fam, posture="NOVEL_EXPLORATORY", code="strategy_code:novel")
    wallet = version(fam, posture="WALLET_DEPENDENT", code="strategy_code:wallet")
    ok(store, exploratory)
    ok(store, wallet)
    ok(store, allocation(exploratory, pol, band="MATURE_LIVE", budget="300"))
    ok(store, allocation(wallet, pol, band="VALIDATED_LIVE", budget="1"))
    assert err(store, allocation(root, pol, band="MATURE_LIVE", budget="1")) == "CAPACITY_INVALID"
    result = evaluate_portfolio_capacity(snap(store), 100)
    assert result.status == PORTFOLIO_CAPACITY_VALID
    assert result.mature_active_usd == "300" and result.total_active_usd == "301"


def test_per_strategy_limit_rejects(store: Path) -> None:
    fam, root, pol = seeded(store)
    assert err(store, allocation(root, pol, budget="100.01")) == "CAPACITY_INVALID"
    assert err(store, allocation(root, pol, band="VALIDATED_LIVE", budget="201")) == "CAPACITY_INVALID"
    ok(store, allocation(root, pol, budget="100"))
    assert snap(store).allocation_of(root.strategy_version_id).active_budget_usd == "100"


def test_band_pool_overflow_rejects(store: Path) -> None:
    fam, root, pol = seeded(store, max_active_strategies=10)
    others = extra_roots(store, fam, 6)
    for ver in others[:3]:
        ok(store, allocation(ver, pol, budget="100"))
    assert err(store, allocation(root, pol, budget="1")) == "CAPACITY_INVALID"
    ok(store, allocation(others[3], pol, band="VALIDATED_LIVE", budget="200"))
    assert err(store, allocation(others[4], pol, band="VALIDATED_LIVE", budget="101")) == "CAPACITY_INVALID"
    ok(store, allocation(others[4], pol, band="MATURE_LIVE", budget="300"))
    assert err(store, allocation(others[5], pol, band="MATURE_LIVE", budget="1")) == "CAPACITY_INVALID"
    ok(store, allocation(others[0], pol, budget="40", t=101))
    ok(store, allocation(root, pol, budget="60"))


def test_band_pool_sweep_checks_overlapping_windows(store: Path) -> None:
    fam, root, pol = seeded(store, exploratory_pool_max_usd="150")
    a, b, c = extra_roots(store, fam, 3)
    ok(store, allocation(a, pol, budget="100", start=100, end=200))
    ok(store, allocation(b, pol, budget="100", start=200))
    assert err(store, allocation(c, pol, budget="60", start=150, end=250)) == "CAPACITY_INVALID"
    assert err(store, allocation(c, pol, budget="60", start=50 + 100, end=None)) == "CAPACITY_INVALID"
    ok(store, allocation(c, pol, budget="50", start=150, end=250))


def test_global_capital_overflow_rejects(store: Path) -> None:
    fam, root, pol = seeded(store, global_capital_at_risk_max_usd="900", max_active_strategies=10)
    others = extra_roots(store, fam, 4)
    for ver, band in zip(others, ("EXPLORATORY_LIVE", "VALIDATED_LIVE", "MATURE_LIVE")):
        ok(store, allocation(ver, pol, band=band, budget="100" if band == "EXPLORATORY_LIVE" else "200"))
    ok(store, allocation(others[3], pol, band="EXPLORATORY_LIVE", budget="100"))
    assert err(store, allocation(root, pol, band="MATURE_LIVE", budget="100.5")) == "CAPACITY_INVALID"
    # A valid policy keeps pool sum <= global capital, so a global overflow can only
    # co-occur with a pool overflow; the evaluator still reports it independently.
    state = P._LifecycleState()
    for record in (fam, *others, pol, activate(pol)):
        state.apply(record)
    bypass = zip(
        others,
        ("EXPLORATORY_LIVE", "VALIDATED_LIVE", "MATURE_LIVE", "EXPLORATORY_LIVE"),
        ("100", "200", "300", "201"),
    )
    for ver, band, budget in bypass:
        state.allocations[ver.strategy_version_id] = allocation(ver, pol, band=band, budget=budget)
    view = state.snapshot(store_head_entry_hash=None, total_rows=0, total_payload_bytes=0)
    result = evaluate_portfolio_capacity(view, 100)
    assert result.status == PORTFOLIO_CAPACITY_REJECTED
    assert result.total_active_usd == "801"
    assert "GLOBAL_CAPITAL_LIMIT_EXCEEDED" not in result.reason_codes
    state.allocations[others[2].strategy_version_id] = allocation(
        others[2], pol, band="MATURE_LIVE", budget="400"
    )
    view = state.snapshot(store_head_entry_hash=None, total_rows=0, total_payload_bytes=0)
    result = evaluate_portfolio_capacity(view, 100)
    assert result.total_active_usd == "901"
    assert {"GLOBAL_CAPITAL_LIMIT_EXCEEDED", "MATURE_POOL_EXCEEDED"} <= set(result.reason_codes)


def test_max_active_strategies_rejects(store: Path) -> None:
    fam, root, pol = seeded(store)
    others = extra_roots(store, fam, 3)
    for ver in others:
        ok(store, allocation(ver, pol, budget="10"))
    assert err(store, allocation(root, pol, budget="10")) == "CAPACITY_INVALID"
    ok(store, allocation(root, pol, budget="0"))
    result = evaluate_portfolio_capacity(snap(store), 100)
    assert result.status == PORTFOLIO_CAPACITY_VALID and result.active_real_risk_strategy_count == 3
    ok(store, allocation(others[0], pol, budget="0", t=101))
    ok(store, allocation(root, pol, budget="10", t=102))


def test_quarantined_or_retired_positive_budget_rejects(store: Path) -> None:
    fam, root, pol = seeded(store)
    (other,) = extra_roots(store, fam, 1)
    ok(store, allocation(root, pol, budget="50"))
    ok(store, health(root, "NEW", "QUARANTINED"))
    result = evaluate_portfolio_capacity(snap(store), 100)
    own = result.strategy_result(root.strategy_version_id)
    assert own.reason_codes == ("HEALTH_BLOCKS_ACTIVE_RISK",)
    assert result.status == PORTFOLIO_CAPACITY_REJECTED
    assert err(store, allocation(root, pol, budget="10", t=101)) == "CAPACITY_INVALID"
    ok(store, allocation(root, pol, budget="0", t=102))
    assert evaluate_portfolio_capacity(snap(store), 100).status == PORTFOLIO_CAPACITY_VALID
    ok(store, health(other, "NEW", "RETIRED"))
    assert err(store, allocation(other, pol, budget="1")) == "CAPACITY_INVALID"
    ok(store, allocation(other, pol, band="PAPER", budget="0"))


def test_pause_or_paper_only_positive_budget_rejects(store: Path) -> None:
    fam, root, pol = seeded(store)
    (other,) = extra_roots(store, fam, 1)
    ok(store, allocation(root, pol, budget="50"))
    ok(store, restriction(root, key="pause.1"))
    result = evaluate_portfolio_capacity(snap(store), 100)
    assert result.strategy_result(root.strategy_version_id).reason_codes == ("RESTRICTION_BLOCKS_ACTIVE_RISK",)
    assert err(store, allocation(root, pol, budget="5", t=101)) == "CAPACITY_INVALID"
    ok(store, restriction(other, key="paper.only", kind="PAPER_ONLY"))
    assert err(store, allocation(other, pol, budget="5")) == "CAPACITY_INVALID"
    ok(store, allocation(other, pol, band="PAPER", budget="0"))
    ok(store, restriction(root, key="pause.1", action="CLEAR", t=70))
    assert evaluate_portfolio_capacity(snap(store), 100).status == PORTFOLIO_CAPACITY_VALID


def test_active_budget_cap_enforced(store: Path) -> None:
    fam, root, pol = seeded(store)
    ok(store, restriction(root, key="cap.a", kind="ACTIVE_BUDGET_CAP", cap="30"))
    assert err(store, allocation(root, pol, budget="40")) == "CAPACITY_INVALID"
    ok(store, allocation(root, pol, budget="30"))
    ok(store, restriction(root, key="cap.b", kind="ACTIVE_BUDGET_CAP", cap="20", t=61))
    result = evaluate_portfolio_capacity(snap(store), 100)
    assert result.strategy_result(root.strategy_version_id).reason_codes == ("ACTIVE_BUDGET_CAP_EXCEEDED",)
    ok(store, allocation(root, pol, budget="20", t=101))
    assert evaluate_portfolio_capacity(snap(store), 100).is_valid


def test_expired_and_future_allocations_excluded(store: Path) -> None:
    fam, root, pol = seeded(store, max_active_strategies=1)
    (other,) = extra_roots(store, fam, 1)
    ok(store, allocation(root, pol, budget="80", start=100, end=200))
    ok(store, allocation(other, pol, budget="90", start=200))
    current = snap(store)
    for at_time, expected in ((50, "0"), (99, "0"), (100, "80"), (199, "80"), (200, "90"), (10**12, "90")):
        result = evaluate_portfolio_capacity(current, at_time)
        assert result.status == PORTFOLIO_CAPACITY_VALID and result.total_active_usd == expected, at_time
    assert evaluate_portfolio_capacity(current, 5).reason_codes == ("POLICY_NOT_EFFECTIVE",)
    for bad in (True, -1, "100", None):
        assert evaluate_portfolio_capacity(current, bad).reason_codes == ("INTERNAL_VALIDATION_FAILED",)
    assert evaluate_portfolio_capacity(object(), 100).reason_codes == ("INTERNAL_VALIDATION_FAILED",)
    ok(store, revoke(pol, t=300))
    assert evaluate_portfolio_capacity(snap(store), 250).reason_codes == ("POLICY_NOT_ACTIVE",)
    expiring = policy(label="Expiring", expires=1000)
    ok(store, expiring)
    ok(store, activate(expiring, t=310))
    expired = evaluate_portfolio_capacity(snap(store), 1000)
    assert expired.reason_codes == ("POLICY_EXPIRED",)
    mismatch = evaluate_portfolio_capacity(snap(store), 500)
    assert mismatch.strategy_result(other.strategy_version_id).reason_codes == ("ALLOCATION_POLICY_MISMATCH",)
    assert mismatch.total_active_usd == "0"
    with pytest.raises(StrategyLifecycleError):
        StrategyLifecycleSnapshot(None, 0, 0, None, (), (), (), (), (), ())
    with pytest.raises(StrategyLifecycleError):
        StrategyLifecycleSnapshot(
            None, 0, 0, None, (), (), (), (), (), (), no_live_authority=False,
            _replay_token=P._REPLAY_TOKEN,
        )


def test_quarantine_isolated_from_unrelated_strategy(store: Path) -> None:
    fam, root, pol = seeded(store)
    (other,) = extra_roots(store, fam, 1)
    ok(store, allocation(root, pol, budget="50"))
    ok(store, allocation(other, pol, budget="50"))
    ok(store, health(root, "NEW", "QUARANTINED"))
    result = evaluate_portfolio_capacity(snap(store), 100)
    assert result.strategy_result(root.strategy_version_id).status == PORTFOLIO_CAPACITY_REJECTED
    assert result.strategy_result(other.strategy_version_id).status == PORTFOLIO_CAPACITY_VALID
    assert result.reason_codes == ("HEALTH_BLOCKS_ACTIVE_RISK",)
    ok(store, allocation(other, pol, budget="60", t=101))
    assert snap(store).health_of(other.strategy_version_id) == "NEW"
    ok(store, allocation(root, pol, budget="0", t=102))
    assert evaluate_portfolio_capacity(snap(store), 100).status == PORTFOLIO_CAPACITY_VALID


# ---------------------------------------------------------------------------
# Authority / integration negative tests (R054-R057).
# ---------------------------------------------------------------------------

ALLOWED_IMPORTS = {
    "__future__", "collections.abc", "dataclasses", "decimal", "hashlib", "json", "os",
    "pathlib", "re", "sqlite3", "typing",
}


def test_lifecycle_source_imports_are_stdlib_only() -> None:
    files = sorted(path.name for path in PACKAGE.glob("*.py"))
    assert files == ["__init__.py", "models.py", "policy.py", "store.py"]
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    assert node.module in {"models", "policy", "store"}, path
                    continue
                names = [node.module]
            else:
                continue
            for name in names:
                assert name in ALLOWED_IMPORTS, (path.name, name)
        source = path.read_text(encoding="utf-8")
        for forbidden in (
            "socket", "urllib", "requests", "httpx", "websocket", "polymarket import",
            "execution_gateway", "paper_trading", "gate_c", "subprocess", "os.environ",
            "py_clob_client", "local_data",
        ):
            assert forbidden not in source, (path.name, forbidden)


def _spec_scope() -> list[str]:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    return spec["scope"]["required_changed_files"]


def test_package_scope_excludes_dependency_and_workflow_paths() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    scope = spec["scope"]
    assert scope["required_changed_files"] == scope["allowed_changed_files"]
    assert len(scope["required_changed_files"]) == scope["max_changed_files"] == 20
    for path in scope["required_changed_files"]:
        assert not path.startswith((".github/", "tools/", "agent_runtime/", "agent_memory/")), path
        assert Path(path).name not in {"pyproject.toml", "requirements.txt", "package.json", "uv.lock"}, path
        assert not path.endswith(".lock") and not Path(path).name.startswith(".env"), path
    for key in ("dependencies", "workflow_files", "network", "credentials", "scheduler",
                "hermes_runtime", "paper", "execution", "live"):
        assert spec["authority"][key] is False, key
    assert spec["authority"]["strategy"] is True
    assert spec["identity"]["capital_at_risk_usd"] == 0


def test_adjacent_formal_lane_imports_remain_available() -> None:
    expected = {
        "src.paper_trading": ("PaperStrategyBinding", "ResearchPaperStrategyBinding", "PaperEngine"),
        "src.execution_gateway.gate_c": ("GateCStrategyQualification", "GateCSession"),
        "src.data_layer.analytical_research.qualification": ("build_qualification_candidate",),
        "src.data_layer.analytical_research.qualification_gate": ("evaluate_qualification_gate",),
        "src.data_layer.analytical_research.experiment_registry": ("initialize_experiment_registry",),
        "src.research_runtime.executable_edge": ("assess_executable_edge",),
    }
    for module_name, names in expected.items():
        module = importlib.import_module(module_name)
        for name in names:
            assert hasattr(module, name), (module_name, name)
    assert STORE_APPLICATION_ID not in {1464877424, 1464877425, 1464877426, 0x57414C31, 1_347_242_301}


def test_package_scope_excludes_data03_paths() -> None:
    for path in _spec_scope():
        lowered = path.lower()
        assert "qual_data_03" not in lowered and "qual-data-03" not in lowered, path
        assert not lowered.startswith("local_data/"), path
        assert "qualification_oos_accrual" not in lowered, path
    for path in PACKAGE.glob("*.py"):
        source = path.read_text(encoding="utf-8").lower()
        assert "data-03" not in source and "data_03" not in source, path.name


# ---------------------------------------------------------------------------
# Exact-head micro-closure 01: connection contract and canonical event refs.
# ---------------------------------------------------------------------------


def _pragmas(connection: sqlite3.Connection) -> tuple:
    return (
        str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower(),
        connection.execute("PRAGMA synchronous").fetchone()[0],
        connection.execute("PRAGMA foreign_keys").fetchone()[0],
    )


def test_store_connection_pragma_contract_is_exact(store: Path, tmp_path: Path, monkeypatch) -> None:
    seen: list[tuple] = []
    original = S._load

    def recording_load(connection):
        seen.append(_pragmas(connection))
        return original(connection)

    monkeypatch.setattr(S, "_load", recording_load)
    fam = family()
    assert initialize_strategy_lifecycle_store(tmp_path / "second.sqlite3").status == "STORE_INITIALIZED"
    assert load_strategy_lifecycle_store(store).status == "STORE_LOADED_VERIFIED"
    assert append_strategy_lifecycle_record(store, fam).status == "STORE_APPEND_COMMITTED"
    assert seen and set(seen) == {("delete", 2, 1)}
    monkeypatch.setattr(S, "_load", original)

    # A connection whose PRAGMA state cannot satisfy the contract never verifies.
    def weakened(connection):
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA foreign_keys=OFF")

    monkeypatch.setattr(S, "_configure_connection", weakened)
    assert load_strategy_lifecycle_store(store).error_codes == ("SCHEMA_CONFLICT",)
    assert append_strategy_lifecycle_record(store, family(key="other.family")).error_codes == ("SCHEMA_CONFLICT",)
    assert initialize_strategy_lifecycle_store(store).error_codes == ("SCHEMA_CONFLICT",)
    monkeypatch.undo()
    assert snap(store).total_rows == 1

    # Persistent journal-mode drift (WAL) fails closed for load, append and init.
    wal = tmp_path / "wal.sqlite3"
    wal.write_bytes(store.read_bytes())
    connection = sqlite3.connect(wal)
    assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
    connection.close()
    for result in (
        load_strategy_lifecycle_store(wal),
        append_strategy_lifecycle_record(wal, family(key="wal.family")),
        initialize_strategy_lifecycle_store(wal),
    ):
        assert result.status == "STORE_REJECTED" and result.snapshot is None


def test_canonical_public_polymarket_event_ref_is_accepted_exactly() -> None:
    canonical = "event:polymarket:0x" + "0123456789abcdef" * 4
    assert M.opaque_ref(canonical) == canonical
    assert version(family(), refs=(canonical,)).evidence_refs == (canonical,)
    for bad in (
        "0x" + "a" * 64,
        "event:polymarket:0x" + "A" * 64,
        "event:polymarket:0X" + "a" * 64,
        "event:kalshi:0x" + "a" * 64,
        "market:polymarket:0x" + "a" * 64,
        "event:polymarket:0x" + "a" * 63,
        "event:polymarket:0x" + "a" * 65,
        "xevent:polymarket:0x" + "a" * 64,
        "event:polymarket:0x" + "a" * 64 + ":extra",
        "event:polymarket:0x" + "a" * 64 + "g",
        "wallet:0x" + "a" * 64,
        "event:polymarket:0x" + "a" * 64 + "-secret",
    ):
        assert code_of(M.opaque_ref, bad) == "FIELD_VALUE_INVALID", bad
    for safe in (
        "market:polymarket:123456", "token:polymarket:98765432109876543210",
        "strategyversion:sha256:" + HEX, "researchepisode:sha256:" + HEX, "wallet:0x" + "b" * 40,
    ):
        assert M.opaque_ref(safe) == safe
