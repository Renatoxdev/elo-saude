import os

from django.conf import settings

bind = "0.0.0.0:8000"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
timeout = 30
graceful_timeout = 30
worker_tmp_dir = "/tmp"
accesslog = None  # O middleware registra acesso sem URLs ou query strings.
errorlog = "-"
logconfig_dict = settings.LOGGING
forwarded_allow_ips = ""  # Confiança no proxy é configurada explicitamente no Django.
