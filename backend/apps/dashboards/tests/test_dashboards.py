import pytest
from django.urls import reverse


@pytest.mark.django_db
@pytest.mark.parametrize('fixture, target', [
    ('citizen', 'dashboard_citizen'),
    ('agency', 'dashboard_agency'),
    ('admin_user', 'dashboard_admin'),
])
def test_dashboard_redirects_by_role(client, request, fixture, target):
    client.force_login(request.getfixturevalue(fixture))
    response = client.get(reverse('dashboard'))
    assert response.url == reverse(target)


@pytest.mark.django_db
@pytest.mark.parametrize('fixture, url', [
    ('citizen', 'dashboard_citizen'),
    ('agency', 'dashboard_agency'),
    ('admin_user', 'dashboard_admin'),
    ('owner', 'dashboard_owner'),
])
def test_dashboards_render(client, request, report, fixture, url):
    client.force_login(request.getfixturevalue(fixture))
    assert client.get(reverse(url)).status_code == 200


@pytest.mark.django_db
def test_citizen_cannot_open_agency_dashboard(client, citizen):
    client.force_login(citizen)
    assert client.get(reverse('dashboard_agency')).status_code == 302


@pytest.mark.django_db
def test_incomplete_profile_shows_error_instead_of_loop(client, citizen):
    citizen.municipio_origem_id = None
    citizen.save()
    client.force_login(citizen)
    response = client.get(reverse('dashboard_citizen'))
    assert response.status_code == 409


def test_anonymous_redirected_to_login(client, db):
    response = client.get(reverse('dashboard'))
    assert response.status_code == 302
    assert reverse('login') in response.url
