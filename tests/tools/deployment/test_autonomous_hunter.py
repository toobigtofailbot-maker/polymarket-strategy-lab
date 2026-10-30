"""No-service CLI refusal and safe output."""
import json

from tools.deployment import run_autonomous_hunter as cli


def test_no_implicit_activation_or_argument_echo(capsys):
    assert cli.main(['--unknown-secret-value']) == 1
    result = json.loads(capsys.readouterr().out)
    assert result == {'status': 'REFUSED', 'code': 'INPUT_INVALID', 'live_active': False}


def test_report_does_not_claim_software_or_account_ready(capsys):
    assert cli.main(['--report']) == 1
    result = json.loads(capsys.readouterr().out)
    assert result['disposition'] == 'IMPLEMENTATION_BLOCKED'
    assert result['orders'] == 0 and not result['live_active']


def test_supervised_bounded_session_authority(capsys):
    assert cli.main(['--report']) == 1
    report = json.loads(capsys.readouterr().out)
    assert report['disposition'] == 'IMPLEMENTATION_BLOCKED' and not report['live_active']
    assert report['orders'] == 0
