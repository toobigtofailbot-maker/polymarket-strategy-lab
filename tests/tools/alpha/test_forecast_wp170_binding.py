"""S10-R3-FORECAST-WP170-BIND-01: forecast target -> native WP170 ResearchSample / split-role binding.

Every registry below is a real native WP170 registry built with the native builders and verified with
``experiment_registry.load_and_verify_experiment_registry``. Samples cite the real PIT record versions of the
SANITIZED_SYNTHETIC S10-R3-FORECAST-01 grounding. Legacy v1 receipts are produced by the unchanged
pinned merged-main code (c249409, extracted with ``git archive``), not re-created by the new code.
Nothing here is real-world evidence: no OOS release, value, lift or qualification claim.
"""
from __future__ import annotations

import ast
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tarfile
from types import SimpleNamespace

import pytest

import src.data_layer.analytical_research as ar
from src.data_layer.analytical_research import experiment_os as EOS
from src.data_layer.analytical_research import forecast_evaluation as FE
from src.data_layer.point_in_time_market_research import (
    DATASET_REFERENCE_SCHEMA_ID,
    DATASET_REFERENCE_SCHEMA_VERSION,
    build_dataset_snapshot_reference,
    canonical_json_bytes,
    sha256_hex,
)
import tests.data_layer.analytical_research.test_experiment_os_preregistration as PRE
from tests.data_layer.analytical_research.test_experiment_os_identity import feature, label, source_record_id
from tests.tools.alpha.test_forecast_evaluation import (  # noqa: F401 - module fixtures
    CUTOFF, DECISION, MARKETS, _bound, _cases, _mid, baseline, world,
)
from tools.alpha import run_forecast_evaluation as CLI

REPO_ROOT = Path(__file__).resolve().parents[3]
LEGACY_COMMIT = "c249409de3be81de753ef1721842d3c2a5f6fdeb"
IDENTITY_FILES = ("src/data_layer/analytical_research/forecast_evaluation.py", "tools/alpha/run_forecast_evaluation.py",
                  "src/data_layer/analytical_research/source_grounding.py", "tools/alpha/run_source_grounding.py")
FILLERS = {"f": "2026-01-10T00:00:00Z", "s": "2026-03-10T00:00:00Z"}  # keep every split role non-empty
SPLIT = {"split_plan_version": "1.0.0", "formation_start": "2026-01-01T00:00:00Z", "selection_start": "2026-03-01T00:00:00Z",
         "oos_start": "2026-05-01T00:00:00Z", "end_time": "2028-06-01T00:00:00Z",
         "purge_rule": "PURGE_LABEL_AVAILABILITY_AT_OR_AFTER_NEXT_BOUNDARY", "embargo_seconds": 0,
         "group_policy": "EXCLUSIVE", "inclusion_policy": "DECISION_TIME_HALF_OPEN", "min_samples_per_role": 1}
FAKE_RULE = source_record_id("wimbledon-rule-v2")


