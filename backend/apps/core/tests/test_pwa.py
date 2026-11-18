import json

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_manifest_describes_installable_app(client):
    response = client.get(reverse('manifest'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/manifest+json'
    data = json.loads(response.content)
    assert data['display'] == 'standalone'
    assert data['scope'] == '/'
    assert {icon['sizes'] for icon in data['icons']} >= {'192x192', '512x512'}
    assert any(icon.get('purpose') == 'maskable' for icon in data['icons'])


@pytest.mark.django_db
def test_service_worker_is_served_from_root(client):
    response = client.get('/sw.js')
    assert response.status_code == 200
    assert response['Content-Type'].startswith('application/javascript')
    assert response['Service-Worker-Allowed'] == '/'
    body = response.content.decode()
    assert '/offline' in body
    assert 'vendor/bootstrap/bootstrap.min.css' in body


@pytest.mark.django_db
def test_offline_page_renders(client):
    response = client.get(reverse('offline'))
    assert response.status_code == 200
    assert 'sem internet' in response.content.decode()


@pytest.mark.django_db
def test_pages_use_local_assets_and_manifest(client):
    html = client.get('/login').content.decode()
    assert 'rel="manifest"' in html
    assert 'cdn.jsdelivr.net' not in html and 'unpkg.com' not in html
