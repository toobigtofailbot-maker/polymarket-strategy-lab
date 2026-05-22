"""
Local offline read-only code index / blast-radius advisory helper.

Scans local filesystem only. Makes no network calls. Executes no commands.
Modifies no files by default. Does not replace pytest, security checks,
preflight tools, or human review. Advisory only.
"""

import argparse
import ast
import json
import os
import pathlib
import re
import sys
from typing import Any

SUMMARY_SCHEMA_VERSION = "1.0"

# ── Exclusion lists ──────────────────────────────────────────────────────────

EXCLUDED_DIR_PREFIXES = [
    ".git/",
    "local_data/",
    ".venv-security/",
    ".venv-official-client/",
    "tools/.bin/",
    "tools/security/.cache/",
    "security-scan-output/",
    "official-client-sandbox-output/",
    ".pytest_cache/",
    "__pycache__/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".claude/",
]

EXCLUDED_EXACT = [".coverage"]

MAX_FILE_BYTES = 1_048_576  # 1 MB

BINARY_SUFFIXES = {
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".o", ".a",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".db", ".sqlite", ".sqlite3",
}

# ── Sensitive path patterns ──────────────────────────────────────────────────

SENSITIVE_EXACT = [".env"]
SENSITIVE_STARTSWITH = [".env."]
SENSITIVE_NAME_PATTERNS = [
    r"private[_\-.]?key",
    r"wallet[_\-.]?key",
    r"mnemonic",
    r"passphrase",
    r"api[_\-.]?key",
    r"secret[_\-.]?key",
    r"credentials\.json$",
    r"keystore",
    r"id_rsa",
    r"id_ed25519",
    r"\.pem$",
    r"\.p12$",
    r"\.pfx$",
]

# ── Protected boundary patterns ──────────────────────────────────────────────

PROTECTED_PREFIXES = [
    "src/",
    "tools/hermes/",
    "agent_runtime/",
    "agent_memory/",
]

PROTECTED_EXACT = [".env"]
PROTECTED_STARTSWITH = [".env."]

CREDENTIAL_LIKE_PATTERNS = [
    r"private[_\-.]?key",
    r"wallet[_\-.]?key",
    r"mnemonic",
    r"passphrase",
    r"api[_\-.]?key",
    r"secret[_\-.]?key",
    r"credentials\.json$",
    r"keystore",
    r"id_rsa",
    r"id_ed25519",
    r"\.pem$",
    r"\.p12$",
    r"\.pfx$",
]

# ── Dependency/lock patterns ─────────────────────────────────────────────────

DEPENDENCY_LOCK_NAMES = {
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "uv.lock",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
}

DEPENDENCY_LOCK_SUFFIXES = {".lock"}

# ── Generated output patterns ────────────────────────────────────────────────

GENERATED_OUTPUT_PREFIXES = [
    "local_data/",
    "security-scan-output/",
    "official-client-sandbox-output/",
    ".venv-security/",
    ".venv-official-client/",
    "tools/.bin/",
    "tools/security/.cache/",
]

GENERATED_OUTPUT_EXACT = [".coverage"]
GENERATED_OUTPUT_SUFFIXES = [".sarif"]

# ── Repo-truth relationship rules ────────────────────────────────────────────

REPO_TRUTH_RULES: list[tuple[str, list[str], str]] = [
    (
        "docs/repo_truth_index.md",
        [
            "docs/project_status.md",
            "docs/deferred_items_log.md",
            "docs/review_checklist.md",
            "docs/testing_requirements.md",
        ],
        "repo-truth update often requires syncing these docs",
    ),
    (
        "docs/project_status.md",
        ["docs/deferred_items_log.md", "docs/repo_truth_index.md"],
        "project status changes often accompany deferred-item and index updates",
    ),
    (
        "docs/deferred_items_log.md",
        ["docs/project_status.md"],
        "deferred-item changes often accompany project status updates",
    ),
    (
        "docs/review_checklist.md",
        ["docs/ai/codex/"],
        "review checklist often reflects active WP design/helper docs",
    ),
    (
        "docs/testing_requirements.md",
        ["docs/ai/codex/"],
        "testing requirements often reflect active WP design/helper docs",
    ),
]

