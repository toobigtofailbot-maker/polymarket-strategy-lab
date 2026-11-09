"""Verified native SRC-01 sources -> genuine vendored Metaculus source-archive code (S10-R3-METACULUS-SRC-01).

SELECTIVE_UPSTREAM_CODE_REUSE_OFFLINE: ``metaculus_source_archive/{canonicalize,models,quality}.py``
and ``LICENSE`` are byte-identical copies of Metaculus/forecasting-tools@a54dd64 (MIT). The
upstream modules import each other absolutely as
``forecasting_tools.agents_and_tools.source_archive.*``, so ``load_upstream`` registers exactly
six module names (three empty package stubs, three leaf modules executed from the pinned,
blob-verified bytes). The heavy upstream ``source_archive/__init__.py`` (cloud storage, browser
fetchers) is never vendored or loaded; no ``sys.path`` change, import hook or submodule search.

Native SRC-01 (2xx only, login walls, temporal admissibility, URL safety, per-market content
dedup, provenance) stays the only source authority. Upstream ``quality.evaluate`` and URL/content
hashes are a derived comparison: an upstream pass never makes a source ACCEPTED, and caller-local
bytes never become authenticated web evidence.
"""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
from importlib.machinery import ModuleSpec
from importlib.util import module_from_spec
import os
from pathlib import Path
import stat
import sys

from src.data_layer.analytical_research import source_grounding as SG
from src.data_layer.analytical_research.oracle3_upstream_bridge import PROGRAM_CAPABILITY_IDS  # noqa: F401 - re-exported (36 ids)

UPSTREAM_REPOSITORY = "Metaculus/forecasting-tools"
UPSTREAM_COMMIT = "a54dd6443d19745b267e99a3b0b7627e74b9a57a"
UPSTREAM_DIR = "forecasting_tools/agents_and_tools/source_archive"
# Git blob SHA-1 of each vendored file (sha1(b"blob <len>\0" + bytes)), from the upstream tree at UPSTREAM_COMMIT.
VENDOR_PINS = {
    "LICENSE": "95ca3360578732e0f3287fad707e029303427eec",
    "canonicalize.py": "7d722c69940f736b2921629de2eb8da191d3f920",
    "models.py": "08c63cd62764ae9f1b4dad7f1d40a8cd295ab2c1",
    "quality.py": "0bed34975731ae24c1a2e7222e29859ad08b5fb4",
}
PACKAGE = "forecasting_tools.agents_and_tools.source_archive"
PACKAGE_STUBS = ("forecasting_tools", "forecasting_tools.agents_and_tools", PACKAGE)
MODULE_FILES = ((PACKAGE + ".canonicalize", "canonicalize.py"), (PACKAGE + ".models", "models.py"),
                (PACKAGE + ".quality", "quality.py"))
MODULE_NAMES = PACKAGE_STUBS + tuple(name for name, _ in MODULE_FILES)
# Exact import closure of the pinned bytes (stdlib + pydantic 2 + sibling vendored modules only).
IMPORT_CLOSURE = {
    "canonicalize.py": {"__future__", "urllib.parse"},
    "models.py": {"__future__", "hashlib", "datetime", "typing", "pydantic", PACKAGE + ".canonicalize"},
    "quality.py": {"__future__", "pydantic", PACKAGE + ".models"},
}
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FETCHER_LABEL = "native-src01-frozen-local-bytes"
# Only sources that passed every native pre-quality gate reach upstream; everything else abstains.
NATIVE_EVALUABLE = ("ACCEPTED", "QUALITY_FAILED", "DEDUPED")
NATIVE_QUALITY_PASS = ("ACCEPTED", "DEDUPED")
# (upstream passed, native quality passed) -> agreement label
AGREEMENT = {(True, True): "AGREE_PASS", (False, False): "AGREE_FAIL",
             (True, False): "UPSTREAM_PASS_NATIVE_FAIL", (False, True): "UPSTREAM_FAIL_NATIVE_PASS"}
INVOKED = ("canonicalize.canonicalize_url", "models.CaptureResult", "models.CaptureResult.content_hash",
           "models.url_hash", "models.content_hash", "quality.evaluate")
REUSED_CAPABILITIES = ("R3-01", "R3-01-SOURCE_ARCHIVE")

_LOADED: dict = {}


