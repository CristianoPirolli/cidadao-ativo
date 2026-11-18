import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.dashboards.views import CITIZEN_PAGE_SIZE
from apps.reports.models import Report, ReportUrgencyVote
from conftest import MUNICIPIO


def make_reports(user, n):
    Report.objects.bulk_create([
        Report(title=f'Chamado {i}', description='d', category='outros', lat=-27.59, lng=-48.54, user=user,
               municipio_ibge_id=MUNICIPIO['id'], municipio_nome=MUNICIPIO['nome'], municipio_uf=MUNICIPIO['uf'])
        for i in range(n)
    ])


def count_queries(client, url):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get(url).status_code == 200
    return len(ctx)


@pytest.mark.django_db
@pytest.mark.parametrize('fixture, url', [
    ('citizen', 'dashboard_citizen'),
    ('agency', 'dashboard_agency'),
    ('admin_user', 'dashboard_admin'),
])
def test_dashboard_queries_do_not_grow_with_reports(client, request, other_citizen, fixture, url):
    client.force_login(request.getfixturevalue(fixture))
    make_reports(other_citizen, 3)
    few = count_queries(client, reverse(url))
    make_reports(other_citizen, 40)
    assert count_queries(client, reverse(url)) == few


@pytest.mark.django_db
def test_citizen_dashboard_is_paginated(client, citizen, other_citizen):
    make_reports(other_citizen, CITIZEN_PAGE_SIZE + 5)
    client.force_login(citizen)
    first = client.get(reverse('dashboard_citizen'))
    assert len(first.context['reports']) == CITIZEN_PAGE_SIZE
    assert 'page=2' in first.content.decode()
    second = client.get(reverse('dashboard_citizen') + '?page=2')
    assert len(second.context['reports']) == 5


@pytest.mark.django_db
def test_vote_count_uses_annotation(client, citizen, other_citizen, report):
    ReportUrgencyVote.objects.create(report=report, user=other_citizen)
    client.force_login(citizen)
    page = client.get(reverse('dashboard_citizen')).context['reports']
    assert page[0].urgency_votes_count == 1
