"""
Configurações do aplicativo Cidadão Ativo
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuração base"""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Uploads
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'app', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Comprovantes de residência
    RESIDENCE_PROOF_MAX_SIZE = 5 * 1024 * 1024  # 5MB
    RESIDENCE_PROOF_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
    RESIDENCE_PROOF_TYPES = {
        'conta_luz': 'Conta de Luz',
        'conta_agua': 'Conta de Água',
        'conta_telefone': 'Conta de Telefone',
        'contrato_aluguel': 'Contrato de Aluguel',
        'declaracao': 'Declaração de Residência'
    }

    # Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'

    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Não expirar tokens CSRF

    # Timezone
    TIMEZONE = 'America/Sao_Paulo'  # UTC-3 (horário de São Paulo)


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True  # Log SQL queries

    # Limites mais relaxados em dev
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    TESTING = False

    # Security extra para produção
    SESSION_COOKIE_SECURE = True  # HTTPS only

    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/cidadao_ativo.log'

    def __init__(self):
        super().__init__()
        # Validações extras (só executam se ProductionConfig for usada)
        if not os.environ.get('SECRET_KEY') or os.environ.get('SECRET_KEY') == 'dev-secret':
            raise ValueError("SECRET_KEY deve ser configurada em produção!")

        if not os.environ.get('SQLALCHEMY_DATABASE_URI'):
            raise ValueError("SQLALCHEMY_DATABASE_URI deve ser configurada!")


class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    DEBUG = True

    # Banco de dados em memória para testes
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Desabilitar CSRF em testes
    WTF_CSRF_ENABLED = False

    # Desabilitar rate limiting
    RATELIMIT_ENABLED = False


class DemoConfig(Config):
    """Configuração para demonstrações (Mostra Tech)"""
    DEBUG = False
    TESTING = False

    # Segurança ajustada para demo pública
    SESSION_COOKIE_SECURE = False  # ngrok usa HTTPS mas o Flask serve HTTP local
    SQLALCHEMY_ECHO = False  # Não poluir logs durante demo

    # Rate limiting mais permissivo para demonstração
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "500 per hour, 100 per minute"  # Mais generoso para visitantes

    # Logging
    LOG_LEVEL = 'WARNING'  # Apenas erros importantes

    # URL pública do ngrok (será preenchida pelo script)
    DEMO_PUBLIC_URL = os.environ.get('DEMO_PUBLIC_URL', None)


# Mapa de configurações
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'demo': DemoConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """Retorna a configuração apropriada baseada no ambiente"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')

    return config_map.get(env, DevelopmentConfig)
