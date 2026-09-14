from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env()

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY.strip():
    raise ImproperlyConfigured("DJANGO_SECRET_KEY não pode ser vazia.")

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "core",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "professionals",
    "appointments",
    "django_filters",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "drf_spectacular_sidecar",
]

MIDDLEWARE = [
    "core.middleware.RequestLoggingMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "core.middleware.APIErrorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "connect_timeout": env.int("POSTGRES_CONNECT_TIMEOUT", default=5),
            "sslmode": env("POSTGRES_SSLMODE", default="prefer"),
        },
    }
}
for field in ("NAME", "USER", "PASSWORD", "HOST"):
    if not DATABASES["default"][field].strip():
        raise ImproperlyConfigured(f"Configuração PostgreSQL obrigatória vazia: {field}.")
if sslrootcert := env("POSTGRES_SSLROOTCERT", default=""):
    DATABASES["default"]["OPTIONS"]["sslrootcert"] = sslrootcert

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
CORS_URLS_REGEX = r"^/api/.*$"
CORS_EXPOSE_HEADERS = ["X-Request-ID"]
DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
SECURE_REFERRER_POLICY = "no-referrer"

APPEND_SLASH = False
VIACEP_BASE_URL = "https://viacep.com.br/ws"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_RATES": {"auth": "10/min", "postal_code": "30/min"},
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Não confiar em X-Forwarded-For sem uma topologia de proxy validada.
    "NUM_PROXIES": 0,
}

JWT_SIGNING_KEY = env("DJANGO_JWT_SIGNING_KEY")
if len(JWT_SIGNING_KEY) < 50 or len(set(JWT_SIGNING_KEY)) < 5 or JWT_SIGNING_KEY == SECRET_KEY:
    raise ImproperlyConfigured("Defina DJANGO_JWT_SIGNING_KEY forte e diferente da SECRET_KEY.")

SIMPLE_JWT = {
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
}

SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    "TITLE": "Elo Saúde API",
    "DESCRIPTION": "Profissionais, consultas e busca auxiliar por CEP. Domínio protegido por JWT.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": False},
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "core.schema.document_errors",
    ],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"console": {"()": "core.logging.SafeJSONFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "console"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
    "loggers": {
        "httpx": {"level": "WARNING"},
        "gunicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "gunicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
