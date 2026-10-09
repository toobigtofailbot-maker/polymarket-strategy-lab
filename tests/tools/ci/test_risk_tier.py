"""Compact behavioral positive/negative matrix for S10-CI-OPT-02."""
import copy
import importlib.util
import json
import os
import pathlib
import subprocess
import re
import textwrap

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
MODULE = ROOT / "tools/ci/risk_tier.py"
loader = importlib.util.spec_from_file_location("ci_risk_tier", MODULE)
r = importlib.util.module_from_spec(loader)
loader.loader.exec_module(r)
BASE, HEAD = "a" * 40, "b" * 40


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).decode().strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "ci-fixture@example.invalid")
    git(tmp_path, "config", "user.name", "CI Fixture")
    git(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / "README.md").write_text("base\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def change(repo, files, routing="true"):
    base = git(repo, "rev-parse", "HEAD")
    if any(p.startswith(("src/", "tools/deployment/")) for p in files) and not any(p.startswith("docs/wp_specs/") for p in files):
        wp = "S10-FIXTURE-01"
        prefix = f"docs/wp_specs/{wp}/"
        artifacts = {prefix + "wp_prompt.txt", prefix + "wp_spec.json", f"docs/status_entries/{wp}.md"}
        authority = dict.fromkeys(r.AUTHORITY, False)
        authority.update(source_runtime=True, docs=True, tests=True, local_offline_tooling=True,
                         canonical_evidence_policy=True, workflow_files=True, network=True,
                         hermes_runtime=True, scheduler=True)
        authority["dependencies"] = any(pathlib.PurePosixPath(p).name in r.DEPENDENCIES for p in files)
        spec = {"schema_id": "polymarket-work-package-spec", "schema_version": "1.0.0",
                "identity": {"wp_id": wp, "risk_level": 3}, "authority": authority,
                "scope": {"required_changed_files": sorted(set(files) | artifacts),
                          "allowed_changed_files": sorted(set(files) | artifacts),
                          "exact_scope_required": True, "max_changed_files": len(files) + 3}}
        files = {**files, prefix + "wp_spec.json": json.dumps(spec),
                 prefix + "wp_prompt.txt": "BEGIN_GOVERNANCE_AUTHORITY_V1\nrisk_level: 3\n" +
                 "".join(f"{k}: {str(authority[k]).lower()}\n" for k in r.AUTHORITY) + "END_GOVERNANCE_AUTHORITY_V1\n",
                 f"docs/status_entries/{wp}.md": "Research only\n"}
    for path, content in files.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, newline="\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "candidate")
    head = git(repo, "rev-parse", "HEAD")
    return r.classify(repo, base, head, routing)


def test_risk_tier_safe_docs_and_isolated_stdlib(repo):
    plan = change(repo, {"docs/user_notes.md": "plain guide\n"})
    assert plan["tier"] == 1
    assert plan["compatibility_matrix"]["include"] == [{"os": "ubuntu-24.04", "python": "3.12", "smoke": True}]
    plan = change(repo, {"tools/text/spacing.py": "def trim(x):\n    return x.strip()\n",
                         "tests/tools/text/test_spacing.py": "from tools.text.spacing import trim\ndef test_trim():\n    assert trim(' x ') == 'x'\n"})
    assert plan["tier"] == 1
    assert not plan["run_dependency_audit"] and not plan["run_ndfd"] and not plan["run_frontend"]


@pytest.mark.parametrize("unsafe", ["eval", "exec", "open", "getattr", "vars"])
def test_isolated_helper_rejects_dynamic_or_io_aliases(repo, unsafe):
    helper = "tools/text/number.py"
    test = "tests/tools/text/test_number.py"
    plan = change(repo, {helper: f"execute = {unsafe}\ndef calculate(value):\n    return execute(value)\n",
                         test: "from tools.text.number import calculate\ndef test_calculate():\n    assert calculate('2+2') == 4\n"})
    assert plan["tier"] == 3 and plan["reason_codes"] == ["UNKNOWN"]


def test_isolated_helper_rejects_dynamic_matching_test(repo):
    plan = change(repo, {"tools/text/spacing.py": "def trim(value):\n    return value.strip()\n",
                         "tests/tools/text/test_spacing.py": "from tools.text.spacing import trim\nexecute = eval\ndef test_trim():\n    assert trim(execute(\"' x '\")) == 'x'\n"})
    assert plan["tier"] == 3


@pytest.mark.parametrize("path", [
    "src/data_layer/wallet_intelligence/public_ingest.py",
    "src/research_runtime/hermes_controlled_runtime/runner.py",
    "src/data_layer/analytical_research/alpha_factory.py",
    "src/research_runtime/alpha_campaign/scheduler.py",
    "src/operator_cockpit.py", "src/operator_cockpit_research.py",
    "src/operator_cockpit_frontend/src/app.tsx", "tools/deployment/telemetry.py",
])
def test_risk_tier_runtime_research_stays_tier_two(repo, path):
    plan = change(repo, {path: "# noncritical research change\n"})
    assert plan["tier"] == 2
    assert plan["run_dependency_audit"] and not plan["run_ndfd"]
    assert plan["run_frontend"] == path.startswith("src/operator_cockpit_frontend/")
    assert plan["compatibility_matrix"]["include"] == [{"os": "ubuntu-24.04", "python": "3.12", "smoke": False}]


@pytest.mark.parametrize("path", [
    "src/execution_gateway/gateway.py", "src/risk_engine/caps.py", "src/paper_trading/accounting.py",
    "src/operator_cockpit_commands.py", "src/auth.py", "src/signing.py", "tools/deployment/firewall.py",
    ".github/workflows/ci.yml", "tools/ci/risk_tier.py", "tools/wp/wp_spec_guard.py",
    "pyproject.toml", "src/operator_cockpit_frontend/package-lock.json", "docs/security_policy.md",
    "tests/test_authority_validator.py", "src/data_layer/native_adapter.py",
    "src/research_runtime/nautilus_offline/replay.py",
    "tests/research_runtime/nautilus_offline/test_replay.py",
    "src/data_layer/analytical_research/nws_ndfd_history.py",
    "tests/data_layer/analytical_research/test_ndfd_grib_dependency_compatibility.py",
])
def test_risk_tier_protected_boundaries_force_tier_three(repo, path):
    assert change(repo, {path: "# change\n"})["tier"] == 3


@pytest.mark.parametrize("routing", ["", "false", "TRUE", "malformed"])
def test_risk_tier_base_trust_and_first_bootstrap(repo, routing):
    plan = change(repo, {"tools/ci/risk_tier.py": "raise RuntimeError('head must never run')\n"}, routing)
    assert plan["tier"] == 3 and len(plan["compatibility_matrix"]["include"]) == 4
    assert plan["run_dependency_audit"] and plan["run_ndfd"] and plan["run_frontend"]
    assert plan["reason_codes"] == ["DEFAULT_OFF"]
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert 'git show "$BASE_SHA:tools/ci/risk_tier.py"' in workflow
    assert 'python "$RUNNER_TEMP/base_risk_tier.py"' in workflow
    assert 'python tools/ci/risk_tier.py' not in workflow


@pytest.mark.parametrize("raw", [b"", b"M\0docs/a.md", b"Z\0docs/a.md\0", b"R100\0docs/a.md\0",
    b"M\0../escape\0", b"A\0/a\0", b"M\0a\\b\0", b"M\0a\0M\0a\0", b"M\0\xff\0"])
def test_risk_tier_bad_diff_and_metadata_fail_closed(raw):
    with pytest.raises((r.InvalidPlan, UnicodeError)):
        r.provenance(raw)
    assert r.provenance(b"R100\0src/execution_gateway/gateway.py\0docs/note.md\0")[0][1][0].startswith("src/")


def test_rename_copy_delete_and_symlink_provenance(repo):
    plan = change(repo, {"src/execution_gateway/gateway.py": "sensitive original\n"})
    base = git(repo, "rev-parse", "HEAD")
    (repo / "docs").mkdir(exist_ok=True)
    git(repo, "mv", "src/execution_gateway/gateway.py", "docs/note.md")
    git(repo, "commit", "-qm", "rename")
    assert r.classify(repo, base, git(repo, "rev-parse", "HEAD"), "true")["tier"] == 3
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "rm", "docs/note.md")
    git(repo, "commit", "-qm", "delete")
    assert r.classify(repo, base, git(repo, "rev-parse", "HEAD"), "true")["tier"] != 1
    base = git(repo, "rev-parse", "HEAD")
    # Use the Git index to model a symlink even on Windows without symlink privileges.
    oid = subprocess.check_output(["git", "-C", str(repo), "hash-object", "-w", "--stdin"], input=b"README.md").decode().strip()
    git(repo, "update-index", "--add", "--cacheinfo", "120000," + oid + ",docs/link")
    git(repo, "commit", "-qm", "symlink")
    with pytest.raises(r.InvalidPlan):
        r.classify(repo, base, git(repo, "rev-parse", "HEAD"), "true")


