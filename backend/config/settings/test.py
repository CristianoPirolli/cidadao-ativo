"""Configurações para a suíte de testes (PostgreSQL também)."""
import tempfile
from pathlib import Path

from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = 'test-secret-key'
ALLOWED_HOSTS = ['*']
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
MEDIA_ROOT = Path(tempfile.mkdtemp(prefix='cidadao-media-'))
DATA_DIR = Path(tempfile.mkdtemp(prefix='cidadao-data-'))
STORAGES = {
    **STORAGES,  # noqa: F405
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
PLATFORM_OWNER_EMAIL = 'owner@test.com'
STATIC_ROOT = Path(tempfile.mkdtemp(prefix='cidadao-static-'))
