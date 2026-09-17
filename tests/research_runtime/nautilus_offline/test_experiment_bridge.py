"""WP175D PMXT v2 -> WP170 external historical research bridge tests.

Covers R001, R002-R008 (shared with test_conversion), R009-R016 boundary cases,
R011, R012, R017, R018. External history never becomes canonical PIT; availability
is receive-time; the bridge introduces no forbidden authority and never echoes.
"""

from __future__ import annotations

import ast
from dataclasses import asdict, is_dataclass, replace
from pathlib import Path

import src.data_layer.analytical_research as ar
import src.research_runtime.nautilus_offline as off
from src.data_layer.analytical_research import experiment_os as os_contract
from src.research_runtime.nautilus_offline.conversion import PmxtV2ResearchLineage
from tests.research_runtime.nautilus_offline.test_conversion import (
    _context,
    _write_files,
    default_rows,
)
from tests.data_layer.analytical_research.test_experiment_os_identity import feature, label

ROOT = Path(__file__).resolve().parents[3]
BRIDGE_SOURCE = ROOT / "src/research_runtime/nautilus_offline/experiment_bridge.py"
CONVERSION_SOURCE = ROOT / "src/research_runtime/nautilus_offline/conversion.py"


# --------------------------------------------------------------------------- #
# Shared external-lineage fixtures
# --------------------------------------------------------------------------- #

def lineage(tmp_path, digests=None):
    """Return (source, context, stream, lineage) for the default PMXT source."""
    source = _write_files(tmp_path, [default_rows()])
    context = _context()
    stream = off.convert_pmxt_v2_events(source, context)
    assert stream.is_valid, stream.error_codes
    result = off.build_pmxt_v2_research_lineage(
        source, context, digests if digests is not None else list(stream.ordered_event_digests)
    )
    return source, context, stream, result


def external_binding(tmp_path):
    _source, _context_obj, _stream, lin = lineage(tmp_path)
    result = off.build_pmxt_v2_dataset_binding(lin, "commit:test")
    assert result.is_valid, result.error_codes
    return lin, result.record


def external_sample(member_id, decision, target, available, *, feature_time, group=None):
    return {
        "source_record_version_ids": [member_id],
        "market_id": f"market:{member_id[-6:]}",
        "related_group_id": None,
        "leakage_group_id": group,
        "decision_time": decision,
        "feature_availability_time": feature_time,
        "target_time": target,
        "label_availability_time": available,
    }


def external_manifest(tmp_path):
    lin, binding = external_binding(tmp_path)
    member_id = lin.members[0].member_id
    sample = external_sample(
        member_id,
        "2030-01-01T00:00:00Z",
        "2030-01-02T00:00:00Z",
        "2030-01-03T00:00:00Z",
        feature_time="2020-01-01T00:00:00Z",
    )
    result = off.build_pmxt_v2_research_dataset_manifest(
        lin, binding, [feature()], label(), [sample], "DECLARED_NO_ISOLATION"
    )
    assert result.is_valid, result.error_codes
    return lin, binding, result.record


