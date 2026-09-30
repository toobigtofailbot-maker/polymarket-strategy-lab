"""S10-QUAL-DATA-01 readiness assembly tests (R014-R024, R029). Hermetic, offline, no decoder."""

from __future__ import annotations

import ast
import copy
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.data_layer.analytical_research import nws_ndfd_history as ndfd
from src.data_layer.analytical_research import pendulumflow_v3 as v3
from src.data_layer.analytical_research import qualification_data_readiness as qd

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "ndfd_grib" / "ndfd_pop12_reference.grib2"
MODULE = ROOT / "src" / "data_layer" / "analytical_research" / "qualification_data_readiness.py"
OPERATOR = ROOT / "tools" / "qualification" / "run_s10_qual_data_01.py"
CONDITION = "0x" + "0f" * 32
YES, NO = "104019219973195927512773044938021400951414920684302388248992716945822821205929", "113167652799514890762834887413625876113191931693034136211969831764710778770543"

RULE_FIRST = (
    'This market will resolve to "Yes" if New York, NY records measurable precipitation on September 3, 2026. '
    'Otherwise, this market will resolve to "No".\n\nMeasurable precipitation means 0.01 inches or more as reported by '
    "the PRECIPITATION (IN) figure in the NWS Daily Climate Report (CLI) for the city's station.\n\n"
    'A report of trace ("T") does not qualify.\n\nThe observation period is the NWS climate day for KNYC: midnight to '
    "midnight local standard time. The final CLI report for a climate day is issued the following morning.\n\n"
    "Resolution is based on the station's first published precipitation figure for the day. Subsequent revisions or "
    "corrections to the published data will not be considered; the first published value is final. If no figure has "
    'been published by 11:59 PM ET on the day following the observation date, this market will resolve to "No".\n\n'
    "The resolution source for this market is the NWS Daily Climate Report (CLI) for KNYC."
)
RULE_LATEST = RULE_FIRST.replace(
    "Resolution is based on the station's first published precipitation figure for the day. Subsequent revisions or "
    "corrections to the published data will not be considered; the first published value is final.",
    "Resolution is based on the latest published precipitation figure available by 11:59 PM ET on the day following the observation date.",
)
RULE_LAST_1400 = RULE_FIRST.replace(
    "Resolution is based on the station's first published precipitation figure for the day. Subsequent revisions or "
    "corrections to the published data will not be considered; the first published value is final.",
    "Resolution is based on the last published precipitation figure available before 2:00 PM ET on the day following the observation date.",
)


def candidate(market_id: str = "3719310", received: str = "2026-09-03T11:09:14.805697Z") -> qd.MarketCandidate:
    return qd.MarketCandidate(market_id, CONDITION, (YES, NO), ("Yes", "No"), "Will it rain in New York, NY on September 3?",
                              "where-will-it-rain-on-september-3-2026-new-york-ny", received, "2026-09-03/11")


def gamma_doc(**overrides: object) -> dict[str, object]:
    document: dict[str, object] = {
        "id": "3719310", "conditionId": CONDITION, "slug": "where-will-it-rain-on-september-3-2026-new-york-ny",
        "clobTokenIds": json.dumps([YES, NO]), "outcomes": json.dumps(["Yes", "No"]),
        "outcomePrices": json.dumps(["0", "1"]), "closed": True, "umaResolutionStatus": "resolved",
        "startDate": "2026-09-03T11:09:13Z", "closedTime": "2026-09-04 14:18:05.177609+00", "description": RULE_FIRST,
        "resolutionSource": "https://forecast.weather.gov/product.php?site=NWS&issuedby=NYC&product=CLI",
        "feesEnabled": True, "feeType": "weather_fees", "feeSchedule": {"rate": 0.05, "takerOnly": True},
        "orderMinSize": 5, "orderPriceMinTickSize": 0.001,
    }
    document.update(overrides)
    return document


def event(family: str, received: str, venue: str | None = None, *, asset: str | None = YES, hour: str | None = None,
          **fields: str | None) -> v3.V3Event:
    market_id = "3719310" if family in ("new_market", "market_resolved") else None
    return v3.V3Event(family, hour or received[:10] + "/" + received[11:13], 0, CONDITION,
                      None if family in ("new_market", "market_resolved") else asset, market_id,
                      received, venue or received, tuple(sorted(fields.items())))


def weather_parts(public_time: str = "2026-09-03T10:51:56Z"):
    message = FIXTURE.read_bytes()
    header = ndfd.parse_pop12_header(message)
    piece = ndfd.MessageSlice(0, 80, len(message), "ecdac869039c2342f8a8ff8c57aa4fef602728e3257d0de7af5c091047c719ea")
    station = ndfd.StationMetadata("KNYC", 40.78333, -73.96667, "America/New_York", "Central Park")
    value = ndfd.StationValue("KNYC", 1846511, 40.775844, -73.970832, 1.03, 99)
    decoded = ndfd.DecodedPop12(header, (("edition", 2),), (value,))
    vintage = ndfd.NdfdObject("wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046", "2026-09-03T10:46:00Z", public_time,
                              ndfd.AVAILABILITY_BASIS, 2660227)
    return vintage, [(piece, decoded)], station


CHECKPOINT = datetime(2026, 9, 3, 12, 9, 14, 805697, tzinfo=timezone.utc)