def _plus(ts: str, **delta) -> str:
    return (datetime.fromisoformat(ts.replace("Z", "+00:00")) + timedelta(**delta)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stdout(capsys):
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def grounding(world):
    return _bound(world, _cases(world["src_receipt"]["receipt_id"]))


@pytest.fixture(scope="module")
def nm(grounding):
    """slug -> native PIT ObservedMarketState of the verified grounding universe."""
    by_id = {m.market_id: m for m in grounding["universe"].markets}
    return {slug: by_id[_mid(slug)] for slug, *_ in MARKETS}


def _sample(m, *, decision=DECISION, cite=None, leak=None, **over):
    value = {"source_record_version_ids": cite or [m.metadata_record_version_id], "market_id": m.market_id,
             "related_group_id": m.event_id, "leakage_group_id": leak or m.event_id, "decision_time": decision,
             "feature_availability_time": decision, "target_time": m.resolution_date,
             "label_availability_time": _plus(m.resolution_date, days=1)}
    value.update(over)
    return value


def _filler(suffix, decision):
    return {"source_record_version_ids": [source_record_id("filler-" + suffix)], "market_id": f"market:filler:{suffix}",
            "related_group_id": f"event:filler:{suffix}", "leakage_group_id": f"leak:filler:{suffix}",
            "decision_time": decision, "feature_availability_time": decision, "target_time": _plus(decision, days=1),
            "label_availability_time": _plus(decision, days=2)}


def _reference(ids):
    preimage = {"schema_id": DATASET_REFERENCE_SCHEMA_ID, "schema_version": DATASET_REFERENCE_SCHEMA_VERSION,
                "derivation_mode": "VALIDATED_RECORD_BATCH", "validated_batch_sha256": "a" * 64,
                "ordinary_record_version_ids": sorted(set(ids)), "review_conflict_record_version_ids": [],
                "query_spec_sha256": None, "query_result_sha256": None, "cutoff_mode": None, "cutoff_time": None,
                "result_view": None, "query_engine_version": None, "validator_version": "wp170-bind-test",
                "parameter_set_id": "wp170-bind-test", "human_review_required": False, "advisory_only": True,
                "no_execution_authority": True}
    mapping = dict(preimage, dataset_snapshot_reference_id="datasetref:sha256:" + sha256_hex(canonical_json_bytes(preimage)),
                   created_from_manifest_entry_id=None)
    result = build_dataset_snapshot_reference(mapping)
    assert result.is_valid
    return result.reference


def _registry(path: Path, nm: dict, samples: list, fillers=FILLERS, **split_over):
    """A real native WP170 registry: binding -> manifest (embedded samples) -> split -> preregistered experiment."""
    fill = [_filler(k, d) for k, d in fillers.items()]
    ids = [i for x in samples + fill for i in x["source_record_version_ids"]]  # WP170 caps the reference JSON size
    binding = ar.build_dataset_binding(_reference(ids), None, "commit:test")
    assert binding.is_valid, binding.error_codes
    features, label_def = [feature()], label()
    manifest = ar.build_research_dataset_manifest(binding.record, features, label_def,
                                                  samples + fill, "EXCLUSIVE")
    assert manifest.is_valid, manifest.error_codes
    split = ar.build_temporal_split_manifest(manifest.record, dict(SPLIT, **split_over))
    assert split.is_valid, split.error_codes
    hyp, met, base, fam = PRE.hypothesis(), PRE.metric(), PRE.baseline(), PRE.family()
    plan = {"trial_number": 1, "inclusion_exclusion_rules": "Use exact registered membership only.",
            "acceptance_thresholds": {"primary_metric_operator": "GTE", "primary_metric_threshold": "0.6"},
            "search_space": {"window_seconds": [60]}, "parameters": {"window_seconds": 60}, "random_seeds": [7],
            "cost_model_reference": None, "stop_failure_rules": "Stop on invalid evidence.", "code_version": "commit:test",
            "creation_provenance": "human:test", "preregistered_at": "2025-12-31T00:00:00Z"}
    experiment = ar.build_preregistered_experiment(hyp, binding.record, features, label_def, split.record, met, [], base,
                                                   fam, plan)
    assert experiment.is_valid, experiment.error_codes
    path.parent.mkdir(parents=True, exist_ok=True)
    assert ar.initialize_experiment_registry(path).is_valid
    records = (binding.record, features[0], label_def, manifest.record, split.record, hyp, met, base, fam, experiment.record)
    assert ar.append_experiment_records(path, records).is_valid
    return SimpleNamespace(path=path.resolve(), experiment=experiment.record, split=split.record, manifest=manifest.record)


def _rows(world, grounding, cases=None):
    cases = cases or _cases(world["src_receipt"]["receipt_id"])
    rows = FE.evaluate_targets(cases, grounding)
    FE.freeze_cohort(rows, cases["sampler"])
    return rows


def _map(world, grounding, reg, cases=None, g=None):
    _, native = FE.load_wp170(reg.path, reg.experiment.experiment_id)
    return FE.map_wp170_membership(_rows(world, grounding, cases), native, g or grounding, CUTOFF)


def _by_case(membership):
    return {e["case_id"]: e for e in membership["entries"]}


def _run(tmp_path, world, cases, name):
    path = tmp_path / f"{name}-cases.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    scratch = (tmp_path / name).resolve()
    code = CLI.main(["run", "--grounding-scratch", str(world["grounding"]), "--cases", str(path), "--scratch-dir", str(scratch)])
    receipt = json.loads((scratch / "receipt.json").read_text(encoding="utf-8")) if (scratch / "receipt.json").exists() else None
    return code, scratch, receipt


def _bound_cases(world, reg):
    return _cases(world["src_receipt"]["receipt_id"],
                  wp170={"registry_file": str(reg.path), "experiment_id": reg.experiment.experiment_id})


def _write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, sort_keys=True, indent=1).encode("utf-8"))


@pytest.fixture(scope="module")
def full_registry(tmp_path_factory, nm):
    """Every eligible grounded target has exactly one well-formed sample (all OUT_OF_SAMPLE)."""
    eligible = [s for s, _e, c, *_ in MARKETS if c != "crypto"]
    return _registry(tmp_path_factory.mktemp("wp170_full") / "registry.sqlite3", nm, [_sample(nm[s]) for s in eligible])


@pytest.fixture(scope="module")
def legacy(world, full_registry, tmp_path_factory):
    """Genuine pre-WP v1 receipts: the unchanged merged-main c249409 CLI, run as its own process."""
    root = tmp_path_factory.mktemp("legacy_code")
    archive = subprocess.run(["git", "-C", str(REPO_ROOT), "archive", "--format=tar", LEGACY_COMMIT, "src", "tools"],
                             capture_output=True, timeout=300)
    assert archive.returncode == 0, "the pinned legacy commit must be in the checkout history (fetch-depth 0)"
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(root, filter="data")
    out = {}
    base = tmp_path_factory.mktemp("legacy_runs")
    rid = world["src_receipt"]["receipt_id"]
    for name, cases in (("unbound", _cases(rid)), ("bound", _bound_cases(world, full_registry))):
        path = base / f"{name}-cases.json"
        path.write_text(json.dumps(cases), encoding="utf-8")
        scratch = (base / name).resolve()
        proc = subprocess.run([sys.executable, "-B", str(root / "tools" / "alpha" / "run_forecast_evaluation.py"), "run",
                               "--grounding-scratch", str(world["grounding"]), "--cases", str(path), "--scratch-dir",
                               str(scratch)], capture_output=True, text=True, timeout=600, cwd=str(base))
        assert proc.returncode == 0, proc.stdout + proc.stderr
        out[name] = (scratch, json.loads((scratch / "receipt.json").read_text(encoding="utf-8")), json.loads(proc.stdout))
    return out


