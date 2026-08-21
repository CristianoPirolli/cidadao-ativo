"""
Testes para os modelos de dados
"""
import pytest
from app.models.models import User, Report
from werkzeug.security import check_password_hash, generate_password_hash


class TestUserModel:
    """Testes para o modelo User"""

    def test_create_user(self, app):
        """Testa criação de usuário"""
        with app.app_context():
            from app import db

            user = User(
                name='Test User',
                email='test@example.com',
                password_hash=generate_password_hash('password')
            )
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.name == 'Test User'
            assert user.email == 'test@example.com'
            assert user.is_active is True

    def test_user_password_hashing(self, app):
        """Testa hash de senha"""
        with app.app_context():
            password = 'my_secret_password'
            hashed = generate_password_hash(password)

            assert hashed != password
            assert check_password_hash(hashed, password)
            assert not check_password_hash(hashed, 'wrong_password')

    def test_user_to_dict(self, admin_user, app):
        """Testa serialização para dict"""
        with app.app_context():
            from app.models.models import User
            user = User.query.get(admin_user.id)
            user_dict = user.to_dict()

            assert 'id' in user_dict
            assert 'name' in user_dict
            assert 'email' in user_dict
            assert 'password_hash' not in user_dict  # Nunca expor senha

    def test_user_unique_email(self, app):
        """Testa constraint de email único"""
        with app.app_context():
            from app import db

            user1 = User(
                name='User 1',
                email='same@email.com',
                password_hash=generate_password_hash('pass1')
            )
            db.session.add(user1)
            db.session.commit()

            # Tentar criar outro usuário com mesmo email
            user2 = User(
                name='User 2',
                email='same@email.com',
                password_hash=generate_password_hash('pass2')
            )
            db.session.add(user2)

            with pytest.raises(Exception):  # Violação de constraint
                db.session.commit()


class TestReportModel:
    """Testes para o modelo Report"""

    def test_create_report(self, app):
        """Testa criação de report"""
        with app.app_context():
            from app import db

            report = Report(
                title='Buraco na via',
                description='Buraco grande',
                category='Vias',
                lat=-23.55,
                lng=-46.63
            )
            db.session.add(report)
            db.session.commit()

            assert report.id is not None
            assert report.status == 'aberto'  # Status padrão
            assert report.created_at is not None

    def test_report_to_dict(self, sample_report, app):
        """Testa serialização para dict"""
        with app.app_context():
            from app.models.models import Report
            report = Report.query.get(sample_report.id)
            report_dict = report.to_dict()

            assert report_dict['id'] == report.id
            assert report_dict['title'] == report.title
            assert report_dict['status'] == 'aberto'
            assert 'created_at' in report_dict

    def test_report_status_display(self, sample_report, app):
        """Testa propriedade status_display"""
        with app.app_context():
            from app.models.models import Report
            report = Report.query.get(sample_report.id)

            assert report.status_display == 'Aberto'

            report.status = 'em_execucao'
            assert report.status_display == 'Em Execução'

            report.status = 'resolvido'
            assert report.status_display == 'Resolvido'

    def test_report_status_color(self, sample_report, app):
        """Testa propriedade status_color"""
        with app.app_context():
            from app.models.models import Report
            report = Report.query.get(sample_report.id)

            assert report.status_color == 'danger'

            report.status = 'em_execucao'
            assert report.status_color == 'warning'

            report.status = 'resolvido'
            assert report.status_color == 'success'
