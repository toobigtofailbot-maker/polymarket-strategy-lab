"""Exact package certificate and native owner-account denial tests."""
from dataclasses import replace
from pathlib import Path
import subprocess

from src.live_pilot import autonomous_cycle as A
from tests.live_pilot.test_autonomous_cycle import harness, policy, save
from tests.tools.alpha.test_near_term_market_screener import NOW


def test_protected_activation_chain():
    root = Path(__file__).resolve().parents[2]
    package = root/'docs/wp_specs/S10-HERMES-LIVE-INTEGRATED-01'
    command = ['python', '-B', str(root/'tools/wp/wp_readiness_gate.py'), '--wp', str(package/'wp_prompt.txt'),
        '--spec', str(package/'wp_spec.json'), '--certificate', str(package/'draftability_certificate.json'),
        '--repo-root', str(root), '--format', 'json']
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0 and '"certificate_hash_bound":true' in result.stdout


def test_secure_account_access_and_wallet_binding(tmp_path, monkeypatch):
    s = harness(tmp_path, monkeypatch)
    s.policy['public_wallet'] = '0x'+'f'*40
    save(s.path, s.policy)
    result = A.run(**s.args)
    assert result['code'] == 'OWNER_SETUP_REQUIRED' and not s.calls
    assert s.native.harness.secret_requests == 0 and not s.native.harness.venue.posts


def test_first_live_canary_activation_fails_closed(tmp_path):
    p = policy(tmp_path, mode='LIVE')
    path = save(tmp_path/'auto.json', p)
    deps = A.AutonomousDependencies(native=replace(A.native.LiveOrchDependencies(), clock_ns=lambda: NOW))
    result = A.run(policy_path=path, dependencies=deps)
    assert result['code'] == 'OWNER_SETUP_REQUIRED' and not result['live_active']
    assert not (tmp_path/'state').exists()
    source = Path(A.__file__).read_text()
    assert '.canary(' not in source and '.exit_sell(' not in source and '.cancel(' not in source


def test_consolidated_owner_handoff():
    report = A.activation_report(software_verified=True)
    assert report['blockers'] == ['CALIBRATION_NOT_VERIFIED', 'OWNER_SETUP_REQUIRED', 'CANARY_APPROVAL_MISSING']
    assert 'private' not in str(report) and report['orders'] == 0