# ------------------------------------------------------------------ R001


def test_wp170_registry_manifest_and_sample_load(world, grounding, nm, full_registry, tmp_path):
    reg = full_registry
    before = _sha(reg.path.read_bytes())
    public, native = FE.load_wp170(reg.path, reg.experiment.experiment_id)
    loaded = ar.load_and_verify_experiment_registry(reg.path)
    assert loaded.is_valid and public["registry_head_entry_hash"] == loaded.snapshot.head_entry_hash
    assert native["experiment"] == reg.experiment and native["split"] == reg.split and native["manifest"] == reg.manifest
    manifest = native["manifest"]
    assert isinstance(manifest, EOS.ResearchDatasetManifest) and all(isinstance(s, EOS.ResearchSample) for s in manifest.samples)
    assert len(manifest.samples) == manifest.total_sample_count == len([m for m in MARKETS if m[2] != "crypto"]) + 2
    assert manifest.research_dataset_manifest_id == reg.experiment.research_dataset_manifest_id == reg.split.dataset_manifest_id
    assert manifest.dataset_binding_id == reg.experiment.dataset_binding_id and manifest.label_definition_id == reg.experiment.label_definition_id
    assert public["oos_membership_hash"] == EOS.membership_hash(reg.split, "OUT_OF_SAMPLE")
    assert FE.bind_wp170(reg.path, reg.experiment.experiment_id) == public  # v1 public block unchanged in shape
    # read-only: bytes, row count and sidecars untouched; no sample is manufactured
    assert _sha(reg.path.read_bytes()) == before and not any(Path(str(reg.path) + s).exists() for s in ("-wal", "-shm", "-journal"))
    with sqlite3.connect(f"file:{reg.path}?mode=ro", uri=True) as con:
        assert con.execute("SELECT COUNT(*) FROM experiment_records").fetchone()[0] == 10
    # identity disagreements stop (forged native objects; a verified registry cannot hold them)
    exp, split = native["experiment"], native["split"]
    forged = (
        (replace(exp, research_dataset_manifest_id="researchdataset:sha256:" + "0" * 64), split, manifest),
        (replace(exp, dataset_binding_id="dataset:sha256:" + "0" * 64), split, manifest),
        (exp, replace(split, feature_set_id="featureset:sha256:" + "0" * 64), manifest),
        (exp, split, replace(manifest, label_definition_id="label:sha256:" + "0" * 64)),
        (exp, split, replace(manifest, samples=manifest.samples + manifest.samples[:1], total_sample_count=manifest.total_sample_count + 1)),
        (exp, split, replace(manifest, samples=(replace(manifest.samples[0], feature_set_id="x"),) + manifest.samples[1:])),
    )
    for args in forged:
        with pytest.raises(FE.EvaluationStop, match="WP170_IDENTITY_MISMATCH"):
            FE.check_wp170_identities(*args)
    with pytest.raises(FE.EvaluationStop, match="WP170_SPLIT_INVALID"):
        FE.check_wp170_identities(exp, replace(split, oos_sample_ids=split.oos_sample_ids + ("sample:sha256:" + "0" * 64,)), manifest)
    # missing experiment, missing / corrupt / tampered registry stop the whole run
    with pytest.raises(FE.EvaluationStop, match="WP170_EXPERIMENT_NOT_FOUND"):
        FE.load_wp170(reg.path, "experiment:sha256:" + "0" * 64)
    with pytest.raises(FE.EvaluationStop, match="WP170_REGISTRY_INVALID"):
        FE.load_wp170(tmp_path / "absent.sqlite3", reg.experiment.experiment_id)
    tampered = tmp_path / "tampered.sqlite3"  # the registry is append-only, so tamper the stored bytes directly
    raw = reg.path.read_bytes()
    assert b"DECISION_TIME_HALF_OPEN" in raw
    tampered.write_bytes(raw.replace(b"DECISION_TIME_HALF_OPEN", b"DECISION_TIME_HALF_OPEM"))
    with pytest.raises(FE.EvaluationStop, match="WP170_REGISTRY_INVALID"):
        FE.load_wp170(tampered, reg.experiment.experiment_id)


# ------------------------------------------------------------------ R002