def test_missing_or_contradictory_package_never_downgrades(repo):
    with pytest.raises(r.InvalidPlan):
        change(repo, {"docs/status_entries/S10-FAKE-01.md": "Risk 0\n"})
    with pytest.raises(r.InvalidPlan):
        change(repo, {"docs/wp_specs/S10-FAKE-01/wp_spec.json": '{"authority": {"live": false}}'})
    with pytest.raises(r.InvalidPlan):
        r.validate_refs(repo, "main", HEAD)
    with pytest.raises(r.InvalidPlan):
        r.strict_json('{"tier":1,"tier":3}')


def needs_for(plan):
    required = {"classify": True, "compatibility": True,
                "dependency-audit": plan["run_dependency_audit"], "ndfd-grib-compat": plan["run_ndfd"],
                "ndfd-grib-dependency-audit": plan["run_ndfd"], "cockpit-frontend": plan["run_frontend"]}
    needs = {name: {"result": "success" if required else "skipped"} for name, required in required.items()}
    needs["classify"]["outputs"] = {"plan": json.dumps(plan), "matrix": json.dumps(plan["compatibility_matrix"]),
        **{k: str(plan[k]).lower() for k in ("run_dependency_audit", "run_ndfd", "run_frontend")}}
    return needs


def test_ci_tier_plan_and_final_gate_fail_closed():
    for tier in (1, 2, 3):
        reason = "BENIGN" if tier == 1 else "RESEARCH" if tier == 2 else "PROTECTED"
        plan = r.canonical_plan(tier, BASE, HEAD, reason)
        needs = needs_for(plan)
        assert r.final_gate(plan, needs, BASE, HEAD, "true", plan) is None
        for job in needs:
            if needs[job]["result"] != "success":
                continue
            for outcome in ("failure", "cancelled", "skipped", "unknown", None):
                bad = copy.deepcopy(needs)
                bad[job]["result"] = outcome
                with pytest.raises(r.InvalidPlan):
                    r.final_gate(plan, bad, BASE, HEAD, "true", plan)
        for mutate in (lambda p: p.update(head=BASE), lambda p: p.update(tier=True),
                       lambda p: p.update(run_ndfd="false"),
                       lambda p: p.update(compatibility_matrix={"include": []}),
                       lambda p: p.update(run_dependency_audit=False)):
            bad = copy.deepcopy(plan)
            mutate(bad)
            if bad == plan:
                continue
            with pytest.raises(r.InvalidPlan):
                r.final_gate(bad, needs, BASE, HEAD, "true", plan)


