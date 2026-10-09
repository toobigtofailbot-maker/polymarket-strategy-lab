"""Base-owned, stdlib-only CI planning. No product imports or network access.

Run this file from the verified base tree, never import helpers from a PR head.
Unknown provenance or authority rejects classification; unknown impact selects
the full compatibility tier. Local evidence and independent review remain required.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys

MAX_BYTES = 4 * 1024 * 1024
MAX_PATHS = 2048
SHA = re.compile(r"[0-9a-f]{40}")
AUTHORITY = (
    "workflow_governance", "local_offline_tooling", "canonical_evidence_policy",
    "docs", "tests", "source_runtime", "workflow_files", "dependencies", "network",
    "credentials", "scheduler", "hermes_runtime", "strategy", "paper", "execution", "live",
)
LEGACY_JOBS = ("compatibility", "dependency-audit", "ndfd-grib-compat",
               "ndfd-grib-dependency-audit", "cockpit-frontend")
DEPENDENCIES = {"pyproject.toml", "requirements.txt", "requirements-dev.txt", "package.json",
                "package-lock.json", "uv.lock", "poetry.lock", "Pipfile.lock", "pdm.lock",
                "Cargo.toml", "Cargo.lock"}
CRITICAL = (
    ".github/", "tools/ci/", "tools/wp/", "tools/git/", "tools/security/",
    "src/execution_gateway/", "src/risk_engine/", "src/paper_trading/",
    "src/strategy_lifecycle/", "src/execution_feasibility/", "src/exploratory_gate_c/",
    "src/research_runtime/executable_edge/", "src/operator_cockpit_commands.py",
    "src/research_runtime/nautilus_offline/", "tests/research_runtime/nautilus_offline/",
    "src/data_layer/analytical_research/nws_ndfd_history.py",
    "tests/data_layer/analytical_research/test_nws_ndfd",
    "tests/data_layer/analytical_research/test_ndfd_grib",
    "config/", "credentials/", "secrets/", "agent_runtime/", "agent_memory/",
    "docs/ai/", "AGENTS.md", "AI_CODING_AGENT_START_HERE.md", "CODEX_START_HERE.md",
    "CLAUDE_START_HERE.md", "docs/live_trading_authorization.md", "docs/security_",
    "docs/deferred_items_log.md", "tests/tools/ci/", "tests/tools/wp/", "tests/tools/git/",
    "tests/tools/security/", "tests/test_codex_workflow_docs.py",
    "tests/test_architecture_boundaries.py",
)
SENSITIVE = re.compile(r"(?:^|[/_.-])(auth|credential|secret|signing|signer|order|orders|cancel|oms|"
                       r"risk|capital|economic|live|kill|safe_mode|gate_c|privilege|ingress|firewall|"
                       r"reconciliation|validator|guard|scorer|parser|native|abi|pins)(?:$|[/_.-])", re.I)
PRIVILEGED_DIFF = re.compile(
    r"\b(?:getpass|load_dotenv|Authorization|command_auth|authenticate|create_order|cancel_order|"
    r"sign_order|private_key|mnemonic|CAP_NET_ADMIN|sudo|systemctl|ufw|iptables|setuid|"
    r"GATE_C|LIVE_ENABLED|risk_cap|kill_switch|economic_reconciliation)\b", re.I)
PUBLIC_RECONCILIATION = {
    "src/data_layer/wallet_intelligence/reconciliation.py",
    "src/research_runtime/hermes_controlled_runtime/context_reconciliation.py",
}
RESEARCH = ("src/data_layer/", "src/research_runtime/", "src/operator_cockpit",
            "src/monitoring/", "src/strategy_modules/", "tools/deployment/",
            "tools/hermes/", "tools/qualification/", "tools/research/", "tools/alpha/",
            "tools/wallet/", "tests/data_layer/", "tests/research_runtime/",
            "tests/deployment/", "src/operator_cockpit_frontend/")


class InvalidPlan(ValueError):
    """Closed failure; never echo untrusted input."""


def strict_json(raw: bytes | str):
    if len(raw) > MAX_BYTES:
        raise InvalidPlan()
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InvalidPlan()
            result[key] = value
        return result
    def constant(_):
        raise InvalidPlan()
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def git(repo: pathlib.Path, *args: str) -> bytes:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=60)
    if proc.returncode or len(proc.stdout) > MAX_BYTES:
        raise InvalidPlan()
    return proc.stdout


def safe_path(value: str) -> str:
    if (not value or len(value) > 512 or value.startswith(("/", "-")) or
            any(c in value for c in "\\:\n\r\x00") or any(ord(c) < 32 for c in value) or
            any(part in {"", ".", ".."} for part in value.split("/"))):
        raise InvalidPlan()
    return value


def provenance(raw: bytes) -> list[tuple[str, tuple[str, ...]]]:
    if not raw or len(raw) > MAX_BYTES or not raw.endswith(b"\0"):
        raise InvalidPlan()
    parts = raw[:-1].decode("utf-8", errors="strict").split("\0")
    changes = []
    i = 0
    destinations = set()
    while i < len(parts):
        status = parts[i]
        if not re.fullmatch(r"[AMDT]|[RC](?:100|[0-9]{1,2})", status):
            raise InvalidPlan()
        count = 2 if status[0] in "RC" else 1
        if i + count >= len(parts):
            raise InvalidPlan()
        paths = tuple(safe_path(p) for p in parts[i + 1:i + 1 + count])
        if paths[-1] in destinations:
            raise InvalidPlan()
        destinations.add(paths[-1])
        changes.append((status[0], paths))
        i += count + 1
    if len(changes) > MAX_PATHS:
        raise InvalidPlan()
    return changes


def blob(repo: pathlib.Path, ref: str, path: str) -> bytes:
    rows = git(repo, "ls-tree", "-z", ref, "--", safe_path(path)).split(b"\0")
    if len(rows) != 2 or not rows[0].startswith((b"100644 blob ", b"100755 blob ")):
        raise InvalidPlan()
    return git(repo, "show", ref + ":" + path)


def validate_refs(repo: pathlib.Path, base: str, head: str) -> None:
    if not SHA.fullmatch(base) or not SHA.fullmatch(head) or base == head:
        raise InvalidPlan()
    for ref in (base, head):
        if git(repo, "rev-parse", "--verify", ref + "^{commit}").decode().strip() != ref:
            raise InvalidPlan()
    git(repo, "merge-base", "--is-ancestor", base, head)


def canonical_plan(tier: int, base: str, head: str, reason: str, frontend: bool = False) -> dict:
    if type(tier) is not int or tier not in (1, 2, 3) or not SHA.fullmatch(base) or not SHA.fullmatch(head):
        raise InvalidPlan()
    matrix = [{"os": os, "python": py, "smoke": tier == 1}
              for os in (["ubuntu-24.04", "windows-2022"] if tier == 3 else ["ubuntu-24.04"])
              for py in (["3.12", "3.14"] if tier == 3 else ["3.12"])]
    return {"tier": tier, "reason_codes": [reason], "base": base, "head": head,
            "compatibility_matrix": {"include": matrix}, "run_dependency_audit": tier >= 2,
            "run_ndfd": tier == 3, "run_frontend": tier == 3 or (tier == 2 and frontend)}


def validate_plan(plan: dict, base: str, head: str, routing: str) -> None:
    reasons = {"DEFAULT_OFF", "BOOTSTRAP", "BENIGN", "RESEARCH", "PROTECTED", "UNKNOWN"}
    if not isinstance(plan, dict) or plan.get("reason_codes") not in [[r] for r in reasons]:
        raise InvalidPlan()
    tier = plan.get("tier")
    frontend = plan.get("run_frontend")
    if type(frontend) is not bool or type(tier) is not int:
        raise InvalidPlan()
    expected = canonical_plan(tier, base, head, plan["reason_codes"][0], frontend)
    if json.dumps(plan, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False) or any(type(plan[k]) is not bool for k in
                               ("run_dependency_audit", "run_ndfd", "run_frontend")):
        raise InvalidPlan()
    if routing != "true" and (tier != 3 or plan["reason_codes"] != ["DEFAULT_OFF"]):
        raise InvalidPlan()
    if routing == "true" and plan["reason_codes"] in (["DEFAULT_OFF"], ["BOOTSTRAP"]):
        raise InvalidPlan()
    if ((tier == 1 and plan["reason_codes"] != ["BENIGN"]) or
        (tier == 2 and plan["reason_codes"] != ["RESEARCH"]) or
        (tier == 3 and plan["reason_codes"] == ["BENIGN"])):
        raise InvalidPlan()


def verify_packages(repo: pathlib.Path, base: str, head: str, changes) -> tuple[bool, bool]:
    paths = {p for _, ps in changes for p in ps}
    specs = {p for p in paths if re.fullmatch(r"docs/wp_specs/[A-Z0-9-]+/wp_spec.json", p)}
    # A new governed WP must supply its spec, prompt and status; metadata never grants a cheap tier.
    for path in paths:
        match = re.fullmatch(r"docs/(?:wp_specs/([^/]+)/[^/]+|status_entries/([^/]+)\.md)", path)
        if match:
            wp = match.group(1) or match.group(2)
            specs.add(f"docs/wp_specs/{wp}/wp_spec.json")
    protected_authority = False
    if len(specs) > 1:
        raise InvalidPlan()
    for path in sorted(specs):
        doc = strict_json(blob(repo, head, path))
        if (doc.get("schema_id") != "polymarket-work-package-spec" or
            doc.get("schema_version") != "1.0.0" or set(doc.get("authority", {})) != set(AUTHORITY) or
            any(type(doc["authority"][k]) is not bool for k in AUTHORITY)):
            raise InvalidPlan()
        identity = doc.get("identity", {})
        risk = identity.get("risk_level")
        wp = path.split("/")[2]
        if identity.get("wp_id") != wp or type(risk) is not int or not 0 <= risk <= 4:
            raise InvalidPlan()
        protected_authority |= any(doc["authority"][k] for k in ("credentials", "execution", "live", "dependencies"))
        scope = doc.get("scope", {})
        allowed = scope.get("allowed_changed_files", [])
        required = scope.get("required_changed_files", [])
        if (not required or not isinstance(allowed, list) or not isinstance(required, list) or
            len(set(allowed)) != len(allowed) or not set(required) <= set(allowed) or
            any(safe_path(p) != p for p in allowed)):
            raise InvalidPlan()
        destinations = {ps[-1] for _, ps in changes}
        if (scope.get("exact_scope_required") is not True or set(required) != set(allowed) or
            destinations != set(required) or type(scope.get("max_changed_files")) is not int or
            len(destinations) > scope["max_changed_files"]):
            raise InvalidPlan()
        prompt = blob(repo, head, f"docs/wp_specs/{wp}/wp_prompt.txt").decode("utf-8")
        blocks = re.findall(r"BEGIN_GOVERNANCE_AUTHORITY_V1\n(.*?)END_GOVERNANCE_AUTHORITY_V1", prompt, re.S)
        expected = "risk_level: " + str(risk) + "\n" + "".join(
            f"{k}: {str(doc['authority'][k]).lower()}\n" for k in AUTHORITY)
        if blocks != [expected]:
            raise InvalidPlan()
        for p in paths - {old for status, ps in changes if status == "C" for old in ps[:-1]}:
            if p not in allowed:
                raise InvalidPlan()
            needed = "source_runtime" if p.startswith("src/") else "tests" if p.startswith("tests/") else None
            if needed and not doc["authority"][needed]:
                raise InvalidPlan()
            if (p.startswith(".github/workflows/") and not doc["authority"]["workflow_files"] or
                pathlib.PurePosixPath(p).name in DEPENDENCIES and not doc["authority"]["dependencies"]):
                raise InvalidPlan()
        # A base-existing declaration cannot be weakened by the PR.
        existing = git(repo, "ls-tree", "-z", base, "--", path)
        if existing:
            prior = strict_json(blob(repo, base, path))
            if prior.get("authority") != doc["authority"]:
                raise InvalidPlan()
    return bool(specs), protected_authority


def benign_helper(repo: pathlib.Path, base: str, head: str, path: str, paths: set[str]) -> bool:
    """Positive proof for pure self-contained stdlib helpers, with a changed matching test.

    Deliberately narrow: no IO, subprocess, dynamic imports, product imports or sensitive names.
    Full local testing is an operator evidence obligation, never inferred from this function.
    """
    if not path.startswith("tools/") or not path.endswith(".py") or SENSITIVE.search(path):
        return False
    test = "tests/" + path.removesuffix(".py").rsplit("/", 1)[0] + "/test_" + path.rsplit("/", 1)[1]
    if test not in paths:
        return False
    test_tree = ast.parse(blob(repo, head, test))
    if not any(isinstance(n, ast.Assert) and not isinstance(n.test, ast.Constant) for n in ast.walk(test_tree)):
        return False
    helper_module = path.removesuffix(".py").replace("/", ".")
    for node in ast.walk(test_tree):
        if isinstance(node, ast.ImportFrom) and (node.level or node.module not in {helper_module, "pytest", "__future__"}):
            return False
        if isinstance(node, ast.Import) and any(a.name not in {helper_module, "pytest"} for a in node.names):
            return False
    for ref in (base, head):
        if not git(repo, "ls-tree", "-z", ref, "--", path):
            continue
        tree = ast.parse(blob(repo, ref, path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.With, ast.AsyncWith)):
                return False
            if isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in
                {"write", "read", "write_text", "read_text", "write_bytes", "read_bytes", "unlink", "mkdir", "system", "run"}):
                return False
            if isinstance(node, ast.Name) and node.id.startswith("__"):
                return False
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [node.module]
                if any(m not in {"math", "decimal", "fractions", "statistics", "re", "typing", "__future__"} for m in modules):
                    return False
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                if name in {"open", "exec", "eval", "compile", "__import__", "getattr", "setattr", "globals", "locals", "breakpoint", "input"}:
                    return False
    return True


def classify(repo: pathlib.Path, base: str, head: str, routing: str) -> dict:
    validate_refs(repo, base, head)
    changes = provenance(git(repo, "diff", "--name-status", "-z", "--find-renames=50%",
                             "--find-copies=50%", "--find-copies-harder", base, head, "--"))
    for status, paths in changes:
        for path in paths:
            for ref in (base, head):
                mode = git(repo, "ls-tree", "-z", ref, "--", path)
                if mode and not mode.startswith((b"100644 blob ", b"100755 blob ")):
                    raise InvalidPlan()
    governed, protected_authority = verify_packages(repo, base, head, changes)
    paths = {p for _, ps in changes for p in ps}
    if routing != "true":
        return canonical_plan(3, base, head, "DEFAULT_OFF")
    impact = git(repo, "diff", "--no-ext-diff", "--no-textconv", "--unified=0", base, head, "--",
                 "src/", "tools/deployment/", "tools/hermes/").decode("utf-8", errors="strict")
    changed_lines = "\n".join(line[1:] for line in impact.splitlines()
                             if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
    if protected_authority or PRIVILEGED_DIFF.search(changed_lines):
        return canonical_plan(3, base, head, "PROTECTED")
    if any(p.startswith(CRITICAL) or pathlib.PurePosixPath(p).name in DEPENDENCIES or
           (not p.startswith(("docs/status_entries/", "docs/wp_specs/")) and
            p not in PUBLIC_RECONCILIATION and SENSITIVE.search(p))
           for p in paths):
        return canonical_plan(3, base, head, "PROTECTED")
    benign = lambda p: (p in {"docs/project_status.md", "docs/repo_truth_index.md", "README.md"} or
                         p.startswith(("docs/status_entries/", "docs/wp_specs/")) or
                         (p.startswith("docs/") and not SENSITIVE.search(p)))
    helpers = {p for p in paths if benign_helper(repo, base, head, p, paths)}
    helper_tests = {"tests/" + p.removesuffix(".py").rsplit("/", 1)[0] + "/test_" + p.rsplit("/", 1)[1]
                    for p in helpers}
    if all(benign(p) or p in helpers | helper_tests for p in paths) and all(s not in {"D", "T"} for s, _ in changes):
        return canonical_plan(1, base, head, "BENIGN")
    if all(benign(p) or p.startswith(RESEARCH) for p in paths):
        if not governed:
            return canonical_plan(3, base, head, "UNKNOWN")
        return canonical_plan(2, base, head, "RESEARCH", any(p.startswith("src/operator_cockpit_frontend/") for p in paths))
    return canonical_plan(3, base, head, "UNKNOWN")


def final_gate(plan: dict, needs: dict, base: str, head: str, routing: str, actual_plan: dict) -> None:
    validate_plan(plan, base, head, routing)
    if plan != actual_plan or not isinstance(needs, dict) or set(needs) != {"classify", *LEGACY_JOBS}:
        raise InvalidPlan()
    required = {"classify": True, "compatibility": True,
                "dependency-audit": plan["run_dependency_audit"], "ndfd-grib-compat": plan["run_ndfd"],
                "ndfd-grib-dependency-audit": plan["run_ndfd"], "cockpit-frontend": plan["run_frontend"]}
    for name, must_run in required.items():
        if not isinstance(needs[name], dict) or needs[name].get("result") != ("success" if must_run else "skipped"):
            raise InvalidPlan()
    outputs = needs["classify"].get("outputs", {})
    if (strict_json(outputs.get("plan", "")) != plan or
        strict_json(outputs.get("matrix", "")) != plan["compatibility_matrix"] or
        any(outputs.get(k) != str(plan[k]).lower() for k in
            ("run_dependency_audit", "run_ndfd", "run_frontend"))):
        raise InvalidPlan()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--routing", default="false")
    parser.add_argument("--needs-file")
    parser.add_argument("--plan-file")
    args = parser.parse_args(argv)
    try:
        plan = classify(pathlib.Path(args.repo_root), args.base, args.head, args.routing)
        if args.needs_file:
            final_gate(strict_json(pathlib.Path(args.plan_file).read_bytes()),
                       strict_json(pathlib.Path(args.needs_file).read_bytes()),
                       args.base, args.head, args.routing, plan)
            print("CI_FINAL_GATE_PASS")
        else:
            print(json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False))
        return 0
    except (InvalidPlan, OSError, ValueError, TypeError, KeyError, RecursionError, subprocess.SubprocessError):
        print("CI_PLAN_INVALID", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