def test_frozen_dates_and_checkpoint_formulas() -> None:
    dates = qd.target_dates()
    assert len(dates) == 40 and dates[0] == "2026-08-18" and dates[-1] == "2026-09-26"
    assert len(set(dates)) == 40
    receive = qd.parse_utc("2026-09-03T11:09:14.805697Z")
    # Gamma open earlier than the v3 capture: the later (v3) time wins.
    assert qd.checkpoint_a(receive, qd.parse_utc("2026-09-03T11:09:13Z")) == CHECKPOINT
    # Gamma open later than the v3 capture: the later (Gamma) time wins.
    later = qd.parse_utc("2026-09-03T11:30:00Z")
    assert qd.checkpoint_a(receive, later) == later + timedelta(minutes=60)
    # Untrustworthy Gamma open times are ignored.
    assert qd.gamma_open_time_if_trustworthy("not a time", receive) is None
    assert qd.gamma_open_time_if_trustworthy("2026-09-01T00:00:00Z", receive) is None
    assert qd.gamma_open_time_if_trustworthy(None, receive) is None
    assert qd.checkpoint_a(receive, None) == receive + timedelta(minutes=60)
    # Checkpoint B: LST midnight (EST, UTC-5) of the target date; eligible only if open 60 min before.
    b_time, eligible = qd.checkpoint_b(date(2026, 9, 3), -300, receive)
    assert b_time == datetime(2026, 9, 3, 5, tzinfo=timezone.utc) and eligible is False
    b_time, eligible = qd.checkpoint_b(date(2026, 9, 4), -300, receive)
    assert b_time == datetime(2026, 9, 4, 5, tzinfo=timezone.utc) and eligible is True
    _t, eligible = qd.checkpoint_b(date(2026, 9, 3), -300, datetime(2026, 9, 3, 4, 0, 1, tzinfo=timezone.utc))
    assert eligible is False  # 59m59s is not >= 60 minutes
    _t, eligible = qd.checkpoint_b(date(2026, 9, 3), -300, datetime(2026, 9, 3, 4, 0, tzinfo=timezone.utc))
    assert eligible is True
    assert qd.parse_rain_slug("where-will-it-rain-on-september-3-2026-new-york-ny") == (date(2026, 9, 3), "new-york-ny")
    for slug in ("where-will-it-rain-on-septembr-3-2026-nyc", "will-it-snow-on-september-3-2026-nyc", "where-will-it-rain-on-february-30-2026-x", None):
        assert qd.parse_rain_slug(slug) is None


def test_lookback_windows_frozen() -> None:
    assert qd.MARKET_HISTORY_LOOKBACK == timedelta(hours=24)
    assert qd.NDFD_VINTAGE_LOOKBACK == timedelta(hours=48)
    qd.assert_frozen_windows(timedelta(hours=24), timedelta(hours=48))
    for market_history, ndfd_lookback in ((timedelta(hours=25), timedelta(hours=48)), (timedelta(hours=24), timedelta(hours=72)),
                                          (timedelta(hours=12), timedelta(hours=48))):
        with pytest.raises(qd.ReadinessError) as excinfo:
            qd.assert_frozen_windows(market_history, ndfd_lookback)
        assert excinfo.value.code == "READINESS_WINDOW_INVALID"
    events = [event("best_bid_ask", "2026-09-02T12:00:00.000000Z", best_bid="0.4", best_ask="0.5", spread="0.1", hour="2026-09-02/12")]
    with pytest.raises(qd.ReadinessError):
        qd.select_latest_market_event(events, family="best_bid_ask", asset_id=YES, checkpoint=CHECKPOINT,
                                      lookback=timedelta(hours=48), scanned_hours=["2026-09-02/12"], hour_coverage={})
    # An event older than exactly 24 h is outside the window.
    with pytest.raises(qd.RuleExclusion) as excinfo:
        qd.select_latest_market_event(events, family="best_bid_ask", asset_id=YES, checkpoint=CHECKPOINT,
                                      lookback=qd.MARKET_HISTORY_LOOKBACK, scanned_hours=["2026-09-02/12"],
                                      hour_coverage={"2026-09-02/12": "FULL"})
    assert excinfo.value.code == "MARKET_HISTORY_NOT_OBSERVED_IN_LOOKBACK"
    vintage, _decoded, _station = weather_parts(public_time="2026-09-01T12:09:00Z")
    assert ndfd.select_vintage([vintage], CHECKPOINT, qd.NDFD_VINTAGE_LOOKBACK) is None  # 48h + 14s before


