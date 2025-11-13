from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_mail import Mail
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

# Inicializar extensões
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def create_app(config_name='development'):
    """Application Factory Pattern"""
    app = Flask(__name__)

    # Importar e aplicar configuração da classe Config
    from config import get_config
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Garantir que o diretório de uploads exista
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    # Configurações de email (não estão no Config, então mantém aqui)
    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "True") == "True"
    app.config["MAIL_USE_SSL"] = os.environ.get("MAIL_USE_SSL", "False") == "True"
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@cidadaoativo.com")

    # Inicializar extensões
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Configurar Flask-Login
    login_manager.login_view = 'views.login'
    login_manager.login_message = 'Faça login para acessar esta página'
    login_manager.login_message_category = 'warning'
    login_manager.session_protection = 'strong'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.models import User
        return User.query.get(int(user_id))

    # Registrar filtros Jinja2 customizados
    from app.utils.timezone import format_datetime_sp
    app.jinja_env.filters['format_datetime_sp'] = format_datetime_sp

    # Configurar logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/cidadao_ativo.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Cidadão Ativo startup')

    # Registrar blueprints
    from app.controllers.view_routes import views_bp
    from app.controllers.api_routes import api_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)

    # Rota para servir uploads (com proteção CSRF desabilitada)
    @app.route('/uploads/<path:filename>')
    @csrf.exempt
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Comandos CLI
    @app.cli.command("init-db")
    def init_db():
        """Cria as tabelas do banco MySQL."""
        db.create_all()
        print("[OK] Banco inicializado com sucesso.")

    @app.cli.command("create-admin")
    def create_admin():
        """Cria um usuário administrador"""
        from app.models.models import User
        from werkzeug.security import generate_password_hash

        email = input("Email do admin: ")
        name = input("Nome do admin: ")
        password = input("Senha: ")

        if User.query.filter_by(email=email).first():
            print("[ERRO] Este email ja esta cadastrado")
            return

        admin = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            user_type='admin',
            is_admin=True,
            is_approved=True,  # Admin não precisa de aprovação
            is_active=True
        )

        db.session.add(admin)
        db.session.commit()
        print(f"[OK] Admin {name} criado com sucesso!")
        print(f"   Email: {email}")
        print(f"   Acesso: http://localhost:5000/login")

    @app.cli.command("create-dev-admin")
    def create_dev_admin():
        """Cria o usuário admin desenvolvedor padrão"""
        from app.models.models import User
        from werkzeug.security import generate_password_hash

        # Dados do admin desenvolvedor
        email = "admin@cidadaoativo.com"
        name = "Administrador Desenvolvedor"
        password = "admin123"  # ALTERAR EM PRODUÇÃO!

        if User.query.filter_by(email=email).first():
            print("[ERRO] Admin desenvolvedor ja existe!")
            existing = User.query.filter_by(email=email).first()
            print(f"   Email: {existing.email}")
            print(f"   Nome: {existing.name}")
            return

        admin = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            user_type='admin',
            is_admin=True,
            is_approved=True,
            is_active=True
        )

        db.session.add(admin)
        db.session.commit()

        print("[OK] Admin desenvolvedor criado com sucesso!")
        print(f"   Email: {email}")
        print(f"   Senha: {password}")
        print(f"   Acesso: http://localhost:5000/login")
        print("")
        print("[AVISO] IMPORTANTE: Altere a senha apos o primeiro login!")

    # Handler de erros
    @app.errorhandler(404)
    def not_found_error(error):
        return {"error": "Recurso não encontrado"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {"error": "Erro interno do servidor"}, 500

    return app

# Para compatibilidade com o código antigo
app = create_app(os.environ.get('FLASK_ENV', 'development'))
