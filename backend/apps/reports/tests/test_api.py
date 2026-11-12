import json

import pytest
from django.urls import reverse

from apps.reports.models import Report, ReportHistory, ReportUrgencyVote
from apps.reports.services.geo import distance_meters
from conftest import MUNICIPIO


def test_distance_meters():
    assert distance_meters(0, 0, 0, 0) == 0
    assert 110_000 < distance_meters(0, 0, 1, 0) < 112_000


@pytest.mark.django_db
class TestCreateReport:
    def payload(self, **extra):
        data = {
            'title': 'Buraco na rua',
            'description': 'Buraco grande na via',
            'category': 'via_publica',
            'lat': '-27.59',
            'lng': '-48.54',
            'municipio_ibge_id': MUNICIPIO['id'],
            'municipio_nome': MUNICIPIO['nome'],
            'municipio_uf': MUNICIPIO['uf'],
        }
        data.update(extra)
        return data

    def test_requires_login(self, client):
        response = client.post(reverse('api_create_report'), self.payload())
        assert response.status_code == 302

    def test_requires_csrf_token(self, csrf_client, citizen):
        csrf_client.force_login(citizen)
        response = csrf_client.post(reverse('api_create_report'), self.payload())
        assert response.status_code == 403

    def test_creates_report_with_image(self, client, citizen, agency, png_file):
        client.force_login(citizen)
        response = client.post(reverse('api_create_report'), self.payload(image=png_file))
        assert response.status_code == 201
        report = Report.objects.get()
        assert report.assigned_user == agency
        assert report.image_path.endswith('.png')
        assert ReportHistory.objects.filter(report=report, action='criado').exists()

    def test_validates_required_fields(self, client, citizen):
        client.force_login(citizen)
        response = client.post(reverse('api_create_report'), {'title': 'x'})
        assert response.status_code == 400


@pytest.mark.django_db
class TestUrgencyVote:
    def vote(self, client, report, lat, lng):
        return client.post(
            reverse('api_vote_urgency', args=[report.id]),
            data=json.dumps({'lat': lat, 'lng': lng}),
            content_type='application/json',
        )

    def test_vote_near_report(self, client, other_citizen, report):
        client.force_login(other_citizen)
        response = self.vote(client, report, report.lat, report.lng)
        assert response.status_code == 201
        assert response.json()['urgency_votes_count'] == 1

    def test_vote_too_far(self, client, other_citizen, report):
        client.force_login(other_citizen)
        response = self.vote(client, report, report.lat + 1, report.lng)
        assert response.status_code == 403

    def test_cannot_vote_twice(self, client, other_citizen, report):
        ReportUrgencyVote.objects.create(report=report, user=other_citizen)
        client.force_login(other_citizen)
        response = self.vote(client, report, report.lat, report.lng)
        assert response.status_code == 409

    def test_cannot_vote_own_report(self, client, citizen, report):
        client.force_login(citizen)
        response = self.vote(client, report, report.lat, report.lng)
        assert response.status_code == 400


@pytest.mark.django_db
class TestUpdateStatus:
    def update(self, client, report, status):
        return client.post(
            reverse('api_update_report', args=[report.id]),
            data=json.dumps({'status': status, 'comment': 'ok'}),
            content_type='application/json',
        )

    def test_agency_updates_status(self, client, agency, report):
        client.force_login(agency)
        response = self.update(client, report, 'em_execucao')
        assert response.status_code == 200
        report.refresh_from_db()
        assert report.status == 'em_andamento'

    def test_citizen_cannot_update(self, client, citizen, report):
        client.force_login(citizen)
        assert self.update(client, report, 'resolvido').status_code == 403

    def test_invalid_status(self, client, agency, report):
        client.force_login(agency)
        assert self.update(client, report, 'xpto').status_code == 400


@pytest.mark.django_db
def test_stats_counts_by_category(client, report):
    data = client.get(reverse('api_stats')).json()['data']
    assert data['total'] == 1
    assert data['by_category']['iluminacao'] == 1
    assert data['by_category']['via_publica'] == 0


@pytest.mark.django_db
def test_report_detail_marks_viewed_for_agency(client, agency, report):
    client.force_login(agency)
    assert client.get(reverse('report_detail', args=[report.id])).status_code == 200
    report.refresh_from_db()
    assert report.viewed_at is not None


@pytest.mark.django_db
def test_citizen_from_other_city_cannot_see_report(client, other_citizen, report):
    other_citizen.municipio_origem_id = 1
    other_citizen.save()
    client.force_login(other_citizen)
    response = client.get(reverse('report_detail', args=[report.id]))
    assert response.status_code == 302


@pytest.mark.django_db
def test_report_list_requires_login(client, report):
    assert client.get(reverse('api_get_reports')).status_code == 302


@pytest.mark.django_db
def test_report_list_hides_author_email(client, agency, report):
    client.force_login(agency)
    data = client.get(reverse('api_get_reports')).json()['data']
    assert data[0]['id'] == report.id
    assert 'user_email' not in data[0]