def test_feature_evidence_never_after_checkpoint() -> None:
    coverage = {"2026-09-03/11": "FULL", "2026-09-03/12": "FULL"}
    events = [
        event("best_bid_ask", "2026-09-03T11:40:00.000000Z", best_bid="0.30", best_ask="0.40", spread="0.10"),
        event("best_bid_ask", "2026-09-03T12:09:14.805697Z", "2026-09-03T12:09:00.000Z", best_bid="0.31", best_ask="0.39", spread="0.08"),
        # Received after the checkpoint although its venue timestamp is before it: never selected.
        event("best_bid_ask", "2026-09-03T12:09:14.805698Z", "2026-09-03T12:08:00.000Z", best_bid="0.99", best_ask="0.99", spread="0"),
        event("best_bid_ask", "2026-09-03T12:05:00.000000Z", asset=NO, best_bid="0.60", best_ask="0.70", spread="0.10"),
    ]
    latest = qd.select_latest_market_event(events, family="best_bid_ask", asset_id=YES, checkpoint=CHECKPOINT,
                                           lookback=qd.MARKET_HISTORY_LOOKBACK, scanned_hours=list(coverage), hour_coverage=coverage)
    assert latest.field("best_bid") == "0.31" and latest.timestamp_received == "2026-09-03T12:09:14.805697Z"
    future = events[2]
    with pytest.raises(qd.ReadinessError) as excinfo:
        qd.market_history_evidence(future, None, CHECKPOINT, coverage, coverage, list(coverage))
    assert excinfo.value.code == "READINESS_LOOK_AHEAD"
    # A later (possibly missing) hour that was not scanned or is inadmissible excludes the row.
    with pytest.raises(qd.RuleExclusion) as excinfo:
        qd.select_latest_market_event(events[:1], family="best_bid_ask", asset_id=YES, checkpoint=CHECKPOINT,
                                      lookback=qd.MARKET_HISTORY_LOOKBACK, scanned_hours=["2026-09-03/11"], hour_coverage=coverage)
    assert excinfo.value.code == "MARKET_HISTORY_NOT_OBSERVED_IN_LOOKBACK"
    with pytest.raises(qd.RuleExclusion) as excinfo:
        qd.select_latest_market_event(events[:1], family="best_bid_ask", asset_id=YES, checkpoint=CHECKPOINT,
                                      lookback=qd.MARKET_HISTORY_LOOKBACK, scanned_hours=list(coverage),
                                      hour_coverage={**coverage, "2026-09-03/12": "PARTIAL"})
    assert excinfo.value.code == "MARKET_HISTORY_COVERAGE_INADMISSIBLE"
    # Weather: a vintage public after the checkpoint is never used, even if its bulletin time is earlier.
    vintage, decoded, station = weather_parts(public_time="2026-09-03T12:09:15Z")
    with pytest.raises(qd.ReadinessError) as excinfo:
        qd.weather_evidence(vintage, "a" * 64, decoded, station, -300, date(2026, 9, 3), CHECKPOINT)
    assert excinfo.value.code == "READINESS_LOOK_AHEAD"
    good_vintage, decoded, station = weather_parts()
    weather = qd.weather_evidence(good_vintage, "a" * 64, decoded, station, -300, date(2026, 9, 3), CHECKPOINT)
    assert weather["public_available_time"] == "2026-09-03T10:51:56Z"
    assert weather["bulletin_time"] == "2026-09-03T10:46:00Z"
    assert weather["periods"][0]["reference_time"] == "2026-09-03T11:00:00Z"
    assert weather["periods"][0]["pop12_percent"] == 99
    assert weather["station"]["standard_utc_offset_minutes"] == -300
    assert "probability" not in json.dumps(weather).lower().replace("pop12", "")  # no combined model output
    missing = [(decoded[0][0], ndfd.DecodedPop12(decoded[0][1].header, (), (ndfd.StationValue("KNYC", 1, 40.7, -73.9, 1.0, None),)))]
    with pytest.raises(qd.RuleExclusion) as excinfo:
        qd.weather_evidence(good_vintage, "a" * 64, missing, station, -300, date(2026, 9, 3), CHECKPOINT)
    assert excinfo.value.code == "WEATHER_VALUE_MISSING"
    with pytest.raises(qd.RuleExclusion) as excinfo:
        qd.weather_evidence(good_vintage, "a" * 64, decoded, station, -300, date(2026, 9, 5), CHECKPOINT)
    assert excinfo.value.code == "WEATHER_NO_OVERLAPPING_PERIOD"


def test_labels_separated_and_require_agreement() -> None:
    gamma = qd.normalize_gamma_market(gamma_doc(), candidate())
    assert gamma.winning_outcome == "No" and gamma.closed_time == "2026-09-04T14:18:05.177609Z"
    resolved = [event("market_resolved", "2026-09-04T14:18:58.893393Z", winning_asset_id=NO, winning_outcome="No", assets_ids=f"{YES},{NO}"),
                event("market_resolved", "2026-09-04T14:23:30.922684Z", winning_asset_id=NO, winning_outcome="No", assets_ids=f"{YES},{NO}")]
    label = qd.resolve_label(gamma, resolved)
    assert (label.winning_outcome, label.winning_token_id, label.v3_resolution_received) == ("No", NO, "2026-09-04T14:18:58.893393Z")
    rule = qd.parse_rule(RULE_FIRST)
    mapping = label.to_mapping(rule)
    assert mapping["post_outcome_evidence"] is True and mapping["rule_cohort_id"] == rule.rule_cohort_id
    disagree = resolved + [event("market_resolved", "2026-09-04T14:30:00Z", winning_asset_id=YES, winning_outcome="Yes", assets_ids=f"{YES},{NO}")]
    for bad_events, bad_gamma, code in (
        (disagree, gamma, "LABEL_SOURCE_DISAGREEMENT"),
        ([event("market_resolved", "2026-09-04T14:18:58Z", winning_asset_id=YES, winning_outcome="Yes", assets_ids=f"{YES},{NO}")], gamma, "LABEL_SOURCE_DISAGREEMENT"),
        ([event("market_resolved", "2026-09-04T14:18:58Z", winning_asset_id=YES, winning_outcome="No", assets_ids=f"{YES},{NO}")], gamma, "LABEL_SOURCE_DISAGREEMENT"),
        ([], gamma, "LABEL_V3_RESOLUTION_MISSING"),
        (resolved, qd.normalize_gamma_market(gamma_doc(closed=False), candidate()), "LABEL_GAMMA_NOT_FINAL"),
        (resolved, qd.normalize_gamma_market(gamma_doc(outcomePrices=json.dumps(["0.5", "0.5"])), candidate()), "LABEL_GAMMA_NOT_FINAL"),
    ):
        with pytest.raises(qd.RuleExclusion) as excinfo:
            qd.resolve_label(bad_gamma, bad_events)
        assert excinfo.value.code == code
    # Post-outcome evidence never enters feature evidence: rows carry it only under label_evidence.
    row = _row()
    assert "label_evidence" in row and "winning_outcome" not in json.dumps(row["feature_evidence"])
    assert row["label_evidence"]["post_outcome_evidence"] is True
    bad_label = dict(mapping)
    bad_label["post_outcome_evidence"] = False
    with pytest.raises(qd.ReadinessError):
        _row(label=bad_label)


