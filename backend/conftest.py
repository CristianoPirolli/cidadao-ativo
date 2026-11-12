"""Fixtures compartilhadas pela suíte de testes."""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User, UserType
from apps.reports.models import Report

MUNICIPIO = {'id': 4205407, 'nome': 'Florianópolis', 'uf': 'SC'}


def make_png(name='foto.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), color='red').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


@pytest.fixture
def png_file():
    return make_png()


@pytest.fixture
def citizen(db):
    user = User(
        name='Maria Cidadã',
        email='maria@example.com',
        user_type=UserType.CITIZEN,
        cpf='52998224725',
        is_approved=True,
        municipio_origem_id=MUNICIPIO['id'],
        municipio_origem_nome=MUNICIPIO['nome'],
        municipio_origem_uf=MUNICIPIO['uf'],
    )
    user.set_password('senha-forte-123')
    user.save()
    return user


@pytest.fixture
def other_citizen(db):
    user = User(
        name='João Vizinho',
        email='joao@example.com',
        user_type=UserType.CITIZEN,
        cpf='11144477735',
        is_approved=True,
        municipio_origem_id=MUNICIPIO['id'],
        municipio_origem_nome=MUNICIPIO['nome'],
        municipio_origem_uf=MUNICIPIO['uf'],
    )
    user.set_password('senha-forte-123')
    user.save()
    return user


@pytest.fixture
def agency(db):
    user = User(
        name='Prefeitura',
        email='prefeitura@example.com',
        user_type=UserType.AGENCY,
        cnpj='11222333000181',
        orgao_nome='Prefeitura de Florianópolis',
        is_approved=True,
        municipio_ibge_id=MUNICIPIO['id'],
        municipio_nome=MUNICIPIO['nome'],
        municipio_uf=MUNICIPIO['uf'],
    )
    user.set_password('senha-forte-123')
    user.save()
    return user


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email='admin@example.com', name='Admin', password='senha-forte-123')


@pytest.fixture
def owner(db):
    return User.objects.create_superuser(email='owner@test.com', name='Dono', password='senha-forte-123')


@pytest.fixture
def report(citizen, agency):
    return Report.objects.create(
        title='Poste apagado',
        description='Poste sem luz há uma semana',
        category='iluminacao',
        lat=-27.5954,
        lng=-48.5480,
        user=citizen,
        assigned_user=agency,
        municipio_ibge_id=MUNICIPIO['id'],
        municipio_nome=MUNICIPIO['nome'],
        municipio_uf=MUNICIPIO['uf'],
    )


@pytest.fixture
def csrf_client():
    """Cliente que valida CSRF, como em produção."""
    from django.test import Client

    return Client(enforce_csrf_checks=True)