@pytest.mark.parametrize("key", ["plan", "matrix", "run_dependency_audit", "run_ndfd", "run_frontend"])
def test_final_gate_rejects_missing_classifier_outputs(key):
    plan = r.canonical_plan(3, BASE, HEAD, "DEFAULT_OFF")
    needs = needs_for(plan)
    del needs["classify"]["outputs"][key]
    with pytest.raises((r.InvalidPlan, ValueError)):
        r.final_gate(plan, needs, BASE, HEAD, "false", plan)


@pytest.mark.parametrize("key", ["plan", "matrix"])
def test_final_gate_rejects_integer_alias_for_boolean_output(key):
    plan = r.canonical_plan(3, BASE, HEAD, "DEFAULT_OFF")
    needs = needs_for(plan)
    output = json.loads(needs["classify"]["outputs"][key])
    matrix = output["compatibility_matrix"] if key == "plan" else output
    matrix["include"][0]["smoke"] = 0
    needs["classify"]["outputs"][key] = json.dumps(output)
    with pytest.raises(r.InvalidPlan):
        r.final_gate(plan, needs, BASE, HEAD, "false", plan)


def test_default_off_cannot_be_downgraded():
    with pytest.raises(r.InvalidPlan):
        r.validate_plan(r.canonical_plan(1, BASE, HEAD, "BENIGN"), BASE, HEAD, "false")
    with pytest.raises(r.InvalidPlan):
        r.validate_plan(r.canonical_plan(3, BASE, HEAD, "DEFAULT_OFF"), BASE, HEAD, "true")