def test_gamma_v3_identity_mismatch_excludes() -> None:
    for patch in ({"id": "999"}, {"conditionId": "0x" + "11" * 32}, {"slug": "other"},
                  {"clobTokenIds": json.dumps([NO, YES])}, {"outcomes": json.dumps(["Up", "Down"])},
                  {"clobTokenIds": "not-json"}):
        with pytest.raises(qd.RuleExclusion) as excinfo:
            qd.normalize_gamma_market(gamma_doc(**patch), candidate())
        assert excinfo.value.code == "GAMMA_V3_IDENTITY_MISMATCH"
    with pytest.raises(qd.RuleExclusion) as excinfo:
        qd.normalize_gamma_market(["not", "a", "market"], candidate())
    assert excinfo.value.code == "GAMMA_UNAVAILABLE"
    new_market = [event("new_market", "2026-09-03T11:09:14.805697Z", assets_ids=f"{YES},{NO}", outcomes="Yes\u001fNo",
                        question="q", slug="where-will-it-rain-on-september-3-2026-new-york-ny"),
                  event("new_market", "2026-09-03T11:09:16.414571Z", assets_ids=f"{NO},{YES}", outcomes="Yes\u001fNo",
                        question="q", slug="where-will-it-rain-on-september-3-2026-new-york-ny")]
    candidates, inconsistent = qd.candidates_from_new_market(new_market)
    assert candidates == () and inconsistent == ({"market_id": "3719310", "reason": "V3_MARKET_IDENTITY_INCONSISTENT"},)
    candidates, inconsistent = qd.candidates_from_new_market([new_market[0], new_market[0]])
    assert len(candidates) == 1 and candidates[0].first_received == "2026-09-03T11:09:14.805697Z" and inconsistent == ()


def test_rule_cohort_parsing_deterministic() -> None:
    first = qd.parse_rule(RULE_FIRST)
    assert first == qd.parse_rule(RULE_FIRST)
    assert (first.station_id, first.threshold_inches, first.trace_qualifies, first.finality_policy) == ("KNYC", "0.01", False, "FIRST_PUBLISHED_FINAL")
    assert first.rule_cohort_id.startswith(qd.RULE_COHORT_PREFIX)
    # Station and date are per-market bindings: another city with identical semantics shares the cohort.
    other_city = qd.parse_rule(RULE_FIRST.replace("KNYC", "KMIA").replace("New York, NY", "Miami, FL"))
    assert other_city.rule_cohort_id == first.rule_cohort_id and other_city.station_id == "KMIA"
    assert other_city.rule_text_sha256 != first.rule_text_sha256
    assert qd.parse_rule(RULE_LATEST).finality_policy == "LATEST_BEFORE_2359_ET"
    assert qd.parse_rule(RULE_LAST_1400).finality_policy == "LAST_BEFORE_1400_ET"
    assert len({qd.parse_rule(r).rule_cohort_id for r in (RULE_FIRST, RULE_LATEST, RULE_LAST_1400)}) == 3
    ambiguous = RULE_FIRST + " Resolution is based on the last published precipitation figure available before 2:00 PM ET."
    cases = {
        ambiguous: "RULE_SEMANTICS_UNSUPPORTED",
        RULE_FIRST.replace("first published", "average published").replace("will not be considered", "may be considered"): "RULE_SEMANTICS_UNSUPPORTED",
        RULE_FIRST.replace('A report of trace ("T") does not qualify.', ""): "RULE_SEMANTICS_UNSUPPORTED",
        RULE_FIRST.replace("KNYC", "the station"): "RULE_STATION_MISSING",
        RULE_FIRST.replace("(CLI) for KNYC.", "(CLI) for KLGA."): "RULE_STATION_AMBIGUOUS",
        RULE_FIRST.replace("0.01 inches or more", "0.1 inches or more"): "RULE_THRESHOLD_MISSING",
        RULE_FIRST.replace("midnight to midnight local standard time", "midnight to midnight local time"): "RULE_CLIMATE_DAY_MISSING",
        "": "RULE_STATION_MISSING",
    }
    for text, code in cases.items():
        with pytest.raises(qd.RuleExclusion) as excinfo:
            qd.parse_rule(text)
        assert excinfo.value.code == code


OBSERVED_BASE = RULE_FIRST.split("Resolution is based on")[0]
OBSERVED_LAST_1400 = OBSERVED_BASE + (
    "This market will resolve according to the NWS Daily Climate Report as published by 2:00 PM ET on the day following the "
    "observation date. If multiple versions of the report are issued, the last version published before that time governs. "
    'If no figure has been published by that time, this market will resolve to "No".\n\n'
    "The resolution source for this market is the NWS Daily Climate Report (CLI) for KNYC, published at "
    "https://forecast.weather.gov/product.php?site=NWS&product=CLI&issuedby=NYC.")
OBSERVED_LATEST_2359 = OBSERVED_BASE + (
    "Resolution is based on the most recent CLI report published for the observation date. If multiple versions of the report "
    "are issued, the last version published before 11:59 PM ET on the day following the observation date governs. If no figure "
    'has been published by that time, this market will resolve to "No".\n\n'
    "The resolution source for this market is the NWS Daily Climate Report (CLI) for KNYC.")


