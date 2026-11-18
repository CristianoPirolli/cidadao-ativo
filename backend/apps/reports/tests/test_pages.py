import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_report_detail_has_map_and_readable_labels(client, agency, report):
    client.force_login(agency)
    html = client.get(reverse('report_detail', args=[report.id])).content.decode()
    assert 'data-static-map' in html
    assert 'data-lat="-27.595400"' in html  # ponto decimal mesmo em pt-BR
    assert 'Iluminação' in html  # nome da categoria, não o código
    assert 'id="report-manage-form"' in html
    assert '<option value="em_andamento"' in html


@pytest.mark.django_db
def test_report_form_lists_categories(client, citizen):
    client.force_login(citizen)
    html = client.get(reverse('denuncia')).content.decode()
    assert 'id="report-map-picker"' in html
    assert '<option value="via_publica"' in html


@pytest.mark.django_db
def test_admin_edit_page_keeps_logged_user_in_navigation(client, admin_user, citizen):
    client.force_login(admin_user)
    response = client.get(reverse('edit_user_by_admin', args=[citizen.id]))
    assert response.context['user'] == admin_user
    assert response.context['target'] == citizen