def external_experiment_stack(tmp_path):
    """A full external-binding preregistered-experiment stack (canonical/external
    preregistration parity, R014). Three external samples across the three temporal
    roles, each citing a distinct bound member id."""
    lin, binding = external_binding(tmp_path)
    members = lin.members
    assert len(members) >= 3
    samples = [
        external_sample(members[0].member_id, "2026-01-10T00:00:00Z", "2026-01-11T00:00:00Z", "2026-01-12T00:00:00Z", feature_time="2020-01-01T00:00:00Z"),
        external_sample(members[1].member_id, "2026-02-10T00:00:00Z", "2026-02-11T00:00:00Z", "2026-02-12T00:00:00Z", feature_time="2020-01-01T00:00:00Z"),
        external_sample(members[2].member_id, "2026-03-10T00:00:00Z", "2026-03-11T00:00:00Z", "2026-03-12T00:00:00Z", feature_time="2020-01-01T00:00:00Z"),
    ]
    manifest = off.build_pmxt_v2_research_dataset_manifest(
        lin, binding, [feature()], label(), samples, "DECLARED_NO_ISOLATION"
    )
    assert manifest.is_valid, manifest.error_codes
    split = ar.build_temporal_split_manifest(manifest.record, {
        "split_plan_version": "1.0.0",
        "formation_start": "2026-01-01T00:00:00Z",
        "selection_start": "2026-02-01T00:00:00Z",
        "oos_start": "2026-03-01T00:00:00Z",
        "end_time": "2026-04-01T00:00:00Z",
        "purge_rule": "PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY",
        "embargo_seconds": 0,
        "group_policy": "DECLARED_NO_ISOLATION",
        "inclusion_policy": "DECISION_TIME_HALF_OPEN",
        "min_samples_per_role": 1,
    })
    assert split.is_valid, split.error_codes
    return lin, binding, manifest.record, split.record


# --------------------------------------------------------------------------- #
# R001 — external history never gains canonical-PIT authority
# --------------------------------------------------------------------------- #

def test_external_binding_is_not_canonical_pit(tmp_path) -> None:
    lin, binding = external_binding(tmp_path)
    # WP167 external descriptor kind, never the canonical PIT source kind.
    assert binding.source_kind == ar.EXTERNAL_DATASET_BINDING_SOURCE_KIND
    assert binding.source_kind != ar.SOURCE_KIND_CANONICAL_PIT
    assert binding.schema_id == ar.EXTERNAL_DATASET_BINDING_SCHEMA_ID
    assert binding.dataset_binding_id.startswith("datasetbinding:sha256:")
    assert binding.advisory_only is True and binding.no_execution_authority is True
    # No DatasetSnapshotReference field is present on the external binding at all.
    assert not hasattr(binding, "dataset_snapshot_reference_json")
    # It is NOT a canonical DatasetBinding instance.
    assert not isinstance(binding, ar.DatasetBinding)
    # No local path enters the id, membership digest, or any string field.
    for value in _strings(binding):
        assert str(tmp_path) not in value
        assert ".parquet" not in value


# --------------------------------------------------------------------------- #
# R011 — external manifest accepts only exact bound member ids
# --------------------------------------------------------------------------- #

def test_external_manifest_membership_admission(tmp_path) -> None:
    lin, binding = external_binding(tmp_path)
    member_id = lin.members[0].member_id

    def build(source_ids):
        sample = external_sample(
            member_id, "2030-01-01T00:00:00Z", "2030-01-02T00:00:00Z",
            "2030-01-03T00:00:00Z", feature_time="2020-01-01T00:00:00Z",
        )
        sample["source_record_version_ids"] = source_ids
        return off.build_pmxt_v2_research_dataset_manifest(
            lin, binding, [feature()], label(), [sample], "DECLARED_NO_ISOLATION"
        )

    # Valid bound member -> accepted; the sample cites the external member id.
    ok = build([member_id])
    assert ok.is_valid, ok.error_codes
    assert ok.record.samples[0].source_record_version_ids == (member_id,)
    assert member_id.startswith("externalmember:sha256:")

    # Foreign externalmember id not in the lineage -> rejected.
    foreign = "externalmember:sha256:" + "0" * 64
    assert build([foreign]).error_codes == ("DATASET_REFERENCE_INVALID",)

    # A canonical-looking record-version id (not an external member) -> rejected.
    assert build(["record:sha256:" + "1" * 64]).error_codes == ("DATASET_REFERENCE_INVALID",)

    # Mixed bound + foreign -> rejected.
    assert build([member_id, foreign]).error_codes == ("DATASET_REFERENCE_INVALID",)

    # A VALID binding of a DIFFERENT lineage (a smaller member selection) -> rejected
    # against this lineage: the binding<->lineage fields do not match.
    source2 = _write_files(tmp_path / "other", [default_rows()])
    context2 = _context()
    stream2 = off.convert_pmxt_v2_events(source2, context2)
    subset = list(stream2.ordered_event_digests)[:2]
    lin_subset = off.build_pmxt_v2_research_lineage(source2, context2, subset)
    assert lin_subset.is_valid and lin_subset.lineage_id != lin.lineage_id
    other_binding = off.build_pmxt_v2_dataset_binding(lin_subset, "commit:test").record
    sample = external_sample(
        member_id, "2030-01-01T00:00:00Z", "2030-01-02T00:00:00Z",
        "2030-01-03T00:00:00Z", feature_time="2020-01-01T00:00:00Z",
    )
    mismatch = off.build_pmxt_v2_research_dataset_manifest(
        lin, other_binding, [feature()], label(), [sample], "DECLARED_NO_ISOLATION"
    )
    assert mismatch.error_codes == ("DATASET_REFERENCE_INVALID",)