def test_wp170_target_to_sample_exact_binding(world, grounding, nm, tmp_path):
    s = nm
    samples = [
        _sample(s["ga-gov"]),                                                           # exact -> MAPPED
        _sample(s["fr-assembly"], decision=_plus(DECISION, days=1)),                    # wrong decision time
        _sample(s["house-control"]),
        _sample(s["house-control"], cite=[s["house-control"].metadata_record_version_id, source_record_id("filler-o")]),
        _sample(s["shutdown"], cite=[source_record_id("filler-o")]),                     # no PIT metadata citation
        _sample(s["tdf"], cite=[s["tdf"].metadata_record_version_id, s["nyc-temp"].metadata_record_version_id]),
        _sample(s["wimbledon"], cite=[s["wimbledon"].metadata_record_version_id, FAKE_RULE]),
        _sample(s["nba-celtics"], cite=[s["nba-celtics"].metadata_record_version_id, s["nba-celtics"].rules[0].rule_record_version_id]),
        _sample(s["oh-sen-dem"], leak="leak:senate-a"),                                 # one event, two leakage groups
        _sample(s["oh-sen-rep"], leak="leak:senate-b"),
        _sample(s["nyc-rain"], leak="leak:shared"),                                     # two events, one leakage group
        _sample(s["london-snow"], leak="leak:shared"),
        _sample(s["btc-100k"]),                                                         # ineligible target: never bound
    ]
    reg = _registry(tmp_path / "r2" / "registry.sqlite3", nm, samples)
    # a second native rule version for wimbledon whose hash differs from the target's bound rule
    wim = s["wimbledon"]
    extra = replace(wim.rules[0], rule_record_version_id=FAKE_RULE, rule_content_sha256="0" * 64)
    g2 = dict(grounding, universe=SimpleNamespace(markets=tuple(
        replace(m, rules=m.rules + (extra,)) if m.market_id == wim.market_id else m for m in grounding["universe"].markets)))
    membership = _map(world, grounding, reg, g=g2)
    cases = _by_case(membership)
    expect = {
        "t-ga-gov": ("MAPPED", None), "t-uk-pm": ("UNMAPPED", "SAMPLE_NOT_FOUND"),
        "t-fr-assembly": ("UNMAPPED", "DECISION_TIME_MISMATCH"), "t-house-control": ("AMBIGUOUS", "MULTIPLE_SAMPLES_MATCH"),
        "t-shutdown": ("UNMAPPED", "SOURCE_PROVENANCE_UNPROVEN"), "t-tdf": ("REFUSED", "CROSS_MARKET_SOURCE"),
        "t-wimbledon": ("REFUSED", "RULE_VERSION_CONFLICT"), "t-nba-celtics": ("MAPPED", None),
        "t-oh-sen-dem": ("REFUSED", "EVENT_LEAKAGE_GROUP_CONFLICT"), "t-oh-sen-rep": ("REFUSED", "EVENT_LEAKAGE_GROUP_CONFLICT"),
        "t-nyc-rain": ("REFUSED", "EVENT_LEAKAGE_GROUP_CONFLICT"), "t-london-snow": ("REFUSED", "EVENT_LEAKAGE_GROUP_CONFLICT"),
    }
    for case_id, (status, reason) in expect.items():
        assert (cases[case_id]["status"], cases[case_id]["reason"]) == (status, reason), case_id
    native_ids = {x.market_id: x.sample_id for x in reg.manifest.samples}
    assert cases["t-ga-gov"]["sample_id"] == native_ids[_mid("ga-gov")] and cases["t-ga-gov"]["role"] == "OUT_OF_SAMPLE"
    assert cases["t-shutdown"]["sample_id"] is None and cases["t-uk-pm"]["sample_id"] is None
    assert "t-btc-100k" not in cases  # ineligible (crypto): counted, not bound
    d = membership["denominators"]
    assert d["targets_offered"] == len(MARKETS) and d["binding_frame"] + d["not_eligible_not_bound"] == d["targets_offered"]
    assert d["mapped"] + d["unmapped"] + d["ambiguous"] + d["refused"] == d["binding_frame"] == len(membership["entries"])
    assert d["mapped"] == 2 and d["ambiguous"] == 1 and d["refused"] == 6
    assert d["by_reason"]["SAMPLE_NOT_FOUND"] == d["binding_frame"] - len(expect) + 1  # every target without a sample
    assert sum(d["by_reason"].values()) == d["binding_frame"] - d["mapped"]
    assert d["mapped_by_role"] == {"FORMATION": 0, "SELECTION": 0, "OUT_OF_SAMPLE": 2}
    # deterministic, and the frozen cohort is unchanged by binding
    assert _map(world, grounding, reg, g=g2) == membership
    assert membership["cohort_selection_changed"] is False and membership["labels_read_for_mapping"] is False


# ------------------------------------------------------------------ R003


