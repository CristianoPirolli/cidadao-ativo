"""Configurações para produção (Docker + Nginx)."""
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import env, env_bool

DEBUG = False

SECRET_KEY = env('DJANGO_SECRET_KEY')
if not SECRET_KEY or SECRET_KEY.startswith('insecure'):
    raise ImproperlyConfigured('Defina DJANGO_SECRET_KEY com um valor seguro em produção.')

# Atrás do Nginx
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Ative quando a aplicação estiver servida via HTTPS
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', False)
SESSION_COOKIE_SECURE = env_bool('DJANGO_SECURE_COOKIES', False)
CSRF_COOKIE_SECURE = env_bool('DJANGO_SECURE_COOKIES', False)
SECURE_HSTS_SECONDS = int(env('DJANGO_SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
