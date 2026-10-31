"""Offline boundary tests. Fixture forecasts are never original historical evidence."""
from datetime import datetime, timezone
from email.utils import format_datetime
import json

import pytest

from tools.alpha import run_edge_evidence_capture as C
from tests.tools.alpha import test_alpha_hunter as T


def execute(tmp_path, *, data=None, transport=None):
    payload = T.payloads() if data is None else data
    calls = []
    def fetch(url, timeout, maximum):
        calls.append((url, timeout, maximum))
        value = payload.get(url)
        return ('HTTP_2XX', C.H.canonical(value),
                format_datetime(datetime.fromtimestamp(T.NOW//10**9, timezone.utc)), 200) if value is not None else (
                    'HTTP_4XX', None, None, 404)
    root = tmp_path/'edge-capture'
    result = C.run(root, transport=transport or fetch, clock_ns=T.clock())
    return root, result, calls


def test_bounded_public_capture_and_replay(tmp_path):
    root, result, calls = execute(tmp_path)
    assert result['status'] == 'REPLAY_VERIFIED', result
    assert 0 < len(calls) <= 40 and all(t <= 10 and n <= 2*1024*1024 for _, t, n in calls)
    assert not any('espn' in url for url, _, _ in calls)
    assert result['pre_event_forecasts'] == result['unresolved_groups'] == 1
    assert result['verified_settled_groups'] == result['n_holdout'] == result['n_bucket'] == 0
    assert not result['production_eligible'] and result['source_counts']['ESPN'] == 0
    from src.live_pilot.provenance import verify_capture
    assert verify_capture(root) == result
    assert C.run(root)['status'] == 'REFUSED'  # Same scratch never starts another attempt.
    assert not (root/'op-000002').exists()


def test_transport_endpoints_caps_clocks_and_no_retry(tmp_path):
    op = tmp_path/'op'; op.mkdir()
    calls = []
    def failed(url, timeout, maximum):
        calls.append(url)
        return 'HTTP_4XX', None, None, 404
    f = C.Fetcher(op, clock_ns=T.clock(), transport=failed)
    url = C.H.rain_event_url(datetime.fromtimestamp(T.NOW//10**9, timezone.utc).date()+C.timedelta(days=1))
    assert f.get(url) is None and calls == [url]
    for bad in ('https://example.org/', C.H.S.DISCOVERY_URL, C.H.S.ESPN+'scoreboard?dates=20261027',
                'https://api.weather.gov@evil.invalid/stations/KNYC', 'http://api.weather.gov/stations/KNYC'):
        with pytest.raises(C.H.Stop):
            f.get(bad)
    assert calls == [url]
    # A refused endpoint permanently closes this fetcher; it cannot resume later.
    with pytest.raises(C.H.Stop):
        f.get(url)
    assert calls == [url]
    cap = tmp_path/'cap'; cap.mkdir()
    f = C.Fetcher(cap, clock_ns=T.clock(), transport=failed)
    f.receipts = [None]*40
    with pytest.raises(C.H.Stop, match='BUDGET_EXHAUSTED'):
        f.get(url)
    assert calls == [url]
    other = tmp_path/'clock'; other.mkdir()
    g = C.Fetcher(other, clock_ns=iter((T.NOW, T.NOW-1)).__next__, transport=failed)
    with pytest.raises(C.H.Stop, match='CLOCK_REFUSED'):
        g.get(url)
    assert calls == [url]


@pytest.mark.parametrize('status', ['TIMEOUT', 'OVERSIZE', 'HTTP_5XX'])
def test_unavailable_transport_preserves_denominator(tmp_path, status):
    root, result, _ = execute(tmp_path, transport=lambda *args: (status, None, None, None))
    assert result['status'] == 'REPLAY_VERIFIED' and result['pre_event_forecasts'] == 0
    assert result['source_counts'] == dict(GAMMA=0, ESPN=0, CLOB=0, NWS=0)
    assert len(list((root/'op-000001').glob('receipt-*.json'))) == 2
    assert not list((root/'op-000001').glob('source-*.json'))


def test_secret_like_public_body_is_not_persisted_or_echoed(tmp_path):
    sentinel = b'{"access_token":"synthetic-do-not-retain"}'
    root, result, _ = execute(tmp_path, transport=lambda *args: ('HTTP_2XX', sentinel, None, 200))
    assert result['pre_event_forecasts'] == 0 and b'synthetic-do-not-retain' not in C.H.canonical(result)
    assert not list(root.rglob('source-*.json'))


def test_capture_parser_does_not_echo_invalid_argument(capsys):
    assert C.main(['untrusted-argument-sentinel']) == 1
    out = capsys.readouterr()
    assert 'untrusted-argument-sentinel' not in out.out+out.err
    assert json.loads(out.out)['status'] == 'REFUSED'


def test_kill_latch_precedes_next_source_and_cannot_rearm(tmp_path):
    calls = []
    root = tmp_path/'edge-capture'
    def transport(*args):
        calls.append(args[0])
        (root/'capture-killed.json').write_text('{}')
        return 'HTTP_2XX', b'{"markets":[]}', None, 200
    result = C.run(root, transport=transport, clock_ns=T.clock())
    assert len(calls) == 1 and result['status'] == 'REFUSED'
    assert C.run(root, transport=transport)['status'] == 'REFUSED' and len(calls) == 1


def test_observed_kill_latches_even_if_marker_is_removed(tmp_path):
    op = tmp_path/'op'; op.mkdir()
    marker = tmp_path/'capture-killed.json'; marker.write_text('{}')
    calls = []
    f = C.Fetcher(op, clock_ns=T.clock(), transport=lambda *args: calls.append(args))
    url = C.H.NWS+'stations/KNYC'
    with pytest.raises(C.H.Stop, match='KILLED'):
        f.get(url)
    marker.unlink()
    with pytest.raises(C.H.Stop, match='KILLED'):
        f.get(url)
    assert not calls


@pytest.mark.parametrize('status,http', [('HTTP_4XX', 401), ('HTTP_4XX', 403),
                                       ('HTTP_4XX', 451), ('REDIRECT_REFUSED', None)])
def test_access_refusal_ends_entire_capture(tmp_path, status, http):
    calls = []
    def transport(url, *args):
        calls.append(url)
        return status, None, None, http
    root, result, _ = execute(tmp_path, transport=transport)
    assert len(calls) == 1 and result['status'] == 'REFUSED'
    assert result['observed_rows'] is None and result['accepted_production_methods'] == 0
    assert len(list((root/'op-000001').glob('transport-*.json'))) == 1


def test_real_http_reader_refuses_truncated_and_oversize_bodies(monkeypatch):
    import http.client
    import io
    class Socket:
        def __init__(self, raw):
            self.raw = raw
        def makefile(self, *args):
            return io.BytesIO(self.raw)
    class Opener:
        def __init__(self, response):
            self.response = response
        def open(self, *args, **kwargs):
            return self.response
    for length, body, expected in ((20, b'{}', 'TRANSPORT_UNAVAILABLE'),
                                    (200, b'{}', 'OVERSIZE'), (2, b'{}', 'HTTP_2XX')):
        response = http.client.HTTPResponse(Socket(b'HTTP/1.1 200 OK\r\nContent-Length: '+str(length).encode()+b'\r\n\r\n'+body))
        response.begin()
        monkeypatch.setattr(C.urllib.request, 'build_opener', lambda *args: Opener(response))
        result = C.public_read('https://api.weather.gov/stations/KNYC', 10, 100)
        assert result[0] == expected
        assert result[1] == (body if expected == 'HTTP_2XX' else None)
