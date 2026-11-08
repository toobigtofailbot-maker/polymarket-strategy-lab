"""Verified S10-R3-REL-01 evidence -> genuine vendored Oracle3 ``check_constraint`` (S10-R3-ORACLE-UPSTREAM-01).

SELECTIVE_UPSTREAM_CODE_REUSE: ``oracle3/{__init__,arbitrage,fees}.py`` plus LICENSE/NOTICE are
byte-identical copies of YichengYang-Ethan/oracle3-prediction-market-agent@267fb7c (Apache-2.0
with MIT ancestry; see ``oracle3/NOTICE``). Upstream ``arbitrage.py`` imports ``oracle3.fees``
absolutely, so ``load_upstream`` registers exactly three module names from the pinned,
blob-verified bytes (no ``sys.path`` change, no import hook, no filesystem submodule search).

The upstream math is a STATIC, float, top-of-book comparison. Native REL-01 (exact Decimal,
depth sweep, decision-time fee provenance) stays the only economic authority; this module only
reports where the two agree or differ. Every case is conditional on a caller-declared relation;
nothing here is tradable, an executable edge, a profit claim or an order intent. Unknown,
default, expired or category fees abstain; the upstream ``default_schedule`` is never reached
because every ``Quote`` carries an explicit schedule.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec
import os
from pathlib import Path
import stat
import sys

from src.execution_feasibility import public_market as PM

UPSTREAM_REPOSITORY = "YichengYang-Ethan/oracle3-prediction-market-agent"
UPSTREAM_COMMIT = "267fb7c48dae7c4ff8922c02a3a223443e51bf0b"
UPSTREAM_VERSION = "1.2.2"
# Git blob SHA-1 of each vendored file (sha1(b"blob <len>\0" + bytes)), from the upstream tree at UPSTREAM_COMMIT.
VENDOR_PINS = {
    "__init__.py": "7975dfeb618a1b84f4351adea496aef9aa9b843b",
    "arbitrage.py": "4805d572b55ce6547c9c46ab92a2aa4ce90de808",
    "fees.py": "24624f84d40a43610302f7b8c3d17c347fa62e0c",
    "LICENSE": "0a1f3263b67e7fbc96d62f30563f2ef61bb57661",
    "NOTICE": "39dd4d41d44d48f6f62163578909c407cd08a78d",
}
MODULE_FILES = (("oracle3", "__init__.py"), ("oracle3.fees", "fees.py"), ("oracle3.arbitrage", "arbitrage.py"))
RELATIONS = {"IMPLICATION": "implication", "EXCLUSIVITY": "exclusivity", "COMPLEMENT": "complement",
             "SAME_EVENT": "same_event", "EVENT_SUM": "event_sum"}
# Only native rule-hash-bound, fresh, primary markets with no formal resolver; every other class abstains.
ADMITTED_REAL_WORLD = ("INCONCLUSIVE_RULE_SEMANTICS",)
VENUE = "polymarket"  # native REL-01 venue snapshots are Polymarket only; no cross-venue quote is ever built
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
PROGRAM_CAPABILITY_IDS = tuple(f"R3-{n:02d}" for n in range(1, 30)) + (
    "R3-01-SOURCE_ARCHIVE", "R3-03-FEES", "R3-05-CITATIONS", "R3-07-ROUTER", "R3-09-BOOK_GAPS", "R3-10-WANG",
    "R3-12-SAMPLER")
REUSED_CAPABILITIES = ("R3-03", "R3-03-FEES")
CONDITIONAL_ON = ["CALLER_DECLARED_FORMAL_RELATION", "CALLER_SUPPLIED_VENUE_BYTES_UNAUTHENTICATED",
                  "UPSTREAM_STATIC_TOP_OF_BOOK_FULL_FILL_ASSUMPTION", "SIMULTANEOUS_MULTI_LEG_FILL_UNPROVEN"]

_LOADED: dict = {}


class Oracle3Stop(Exception):
    """Fail-closed stop with a stable code (never echoes paths or upstream exception text)."""


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def vendor_dir() -> Path:
    return Path(__file__).resolve().parent / "oracle3"


def _unsafe(path: Path, *, directory: bool) -> bool:
    try:
        info = os.lstat(path)
    except OSError:
        return True
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    return not stat.S_ISDIR(info.st_mode) if directory else (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1)


def read_verified_vendor() -> dict:
    """All five vendored files, each a regular single-link file whose Git blob equals its pin."""
    root = vendor_dir()
    if _unsafe(root, directory=True):
        raise Oracle3Stop("UPSTREAM_VENDOR_DIR_UNSAFE")
    out = {}
    for name, pin in VENDOR_PINS.items():
        path = root / name
        if not os.path.lexists(path):
            raise Oracle3Stop("UPSTREAM_FILE_MISSING")
        if _unsafe(path, directory=False):
            raise Oracle3Stop("UPSTREAM_FILE_UNSAFE")
        data = path.read_bytes()
        if git_blob_sha1(data) != pin:
            raise Oracle3Stop("UPSTREAM_BLOB_MISMATCH")
        out[name] = data
    return out


def load_upstream() -> tuple:
    """(oracle3.fees, oracle3.arbitrage) executed from the verified bytes under their original names."""
    data = read_verified_vendor()
    names = [name for name, _ in MODULE_FILES]
    if all(name in _LOADED and sys.modules.get(name) is _LOADED[name] for name in names):
        return _LOADED["oracle3.fees"], _LOADED["oracle3.arbitrage"]
    for name in names:
        if name in sys.modules and sys.modules[name] is not _LOADED.get(name):
            raise Oracle3Stop("UPSTREAM_ALIAS_COLLISION")  # never overwrite a foreign module
    for name in names:
        sys.modules.pop(name, None)  # only our own stale entries reach here
    _LOADED.clear()
    root, registered = vendor_dir(), []
    try:
        for name, filename in MODULE_FILES:
            path = root / filename
            module = module_from_spec(ModuleSpec(name, None, origin=str(path), is_package=name == "oracle3"))
            module.__file__ = str(path)
            if name == "oracle3":
                module.__path__ = []  # a package with no search path: no other upstream file can be imported
            sys.modules[name] = module
            registered.append(name)
            # Execute exactly the verified bytes (no re-read, no bytecode cache write).
            exec(compile(data[filename], str(path), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
            if name != "oracle3":
                setattr(sys.modules["oracle3"], name.split(".")[1], module)
            _LOADED[name] = module
    except Exception:
        for name in registered:
            sys.modules.pop(name, None)
        _LOADED.clear()
        raise Oracle3Stop("UPSTREAM_IMPORT_FAILED") from None
    return _LOADED["oracle3.fees"], _LOADED["oracle3.arbitrage"]


def upstream_identity() -> dict:
    data = read_verified_vendor()
    return {"repository": UPSTREAM_REPOSITORY, "commit": UPSTREAM_COMMIT, "version": UPSTREAM_VERSION,
            "license": "Apache-2.0 (NOTICE: MIT ancestry ulab-uiuc/oracle3 and coinjure)",
            "git_blob_sha1": {name: git_blob_sha1(data[name]) for name in VENDOR_PINS},
            "sha256": {name: hashlib.sha256(data[name]).hexdigest() for name in VENDOR_PINS},
            "invoked": ["oracle3.arbitrage.Quote", "oracle3.arbitrage.check_constraint",
                        "oracle3.fees.PolymarketSchedule", "oracle3.fees.PolymarketSchedule.from_gamma_market"],
            "never_invoked": ["oracle3.fees.default_schedule", "oracle3.fees.PolymarketSchedule.for_category"]}


# ------------------------------------------------------------------ fee schedules (explicit only)


def _gamma_schedule(fees, raw: bytes):
    """Per-market schedule from frozen Gamma bytes, only when the body states its fee terms."""
    try:
        document = PM.decode_public_json(raw)
    except Exception:  # noqa: BLE001 - any undecodable body abstains
        return None, "FEE_SOURCE_UNREADABLE"
    if not isinstance(document, dict) or not (document.get("feesEnabled") is False or isinstance(document.get("feeSchedule"), dict)):
        # PolymarketSchedule.from_gamma_market would fall back to a conservative default here: never used.
        return None, "FEE_SCHEDULE_NOT_EXPLICIT_NO_DEFAULT"
    try:
        return fees.PolymarketSchedule.from_gamma_market(document), None
    except (fees.UnsupportedFeeSchedule, ValueError):
        return None, "FEE_SCHEDULE_UNSUPPORTED_BY_UPSTREAM"


def _schedules(fees, fee_policy: dict, policy: dict, leg_sources: dict, read) -> tuple:
    """market_id -> explicit upstream schedule, or (None, abstention reason)."""
    if fee_policy.get("status") != "WINDOW_VALID":
        return None, "FEE_" + str(fee_policy.get("status")).removeprefix("FEE_")
    if fee_policy.get("kind") == "TEST_ONLY_HYPOTHETICAL":
        if policy.get("test_exponent") != 1 or type(policy.get("test_exponent")) is not int:
            return None, "FEE_EXPONENT_UNSUPPORTED_BY_UPSTREAM"
        try:
            schedule = fees.PolymarketSchedule(rate=Decimal(policy["test_rate"]),
                                               source="TEST_ONLY_HYPOTHETICAL:" + policy["policy_id"])
        except (ArithmeticError, ValueError, TypeError):
            return None, "FEE_SCHEDULE_UNSUPPORTED_BY_UPSTREAM"
        return {market: schedule for market in leg_sources}, None
    if fee_policy.get("kind") != "GAMMA_BODY_PER_MARKET":
        return None, "FEE_CONFIG_UNKNOWN"
    out = {}
    for market, sources in leg_sources.items():
        found = set()
        for rel in sources:
            schedule, reason = _gamma_schedule(fees, read(rel))
            if reason:
                return None, reason
            found.add((schedule.rate, schedule.source))
            out[market] = schedule
        if len(found) != 1:
            return None, "FEE_SCHEDULE_CONFLICT"
    return out, None


# ------------------------------------------------------------------ per-model comparison


def _usable_sides(row: dict) -> dict:
    """(market_id, side) -> (best ask text, venue_snapshot_id) from native baskets whose every leg is COST_KNOWN."""
    sides = {}
    for basket in row["economics"]["baskets"]:
        legs = basket["legs"]
        if basket["status"] == "NOT_EXECUTABLE" or not legs or any(
                leg["status"] != "COST_KNOWN" or leg["best_ask"] is None for leg in legs):
            continue
        for leg in legs:
            sides[(leg["market_id"], leg["side"])] = (leg["best_ask"], leg["venue_snapshot_id"])
    return sides


def _abstention(row: dict, corpus_class: str) -> str | None:
    if row.get("status") != "EVALUATED":
        return "NATIVE_NOT_EVALUATED:" + str(row.get("status"))
    if not row.get("formal") or row["formal"]["status"] != "FORMAL_BOUNDED_PAYOFF_PROOF":
        return "NO_FORMAL_PROOF"
    if row["relation"] not in RELATIONS:
        return "RELATION_UNSUPPORTED"
    if corpus_class != "SANITIZED_SYNTHETIC":
        # LOCAL_REAL_PIT needs decision-time confirmed rules; native REL-01 never emits REAL_WORLD_RULE_VERIFIED.
        return "REAL_RULE_CONFIRMATION_ABSENT"
    if row["real_world"]["status"] not in ADMITTED_REAL_WORLD:
        return "RELATION_NOT_ADMISSIBLE:" + row["real_world"]["status"]
    return None


def _num(value: float) -> Decimal:
    return Decimal(repr(value))


def _compare(upstream_basket, native: dict) -> dict:
    native_fee = sum((Decimal(leg["fee_bound_usd"]) for leg in native["legs"]), Decimal(0))
    up = {"description": upstream_basket.description, "payoff_per_contract": repr(upstream_basket.payoff_per_contract),
          "contracts": repr(upstream_basket.contracts), "cost": repr(upstream_basket.cost), "fees": repr(upstream_basket.fees),
          "gross_edge": repr(upstream_basket.gross_edge), "net_edge": repr(upstream_basket.net_edge),
          "legs": [{"market_id": leg.market_id, "side": leg.side, "price": repr(leg.price), "fee": repr(leg.fee)}
                   for leg in upstream_basket.legs]}
    nat = {"status": native["status"], "certified_payout_usd": native["certified_payout_usd"],
           "top_of_book_cost_usd": native["top_of_book_cost_usd"], "fee_bound_usd": str(native_fee),
           "all_in_cost_usd": native["all_in_cost_usd"], "conditional_margin_usd": native["conditional_margin_usd"]}
    if native["conditional_margin_usd"] is None or native["top_of_book_cost_usd"] is None:
        return {"basket_id": native["basket_id"], "upstream": up, "native": nat, "delta": None,
                "edge_sign_agrees": None, "parity": "NATIVE_COST_UNKNOWN"}
    margin = Decimal(native["conditional_margin_usd"])
    delta = {"payout_usd": str(_num(upstream_basket.payoff_per_contract * upstream_basket.contracts) - Decimal(native["certified_payout_usd"])),
             "cost_usd": str(_num(upstream_basket.cost) - Decimal(native["top_of_book_cost_usd"])),
             "fees_usd": str(_num(upstream_basket.fees) - native_fee),
             "net_edge_usd": str(_num(upstream_basket.net_edge) - margin)}
    agrees = (_num(upstream_basket.net_edge) > 0) == (margin > 0)
    if not agrees:
        label = "SIGN_MISMATCH"
    elif all(Decimal(v) == 0 for v in delta.values()):
        label = "EXACT"
    else:
        label = "SIGN_AGREES_VALUE_DELTA"
    return {"basket_id": native["basket_id"], "upstream": up, "native": nat, "delta": delta, "edge_sign_agrees": agrees,
            "parity": label}


def assess_case(row: dict, *, corpus_class: str, fee_policy: dict, policy: dict, shares: str, venue_sources: dict,
                read, counter: list) -> dict:
    """One native REL-01 result row -> conditional upstream verdict (or an abstention)."""
    out = {"model_id": row.get("model_id"), "relation": row.get("relation"), "market_ids": list(row.get("market_ids") or []),
           "native_disposition": row.get("disposition"), "native_economic_status": row["economics"]["status"],
           "verdict": "ABSTAINED", "reason": None, "upstream": None, "parity": [], "tradable": False,
           "executable_edge": False, "profit_claim": False, "conditional_on": list(CONDITIONAL_ON)}
    reason = _abstention(row, corpus_class)
    sides = {} if reason else _usable_sides(row)
    if not reason and not sides:
        reason = "NO_USABLE_QUOTE_OR_DEPTH"
    if reason:
        return dict(out, reason=reason)
    fees, arbitrage = load_upstream()
    leg_sources: dict = {}
    for (market, _side), (_ask, snapshot_id) in sides.items():
        leg_sources.setdefault(market, set()).update(venue_sources.get(snapshot_id, ()))
    if any(not sources for sources in leg_sources.values()):
        return dict(out, reason="FEE_SOURCE_UNBOUND")
    schedules, reason = _schedules(fees, fee_policy, policy, {m: sorted(s) for m, s in leg_sources.items()}, read)
    if reason:
        return dict(out, reason=reason)
    if any(schedules.get(market) is None for market in row["market_ids"]):
        return dict(out, reason="FEE_SCHEDULE_MISSING_NO_DEFAULT")  # a None schedule would reach default_schedule
    try:
        quotes = []
        for market in row["market_ids"]:
            yes, no = sides.get((market, "YES")), sides.get((market, "NO"))
            quotes.append(arbitrage.Quote(market_id=market, venue=VENUE, schedule=schedules[market],
                                          yes_ask=None if yes is None else float(Decimal(yes[0])),
                                          no_ask=None if no is None else float(Decimal(no[0]))))
        counter.append(row["model_id"])
        check = arbitrage.check_constraint(RELATIONS[row["relation"]], quotes, contracts=float(Decimal(shares)), maker=False)
        payload = check.to_dict()
    except (ArithmeticError, ValueError, TypeError):
        return dict(out, verdict="UPSTREAM_REFUSED", reason="UPSTREAM_INPUT_REJECTED")
    natives = {tuple(b["sides"]): b for b in row["economics"]["baskets"]}
    parity = [_compare(b, natives[tuple(leg.side.upper() for leg in b.legs)]) for b in check.baskets]
    worst = "SIGN_MISMATCH" if any(p["parity"] == "SIGN_MISMATCH" for p in parity) else None
    return dict(out, verdict="UPSTREAM_CONDITIONAL_EVALUATED", reason=worst, parity=parity, upstream={
        "relation": payload["relation"], "constraint": payload["constraint"], "contracts": repr(check.contracts),
        "order_type": payload["order_type"], "violated": payload["violated"],
        "profitable_after_fees": payload["profitable_after_fees"], "missing_quotes": payload["missing_quotes"],
        "assessment": payload["assessment"], "assumptions": payload["assumptions"],
        "schedules": {m: schedules[m].describe() | {"taker_rate": str(schedules[m].rate)} for m in sorted(schedules)}})


def assess_rel_core(core: dict, request: dict, read) -> dict:
    """All native REL-01 result rows -> conditional upstream cases with full denominators."""
    venue_sources: dict = {}
    for outcome in core["venue"]["entries"]:
        if outcome["status"] == "BOUND" and outcome["venue_snapshot_id"]:
            venue_sources.setdefault(outcome["venue_snapshot_id"], set()).add(request["venue"][outcome["index"]]["gamma_file"])
    counter: list = []
    cases = [assess_case(row, corpus_class=core["corpus_class"], fee_policy=core["fee_policy"], policy=request["fee_policy"],
                         shares=request["basket_shares"], venue_sources=venue_sources, read=read, counter=counter)
             for row in core["results"]]
    parity = [p["parity"] for c in cases for p in c["parity"]]
    reasons: dict = {}
    for case in cases:
        if case["verdict"] == "ABSTAINED":
            reasons[case["reason"]] = reasons.get(case["reason"], 0) + 1
    return {"cases": cases, "check_constraint_invocations": len(counter), "counts": {
        "cases_total": len(cases),
        "upstream_evaluated": sum(1 for c in cases if c["verdict"] == "UPSTREAM_CONDITIONAL_EVALUATED"),
        "upstream_refused": sum(1 for c in cases if c["verdict"] == "UPSTREAM_REFUSED"),
        "abstained": sum(1 for c in cases if c["verdict"] == "ABSTAINED"),
        "abstention_reasons": dict(sorted(reasons.items())),
        "baskets_compared": len(parity),
        "parity_exact": parity.count("EXACT"), "parity_sign_agrees_value_delta": parity.count("SIGN_AGREES_VALUE_DELTA"),
        "parity_sign_mismatch": parity.count("SIGN_MISMATCH"), "parity_native_cost_unknown": parity.count("NATIVE_COST_UNKNOWN"),
        "upstream_violated": sum(1 for c in cases if c["upstream"] and c["upstream"]["violated"]),
        "upstream_profitable_after_fees_conditional": sum(1 for c in cases if c["upstream"] and c["upstream"]["profitable_after_fees"]),
        "real_world_verified": 0, "tradable": 0}}
