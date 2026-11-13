"""
Configurações base do projeto Cidadão Ativo.

Compartilhadas entre todos os ambientes. Ajustes específicos ficam em
``development.py``, ``production.py`` e ``test.py``.
"""
import os
from pathlib import Path

from django.contrib.messages import constants as message_constants
from dotenv import load_dotenv

# backend/config/settings/base.py → backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Raiz do repositório (contém backend/ e frontend/)
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = Path(os.environ.get('FRONTEND_DIR', PROJECT_ROOT / 'frontend'))

load_dotenv(PROJECT_ROOT / '.env')


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


# ── Segurança ──────────────────────────────────────────────────────────────
SECRET_KEY = env('DJANGO_SECRET_KEY', 'insecure-dev-key-change-me')
DEBUG = env_bool('DJANGO_DEBUG', False)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000')

# ── Aplicações ─────────────────────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.locations',
    'apps.reports',
    'apps.ouvidoria',
    'apps.dashboards',
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [FRONTEND_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.map_settings',
            ],
        },
    },
]

# ── Banco de dados (PostgreSQL) ────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB', 'cidadao_ativo'),
        'USER': env('POSTGRES_USER', 'cidadao_ativo'),
        'PASSWORD': env('POSTGRES_PASSWORD', 'cidadao_ativo'),
        'HOST': env('POSTGRES_HOST', 'localhost'),
        'PORT': env('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': int(env('POSTGRES_CONN_MAX_AGE', '60')),
        'CONN_HEALTH_CHECKS': True,
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Autenticação ───────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'index'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internacionalização ────────────────────────────────────────────────────
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# ── Arquivos estáticos e uploads ───────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [FRONTEND_DIR / 'static']
STATIC_ROOT = Path(env('DJANGO_STATIC_ROOT', BASE_DIR / 'staticfiles'))

MEDIA_URL = '/uploads/'
MEDIA_ROOT = Path(env('DJANGO_MEDIA_ROOT', BASE_DIR / 'media'))

# Diretório para dados gerados em runtime (ex.: cache de municípios do IBGE)
DATA_DIR = Path(env('DJANGO_DATA_DIR', BASE_DIR / 'var'))

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

# Serve /uploads/ pelo próprio Django (útil sem proxy reverso). Em produção o
# Nginx serve esses arquivos e esta opção fica desligada.
SERVE_MEDIA = env_bool('DJANGO_SERVE_MEDIA', False)

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

REPORT_IMAGE_MAX_SIZE_MB = 10
RESIDENCE_PROOF_MAX_SIZE = 5 * 1024 * 1024
RESIDENCE_PROOF_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
RESIDENCE_PROOF_TYPES = {
    'conta_luz': 'Conta de Luz',
    'conta_agua': 'Conta de Água',
    'conta_telefone': 'Conta de Telefone',
    'contrato_aluguel': 'Contrato de Aluguel',
    'declaracao': 'Declaração de Residência',
}

# ── Sessão e cookies ───────────────────────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60  # 1 hora
CSRF_COOKIE_SAMESITE = 'Lax'

# ── E-mail ─────────────────────────────────────────────────────────────────
EMAIL_BACKEND = env('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(env('EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'noreply@cidadaoativo.com')

# ── Regras de negócio ──────────────────────────────────────────────────────
URGENCY_VOTE_MAX_DISTANCE_METERS = int(env('URGENCY_VOTE_MAX_DISTANCE_METERS', '200'))
PLATFORM_OWNER_EMAIL = (env('PLATFORM_OWNER_EMAIL') or '').strip().lower()
DEMO_PUBLIC_URL = env('DEMO_PUBLIC_URL')

# ── Mapas (Leaflet) ────────────────────────────────────────────────────────
# Provedor de tiles do mapa base. O padrão (Esri World Street Map) não exige
# chave. Para usar outro provedor (ex.: MapTiler, Stadia), defina a URL e a
# atribuição no .env.
MAP_TILE_URL = env(
    'MAP_TILE_URL',
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
)
MAP_TILE_ATTRIBUTION = env(
    'MAP_TILE_ATTRIBUTION',
    'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, &copy; OpenStreetMap contributors, and the GIS user community',
)
MAP_TILE_MAX_ZOOM = int(env('MAP_TILE_MAX_ZOOM', '19'))

# ── Mensagens → classes Bootstrap ──────────────────────────────────────────
MESSAGE_TAGS = {
    message_constants.DEBUG: 'secondary',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'danger',
}

# ── Logging ────────────────────────────────────────────────────────────────
LOG_LEVEL = env('DJANGO_LOG_LEVEL', 'INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'default'},
    },
    'root': {'handlers': ['console'], 'level': LOG_LEVEL},
    'loggers': {
        'django.db.backends': {'level': 'WARNING'},
    },
}
