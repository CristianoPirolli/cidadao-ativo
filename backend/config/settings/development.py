"""Configurações para desenvolvimento local."""
from .base import *  # noqa: F401,F403
from .base import env_bool

DEBUG = env_bool('DJANGO_DEBUG', True)
SERVE_MEDIA = env_bool('DJANGO_SERVE_MEDIA', True)
ALLOWED_HOSTS = ['*']

# Em desenvolvimento, e-mails são exibidos no console por padrão
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Sem manifest, para não exigir collectstatic durante o desenvolvimento
STORAGES = {
    **STORAGES,  # noqa: F405
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

# WhiteNoise lê os arquivos direto de frontend/static/ (sem collectstatic)
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
