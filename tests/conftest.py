"""
Fixtures de teste compartilhadas
"""
import pytest
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.models import User, Report
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Cria uma instância do app para testes"""
    app = create_app('testing')

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Cliente de teste"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner para testes"""
    return app.test_cli_runner()


from types import SimpleNamespace


@pytest.fixture
def admin_user(app):
    """Cria e mantém um usuário admin ativo durante o teste"""
    with app.app_context():
        user = User(
            name='Admin Test',
            email='admin@test.com',
            password_hash=generate_password_hash('password123'),
            user_type='admin',
            is_admin=True,
            is_active=True,
            is_approved=True
        )
        db.session.add(user)
        db.session.commit()
        admin_id = user.id

    yield SimpleNamespace(id=admin_id)


@pytest.fixture
def sample_report(app):
    """Cria um report de exemplo e mantém o contexto ativo"""
    with app.app_context():
        report = Report(
            title='Buraco na rua',
            description='Grande buraco na Rua Teste',
            category='Vias',
            lat=-23.55,
            lng=-46.63,
            status='aberto'
        )
        db.session.add(report)
        db.session.commit()
        report_id = report.id

    yield SimpleNamespace(id=report_id)


@pytest.fixture
def auth_client(client, admin_user):
    """Cliente autenticado"""
    with client:
        client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        yield client