class MetaculusStop(Exception):
    """Fail-closed stop with a stable code (never echoes paths, URLs, bodies or upstream exception text)."""


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def vendor_dir() -> Path:
    return Path(__file__).resolve().parent / "metaculus_source_archive"


def _unsafe(path: Path, *, directory: bool) -> bool:
    try:
        info = os.lstat(path)
    except OSError:
        return True
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    return not stat.S_ISDIR(info.st_mode) if directory else (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1)


def read_verified_vendor() -> dict:
    """All four vendored files, each a regular single-link file whose Git blob equals its pin."""
    root = vendor_dir()
    if _unsafe(root, directory=True):
        raise MetaculusStop("UPSTREAM_VENDOR_DIR_UNSAFE")
    if {p.name for p in root.iterdir()} - set(VENDOR_PINS) - {"__pycache__"}:
        raise MetaculusStop("UPSTREAM_VENDOR_DIR_UNEXPECTED_FILE")  # e.g. a planted __init__.py
    out = {}
    for name, pin in VENDOR_PINS.items():
        path = root / name
        if not os.path.lexists(path):
            raise MetaculusStop("UPSTREAM_FILE_MISSING")
        if _unsafe(path, directory=False):
            raise MetaculusStop("UPSTREAM_FILE_UNSAFE")
        data = path.read_bytes()
        if git_blob_sha1(data) != pin:
            raise MetaculusStop("UPSTREAM_BLOB_MISMATCH")
        out[name] = data
    if not out["LICENSE"].startswith(b"MIT License\n") or b"Permission is hereby granted, free of charge" not in out["LICENSE"]:
        raise MetaculusStop("UPSTREAM_LICENSE_INVALID")
    return out


def import_closure(source: bytes) -> set:
    """Every module a vendored file imports (static AST; nothing is executed)."""
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Call) and (getattr(node.func, "id", None) in ("__import__", "exec", "eval", "compile")
                                             or getattr(node.func, "attr", None) == "import_module"):
            names.add("<dynamic>")
    return names


def _require_pydantic() -> str:
    try:
        import pydantic
    except ImportError:
        raise MetaculusStop("PYDANTIC_UNAVAILABLE") from None
    version = str(getattr(pydantic, "VERSION", ""))
    if version.split(".")[0] != "2" or not hasattr(pydantic, "BaseModel") or not hasattr(pydantic, "Field"):
        raise MetaculusStop("PYDANTIC_INCOMPATIBLE")
    return version


