from django.core.exceptions import ImproperlyConfigured

from .base import *

if env.bool("DJANGO_DEBUG", default=False):
    raise ImproperlyConfigured("DJANGO_DEBUG deve ser false em staging e produção.")
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("Use uma DJANGO_SECRET_KEY forte em staging e produção.")
if not ALLOWED_HOSTS or any(not host.strip() or "*" in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("Defina DJANGO_ALLOWED_HOSTS explicitamente, sem curingas.")
if DATABASES["default"]["OPTIONS"]["sslmode"] not in {"require", "verify-ca", "verify-full"}:
    raise ImproperlyConfigured("Staging e produção exigem conexão PostgreSQL com TLS.")

DEBUG = False
SECURE_SSL_REDIRECT = True
# Probes internos não carregam dados nem credenciais e não dependem do terminador TLS.
SECURE_REDIRECT_EXEMPT = [r"^health/(live|ready)/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# O proxy deve remover o cabeçalho do cliente e definir seu próprio valor.
if env.bool("DJANGO_TRUST_PROXY_SSL_HEADER", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