def test_cli_closed_failure_and_no_untrusted_echo(repo):
    proc = subprocess.run([os.sys.executable, str(MODULE), "--repo-root", str(repo),
                           "--base", "not-a-ref", "--head", HEAD], capture_output=True, text=True)
    assert proc.returncode == 1 and proc.stderr.strip() == "CI_PLAN_INVALID"
    assert "not-a-ref" not in proc.stdout + proc.stderr


def test_real_default_off_workflow_gate_negative_matrix(tmp_path):
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    scripts = re.findall(r"          python - <<'PY'\n(.*?)          PY", workflow, re.S)
    assert len(scripts) == 4
    for source in scripts:
        compile(textwrap.dedent(source), "workflow", "exec")
    plan = r.canonical_plan(3, BASE, HEAD, "DEFAULT_OFF")
    needs = needs_for(plan)
    env = {**os.environ, "RUNNER_TEMP": str(tmp_path), "BASE_SHA": BASE, "HEAD_SHA": HEAD}
    def run(candidate, outcomes):
        (tmp_path / "plan.json").write_text(json.dumps(candidate))
        (tmp_path / "needs.json").write_text(json.dumps(outcomes))
        return subprocess.run([os.sys.executable, "-"], input=textwrap.dedent(scripts[-1]),
                              env=env, capture_output=True, text=True).returncode
    assert run(plan, needs) == 0
    for job in needs:
        for outcome in ("failure", "cancelled", "skipped", "unknown"):
            bad = copy.deepcopy(needs)
            bad[job]["result"] = outcome
            assert run(plan, bad) != 0
    for field, value in (("head", BASE), ("tier", True), ("run_ndfd", 1),
                         ("compatibility_matrix", {"include": []})):
        bad = {**plan, field: value}
        assert run(bad, needs) != 0


def test_actual_sensitive_diff_cannot_hide_under_research_name(repo):
    plan = change(repo, {"src/operator_cockpit.py": "command_auth = authenticate(request)\n"})
    assert plan["tier"] == 3


def test_ungoverned_runtime_cannot_claim_tier_two(repo):
    base = git(repo, "rev-parse", "HEAD")
    path = repo / "src/data_layer/research_notes.py"
    path.parent.mkdir(parents=True)
    path.write_text("# research\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "missing package")
    assert r.classify(repo, base, git(repo, "rev-parse", "HEAD"), "true")["tier"] == 3