def test_wp170_oos_seal_and_split_roles(world, grounding, nm, tmp_path, full_registry):
    s = nm
    oos = _map(world, grounding, full_registry)
    assert oos["denominators"]["mapped"] == oos["denominators"]["binding_frame"]
    split = full_registry.split
    assert oos["membership_hashes"] == {r: EOS.membership_hash(split, r) for r in ("FORMATION", "SELECTION", "OUT_OF_SAMPLE")}
    assert oos["split_assignment_hash"] == split.assignment_hash
    assert {e["sample_id"] for e in oos["entries"]} <= set(split.oos_sample_ids)
    # SELECTION role: same targets, a split whose selection window holds the decision time
    sel_over = dict(oos_start="2027-12-01T00:00:00Z", end_time="2028-06-01T00:00:00Z")
    reg = _registry(tmp_path / "sel" / "registry.sqlite3", nm,
                    [_sample(s["ga-gov"]), _sample(s["uk-pm"], label_availability_time="2027-12-02T00:00:00Z")],
                    fillers=dict(FILLERS, o="2027-12-10T00:00:00Z"), **sel_over)
    cases = _by_case(_map(world, grounding, reg))
    assert cases["t-ga-gov"]["status"] == "MAPPED" and cases["t-ga-gov"]["role"] == "SELECTION"
    assert cases["t-ga-gov"]["sample_id"] in reg.split.selection_sample_ids
    assert (cases["t-uk-pm"]["status"], cases["t-uk-pm"]["reason"]) == ("REFUSED", "SAMPLE_PURGED")
    assert cases["t-uk-pm"]["sample_id"] in reg.split.purged_sample_ids and cases["t-uk-pm"]["role"] is None
    # embargoed and outside the split window
    emb = _registry(tmp_path / "emb" / "registry.sqlite3", nm, [_sample(s["ga-gov"])],
                    fillers=dict(FILLERS, o="2026-07-10T00:00:00Z"), oos_start="2026-06-01T00:00:00Z", embargo_seconds=172800)
    e = _by_case(_map(world, grounding, emb))["t-ga-gov"]
    assert (e["status"], e["reason"]) == ("REFUSED", "SAMPLE_EMBARGOED") and e["sample_id"] in emb.split.embargoed_sample_ids
    out = _registry(tmp_path / "out" / "registry.sqlite3", nm, [_sample(s["ga-gov"])],
                    fillers=dict(FILLERS, o="2026-05-10T00:00:00Z"), end_time="2026-06-01T00:00:00Z")
    e = _by_case(_map(world, grounding, out))["t-ga-gov"]
    assert (e["status"], e["reason"]) == ("REFUSED", "SAMPLE_OUTSIDE_SPLIT_WINDOW")
    # a sample in two role sets is a corrupt split (a verified registry rebuilds splits), never resolved by choosing one
    _, native = FE.load_wp170(full_registry.path, full_registry.experiment.experiment_id)
    ga = next(x.sample_id for x in native["manifest"].samples if x.market_id == _mid("ga-gov"))
    for field in ("selection_sample_ids", "purged_sample_ids"):
        forged = replace(native["split"], **{field: getattr(native["split"], field) + (ga,)})
        with pytest.raises(FE.EvaluationStop, match="WP170_SPLIT_INVALID"):
            FE.check_wp170_identities(native["experiment"], forged, native["manifest"])
    # diagnostic only: no OOS release, RunEvidenceReceipt, lifecycle record or registry write
    assert oos["oos_release"] == "NOT_RELEASED" and oos["run_evidence_receipt"] is None and oos["qualification_claim"] is False
    kinds = {type(x.record).__name__ for x in ar.load_and_verify_experiment_registry(full_registry.path).snapshot.entries}
    assert not kinds & {"RunEvidenceReceipt", "LifecycleReceipt"}


# ------------------------------------------------------------------ R004


def test_wp170_temporal_and_leakage_safety(world, grounding, nm, tmp_path, full_registry, capsys):
    s = nm
    early = "2026-06-01T00:00:00Z"  # before the native PIT metadata observation (00:00:01Z)
    reg = _registry(tmp_path / "r4" / "registry.sqlite3", nm, [
        _sample(s["ga-gov"], feature_availability_time=early),
        _sample(s["uk-pm"], target_time=_plus(DECISION, hours=1), label_availability_time=_plus(DECISION, hours=2)),
        _sample(s["fr-assembly"], label_availability_time="2028-02-01T00:00:00Z"),
        _sample(s["house-control"]),
    ])
    cases = _by_case(_map(world, grounding, reg))
    assert cases["t-ga-gov"]["reason"] == "FEATURE_BEFORE_SOURCE_OBSERVED"
    assert cases["t-uk-pm"]["reason"] == "TARGET_BEFORE_NATIVE_RESOLUTION"
    assert cases["t-fr-assembly"]["reason"] == "LABEL_AVAILABLE_AFTER_SCORING_CUTOFF"
    assert cases["t-house-control"]["status"] == "MAPPED"  # sound cases continue
    # a feature available after the decision (forged; the native builder already refuses it)
    _, native = FE.load_wp170(reg.path, reg.experiment.experiment_id)
    m = native["manifest"]
    forged = dict(native, manifest=replace(m, samples=tuple(
        replace(x, feature_availability_time=_plus(DECISION, seconds=1)) if x.market_id == _mid("house-control") else x
        for x in m.samples)))
    e = _by_case(FE.map_wp170_membership(_rows(world, grounding), forged, grounding, CUTOFF))["t-house-control"]
    assert (e["status"], e["reason"]) == ("REFUSED", "FEATURE_AFTER_DECISION")
    # outcomes are never read for mapping: changing or removing every label leaves the binding identical
    rid = world["src_receipt"]["receipt_id"]
    blind = _cases(rid)
    for t in blind["targets"]:
        t["outcome"] = None
    flipped = _cases(rid)
    for t in flipped["targets"]:
        if t["outcome"]:
            t["outcome"]["label"] = "No" if t["outcome"]["label"] == "Yes" else "Yes"
    base = _map(world, grounding, full_registry)
    assert _map(world, grounding, full_registry, blind) == base == _map(world, grounding, full_registry, flipped)
    # whole-run stops: a corrupt registry or a tampered source receipt is never processed per case
    junk = tmp_path / "junk.sqlite3"
    junk.write_bytes(b"SQLite format 3\x00 truncated")
    bad = _cases(rid, wp170={"registry_file": str(junk.resolve()), "experiment_id": full_registry.experiment.experiment_id})
    assert _run(tmp_path, world, bad, "junk")[0] == 1 and _stdout(capsys)["reason_code"] == "WP170_REGISTRY_INVALID"
    foreign = _bound_cases(world, full_registry)
    foreign["grounding_receipt_id"] = FE.SG.RECEIPT_PREFIX + "0" * 64
    assert _run(tmp_path, world, foreign, "foreign")[0] == 1 and _stdout(capsys)["reason_code"] == "GROUNDING_RECEIPT_MISMATCH"