def test_rule_parser_accepts_observed_frozen_policy_word_orders() -> None:
    """S10-QUAL-DATA-01-D008: the real Gamma word orders map to the already-frozen labels only."""
    last = qd.parse_rule(OBSERVED_LAST_1400)
    latest = qd.parse_rule(OBSERVED_LATEST_2359)
    assert last.finality_policy == "LAST_BEFORE_1400_ET" and latest.finality_policy == "LATEST_BEFORE_2359_ET"
    assert last.rule_cohort_id == qd.parse_rule(RULE_LAST_1400).rule_cohort_id  # same normalized semantics
    assert latest.rule_cohort_id == qd.parse_rule(RULE_LATEST).rule_cohort_id
    assert {last.station_id, latest.station_id} == {"KNYC"} and last.threshold_inches == latest.threshold_inches == "0.01"
    assert set(qd.FINALITY_POLICIES) == {"FIRST_PUBLISHED_FINAL", "LATEST_BEFORE_2359_ET", "LAST_BEFORE_1400_ET"}
    near_misses = {
        # 2 PM cutoff but the FIRST version governs: not the frozen "last version" semantics.
        "first_version": OBSERVED_LAST_1400.replace("the last version published before that time governs",
                                                    "the first version published before that time governs"),
        # Cutoff without the governing-version sentence is not explicit enough.
        "no_governing_sentence": OBSERVED_LAST_1400.replace(
            "If multiple versions of the report are issued, the last version published before that time governs. ", ""),
        # Different cutoff hour.
        "wrong_hour": OBSERVED_LAST_1400.replace("2:00 PM ET", "5:00 PM ET"),
        # Most recent report but a different cutoff.
        "latest_wrong_cutoff": OBSERVED_LATEST_2359.replace("11:59 PM ET", "9:00 AM ET"),
        # Both frozen policies stated at once: ambiguous, never guessed.
        "both_policies": OBSERVED_LAST_1400 + " Resolution is based on the most recent CLI report published for the observation "
                         "date. If multiple versions of the report are issued, the last version published before 11:59 PM ET "
                         "on the day following the observation date governs.",
    }
    for name, text in near_misses.items():
        with pytest.raises(qd.RuleExclusion) as excinfo:
            qd.parse_rule(text)
        assert excinfo.value.code == "RULE_SEMANTICS_UNSUPPORTED", name
    # Station, threshold and climate-day requirements are not loosened by the new wordings.
    for text, code in ((OBSERVED_LAST_1400.replace("KNYC", "the station"), "RULE_STATION_MISSING"),
                       (OBSERVED_LATEST_2359.replace("0.01 inches or more", "0.05 inches or more"), "RULE_THRESHOLD_MISSING"),
                       (OBSERVED_LAST_1400.replace("local standard time", "local time"), "RULE_CLIMATE_DAY_MISSING")):
        with pytest.raises(qd.RuleExclusion) as excinfo:
            qd.parse_rule(text)
        assert excinfo.value.code == code


def test_pendulumflow_never_canonical_pit() -> None:
    history = qd.market_history_evidence(
        event("best_bid_ask", "2026-09-03T12:00:00Z", best_bid="0.3", best_ask="0.4", spread="0.1"), None, CHECKPOINT,
        {"2026-09-03/12": "FULL"}, {}, ["2026-09-03/12"])
    assert history["source_class"] == "THIRD_PARTY_NATIVE_FRAME_ARCHIVE"
    assert history["source_authority"] == "EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION"
    assert qd.SOURCE_AUTHORITY["market_history"] == "EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION"
    for laundered in ("SOURCE_KIND_CANONICAL_PIT", "MARKET_PIT", "CANONICAL_PIT", "NATIVE_OFFICIAL_CAPTURE"):
        bad = dict(history)
        bad["source_authority"] = laundered
        with pytest.raises(qd.ReadinessError) as excinfo:
            _row(market_history=bad)
        assert excinfo.value.code == "READINESS_AUTHORITY_LAUNDERING"
    bundle = _bundle()
    laundered_bundle = copy.deepcopy(bundle)
    laundered_bundle["rows"][0]["source_authority"]["market_history"] = "SOURCE_KIND_CANONICAL_PIT"
    with pytest.raises(qd.ReadinessError):
        qd.verify_bundle(laundered_bundle)
    source = MODULE.read_text(encoding="utf-8")
    assert "DatasetSnapshotReference(" not in source and "build_dataset_snapshot_reference" not in source


def _artifact(sha: str, dq: tuple[str, ...] = ("OK",), fidelity: str = "EXACT") -> qd.RetainedArtifact:
    return qd.RetainedArtifact("pendulumflow-v3", "archive.pendulumflow.com/v3/2026-09-03/12/manifest.json", "HTTP_GET", (),
                               sha * 64, 100, "application/json", None, None, None, dq, fidelity)


def _manifests(dq=("OK",), fidelity="EXACT"):
    references = [qd.raw_reference(_artifact(c, dq, fidelity)) for c in "ab"]
    return qd.build_shard_manifests(target_date="2026-09-03", shard_kind="PENDULUMFLOW_MARKET_HISTORY",
                                    references=references, output_records=[{"market_id": "3719310"}],
                                    information_cutoff=CHECKPOINT, repo_code_identity="c" * 40,
                                    dataset_refs=["externaldataset:sha256:" + "d" * 64])


