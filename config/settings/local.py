from pathlib import Path

import environ

# O ambiente do processo tem precedência sobre o .env local.
environ.Env.read_env(Path(__file__).resolve().parents[2] / ".env", overwrite=False)

from .base import *
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