# ------------------------------------------------------------------ R005


def test_wp170_receipt_identity_denominators_and_tamper(world, baseline, full_registry, legacy, tmp_path, capsys):
    code, scratch, receipt = _run(tmp_path, world, _bound_cases(world, full_registry), "bound")
    assert code == 0
    core = receipt["core"]
    assert core["schema_id"] == FE.RECEIPT_SCHEMA and core["code_identity"] == CLI.code_identity()
    w = core["wp170"]
    assert w["status"] == "WP170_REFERENCES_VERIFIED_READ_ONLY_MEMBERSHIP_MAPPED"
    assert w["membership"]["denominators"]["mapped"] == w["membership"]["denominators"]["binding_frame"] > 0
    assert w["membership"]["membership_hashes"]["OUT_OF_SAMPLE"] == w["oos_membership_hash"]
    sel = w["membership"]["denominators"]["selected_mapped_by_role"]["OUT_OF_SAMPLE"]
    assert sel == core["cohort"]["denominators"]["selected"]
    # binding never changes the cohort or scores: identical to the unbound v2 baseline
    unbound = baseline[1]["core"]
    assert unbound["schema_id"] == FE.RECEIPT_SCHEMA and unbound["wp170"]["membership"] is None
    assert core["cohort"] == unbound["cohort"] and core["scoring"] == unbound["scoring"] and core["forecasts"] == unbound["forecasts"]
    assert CLI.verify(scratch)["status"] == "VERIFIED"
    # tamper: a membership entry, a schema downgrade, and the frozen registry copy
    for name, mutate in (("entry", lambda c: c["wp170"]["membership"]["entries"][0].update(role="SELECTION")),
                         ("downgrade", lambda c: c.update(schema_id=FE.LEGACY_RECEIPT_SCHEMA)),
                         ("unknown", lambda c: c.update(schema_id=["v9"]))):
        bad = json.loads(json.dumps(receipt))
        mutate(bad["core"])
        _write(scratch / "receipt.json", bad)
        out = CLI.verify(scratch)
        assert out["status"] == "TAMPER_DETECTED" and "RECEIPT_ID_MISMATCH" in out["failures"], name
    _write(scratch / "receipt.json", receipt)
    frozen_registry = scratch / "inputs" / "wp170.sqlite3"
    original = frozen_registry.read_bytes()
    frozen_registry.write_bytes(original[:-512])
    assert CLI.main(["verify", "--scratch-dir", str(scratch)]) == 1 and _stdout(capsys)["reason_code"] == "WP170_REGISTRY_INVALID"
    frozen_registry.write_bytes(original)
    # genuine legacy v1 receipts from the pinned c249409 code verify unchanged: id, identity and scores
    blobs = hashlib.sha256()
    for path in IDENTITY_FILES:
        blobs.update(subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"{LEGACY_COMMIT}:{path}"], capture_output=True,
                                    check=True).stdout)
    assert FE.LEGACY_V1_CODE_IDENTITY == "code:sha256:" + blobs.hexdigest() != CLI.code_identity()
    for name in ("unbound", "bound"):
        lscratch, lreceipt, run_out = legacy[name]
        lcore = lreceipt["core"]
        assert lcore["schema_id"] == FE.LEGACY_RECEIPT_SCHEMA and lcore["code_identity"] == FE.LEGACY_V1_CODE_IDENTITY
        assert run_out["receipt_id"] == lreceipt["receipt_id"] and "membership" not in lcore["wp170"]
        assert CLI.verify(lscratch) == {"status": "VERIFIED", "failures": [], "receipt_id": lreceipt["receipt_id"],
                                        "network_attempts": 0}
        assert lcore["scoring"] == unbound["scoring"] and lcore["cohort"] == unbound["cohort"]
    assert legacy["bound"][1]["core"]["wp170"]["status"] == "WP170_REFERENCES_VERIFIED_READ_ONLY_MEMBERSHIP_NOT_MAPPED"
    # a legacy receipt is never accepted with altered scores, a current-code digest, or a v2 relabel
    lscratch, lreceipt, _ = legacy["unbound"]
    try:
        for name, mutate in (("score", lambda c: c["scoring"]["denominators"].update(paired_intersection=0)),
                             ("restamp", lambda c: c.update(code_identity=CLI.code_identity())),
                             ("relabel", lambda c: c.update(schema_id=FE.RECEIPT_SCHEMA))):
            bad = json.loads(json.dumps(lreceipt))
            mutate(bad["core"])
            bad["receipt_id"] = FE.RECEIPT_PREFIX + FE.SG.sha256_hex(FE.SG.canonical_bytes(bad["core"]))  # self-consistent forgery
            _write(lscratch / "receipt.json", bad)
            out = CLI.verify(lscratch)
            assert out["status"] == "TAMPER_DETECTED" and any(f.startswith("OUTPUT_MISMATCH:") for f in out["failures"]), name
    finally:
        _write(lscratch / "receipt.json", lreceipt)
    assert CLI.verify(lscratch)["status"] == "VERIFIED"


