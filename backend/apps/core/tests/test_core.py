from datetime import UTC, datetime

import pytest

from apps.core.services.cpf import validate_cpf
from apps.core.services.files import secure_filename, validate_image_file
from apps.core.templatetags.custom_filters import format_datetime_sp, format_duration, tojson
from conftest import make_png


@pytest.mark.django_db
def test_healthcheck_reports_database_ok(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'database': 'ok'}


def test_welcome_page_is_public(client, db):
    assert client.get('/').status_code == 200


@pytest.mark.parametrize('cpf, valid', [
    ('529.982.247-25', True),
    ('52998224725', True),
    ('111.111.111-11', False),
    ('123', False),
])
def test_validate_cpf(cpf, valid):
    assert validate_cpf(cpf)['valid'] is valid


def test_secure_filename_strips_paths():
    assert secure_filename('../../etc/passwd') == 'passwd'
    assert secure_filename('minha foto.png') == 'minha_foto.png'
    assert secure_filename('..') == 'arquivo'


def test_validate_image_file_accepts_png():
    result = validate_image_file(make_png())
    assert result['valid'] is True


def test_tojson_escapes_html():
    assert '<' not in tojson('</script>')


def test_format_datetime_sp_converts_timezone():
    value = datetime(2026, 1, 1, 15, 0, tzinfo=UTC)
    assert format_datetime_sp(value) == '01/01/2026 12:00'


def test_format_duration():
    assert format_duration(30) == '30s'
    assert format_duration(3660) == '1h 1min'


@pytest.mark.django_db
@pytest.mark.parametrize('url', ['/login', '/register', '/qr-demo'])
def test_public_pages_render(client, url):
    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_authenticated_pages_render(client, admin_user, citizen):
    client.force_login(admin_user)
    assert client.get(f'/admin/users/{citizen.id}/edit').status_code == 200
    client.force_login(citizen)
    assert client.get('/denuncia').status_code == 200
