"""Configuração usada pelos testes automatizados (pytest/CI)."""

import os
import tempfile

os.environ.setdefault("DJANGO_SECRET_KEY", "chave-somente-para-testes")
os.environ.setdefault("DJANGO_DEBUG", "0")

from .settings import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # apenas acelera os testes
MEDIA_ROOT = tempfile.mkdtemp(prefix="acessasus-media-")
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = ["*"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