# --------------------------------------------------------------------------- #
# R012 — external feature availability bounds (>= source availability, <= decision)
# --------------------------------------------------------------------------- #

def test_external_feature_availability_bounds(tmp_path) -> None:
    lin, binding = external_binding(tmp_path)
    member = lin.members[0]
    member_id = member.member_id
    # availability_time_ns is receive-time (ts_init); compute the exact UTC boundary.
    boundary = os_contract  # namespace reuse for _utc_to_ns comparisons

    def build(feature_time, decision="2030-01-01T00:00:00Z"):
        sample = external_sample(
            member_id, decision, "2030-06-01T00:00:00Z",
            "2030-07-01T00:00:00Z", feature_time=feature_time,
        )
        return off.build_pmxt_v2_research_dataset_manifest(
            lin, binding, [feature()], label(), [sample], "DECLARED_NO_ISOLATION"
        )

    # Feature availability well after source availability and before decision -> OK.
    assert build("2020-01-01T00:00:00Z").is_valid

    # Feature availability BEFORE the source became available -> leakage.
    assert build("1970-01-01T00:00:00Z").error_codes == ("FEATURE_TIMING_LEAKAGE",)

    # Feature availability AFTER decision -> leakage (decision precedes feature).
    assert build("2020-01-01T00:00:00Z", decision="2019-01-01T00:00:00Z").error_codes == (
        "FEATURE_TIMING_LEAKAGE",
    )

    # Exact-boundary: feature availability == the cited member availability -> OK.
    avail_ns = member.availability_time_ns
    epoch_seconds, sub_ns = divmod(avail_ns, 1_000_000_000)
    import datetime as _dt
    exact = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc) + _dt.timedelta(seconds=epoch_seconds, microseconds=sub_ns // 1000)
    exact_utc = exact.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "000Z" if sub_ns else exact.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Normalize to the canonical UTC form the validator accepts.
    exact_utc = exact.strftime("%Y-%m-%dT%H:%M:%S") + (f".{exact.microsecond:06d}Z" if exact.microsecond else "Z")
    assert build(exact_utc).is_valid


# --------------------------------------------------------------------------- #
# R017 — invalid public surfaces never echo path/raw row/exception/secret
# --------------------------------------------------------------------------- #

def _strings(value):
    if is_dataclass(value) and not isinstance(value, type):
        return _strings(asdict(value))
    if isinstance(value, dict):
        return [item for key, val in value.items() for item in (_strings(key) + _strings(val))]
    if isinstance(value, (list, tuple)):
        return [item for val in value for item in _strings(val)]
    return [value] if isinstance(value, str) else []


def test_bridge_invalid_outputs_do_not_echo(tmp_path) -> None:
    sentinels = (
        "C:\\Users\\private\\wallet.txt",
        "sk_live_NEVER_ECHO_THIS",
        "SELECT secret FROM credentials",
        "Traceback: hostile failure",
        ".parquet",
    )
    lin, binding = external_binding(tmp_path)
    member_id = lin.members[0].member_id
    results = []
    # Hostile digest request (echo attempt via the requested identity).
    results.append(off.build_pmxt_v2_research_lineage(
        _write_files(tmp_path / "echo", [default_rows()]), _context(),
        [sentinels[0]],
    ))
    # Hostile lineage input to the binding builder.
    results.append(off.build_pmxt_v2_dataset_binding(sentinels[1], sentinels[2]))
    # Hostile sample content (market_id / group carry sentinels) on a real lineage.
    hostile_sample = external_sample(
        member_id, "2030-01-01T00:00:00Z", "2030-01-02T00:00:00Z",
        "2030-01-03T00:00:00Z", feature_time="2020-01-01T00:00:00Z",
    )
    hostile_sample["market_id"] = sentinels[2]
    hostile_sample["source_record_version_ids"] = [sentinels[0]]
    results.append(off.build_pmxt_v2_research_dataset_manifest(
        lin, binding, [feature()], label(), [hostile_sample], "DECLARED_NO_ISOLATION"
    ))
    for result in results:
        assert not result.is_valid
        for text in _strings(result):
            for sentinel in sentinels:
                assert sentinel not in text


# --------------------------------------------------------------------------- #
# R018 — no network/credential/scheduler/strategy/paper/execution/live/downloader
# --------------------------------------------------------------------------- #

def test_bridge_module_has_no_forbidden_authority() -> None:
    forbidden_import_roots = {
        "socket", "ssl", "http", "urllib", "requests", "httpx", "aiohttp",
        "websocket", "websockets", "subprocess", "asyncio", "threading",
        "multiprocessing", "sched", "signal", "boto3", "py_clob_client",
        "polymarket", "web3", "eth_account",
    }
    # Bare prose words (e.g. "downloader" in a docstring) are excluded; the
    # import-root scan is the mechanical guarantee that no network/downloader
    # library is reachable. These tokens catch actual runtime network/sleep usage.
    forbidden_tokens = (
        "time.sleep", "while True", "http://", "https://",
        "api_key", "private_key", "mnemonic", "requests.", "urlopen",
    )
    for source_path in (BRIDGE_SOURCE, CONVERSION_SOURCE):
        text = source_path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden_import_roots, alias.name
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                assert root not in forbidden_import_roots, node.module
        for token in forbidden_tokens:
            assert token not in text, token


# --------------------------------------------------------------------------- #
# Additional bridge coverage (lineage/binding mismatch, tamper, forged binding)
# --------------------------------------------------------------------------- #

def test_bridge_requires_valid_lineage_object(tmp_path) -> None:
    # A rejected lineage is not accepted by either bridge builder.
    bad = off.build_pmxt_v2_research_lineage(_write_files(tmp_path, [default_rows()]), _context(), [])
    assert not bad.is_valid
    assert not off.build_pmxt_v2_dataset_binding(bad, "commit:test").is_valid
    # Arbitrary metadata is never a lineage.
    assert not off.build_pmxt_v2_dataset_binding({"lineage_id": "x"}, "commit:test").is_valid


def test_forged_external_binding_identity_is_rejected(tmp_path) -> None:
    lin, binding = external_binding(tmp_path)
    member_id = lin.members[0].member_id
    sample = external_sample(
        member_id, "2030-01-01T00:00:00Z", "2030-01-02T00:00:00Z",
        "2030-01-03T00:00:00Z", feature_time="2020-01-01T00:00:00Z",
    )
    forged = replace(binding, dataset_binding_id="datasetbinding:sha256:" + "0" * 64)
    result = off.build_pmxt_v2_research_dataset_manifest(
        lin, forged, [feature()], label(), [sample], "DECLARED_NO_ISOLATION"
    )
    # The forged id fails the closed public-record identity recomputation.
    assert result.error_codes == ("IDENTITY_DERIVATION_MISMATCH",)
    assert result.record is None