REPO_TRUTH_PREFIX_RULES: list[tuple[str, list[str], str]] = [
    (
        "docs/ai/codex/",
        [
            "docs/ai/codex/README.md",
            "docs/ai/codex/TOKEN_EFFICIENCY_OPERATING_MODEL.md",
            "docs/work_package_template.md",
        ],
        "Codex docs changes often require updating README and operating model",
    ),
    (
        "tools/git/",
        ["tests/tools/git/"],
        "tools/git changes should be paired with tests/tools/git tests",
    ),
    (
        "tools/validation/",
        ["tests/tools/validation/"],
        "tools/validation changes should be paired with tests/tools/validation tests",
    ),
    (
        "src/data_layer/",
        [
            "tests/",
            "docs/runtime_boundaries.md",
            "docs/data_semantics.md",
        ],
        "data-layer changes should have tests and runtime boundary review",
    ),
]

# ── Package-class warning rules ──────────────────────────────────────────────

LIVE_TRADING_AUTH_FILE = "docs/live_trading_authorization.md"

# ── Path normalization ───────────────────────────────────────────────────────

def _norm(p: str) -> str:
    s = p.replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s


def _norm_path(p: pathlib.Path) -> str:
    return _norm(str(p))


# ── Exclusion / sensitivity checks ──────────────────────────────────────────

def is_excluded_path(rel: str) -> bool:
    r = _norm(rel)
    if r in EXCLUDED_EXACT:
        return True
    for prefix in EXCLUDED_DIR_PREFIXES:
        stripped = prefix.rstrip("/")
        if r.startswith(prefix) or r == stripped:
            return True
        # Also match as intermediate directory segment
        if f"/{stripped}/" in f"/{r}/":
            return True
    return False


def is_sensitive_file(name: str) -> bool:
    n = name.lower()
    if n in {s.lower() for s in SENSITIVE_EXACT}:
        return True
    for sw in SENSITIVE_STARTSWITH:
        if n.startswith(sw.lower()):
            return True
    for pat in SENSITIVE_NAME_PATTERNS:
        if re.search(pat, n, re.IGNORECASE):
            return True
    return False


def is_dependency_lock(rel: str) -> bool:
    r = _norm(rel)
    name = r.rsplit("/", 1)[-1]
    if name in DEPENDENCY_LOCK_NAMES:
        return True
    for suf in DEPENDENCY_LOCK_SUFFIXES:
        if name.endswith(suf):
            return True
    return False


def is_generated_output(rel: str) -> bool:
    r = _norm(rel)
    if r in GENERATED_OUTPUT_EXACT:
        return True
    for prefix in GENERATED_OUTPUT_PREFIXES:
        if r.startswith(prefix):
            return True
    for suf in GENERATED_OUTPUT_SUFFIXES:
        if r.endswith(suf):
            return True
    return False


# ── Protected boundary check ─────────────────────────────────────────────────

def get_protected_category(rel: str) -> str | None:
    r = _norm(rel)
    name = r.rsplit("/", 1)[-1].lower()
    if r in {e.lower() for e in PROTECTED_EXACT}:
        return "sensitive-env-file"
    for sw in PROTECTED_STARTSWITH:
        if r.lower().startswith(sw.lower()):
            return "sensitive-env-file"
    for prefix in PROTECTED_PREFIXES:
        if r.startswith(prefix):
            return f"protected-prefix:{prefix.rstrip('/')}"
    for pat in CREDENTIAL_LIKE_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return "credential-like-name"
    if is_dependency_lock(rel):
        return "dependency-lock-file"
    return None


# ── Input validation ─────────────────────────────────────────────────────────

def _is_absolute_path(p: str) -> bool:
    """True if path is absolute on any platform."""
    # os.path.isabs catches Unix-absolute and Windows-absolute
    # Also check leading slash (drive-relative on Windows but not repo-relative)
    # Also check Windows drive letter like C:
    n = _norm(p)
    if os.path.isabs(p):
        return True
    if n.startswith("/"):
        return True
    if len(p) > 1 and p[1] == ":":
        return True
    return False


def validate_input_path(p: str) -> str | None:
    """Return error string if path is invalid, else None."""
    n = _norm(p)
    if _is_absolute_path(p):
        return f"absolute path not allowed: {p!r}"
    if ".." in n.split("/"):
        return f"traversal (..) not allowed: {p!r}"
    return None


def validate_output_path(p: str) -> str | None:
    """Return error string if output path is invalid, else None."""
    n = _norm(p)
    if _is_absolute_path(p):
        return f"absolute output path not allowed: {p!r}"
    if ".." in n.split("/"):
        return f"traversal (..) not allowed in output path: {p!r}"
    if not n.startswith("local_data/code_blast_radius/"):
        return (
            f"output path must be under local_data/code_blast_radius/: {p!r}"
        )
    return None