def load_upstream() -> tuple:
    """(canonicalize, models, quality) executed from the verified bytes under their original upstream names."""
    data = read_verified_vendor()
    for _, filename in MODULE_FILES:
        if import_closure(data[filename]) != IMPORT_CLOSURE[filename]:
            raise MetaculusStop("UPSTREAM_IMPORT_CLOSURE_DRIFT")
    _require_pydantic()
    leaves = [name for name, _ in MODULE_FILES]
    if all(name in _LOADED and sys.modules.get(name) is _LOADED[name] for name in MODULE_NAMES):
        return tuple(_LOADED[name] for name in leaves)
    for name in MODULE_NAMES:
        if name in sys.modules and sys.modules[name] is not _LOADED.get(name):
            raise MetaculusStop("UPSTREAM_ALIAS_COLLISION")  # never overwrite a foreign module
    for name in MODULE_NAMES:
        sys.modules.pop(name, None)  # only our own stale entries reach here
    _LOADED.clear()
    root, registered = vendor_dir(), []
    try:
        for name in PACKAGE_STUBS:
            stub = module_from_spec(ModuleSpec(name, None, is_package=True))
            stub.__path__ = []  # a package with no search path: no other upstream file can be imported
            sys.modules[name] = stub
            registered.append(name)
            if "." in name:
                setattr(sys.modules[name.rsplit(".", 1)[0]], name.rsplit(".", 1)[1], stub)
            _LOADED[name] = stub
        for name, filename in MODULE_FILES:
            path = root / filename
            module = module_from_spec(ModuleSpec(name, None, origin=str(path)))
            module.__file__ = str(path)
            sys.modules[name] = module
            registered.append(name)
            # Execute exactly the verified bytes (no re-read, no bytecode cache write).
            exec(compile(data[filename], str(path), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
            setattr(sys.modules[PACKAGE], name.rsplit(".", 1)[1], module)
            _LOADED[name] = module
    except Exception:
        for name in registered:
            sys.modules.pop(name, None)
        _LOADED.clear()
        raise MetaculusStop("UPSTREAM_IMPORT_FAILED") from None
    return tuple(_LOADED[name] for name in leaves)


def upstream_identity() -> dict:
    data = read_verified_vendor()
    return {"repository": UPSTREAM_REPOSITORY, "commit": UPSTREAM_COMMIT, "license": "MIT",
            "upstream_paths": {name: name if name == "LICENSE" else f"{UPSTREAM_DIR}/{name}" for name in VENDOR_PINS},
            "git_blob_sha1": {name: git_blob_sha1(data[name]) for name in VENDOR_PINS},
            "sha256": {name: hashlib.sha256(data[name]).hexdigest() for name in VENDOR_PINS},
            "module_names": list(MODULE_NAMES), "import_closure": {k: sorted(v) for k, v in IMPORT_CLOSURE.items()},
            "pydantic_major": "2", "invoked": list(INVOKED),
            "never_loaded": [f"{UPSTREAM_DIR}/__init__.py", "fetchers", "storage", "pipeline", "content_store"]}


# ------------------------------------------------------------------ per-source comparison


def _abstain(out: dict, reason: str) -> dict:
    return dict(out, verdict="ABSTAINED", reason=reason)


def assess_source(entry: dict, native: dict, raw: bytes, upstream: tuple, calls: Counter) -> dict:
    """One frozen SRC-01 source + its native outcome -> upstream verdict (or a stable abstention).

    The native outcome is reported verbatim and stays controlling; nothing echoes URL or body text.
    """
    canonicalize, models, quality = upstream
    out = {"index": native["index"], "source_label": native["source_label"], "market_id": native["market_id"],
           "native_status": native["status"], "native_reason": native["reason"],
           "native_quality_pass": native["status"] in NATIVE_QUALITY_PASS, "http_status": None,
           "http_status_class": None, "verdict": "ABSTAINED", "reason": None, "upstream_passed": None,
           "upstream_reason": None, "agreement": None, "url_hash": None, "url_canonical_changed": None,
           "content_sha256": native["content_sha256"], "upstream_content_hash_matches_native": None,
           "capture_content_hash": None, "visible_text_length": None,
           "authenticated_web_evidence": False, "promotes_native_status": False}
    if native["status"] not in NATIVE_EVALUABLE:
        return _abstain(out, "NATIVE_PRE_QUALITY_REFUSED:" + str(native["reason"]))
    if native["reason"] == "INVALID_BYTES":
        return _abstain(out, "INVALID_UTF8_OR_NUL")
    if not SG._safe_url(entry.get("url")):
        return _abstain(out, "NATIVE_URL_UNSAFE")
    if not raw or SG.sha256_hex(raw) != native["content_sha256"] or native["content_sha256"] != entry.get("declared_sha256"):
        return _abstain(out, "SOURCE_BYTES_MISMATCH")
    text = SG._visible_text(raw)
    if text is None:
        return _abstain(out, "INVALID_UTF8_OR_NUL")
    if SG.SECRET_RE.search(text) or SG.SECRET_RE.search(raw.decode("utf-8")):
        return _abstain(out, "SECRET_SHAPED_CONTENT")
    status = entry["http_status"]
    # fetched_at is pinned to the native ingestion clock so the receipt never depends on wall time.
    calls["models.CaptureResult"] += 1
    capture = models.CaptureResult(url=entry["url"], final_url=entry["url"], status_code=status, markdown=text,
                                   fetcher=FETCHER_LABEL, fetched_at=entry["ingestion_time"])
    calls["quality.evaluate"] += 1
    verdict = quality.evaluate(capture)
    calls["models.url_hash"] += 1
    calls["canonicalize.canonicalize_url"] += 2  # once inside url_hash, once directly below
    url_key = models.url_hash(entry["url"])
    changed = canonicalize.canonicalize_url(entry["url"]) != entry["url"]
    calls["models.content_hash"] += 2  # once directly, once inside CaptureResult.content_hash
    raw_hash = models.content_hash(raw)
    calls["models.CaptureResult.content_hash"] += 1
    capture_hash = capture.content_hash
    passed = bool(verdict.passed)
    return dict(out, verdict="UPSTREAM_EVALUATED", http_status=status, http_status_class=f"{status // 100}xx",
                upstream_passed=passed, upstream_reason=verdict.reason or None,
                agreement=AGREEMENT[(passed, out["native_quality_pass"])], url_hash=url_key,
                url_canonical_changed=changed, upstream_content_hash_matches_native=raw_hash == native["content_sha256"],
                capture_content_hash=capture_hash, visible_text_length=len(text))


def _dedup(rows: list) -> dict:
    """URL / content identity counters: upstream (url_hash, capture hash) vs native (market_id, sha256) DEDUPED.

    Like the upstream pipeline (and native), only captures that passed their own quality gate take part in dedup.
    """
    evaluated = [r for r in rows if r["verdict"] == "UPSTREAM_EVALUATED"]
    by_url: dict = {}
    for row in evaluated:
        by_url.setdefault(row["url_hash"], []).append(row)
    seen, upstream_dup, disagreements = set(), [], 0
    for row in evaluated:
        key = (row["url_hash"], row["capture_content_hash"])
        duplicate = row["upstream_passed"] and key in seen
        if row["upstream_passed"]:
            seen.add(key)
        upstream_dup.append(duplicate)
        if duplicate != (row["native_status"] == "DEDUPED"):
            disagreements += 1
    return {"evaluated": len(evaluated), "distinct_url_hash": len(by_url),
            "url_alias_collapsed": len(evaluated) - len(by_url),
            "url_canonical_changed": sum(1 for r in evaluated if r["url_canonical_changed"]),
            "url_hash_same_content_differs": sum(1 for g in by_url.values() if len({r["content_sha256"] for r in g}) > 1),
            "url_hash_spans_markets": sum(1 for g in by_url.values() if len({r["market_id"] for r in g}) > 1),
            "distinct_capture_content_hash": len({r["capture_content_hash"] for r in evaluated}),
            "upstream_url_content_duplicates": sum(upstream_dup),
            "native_deduped": sum(1 for r in evaluated if r["native_status"] == "DEDUPED"),
            "dedup_disagreements": disagreements,
            "upstream_content_hash_mismatch": sum(1 for r in evaluated if not r["upstream_content_hash_matches_native"])}


def assess_sources(case: dict, src_core: dict, read) -> dict:
    """Every frozen SRC-01 source entry -> upstream comparison with exact denominators."""
    entries, natives = case["sources"], src_core["sources"]["entries"]
    if len(entries) != len(natives) or any(n.get("index") != i for i, n in enumerate(natives)):
        raise MetaculusStop("SRC_SOURCE_ROWS_MISALIGNED")
    upstream = load_upstream()
    calls: Counter = Counter({name: 0 for name in INVOKED})
    rows = [assess_source(entry if isinstance(entry, dict) else {}, native,
                          read(entry["file"]) if isinstance(entry, dict) else b"", upstream, calls)
            for entry, native in zip(entries, natives)]
    evaluated = [r for r in rows if r["verdict"] == "UPSTREAM_EVALUATED"]
    agreement = Counter(r["agreement"] for r in evaluated)
    return {"rows": rows, "invocations": dict(sorted(calls.items())), "dedup": _dedup(rows), "counts": {
        "sources_total": len(rows), "upstream_evaluated": len(evaluated),
        "abstained": len(rows) - len(evaluated),
        "abstention_reasons": dict(sorted(Counter(r["reason"] for r in rows if r["verdict"] == "ABSTAINED").items())),
        "upstream_passed": sum(1 for r in evaluated if r["upstream_passed"]),
        "native_quality_passed": sum(1 for r in evaluated if r["native_quality_pass"]),
        "agree_pass": agreement["AGREE_PASS"], "agree_fail": agreement["AGREE_FAIL"],
        "divergent_upstream_pass_native_fail": agreement["UPSTREAM_PASS_NATIVE_FAIL"],
        "divergent_upstream_fail_native_pass": agreement["UPSTREAM_FAIL_NATIVE_PASS"],
        "divergent_total": agreement["UPSTREAM_PASS_NATIVE_FAIL"] + agreement["UPSTREAM_FAIL_NATIVE_PASS"],
        "divergent_non_2xx_upstream_pass": sum(1 for r in evaluated if r["upstream_passed"] and r["http_status_class"] != "2xx"),
        "upstream_reasons": dict(sorted(Counter((r["upstream_reason"] or "PASSED").split("=")[0].split(" ")[0]
                                               for r in evaluated).items())),
        "native_accepted": sum(1 for r in rows if r["native_status"] == "ACCEPTED"),
        "promoted_by_upstream": 0, "authenticated_web_evidence": 0}}