# ------------------------------------------------------------------ R006


def test_wp170_real_cli_offline_no_authority(world, full_registry, legacy, tmp_path):
    before = _sha(full_registry.path.read_bytes())
    cases_path = tmp_path / "cli-cases.json"
    cases_path.write_text(json.dumps(_bound_cases(world, full_registry)), encoding="utf-8")
    entry = str(REPO_ROOT / "tools" / "alpha" / "run_forecast_evaluation.py")
    receipts = []
    for name in ("a", "b"):  # the real entry point as its own process, twice: deterministic membership
        scratch = (tmp_path / f"cli-{name}").resolve()
        proc = subprocess.run([sys.executable, "-B", entry, "run", "--grounding-scratch", str(world["grounding"]), "--cases",
                               str(cases_path), "--scratch-dir", str(scratch)], capture_output=True, text=True, timeout=600)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        out = json.loads(proc.stdout)
        assert out["status"] == "RUN_COMPLETE" and out["network_attempts"] == 0
        assert out["wp170_status"] == "WP170_REFERENCES_VERIFIED_READ_ONLY_MEMBERSHIP_MAPPED"
        receipts.append(json.loads((scratch / "receipt.json").read_text(encoding="utf-8")))
        verify = subprocess.run([sys.executable, "-B", entry, "verify", "--scratch-dir", str(scratch)], capture_output=True,
                                text=True, timeout=600)
        assert verify.returncode == 0 and json.loads(verify.stdout)["status"] == "VERIFIED"
    assert receipts[0]["receipt_id"] == receipts[1]["receipt_id"]
    assert receipts[0]["core"]["wp170"]["membership"] == receipts[1]["core"]["wp170"]["membership"]
    assert _sha(full_registry.path.read_bytes()) == before  # the caller's registry is read, never written
    # tamper rejection through the real process
    scratch = (tmp_path / "cli-a").resolve()
    bad = json.loads(json.dumps(receipts[0]))
    bad["core"]["wp170"]["membership"]["denominators"]["mapped"] += 1
    _write(scratch / "receipt.json", bad)
    proc = subprocess.run([sys.executable, "-B", entry, "verify", "--scratch-dir", str(scratch)], capture_output=True, text=True,
                          timeout=600)
    assert proc.returncode == 1 and json.loads(proc.stdout)["status"] == "TAMPER_DETECTED"
    # legacy replay through the real process (receipts genuinely produced by the pinned c249409 code)
    for name in ("unbound", "bound"):
        lscratch, lreceipt, _ = legacy[name]
        proc = subprocess.run([sys.executable, "-B", entry, "verify", "--scratch-dir", str(lscratch)], capture_output=True,
                              text=True, timeout=600)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert json.loads(proc.stdout) == {"status": "VERIFIED", "failures": [], "receipt_id": lreceipt["receipt_id"],
                                           "network_attempts": 0}
    # no new command, network, provider, registry-write or trading surface in the changed source
    for path in (Path(FE.__file__), Path(CLI.__file__)):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
                {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        assert not names & {"socket", "urllib", "urllib.request", "http.client", "requests", "subprocess", "httpx", "ssl"}
        assert not any(x and any(p in x for p in ("execution", "paper_trading", "live_pilot", "hermes", "research_runtime",
                                                    "polymarket_client", "strategy")) for x in names)
        for word in ("append_experiment_records", "build_run_evidence_receipt", "build_lifecycle_receipt", "initialize_"):
            assert word not in source
    help_out = subprocess.run([sys.executable, "-B", entry, "--help"], capture_output=True, text=True, timeout=120).stdout
    assert "{run,verify}" in help_out


# ------------------------------------------------------------------ R007


def test_wp170_negative_cases_unbound_and_value_truth(world, grounding, baseline, full_registry, tmp_path, monkeypatch, capsys):
    rid = world["src_receipt"]["receipt_id"]
    core = baseline[1]["core"]
    # absent binding stays diagnostic only
    assert core["wp170"]["status"] == "DIAGNOSTIC_ONLY_EXPERIMENT_UNBOUND" and core["wp170"]["membership"] is None
    unbound = FE.bind_wp170(None, None)
    with pytest.raises(FE.EvaluationStop, match="WP170_NATIVE_CONTEXT_MISSING"):
        FE.build_evaluation_core(_cases(rid), grounding, dict(unbound, experiment_id="x"), "code:test", {})
    _, native = FE.load_wp170(full_registry.path, full_registry.experiment.experiment_id)
    with pytest.raises(FE.EvaluationStop, match="WP170_NATIVE_CONTEXT_MISSING"):
        FE.build_evaluation_core(_cases(rid), grounding, unbound, "code:test", {}, native)
    with pytest.raises(FE.EvaluationStop, match="RECEIPT_SCHEMA_UNSUPPORTED"):
        FE.build_evaluation_core(_cases(rid), grounding, unbound, "code:test", {}, None, "s10-r3-forecast01-score-receipt-v3")
    legacy_core = FE.build_evaluation_core(_cases(rid), grounding, unbound, "code:test", {}, None, FE.LEGACY_RECEIPT_SCHEMA)
    assert "membership" not in legacy_core["wp170"] and legacy_core["schema_id"] == FE.LEGACY_RECEIPT_SCHEMA
    # malformed, untrusted or secret / trade-shaped inputs fail closed without echoing them
    reg = str(full_registry.path)
    exp = full_registry.experiment.experiment_id
    for name, binding, code in (
            ("extra", {"registry_file": reg, "experiment_id": exp, "split": "x"}, "WP170_BINDING_INVALID"),
            ("type", {"registry_file": reg, "experiment_id": 7}, "WP170_BINDING_INVALID"),
            ("empty", {}, "WP170_BINDING_INVALID"),
            ("relative", {"registry_file": "registry.sqlite3", "experiment_id": exp}, "WP170_REGISTRY_UNUSABLE")):
        assert _run(tmp_path, world, _cases(rid, wp170=binding), name)[0] == 1
        out = _stdout(capsys)
        assert out["reason_code"] == code and reg not in json.dumps(out), name
    secret = _bound_cases(world, full_registry)
    secret["case_label"] = "fc01-" + "sk" + "-" + "A" * 40
    assert _run(tmp_path, world, secret, "secret")[0] == 1
    assert _stdout(capsys)["reason_code"] in ("SECRET_MATERIAL_REJECTED", "CASE_LABEL_INVALID")
    trade = _bound_cases(world, full_registry)
    trade["targets"][0]["order_size"] = "5"
    assert _run(tmp_path, world, trade, "trade")[0] == 1 and _stdout(capsys)["reason_code"] == "FORBIDDEN_FIELD"
    Path(reg + "-wal").write_bytes(b"")
    try:
        assert _run(tmp_path, world, _bound_cases(world, full_registry), "sidecar")[0] == 1
        assert _stdout(capsys)["reason_code"] == "STORE_SIDECAR_PRESENT"
    finally:
        Path(reg + "-wal").unlink()
    # a non-dict receipt is a shape failure, not trusted
    code, scratch, receipt = _run(tmp_path, world, _bound_cases(world, full_registry), "shape")
    assert code == 0
    _write(scratch / "receipt.json", [receipt])
    assert CLI.verify(scratch)["failures"] == ["RECEIPT_SHAPE_INVALID"]
    # any network attempt during binding fails the run
    monkeypatch.setattr(FE, "map_wp170_membership", lambda *a, **k: socket.create_connection(("example.invalid", 80)))
    assert _run(tmp_path, world, _bound_cases(world, full_registry), "net")[0] == 1
    assert _stdout(capsys)["reason_code"] == "NETWORK_ATTEMPT_BLOCKED"
    monkeypatch.undo()
    # synthetic evidence never becomes real PIT, OOS release, value or adoption acceptance
    core = receipt["core"]
    m = core["wp170"]["membership"]
    assert core["corpus_class"] == "SANITIZED_SYNTHETIC" and core["scoring"]["lift_status"] == "SYNTHETIC_CONTRACT_EVIDENCE_NOT_VALUE"
    assert m["oos_release"] == "NOT_RELEASED" and m["run_evidence_receipt"] is None and m["qualification_claim"] is False
    assert core["authority"]["wp170_run_evidence_receipt"] is False and core["authority"]["real_value_verified"] is False
    assert core["authority"]["network_calls"] == 0 and core["authority"]["provider_calls"] == 0
    a = core["adoption"]
    assert a == FE.ADOPTION and a["R3-12-SAMPLER"] == "INTEGRATED_OFFLINE_NOT_VALUE_VERIFIED"
    assert a["other_program_ids"] == "UNCHANGED_27_OF_36" and a["provider_lanes"] == "UNCHANGED_SIX_OWNER_GATED"
    assert "REAL_VALUE_VERIFIED" not in json.dumps(receipt).replace("NO_REAL_VALUE_VERIFIED", "")
    assert core["successor"]["wp_id"] == "S10-R3-LEARN-01" and core["successor"]["status"] == "MANDATORY_PENDING"