# ── Filesystem walker ────────────────────────────────────────────────────────

def walk_repo_files(repo_root: pathlib.Path) -> list[str]:
    """Walk repo, returning repo-relative forward-slash paths for text files."""
    results = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        rel_dir = pathlib.Path(dirpath).relative_to(repo_root)
        rel_dir_str = _norm(str(rel_dir)) + "/" if str(rel_dir) != "." else ""

        # Prune excluded directories in-place
        pruned = []
        for d in dirnames:
            candidate = rel_dir_str + d + "/"
            if is_excluded_path(candidate):
                continue
            # Also skip hidden dirs other than known ones already in exclusions
            pruned.append(d)
        dirnames[:] = pruned

        for fname in filenames:
            rel_file = rel_dir_str + fname
            if is_excluded_path(rel_file):
                continue
            suffix = pathlib.Path(fname).suffix.lower()
            if suffix in BINARY_SUFFIXES:
                continue
            if is_sensitive_file(fname):
                continue
            full = repo_root / rel_file.replace("/", os.sep)
            try:
                size = full.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            results.append(rel_file)
    return results


def read_text_safe(path: pathlib.Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ── Direct reference detection ───────────────────────────────────────────────

def find_direct_references(
    repo_files: list[str],
    changed_inputs: list[str],
    repo_root: pathlib.Path,
) -> list[dict[str, Any]]:
    """Find files that mention any changed input as a path string or stem."""
    stems = set()
    paths_set = set()
    for ci in changed_inputs:
        n = _norm(ci)
        paths_set.add(n)
        base = n.rsplit("/", 1)[-1]
        stem = base.rsplit(".", 1)[0] if "." in base else base
        if len(stem) >= 4:
            stems.add(stem)

    refs: list[dict[str, Any]] = []
    for rel in repo_files:
        # skip the changed file itself
        if _norm(rel) in paths_set:
            continue
        full = repo_root / rel.replace("/", os.sep)
        text = read_text_safe(full)
        if text is None:
            continue
        matched_terms: list[str] = []
        for cp in paths_set:
            if cp in text:
                matched_terms.append(cp)
        for stem in stems:
            # avoid trivially short stems polluting results
            if stem in text and stem not in matched_terms:
                matched_terms.append(stem)
        if matched_terms:
            refs.append(
                {
                    "file": rel,
                    "matched_terms": matched_terms[:5],
                    "confidence": "medium",
                }
            )
    return refs


# ── Naming heuristics ────────────────────────────────────────────────────────

def naming_heuristic_tests(
    changed_inputs: list[str],
    repo_files: list[str],
) -> list[dict[str, Any]]:
    """Suggest tests based on naming heuristics."""
    suggestions: list[dict[str, Any]] = []
    repo_set = set(repo_files)

    for ci in changed_inputs:
        n = _norm(ci)
        base = n.rsplit("/", 1)[-1]
        stem = base.rsplit(".", 1)[0] if "." in base else base
        parts = n.rsplit("/", 1)
        dir_part = parts[0] if len(parts) == 2 else ""

        candidates = [
            f"tests/tools/git/test_{stem}.py",
            f"tests/tools/validation/test_{stem}.py",
            f"tests/{dir_part}/test_{stem}.py" if dir_part else None,
            f"tests/test_{stem}.py",
        ]

        for cand in candidates:
            if cand is None:
                continue
            cand = _norm(cand)
            if cand in repo_set:
                suggestions.append(
                    {
                        "changed_input": ci,
                        "suggested_test": cand,
                        "reason": "naming heuristic: test_<stem>.py",
                        "confidence": "high",
                    }
                )
        # Also look for any test file containing stem in filename
        for rf in repo_files:
            if rf.startswith("tests/") and stem.lower() in rf.lower():
                existing = [s["suggested_test"] for s in suggestions]
                if rf not in existing:
                    suggestions.append(
                        {
                            "changed_input": ci,
                            "suggested_test": rf,
                            "reason": f"naming heuristic: contains '{stem}'",
                            "confidence": "medium",
                        }
                    )
    return suggestions


def naming_heuristic_docs(
    changed_inputs: list[str],
    repo_files: list[str],
) -> list[dict[str, Any]]:
    """Suggest docs based on naming heuristics."""
    suggestions: list[dict[str, Any]] = []
    repo_set = set(repo_files)

    for ci in changed_inputs:
        n = _norm(ci)
        base = n.rsplit("/", 1)[-1]
        stem = base.rsplit(".", 1)[0] if "." in base else base

        candidates = [
            f"docs/ai/codex/{stem.upper()}.md",
            f"docs/{stem}.md",
        ]
        for cand in candidates:
            cand = _norm(cand)
            if cand in repo_set:
                suggestions.append(
                    {
                        "changed_input": ci,
                        "suggested_doc": cand,
                        "reason": "naming heuristic: matching doc name",
                        "confidence": "medium",
                    }
                )
        # Look for docs with stem in filename
        for rf in repo_files:
            if rf.startswith("docs/") and stem.lower() in rf.lower():
                existing = [s["suggested_doc"] for s in suggestions]
                if rf not in existing:
                    suggestions.append(
                        {
                            "changed_input": ci,
                            "suggested_doc": rf,
                            "reason": f"naming heuristic: doc contains '{stem}'",
                            "confidence": "low",
                        }
                    )
    return suggestions


# ── Repo-truth relationship rules ────────────────────────────────────────────

def apply_repo_truth_rules(
    changed_inputs: list[str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for ci in changed_inputs:
        n = _norm(ci)

        # Exact-file rules
        for trigger_file, related, reason in REPO_TRUTH_RULES:
            if n == _norm(trigger_file):
                for r in related:
                    key = f"{ci}:{r}"
                    if key not in seen:
                        seen.add(key)
                        results.append(
                            {
                                "changed_input": ci,
                                "related": r,
                                "reason": reason,
                                "confidence": "high",
                            }
                        )

        # Prefix rules
        for trigger_prefix, related_list, reason in REPO_TRUTH_PREFIX_RULES:
            if n.startswith(trigger_prefix):
                for r in related_list:
                    key = f"{ci}:{r}"
                    if key not in seen:
                        seen.add(key)
                        results.append(
                            {
                                "changed_input": ci,
                                "related": r,
                                "reason": reason,
                                "confidence": "high",
                            }
                        )

    return results


# ── Python AST import parsing ────────────────────────────────────────────────

def parse_py_imports(path: pathlib.Path) -> list[str]:
    """Return imported module names from a .py file using ast. Returns [] on error."""
    text = read_text_safe(path)
    if text is None:
        return []
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def find_ast_references(
    repo_files: list[str],
    changed_inputs: list[str],
    repo_root: pathlib.Path,
) -> list[dict[str, Any]]:
    """Find .py files that import modules matching changed .py file stems."""
    changed_stems: set[str] = set()
    for ci in changed_inputs:
        n = _norm(ci)
        if n.endswith(".py"):
            base = n.rsplit("/", 1)[-1]
            stem = base[:-3]
            if len(stem) >= 4:
                changed_stems.add(stem)

    if not changed_stems:
        return []

    refs: list[dict[str, Any]] = []
    for rel in repo_files:
        if not rel.endswith(".py"):
            continue
        if _norm(rel) in {_norm(ci) for ci in changed_inputs}:
            continue
        full = repo_root / rel.replace("/", os.sep)
        try:
            imports = parse_py_imports(full)
        except Exception:
            continue
        matched = [imp for imp in imports if any(s in imp for s in changed_stems)]
        if matched:
            refs.append(
                {
                    "file": rel,
                    "imports": matched[:5],
                    "confidence": "medium",
                    "method": "ast-import",
                }
            )
    return refs


# ── Protected / sensitive boundary ──────────────────────────────────────────

def find_protected_hits(changed_inputs: list[str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for ci in changed_inputs:
        cat = get_protected_category(ci)
        if cat:
            hits.append(
                {
                    "path": ci,
                    "category": cat,
                    "note": "Protected/sensitive path. Flag for human review. Helper did not read protected contents.",
                }
            )
    return hits


def find_dep_lock_hits(changed_inputs: list[str]) -> list[dict[str, Any]]:
    hits = []
    for ci in changed_inputs:
        if is_dependency_lock(ci):
            hits.append(
                {
                    "path": ci,
                    "note": "Dependency/lock file change requires explicit authorization and careful review.",
                }
            )
    return hits


def find_generated_output_hits(changed_inputs: list[str]) -> list[dict[str, Any]]:
    hits = []
    for ci in changed_inputs:
        if is_generated_output(ci):
            hits.append(
                {
                    "path": ci,
                    "note": "Generated/local output file. Must not be staged or committed.",
                }
            )
    return hits


# ── Package-class warnings ───────────────────────────────────────────────────

def generate_package_class_warnings(
    package_class: str,
    changed_inputs: list[str],
    repo_files_set: set[str],
) -> list[str]:
    warnings: list[str] = []
    pc = package_class.lower()

    touching_src = any(_norm(ci).startswith("src/") for ci in changed_inputs)
    touching_tools = any(_norm(ci).startswith("tools/") for ci in changed_inputs)
    touching_dep_lock = any(is_dependency_lock(ci) for ci in changed_inputs)
    touching_live_auth = LIVE_TRADING_AUTH_FILE in {_norm(ci) for ci in changed_inputs}
    touching_hermes = any(_norm(ci).startswith("tools/hermes/") or "hermes" in _norm(ci).lower() for ci in changed_inputs)
    touching_agent_runtime = any(
        _norm(ci).startswith("agent_runtime/") or _norm(ci).startswith("agent_memory/")
        for ci in changed_inputs
    )
    touching_network_files = any(
        any(kw in _norm(ci).lower() for kw in ("network", "socket", "http", "websocket"))
        for ci in changed_inputs
    )

    has_live_auth_file = LIVE_TRADING_AUTH_FILE in repo_files_set

    if pc in ("docs-only", "design"):
        if touching_src:
            warnings.append(
                f"package-class '{package_class}' should not touch src/ — found changed inputs under src/"
            )
        if touching_tools and not all(
            _norm(ci).startswith(("tools/git/", "tools/validation/"))
            for ci in changed_inputs
            if _norm(ci).startswith("tools/")
        ):
            warnings.append(
                f"package-class '{package_class}' should not touch unrelated tools/ paths"
            )

    if pc == "local-tooling":
        unrelated_runtime = [
            ci for ci in changed_inputs
            if _norm(ci).startswith("src/") and "data_layer" not in _norm(ci)
        ]
        if unrelated_runtime:
            warnings.append(
                "local-tooling package touching unrelated runtime/product code under src/"
            )

    # Missing tests warning for source packages
    if pc in ("source", "runtime", "data-layer"):
        has_test = any(_norm(ci).startswith("tests/") for ci in changed_inputs)
        if not has_test:
            warnings.append(
                f"package-class '{package_class}' appears to have no test files in changed inputs"
            )

    if touching_dep_lock:
        if pc not in ("dependency", "dependency-update"):
            warnings.append(
                "dependency/lock file changed but package-class is not 'dependency' or 'dependency-update' — "
                "this requires explicit authorization"
            )

    if pc in ("live-trading", "trading"):
        if not has_live_auth_file:
            warnings.append(
                "live-trading package class requires docs/live_trading_authorization.md to exist and be reviewed"
            )

    if pc in ("agent", "hermes", "agent-runtime"):
        if touching_hermes or touching_agent_runtime or touching_network_files:
            warnings.append(
                f"package-class '{package_class}' touching runtime/network/agent files requires explicit approval"
            )

    return warnings


# ── Result capping ───────────────────────────────────────────────────────────

def cap_list(
    items: list[Any],
    max_results: int,
    section_name: str,
    truncated_sections: list[str],
) -> list[Any]:
    if len(items) > max_results:
        truncated_sections.append(
            f"{section_name}: capped at {max_results}, {len(items) - max_results} additional items omitted"
        )
        return items[:max_results]
    return items


# ── Core scan ────────────────────────────────────────────────────────────────

def build_summary(
    changed_files: list[str],
    changed_prefixes: list[str],
    package_class: str,
    include_tests: bool,
    include_docs: bool,
    include_protected: bool,
    max_results: int,
    repo_root: pathlib.Path,
    use_ast: bool,
) -> dict[str, Any]:

    truncated_sections: list[str] = []

    # All changed inputs for analysis
    all_changed = changed_files + changed_prefixes

    # Walk filesystem
    repo_files = walk_repo_files(repo_root)
    repo_files_set = set(repo_files)

    # Repo-truth relationships
    repo_truth_raw = apply_repo_truth_rules(all_changed)
    repo_truth_files: list[str] = []
    seen_rt: set[str] = set()
    for r in repo_truth_raw:
        target = r["related"]
        if target not in seen_rt:
            seen_rt.add(target)
            repo_truth_files.append(target)
    repo_truth_files = cap_list(repo_truth_files, max_results, "repo_truth_files_to_inspect", truncated_sections)

    # Direct text references
    direct_refs_raw = find_direct_references(repo_files, all_changed, repo_root)
    # Include AST references if enabled
    if use_ast:
        ast_refs = find_ast_references(repo_files, changed_files, repo_root)
        # Merge by file (avoid duplicates)
        ast_files = {r["file"] for r in ast_refs}
        direct_ref_files = {r["file"] for r in direct_refs_raw}
        for ar in ast_refs:
            if ar["file"] not in direct_ref_files:
                direct_refs_raw.append(
                    {
                        "file": ar["file"],
                        "matched_terms": ar["imports"],
                        "confidence": ar["confidence"],
                    }
                )
    direct_refs = cap_list(direct_refs_raw, max_results, "direct_references", truncated_sections)

    # Naming heuristic tests
    likely_tests: list[dict[str, Any]] = []
    tests_requested = include_tests
    if include_tests:
        test_hints = naming_heuristic_tests(all_changed, repo_files)
        likely_tests = cap_list(test_hints, max_results, "likely_tests", truncated_sections)

    # Naming heuristic docs
    likely_docs: list[dict[str, Any]] = []
    docs_requested = include_docs
    if include_docs:
        changed_set = set(_norm(ci) for ci in all_changed)
        doc_hints = [
            d for d in naming_heuristic_docs(all_changed, repo_files)
            if _norm(d.get("suggested_doc", "")) not in changed_set
        ]
        likely_docs = cap_list(doc_hints, max_results, "likely_docs", truncated_sections)

    # Related source files: direct refs excluding tests/docs
    related_source = [
        r for r in direct_refs
        if not r["file"].startswith("tests/") and not r["file"].startswith("docs/")
    ]
    related_source = cap_list(related_source, max_results, "related_source_files", truncated_sections)

    # Protected boundaries
    protected_hits: list[dict[str, Any]] = []
    if include_protected:
        protected_hits = find_protected_hits(all_changed)
    protected_hits = cap_list(protected_hits, max_results, "protected_boundary_attention", truncated_sections)

    # Dependency/lock attention
    dep_lock_hits = find_dep_lock_hits(all_changed)
    dep_lock_hits = cap_list(dep_lock_hits, max_results, "dependency_lock_attention", truncated_sections)

    # Generated output attention
    gen_output_hits = find_generated_output_hits(all_changed)
    gen_output_hits = cap_list(gen_output_hits, max_results, "generated_output_attention", truncated_sections)

    # Package-class warnings
    pkg_warnings = generate_package_class_warnings(package_class, all_changed, repo_files_set)

    # Unknown/low-confidence notes
    unknown_notes: list[str] = []
    for ci in all_changed:
        n = _norm(ci)
        if ci in changed_files and n not in repo_files_set and not any(
            n.startswith(p) for p in EXCLUDED_DIR_PREFIXES
        ):
            unknown_notes.append(
                f"changed-file not found in local scan: {ci!r} — verify path is correct"
            )
        if ci in changed_prefixes:
            prefix_files = [f for f in repo_files if _norm(f).startswith(n)]
            if not prefix_files:
                unknown_notes.append(
                    f"changed-prefix matched no local files: {ci!r} — may be empty or excluded"
                )

    summary: dict[str, Any] = {
        "summary_schema_version": SUMMARY_SCHEMA_VERSION,
        "repo_root": str(repo_root),
        "mode": "on_demand_scan",
        "stale_index_status": "not_applicable_on_demand_scan",
        "package_class": package_class,
        "changed_files": changed_files,
        "changed_prefixes": changed_prefixes,
        "related_source_files": related_source,
        "likely_tests": likely_tests,
        "likely_docs": likely_docs,
        "tests_requested": tests_requested,
        "docs_requested": docs_requested,
        "repo_truth_files_to_inspect": repo_truth_files,
        "direct_references": direct_refs,
        "naming_heuristics": {
            "tests": likely_tests,
            "docs": likely_docs,
        },
        "protected_boundary_attention": protected_hits,
        "protected_requested": include_protected,
        "dependency_lock_attention": dep_lock_hits,
        "generated_output_attention": gen_output_hits,
        "package_class_warnings": pkg_warnings,
        "unknown_or_low_confidence_notes": unknown_notes,
        "truncated_sections": truncated_sections,
        "validation_reminder": (
            "REMINDER: This summary does not replace pytest, security checks, "
            "preflight_generated_artifact_guard.py, preflight_sync_main.py "
            "(Remote Main Sync Gate), or human review. Run all required validation "
            "steps before requesting merge."
        ),
        "human_review_reminder": (
            "Human review is required before merge. This advisory summary cannot "
            "authorize merge-ready status."
        ),
        "advisory_only_note": (
            "This output is advisory only. It does not replace direct file "
            "inspection, validation commands, security scans, or repo-truth "
            "verification. Relationship suggestions are heuristic and may be "
            "incomplete or imprecise."
        ),
    }
    return summary


# ── Text formatter ───────────────────────────────────────────────────────────

def format_text(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    sep = "=" * 70

    lines.append(sep)
    lines.append("CODE BLAST RADIUS ADVISORY SUMMARY")
    lines.append(sep)
    lines.append(f"Schema version:  {summary['summary_schema_version']}")
    lines.append(f"Mode:            {summary['mode']}")
    lines.append(f"Package class:   {summary['package_class']}")
    lines.append(f"Repo root:       {summary['repo_root']}")
    lines.append(f"Stale index:     {summary['stale_index_status']}")
    lines.append("")

    def _section(title: str, items: list[Any], key_fn=None):
        lines.append(f"--- {title} ---")
        if not items:
            lines.append("  (none)")
        else:
            for item in items:
                if isinstance(item, dict):
                    if key_fn:
                        lines.append(f"  {key_fn(item)}")
                    else:
                        lines.append(f"  {item}")
                else:
                    lines.append(f"  {item}")
        lines.append("")

    lines.append("Changed files:")
    for f in summary["changed_files"] or ["(none)"]:
        lines.append(f"  {f}")
    lines.append("")

    lines.append("Changed prefixes:")
    for p in summary["changed_prefixes"] or ["(none)"]:
        lines.append(f"  {p}")
    lines.append("")

    lines.append("--- Likely tests ---")
    if summary["likely_tests"]:
        for t in summary["likely_tests"]:
            lines.append(f"  [{t.get('confidence','?')}] {t.get('suggested_test','')}  (reason: {t.get('reason','')})")
    elif summary.get("tests_requested"):
        lines.append("  (none found by naming heuristics)")
    else:
        lines.append("  (not requested — pass --include-tests to enable)")
    lines.append("")

    lines.append("--- Likely docs ---")
    if summary["likely_docs"]:
        for d in summary["likely_docs"]:
            lines.append(f"  [{d.get('confidence','?')}] {d.get('suggested_doc','')}  (reason: {d.get('reason','')})")
    elif summary.get("docs_requested"):
        lines.append("  (none found by naming heuristics)")
    else:
        lines.append("  (not requested — pass --include-docs to enable)")
    lines.append("")

    lines.append("--- Repo-truth files to inspect ---")
    if summary["repo_truth_files_to_inspect"]:
        for r in summary["repo_truth_files_to_inspect"]:
            lines.append(f"  {r}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("--- Direct text references ---")
    if summary["direct_references"]:
        for ref in summary["direct_references"]:
            lines.append(f"  [{ref.get('confidence','?')}] {ref.get('file','')}  (terms: {ref.get('matched_terms',[])})")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("--- Protected boundary attention ---")
    if summary["protected_boundary_attention"]:
        for h in summary["protected_boundary_attention"]:
            lines.append(f"  [WARNING] {h.get('path','')}  category={h.get('category','')}  {h.get('note','')}")
    elif not summary.get("protected_requested", True):
        lines.append("  (not requested — pass --include-protected-boundaries to enable)")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("--- Dependency/lock attention ---")
    if summary["dependency_lock_attention"]:
        for h in summary["dependency_lock_attention"]:
            lines.append(f"  [ATTENTION] {h.get('path','')}  {h.get('note','')}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("--- Generated output attention ---")
    if summary["generated_output_attention"]:
        for h in summary["generated_output_attention"]:
            lines.append(f"  [ATTENTION] {h.get('path','')}  {h.get('note','')}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("--- Package-class warnings ---")
    if summary["package_class_warnings"]:
        for w in summary["package_class_warnings"]:
            lines.append(f"  [WARN] {w}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append("--- Unknown / low-confidence notes ---")
    if summary["unknown_or_low_confidence_notes"]:
        for n in summary["unknown_or_low_confidence_notes"]:
            lines.append(f"  {n}")
    else:
        lines.append("  (none)")
    lines.append("")

    if summary["truncated_sections"]:
        lines.append("--- Truncation notes ---")
        for t in summary["truncated_sections"]:
            lines.append(f"  {t}")
        lines.append("")

    lines.append("-" * 70)
    lines.append(summary["advisory_only_note"])
    lines.append("")
    lines.append(summary["validation_reminder"])
    lines.append("")
    lines.append(summary["human_review_reminder"])
    lines.append("-" * 70)

    return "\n".join(lines) + "\n"


def format_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


# ── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Local offline read-only code index / blast-radius advisory helper. "
            "Advisory only — does not replace pytest, security checks, or human review."
        )
    )
    p.add_argument(
        "--changed-file",
        dest="changed_files",
        action="append",
        default=[],
        metavar="PATH",
        help="Changed file to analyze (repo-relative, may be repeated).",
    )
    p.add_argument(
        "--changed-prefix",
        dest="changed_prefixes",
        action="append",
        default=[],
        metavar="PREFIX",
        help="Changed path prefix to analyze (repo-relative, may be repeated).",
    )
    p.add_argument(
        "--package-class",
        dest="package_class",
        default="unspecified",
        metavar="CLASS",
        help="Active WP package class (advisory warnings only).",
    )
    p.add_argument(
        "--include-tests",
        dest="include_tests",
        action="store_true",
        default=False,
        help="Include likely related tests in output.",
    )
    p.add_argument(
        "--include-docs",
        dest="include_docs",
        action="store_true",
        default=False,
        help="Include likely related docs in output.",
    )
    p.add_argument(
        "--include-protected-boundaries",
        dest="include_protected",
        action="store_true",
        default=False,
        help="Report protected/sensitive path attention areas (does not read protected contents).",
    )
    p.add_argument(
        "--format",
        dest="fmt",
        choices=["text", "json"],
        default="text",
        help="Output format: text (default) or json.",
    )
    p.add_argument(
        "--output",
        dest="output",
        default=None,
        metavar="PATH",
        help=(
            "Optional output file path (must be under local_data/code_blast_radius/). "
            "No file is written by default."
        ),
    )
    p.add_argument(
        "--max-results",
        dest="max_results",
        type=int,
        default=25,
        metavar="N",
        help="Maximum advisory paths per section (default 25).",
    )
    p.add_argument(
        "--fail-on-protected-hit",
        dest="fail_on_protected",
        action="store_true",
        default=False,
        help="Exit 1 when protected boundary hits are detected.",
    )
    p.add_argument(
        "--repo-root",
        dest="repo_root",
        default=".",
        metavar="DIR",
        help="Repository root directory (default: current directory).",
    )
    p.add_argument(
        "--no-ast",
        dest="no_ast",
        action="store_true",
        default=False,
        help="Disable stdlib ast import parsing for .py files.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate max_results
    if args.max_results < 1:
        print(f"ERROR: --max-results must be >= 1, got {args.max_results}", file=sys.stderr)
        return 2

    # Require at least one changed input
    if not args.changed_files and not args.changed_prefixes:
        print(
            "ERROR: at least one --changed-file or --changed-prefix is required.",
            file=sys.stderr,
        )
        return 2

    # Validate changed inputs
    for p in args.changed_files + args.changed_prefixes:
        err = validate_input_path(p)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 2

    # Validate output path if provided
    if args.output is not None:
        err = validate_output_path(args.output)
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 2

    repo_root = pathlib.Path(args.repo_root).resolve()

    summary = build_summary(
        changed_files=[_norm(f) for f in args.changed_files],
        changed_prefixes=[_norm(p) for p in args.changed_prefixes],
        package_class=args.package_class,
        include_tests=args.include_tests,
        include_docs=args.include_docs,
        include_protected=args.include_protected,
        max_results=args.max_results,
        repo_root=repo_root,
        use_ast=not args.no_ast,
    )

    # Format output
    if args.fmt == "json":
        output_str = format_json(summary)
    else:
        output_str = format_text(summary)

    # Print to stdout
    print(output_str, end="")

    # Write to file if requested
    if args.output is not None:
        out_path = repo_root / args.output.replace("/", os.sep)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_str, encoding="utf-8")

    # Exit code logic
    if args.include_protected and args.fail_on_protected and summary["protected_boundary_attention"]:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
