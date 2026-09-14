# syntax=docker/dockerfile:1
FROM python:3.14-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN python -m venv /opt/poetry \
    && /opt/poetry/bin/pip install --no-cache-dir poetry==2.4.3
COPY pyproject.toml poetry.lock poetry.toml ./
RUN /opt/poetry/bin/poetry install --only main --no-root --no-interaction --no-ansi

FROM python:3.14-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" DJANGO_SETTINGS_MODULE=config.settings.production
WORKDIR /app
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app
COPY --from=builder /app/.venv /app/.venv
COPY . .
# Coleta estáticos sem ler .env, acessar banco ou fornecer segredos de runtime ao build.
RUN python - <<'PY'
import secrets
import django
from django.conf import settings
from django.core.management import call_command
settings.configure(
    SECRET_KEY=secrets.token_urlsafe(64),
    INSTALLED_APPS=[
        'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
        'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
        'drf_spectacular_sidecar',
    ],
    STATIC_URL='/static/', STATIC_ROOT='/app/staticfiles',
    STORAGES={'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    }},
)
django.setup()
call_command('collectstatic', interactive=False, verbosity=0)
PY
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=8s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request; r=urllib.request.Request('http://127.0.0.1:8000/health/ready/',headers={'Host':os.environ.get('DJANGO_ALLOWED_HOSTS','localhost').split(',')[0]}); urllib.request.urlopen(r,timeout=7).close()"
CMD ["gunicorn", "--config", "gunicorn.conf.py", "config.wsgi:application"]
