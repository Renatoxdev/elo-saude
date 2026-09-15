#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
python manage.py migrate --noinput
exec gunicorn --config gunicorn.conf.py --bind "0.0.0.0:${PORT:-8000}" config.wsgi:application