def _row(market_history=None, label=None, manifest_ids=None) -> dict[str, object]:
    vintage, decoded, station = weather_parts()
    weather = qd.weather_evidence(vintage, "a" * 64, decoded, station, -300, date(2026, 9, 3), CHECKPOINT)
    history = market_history or qd.market_history_evidence(
        event("best_bid_ask", "2026-09-03T12:00:00Z", best_bid="0.3", best_ask="0.4", spread="0.1"), None, CHECKPOINT,
        {"2026-09-03/12": "FULL"}, {}, ["2026-09-03/12"])
    gamma = qd.normalize_gamma_market(gamma_doc(), candidate())
    rule = qd.parse_rule(RULE_FIRST)
    label_map = label or qd.LabelEvidence("No", NO, "2026-09-04T14:18:58.893393Z", gamma.closed_time).to_mapping(rule)
    ids = manifest_ids if manifest_ids is not None else [m.research_provenance_manifest_id for m in _manifests()]
    return qd.build_row(candidate=candidate(), target_day=date(2026, 9, 3), checkpoint_id=qd.CHECKPOINT_A,
                        checkpoint_time=CHECKPOINT, yes_token_id=YES, market_history=history, weather=weather,
                        label=label_map, manifest_ids=ids)


def _counts(rows):
    return qd.derive_counts(3, rows, [qd.exclusion("2", "GAMMA_UNAVAILABLE", target_date="2026-09-03")],
                            [qd.exclusion("3719310", "CHECKPOINT_B_MARKET_NOT_OPEN_60M", qd.CHECKPOINT_B, "2026-09-03")],
                            {"2026-09-03/12": "FULL", "2026-08-18/06": "PARTIAL"}, ["wmo/pop12/2026/09/03/YDUZ98_KWBN_202609031046"])


def _execution():
    gamma = qd.normalize_gamma_market(gamma_doc(), candidate())
    return {"3719310": qd.execution_facts(gamma, qd.parse_rule(RULE_FIRST), [], [])}


def _bundle(rows=None, source_facts=None, reason="EVIDENCE_COMPLETE_ROWS_PRESENT"):
    rows = [_row()] if rows is None else rows
    ready = [m.research_provenance_manifest_id for m in _manifests()]
    return qd.build_bundle(rows=rows, market_exclusions=[qd.exclusion("2", "GAMMA_UNAVAILABLE", target_date="2026-09-03")],
                           row_exclusions=[qd.exclusion("3719310", "CHECKPOINT_B_MARKET_NOT_OPEN_60M", qd.CHECKPOINT_B, "2026-09-03")],
                           counts=_counts(rows), execution_evidence=_execution(), ready_manifest_ids=ready,
                           diagnostic_manifest_ids=[], external_dataset_ids=["externaldataset:sha256:" + "d" * 64],
                           source_facts=source_facts or {"note": "x"}, terminal_reason=reason)


def test_dataset_identity_path_time_independent_and_mutation_sensitive() -> None:
    first = _bundle()
    second = _bundle()
    assert first == second
    assert first["logical_dataset_id"].startswith(qd.DATASET_ID_PREFIX) and first["bundle_id"].startswith(qd.BUNDLE_ID_PREFIX)
    qd.verify_bundle(first)
    serialized = json.dumps(first)
    for forbidden in ("C:\\", "/Users/", "/home/", "local_data", "latency", "completed_at"):
        assert forbidden not in serialized
    # Key order in inputs does not matter; every committed mutation changes the ids.
    reordered = json.loads(json.dumps(first, sort_keys=False))
    qd.verify_bundle(dict(reversed(list(reordered.items()))))
    for path in (("rows", 0, "checkpoint_time"), ("dataset", "b0_contract_compatibility"), ("dataset", "counts", "included_markets"),
                 ("rows", 0, "feature_evidence", "market_history", "best_bid_ask", "best_bid"), ("terminal",)):
        mutated = copy.deepcopy(first)
        target = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = "MUTATED" if isinstance(target[path[-1]], str) else 999
        with pytest.raises(qd.ReadinessError):
            qd.verify_bundle(mutated)
    # The logical dataset id commits the row set; bundle-only source facts change only the bundle id.
    other_facts = _bundle(source_facts={"note": "y"})
    assert other_facts["logical_dataset_id"] == first["logical_dataset_id"] and other_facts["bundle_id"] != first["bundle_id"]
    # Row ids are content-addressed and order-insensitive at the bundle level (deterministic order).
    row_a = _row()
    assert row_a["row_id"] == _row()["row_id"]
    assert qd.content_id("x:", {"a": 1, "b": [1, 2]}) == qd.content_id("x:", {"b": [1, 2], "a": 1})
    assert qd.content_id("x:", {"a": 1, "b": [1, 2]}) != qd.content_id("x:", {"a": 1, "b": [2, 1]})
    with pytest.raises(qd.ReadinessError):
        qd.canonical_json_bytes({"float": 0.1})


def test_ready_manifest_subset_dq_ok_only() -> None:
    ready = _manifests()
    assert ready and all(qd.is_ready_manifest(m) for m in ready)
    assert all(m.dq_flags == ("OK",) and m.replay_fidelity in ("EXACT", "FAITHFUL") and m.gap_summary == "" for m in ready)
    qd.require_ready_manifests(ready)
    degraded = _manifests(("PARTIALLY_OBSERVED",), "PARTIAL")
    assert degraded and not any(qd.is_ready_manifest(m) for m in degraded)
    assert degraded[0].gap_summary != ""
    with pytest.raises(qd.ReadinessError) as excinfo:
        qd.require_ready_manifests(degraded)
    assert excinfo.value.code == "READINESS_MANIFEST_NOT_READY"
    ok, diagnostic = qd.split_ready_manifests(list(ready) + list(degraded))
    assert ok == tuple(ready) and diagnostic == tuple(degraded)
    # A row pointing at a non-ready manifest cannot be sealed into the bundle.
    row = _row(manifest_ids=[degraded[0].research_provenance_manifest_id])
    with pytest.raises(qd.ReadinessError) as excinfo:
        _bundle(rows=[row])
    assert excinfo.value.code == "READINESS_MANIFEST_NOT_READY"
    # <=256 items per manifest by deterministic sub-sharding.
    many = [qd.raw_reference(qd.RetainedArtifact("s", "e", "HTTP_GET", (), f"{i:064x}", 1, "m", None, None, None, ("OK",), "EXACT"))
            for i in range(600)]
    shards = qd.build_shard_manifests(target_date="2026-09-03", shard_kind="NOAA_NDFD_WEATHER", references=many, output_records=[],
                                      information_cutoff=CHECKPOINT, repo_code_identity="c" * 40, dataset_refs=[])
    assert [len(s.input_evidence_reference_ids) for s in shards] == [256, 256, 88]
    assert shards == qd.build_shard_manifests(target_date="2026-09-03", shard_kind="NOAA_NDFD_WEATHER", references=list(reversed(many)),
                                              output_records=[], information_cutoff=CHECKPOINT, repo_code_identity="c" * 40, dataset_refs=[])
    with pytest.raises(qd.ReadinessError):
        qd.build_shard_manifests(target_date="2026-09-03", shard_kind="CANONICAL_PIT", references=many, output_records=[],
                                 information_cutoff=CHECKPOINT, repo_code_identity="c" * 40, dataset_refs=[])


