import pytest
from fastapi.testclient import TestClient

from app.main import DASHBOARD_DIR, DASHBOARD_V2_DIR, app

client = TestClient(app)
pytestmark = [pytest.mark.integration, pytest.mark.critical]


def _expected_internal_redirect() -> str:
    if DASHBOARD_V2_DIR.exists():
        return '/internal/dashboard/'
    if DASHBOARD_DIR.exists():
        return '/internal/dashboard-legacy/'
    return '/docs'


def test_internal_root_redirects_to_active_surface():
    r = client.get('/internal', follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers['location'] == _expected_internal_redirect()


def test_dashboard_v2_shell_served_when_present():
    r = client.get('/internal/dashboard/')
    if DASHBOARD_V2_DIR.exists():
        assert r.status_code == 200
    else:
        assert r.status_code == 404


def test_dashboard_asset_served_when_present():
    r = client.get('/internal/dashboard/assets/app.js')
    if DASHBOARD_V2_DIR.exists():
        assert r.status_code == 200
        assert 'createRoot' in r.text
    else:
        assert r.status_code == 404


@pytest.mark.parametrize(
    ('path', 'target_hash'),
    [
        ('keys.html', '#/keys'),
        ('metrics.html', '#/metrics'),
        ('activity.html', '#/activity'),
        ('overview.html', '#/overview'),
        ('app.html', '#/overview'),
    ],
)
def test_dashboard_react_legacy_compat_entrypoints(path, target_hash):
    r = client.get(f'/internal/dashboard/{path}')
    if DASHBOARD_V2_DIR.exists():
        assert r.status_code == 200
        assert 'window.location.replace' in r.text
        assert target_hash in r.text
    else:
        assert r.status_code == 404


def test_dashboard_react_legacy_login_entrypoint_redirects_to_overview():
    r = client.get('/internal/dashboard/login.html')
    if DASHBOARD_V2_DIR.exists():
        assert r.status_code == 200
        assert 'window.location.replace' in r.text
        assert '#/overview' in r.text
    else:
        assert r.status_code == 404


def test_dashboard_legacy_login_shell_served_when_present():
    r = client.get('/internal/dashboard-legacy/login.html')
    if DASHBOARD_DIR.exists():
        assert r.status_code == 200
        assert 'Placeholder login gate' in r.text
    else:
        assert r.status_code == 404


def test_dashboard_legacy_keys_shell_served_when_present():
    r = client.get('/internal/dashboard-legacy/keys.html')
    if DASHBOARD_DIR.exists():
        assert r.status_code == 200
        assert 'API Key Management' in r.text
    else:
        assert r.status_code == 404


def test_dashboard_legacy_metrics_shell_served_when_present():
    r = client.get('/internal/dashboard-legacy/metrics.html')
    if DASHBOARD_DIR.exists():
        assert r.status_code == 200
        assert 'Usage & Metrics' in r.text
    else:
        assert r.status_code == 404


def test_dashboard_legacy_activity_shell_served_when_present():
    r = client.get('/internal/dashboard-legacy/activity.html')
    if DASHBOARD_DIR.exists():
        assert r.status_code == 200
        assert 'Recent Activity' in r.text
    else:
        assert r.status_code == 404


def test_dashboard_overview_placeholder_api_payload():
    r = client.get('/internal/api/overview')
    assert r.status_code == 200

    payload = r.json()
    assert payload['source'] == 'placeholder'
    assert payload['range'] == '24h'
    assert payload['requests24h'] > 0
    assert payload['requests'] == payload['requests24h']
    assert payload['fiveXx'] == payload['fiveXx24h']
    assert isinstance(payload['topEndpoints'], list)
    assert payload['topEndpoints'][0]['path'].startswith('/v1/')


def test_dashboard_overview_placeholder_range_query_contract():
    default_payload = client.get('/internal/api/overview').json()

    r_7d = client.get('/internal/api/overview?range=7d')
    assert r_7d.status_code == 200
    payload_7d = r_7d.json()
    assert payload_7d['range'] == '7d'

    r_30d = client.get('/internal/api/overview?range=30d')
    assert r_30d.status_code == 200
    payload_30d = r_30d.json()
    assert payload_30d['range'] == '30d'

    assert payload_7d['requests'] > default_payload['requests']
    assert payload_30d['requests'] > payload_7d['requests']


def test_dashboard_overview_invalid_range_rejected():
    r = client.get('/internal/api/overview?range=1y')
    assert r.status_code == 422


def test_dashboard_metrics_placeholder_api_payload():
    r = client.get('/internal/api/metrics')
    assert r.status_code == 200

    payload = r.json()
    assert payload['source'] == 'placeholder'
    assert payload['range'] == '24h'
    assert payload['summary']['requests'] > 0
    assert payload['summary']['p95LatencyMs'] > 0

    assert isinstance(payload['requestTrend'], list)
    assert payload['requestTrend'][0]['bucket']
    assert payload['requestTrend'][0]['requests'] > 0

    assert isinstance(payload['statusBreakdown'], list)
    assert payload['statusBreakdown'][0]['status'] in ('2xx', '4xx', '5xx')
    assert payload['statusBreakdown'][0]['requests'] > 0

    assert isinstance(payload['latencyBuckets'], list)
    assert payload['latencyBuckets'][0]['bucket']
    assert payload['latencyBuckets'][0]['requests'] > 0

    assert isinstance(payload['topEndpoints'], list)
    assert payload['topEndpoints'][0]['path'].startswith('/v1/')


def test_dashboard_metrics_placeholder_range_query_contract():
    default_payload = client.get('/internal/api/metrics').json()

    r_7d = client.get('/internal/api/metrics?range=7d')
    assert r_7d.status_code == 200
    payload_7d = r_7d.json()
    assert payload_7d['range'] == '7d'

    r_30d = client.get('/internal/api/metrics?range=30d')
    assert r_30d.status_code == 200
    payload_30d = r_30d.json()
    assert payload_30d['range'] == '30d'

    assert payload_7d['summary']['requests'] > default_payload['summary']['requests']
    assert payload_30d['summary']['requests'] > payload_7d['summary']['requests']


def test_dashboard_metrics_invalid_range_rejected():
    r = client.get('/internal/api/metrics?range=1y')
    assert r.status_code == 422


def test_dashboard_activity_api_payload():
    r = client.get('/internal/api/activity')
    assert r.status_code == 200

    payload = r.json()
    assert payload['source'] == 'placeholder'
    assert isinstance(payload['events'], list)
    first = payload['events'][0]
    assert first['actor']
    assert first['action']
    assert first['status'] in ('success', 'info', 'error')
    assert first['target']


def test_dashboard_activity_filter_status_contract():
    r = client.get('/internal/api/activity?status=error')
    assert r.status_code == 200
    payload = r.json()
    assert payload['events']
    assert all(event['status'] == 'error' for event in payload['events'])


def test_dashboard_activity_filter_action_contract():
    r = client.get('/internal/api/activity?action=RoTaTe')
    assert r.status_code == 200
    payload = r.json()
    assert payload['events']
    assert all('rotate' in event['action'].lower() for event in payload['events'])


def test_dashboard_activity_filter_limit_bounds_contract():
    r = client.get('/internal/api/activity?limit=1')
    assert r.status_code == 200
    payload = r.json()
    assert len(payload['events']) == 1

    too_low = client.get('/internal/api/activity?limit=0')
    assert too_low.status_code == 422

    too_high = client.get('/internal/api/activity?limit=101')
    assert too_high.status_code == 422


def test_dashboard_activity_filter_invalid_status_rejected():
    r = client.get('/internal/api/activity?status=warn')
    assert r.status_code == 422


def test_dashboard_keys_api_payload():
    r = client.get('/internal/api/keys')
    assert r.status_code == 200

    payload = r.json()
    assert payload['source'] == 'mock-store'
    assert isinstance(payload['keys'], list)
    assert payload['keys'][0]['prefix'].startswith('yf_')
    assert '••' in payload['keys'][0]['prefix']


def test_dashboard_key_lifecycle_contracts():
    create = client.post('/internal/api/keys/create', json={'label': 'CI worker', 'env': 'test'})
    assert create.status_code == 200
    create_payload = create.json()
    assert create_payload['ok'] is True
    assert create_payload['action'] == 'create'
    assert create_payload['source'] == 'mock-store'

    created_key = create_payload['data']['key']
    assert created_key['label'] == 'CI worker'
    assert created_key['env'] == 'test'
    assert created_key['active'] is True
    key_id = created_key['id']

    rotate = client.post(f'/internal/api/keys/{key_id}/rotate')
    assert rotate.status_code == 200
    rotate_payload = rotate.json()
    assert rotate_payload['ok'] is True
    assert rotate_payload['action'] == 'rotate'
    assert rotate_payload['data']['key']['id'] == key_id

    revoke = client.post(f'/internal/api/keys/{key_id}/revoke')
    assert revoke.status_code == 200
    revoke_payload = revoke.json()
    assert revoke_payload['ok'] is True
    assert revoke_payload['action'] == 'revoke'
    assert revoke_payload['data']['key']['active'] is False

    activate = client.post(f'/internal/api/keys/{key_id}/activate')
    assert activate.status_code == 200
    activate_payload = activate.json()
    assert activate_payload['ok'] is True
    assert activate_payload['action'] == 'activate'
    assert activate_payload['data']['key']['active'] is True


def test_dashboard_key_lifecycle_missing_key_contract():
    missing = client.post('/internal/api/keys/does_not_exist/revoke')
    assert missing.status_code == 404
    payload = missing.json()['detail']
    assert payload['ok'] is False
    assert payload['action'] == 'revoke'
    assert payload['error']['code'] == 'KEY_NOT_FOUND'