def test_counts_factual_no_power_thresholds() -> None:
    rows = [_row()]
    counts = _counts(rows)
    assert counts["discovered_candidates"] == 3 and counts["included_markets"] == 2 and counts["excluded_markets"] == 1
    assert counts["checkpoint_usable_rows"] == {qd.CHECKPOINT_A: 1, qd.CHECKPOINT_B: 0}
    assert counts["independent_target_dates"] == {qd.CHECKPOINT_A: 1, qd.CHECKPOINT_B: 0, "ANY_CHECKPOINT": 1}
    assert counts["pendulumflow_hours_by_coverage_class"]["PARTIAL"] == 1
    assert counts["market_history_rows_available"] == 1
    qd.verify_counts(counts, _counts(rows))
    fabricated = dict(counts)
    fabricated["checkpoint_usable_rows"] = {qd.CHECKPOINT_A: 50, qd.CHECKPOINT_B: 0}
    with pytest.raises(qd.ReadinessError) as excinfo:
        qd.verify_counts(fabricated, _counts(rows))
    assert excinfo.value.code == "READINESS_COUNTS_FABRICATED"
    with pytest.raises(qd.ReadinessError):
        qd.verify_counts({**counts, "required_samples": 100}, {**counts, "required_samples": 100})
    for forbidden in ("required_samples", "min_samples_per_role", "target_power", "\"mde\"", "significance", "brier", "log_loss"):
        assert forbidden not in json.dumps(counts).lower()
        assert forbidden not in json.dumps(_bundle()["dataset"]).lower()
    # A READY terminal needs at least one evidence-complete row; an empty corpus is INSUFFICIENT.
    with pytest.raises(qd.ReadinessError):
        _bundle(rows=[])
    empty = qd.build_bundle(rows=[], market_exclusions=[], row_exclusions=[], counts=qd.derive_counts(0, [], [], [], {}, []),
                            execution_evidence={}, ready_manifest_ids=[], diagnostic_manifest_ids=[], external_dataset_ids=[],
                            source_facts={}, terminal_reason="NO_EVIDENCE_COMPLETE_ROW")
    assert empty["terminal"] == "QUAL_DATA_INSUFFICIENT"
    with pytest.raises(qd.ReadinessError):
        _bundle(reason="NO_EVIDENCE_COMPLETE_ROW")
    assert _bundle(reason="FROZEN_BUDGET_EXHAUSTED")["terminal"] == "QUAL_DATA_INSUFFICIENT"


def test_execution_evidence_factual_states() -> None:
    gamma = qd.normalize_gamma_market(gamma_doc(), candidate())
    rule = qd.parse_rule(RULE_FIRST)
    none_observed = qd.execution_facts(gamma, rule, [], [])
    assert none_observed["FEES"]["state"] == "CURRENT_ONLY"  # never backdated from current metadata
    assert none_observed["RESOLUTION_RULES"]["state"] == "CURRENT_ONLY"
    assert none_observed["TICK_SIZE_MIN_ORDER"]["state"] == "CURRENT_ONLY"
    trade = event("last_trade_price", "2026-09-03T11:50:00Z", price="0.4", side="BUY", size="5", fee_rate_bps="1000")
    tick = event("tick_size_change", "2026-09-03T11:20:00Z", old_tick_size="0.01", new_tick_size="0.001")
    observed = qd.execution_facts(gamma, rule, [trade], [tick])
    assert observed["FEES"]["state"] == "HISTORICALLY_EVIDENCED" and observed["FEES"]["v3_fee_rate_bps_observed"] == ["1000"]
    assert observed["TICK_SIZE_MIN_ORDER"]["tick_size_state"] == "HISTORICALLY_EVIDENCED"
    assert observed["TICK_SIZE_MIN_ORDER"]["min_order_state"] == "CURRENT_ONLY"
    assert observed["TICK_SIZE_MIN_ORDER"]["state"] == "CURRENT_ONLY"  # weakest component, no forced AVAILABLE
    fees_off = qd.normalize_gamma_market(gamma_doc(feesEnabled=False), candidate())
    assert qd.execution_facts(fees_off, rule, [trade], [])["FEES"]["state"] == "SOURCE_DISAGREEMENT"
    bare = qd.normalize_gamma_market(gamma_doc(feesEnabled=None, orderMinSize=None, orderPriceMinTickSize=None), candidate())
    missing = qd.execution_facts(bare, None, [], [])
    assert {c: missing[c]["state"] for c in qd.EXECUTION_CLASSES} == {c: "MISSING" for c in qd.EXECUTION_CLASSES}
    for facts in (none_observed, observed, missing):
        for cls in qd.EXECUTION_CLASSES:
            assert facts[cls]["state"] in qd.EXECUTION_STATES
            assert facts[cls]["state"] != "AVAILABLE"


def test_b0_compatibility_external_only() -> None:
    assert qd.derive_b0_compatibility() == "EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION"
    with pytest.raises(qd.ReadinessError) as excinfo:
        qd.derive_b0_compatibility(["pitsnapshot:sha256:" + "0" * 64])
    assert excinfo.value.code == "READINESS_B0_CANONICAL_BINDING_UNSUPPORTED"
    bundle = _bundle()
    assert bundle["dataset"]["b0_contract_compatibility"] == "EXTERNAL_ONLY_REQUIRES_SEPARATE_COMPATIBILITY_DECISION"
    assert bundle["dataset"]["b0_source_authority"] == "EXTERNAL_THIRD_PARTY_PIT_RECONSTRUCTION"
    assert bundle["market_history_rows_available"] == 1
    forged = copy.deepcopy(bundle)
    forged["dataset"]["b0_contract_compatibility"] = "CANONICAL_PIT_AVAILABLE"
    with pytest.raises(qd.ReadinessError):
        qd.verify_bundle(forged)


def test_no_qualification_candidate_gate_or_trading_path() -> None:
    forbidden_modules = ("qualification", "qualification_gate", "experiment_os", "experiment_registry", "paper", "execution",
                         "live", "gateway", "hermes", "wallet", "order")
    for path in (MODULE, OPERATOR, ROOT / "src" / "data_layer" / "analytical_research" / "pendulumflow_v3.py",
                 ROOT / "src" / "data_layer" / "analytical_research" / "nws_ndfd_history.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        for name in imported:
            leaf_parts = name.split(".")
            assert not any(part in forbidden_modules for part in leaf_parts), (path.name, name)
        text = path.read_text(encoding="utf-8")
        for call in ("build_qualification_candidate", "evaluate_qualification_gate", "QualificationCandidate(", "place_order",
                     "submit_order", "cancel_order", "private_key", "api_key"):
            assert call not in text, (path.name, call)
    flags = _bundle()["dataset"]["no_authority_flags"]
    assert flags["no_qualification_candidate"] is True and flags["no_qualification_gate_run"] is True
    assert flags["no_live_authority"] is True and flags["no_execution_authority"] is True and flags["no_paper_authority"] is True


# ── S10-QUAL-DATA-02 (D011) additive label vocabulary ─────────────────────────

DATA_01_MARKET_EXCLUSION_REASONS = (
    "SLUG_NOT_DAILY_RAIN_FAMILY", "TARGET_DATE_OUTSIDE_CORPUS", "V3_MARKET_IDENTITY_INCONSISTENT", "GAMMA_UNAVAILABLE",
    "GAMMA_V3_IDENTITY_MISMATCH", "RULE_STATION_MISSING", "RULE_STATION_AMBIGUOUS", "RULE_THRESHOLD_MISSING",
    "RULE_CLIMATE_DAY_MISSING", "RULE_SEMANTICS_UNSUPPORTED", "STATION_METADATA_UNAVAILABLE", "STATION_METADATA_INVALID",
    "STATION_OFFSET_UNDERIVABLE", "LABEL_GAMMA_NOT_FINAL", "LABEL_V3_RESOLUTION_MISSING", "LABEL_SOURCE_DISAGREEMENT",
    "BUDGET_EXHAUSTED_BEFORE_EVALUATION",
)


def test_label_source_read_failed_vocabulary_additive() -> None:
    # Exactly one market-level code is added; every S10-QUAL-DATA-01 code survives in order.
    assert tuple(r for r in qd.MARKET_EXCLUSION_REASONS if r != "LABEL_V3_SOURCE_READ_FAILED") == DATA_01_MARKET_EXCLUSION_REASONS
    assert set(qd.MARKET_EXCLUSION_REASONS) - set(DATA_01_MARKET_EXCLUSION_REASONS) == {"LABEL_V3_SOURCE_READ_FAILED"}
    assert "LABEL_V3_SOURCE_READ_FAILED" not in qd.ROW_EXCLUSION_REASONS
    assert qd.RuleExclusion("LABEL_V3_SOURCE_READ_FAILED").code == "LABEL_V3_SOURCE_READ_FAILED"  # never coerced
    assert qd.exclusion("1", "LABEL_V3_SOURCE_READ_FAILED", target_date="2026-09-03")["reason"] == "LABEL_V3_SOURCE_READ_FAILED"
    with pytest.raises(qd.ReadinessError):
        qd.exclusion("1", "LABEL_V3_SOURCE_READ_FAILED", qd.CHECKPOINT_A, "2026-09-03")  # market-level only
    # resolve_label itself is unchanged: an empty (successfully read) window stays RESOLUTION_MISSING.
    with pytest.raises(qd.RuleExclusion) as excinfo:
        qd.resolve_label(qd.normalize_gamma_market(gamma_doc(), candidate()), [])
    assert excinfo.value.code == "LABEL_V3_RESOLUTION_MISSING"
    counts = qd.derive_counts(3, [], [qd.exclusion("1", "LABEL_V3_SOURCE_READ_FAILED"), qd.exclusion("2", "LABEL_V3_RESOLUTION_MISSING")],
                              [], {}, [])
    assert counts["market_exclusion_reasons"] == {"LABEL_V3_RESOLUTION_MISSING": 1, "LABEL_V3_SOURCE_READ_FAILED": 1}
